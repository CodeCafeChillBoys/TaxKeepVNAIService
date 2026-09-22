import os
import json
import uuid
import logging
import base64
import mimetypes
import httpx
import aio_pika
from datetime import datetime, timezone

from app.infrastructure.database import get_db_context
from app.repositories.expense_ocr import ExpenseOcrRepository
from app.repositories.system_config import SystemConfigRepository
from app.schemas.expense_ocr.expense_ocr_schema import (
    AdminCategoryItem,
    GeminiOcrOutput
)
from app.services.expense_ocr.expense_ocr_service import ExpenseOcrService
from app.messaging.expense_ocr.producer import publish_expense_ocr_response
from app.enum.expense_document_enum import DocumentExtractionStatus
from app.errors.expense_ocr_errors import ExpenseOcrError, CorruptedFileError, UnreadableDocumentError

logger = logging.getLogger(__name__)


async def _get_file_bytes_and_mime(file_url: str = None, file_base64: str = None, filename: str = "invoice.jpg"):
    """Tải file từ URL, file local hoặc giải mã Base64 an toàn"""
    file_bytes = None
    mime_type = "image/jpeg"

    if file_base64:
        try:
            file_bytes = base64.b64decode(file_base64)
        except Exception as b64_err:
            raise CorruptedFileError(f"Chuỗi Base64 không hợp lệ hoặc bị hỏng: {str(b64_err)}")
    elif file_url:
        if file_url.startswith("http://") or file_url.startswith("https://"):
            try:
                async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                    file_resp = await client.get(file_url)
                    file_resp.raise_for_status()
                    file_bytes = file_resp.content
                    raw_content_type = file_resp.headers.get("content-type", "")
                    if raw_content_type:
                        mime_type = raw_content_type.split(";")[0].strip().lower()
            except httpx.HTTPError as http_err:
                raise CorruptedFileError(f"Không thể tải tệp từ fileUrl ({str(http_err)})")

    if not file_bytes or len(file_bytes) == 0:
        raise CorruptedFileError("Không thể lấy dữ liệu tệp tin hoặc tệp rỗng (0 bytes).")

    if not mime_type or mime_type == "application/octet-stream":
        guessed, _ = mimetypes.guess_type(filename or file_url or "")
        mime_type = guessed or "image/jpeg"

    return file_bytes, mime_type


async def handle_expense_ocr_job(message: aio_pika.IncomingMessage):
    """
    Lắng nghe message bóc tách hóa đơn chi phí từ .NET Backend
    Hàng đợi: expense.ocr.ai.request.queue
    """
    async with message.process(requeue=False, ignore_processed=True):
        raw_body = message.body.decode("utf-8")
        body = json.loads(raw_body)

        # 1. Hỗ trợ cả định dạng camelCase lẫn PascalCase từ C# .NET
        task_id = body.get("taskId") or body.get("TaskId") or body.get("id") or body.get("Id")
        period_id = body.get("periodId") or body.get("PeriodId")
        user_id = body.get("userId") or body.get("UserId")
        target_year = int(body.get("targetYear") or body.get("TargetYear") or 2026)
        file_url = body.get("fileUrl") or body.get("FileUrl")
        file_base64 = body.get("fileBase64") or body.get("FileBase64")
        original_filename = body.get("originalFilename") or body.get("OriginalFilename") or "invoice.jpg"

        # 2. Xử lý danh mục: Nhận danh mục động do .NET Backend truyền sang
        raw_categories = body.get("categories") or body.get("Categories") or []
        categories = [AdminCategoryItem(**c) for c in raw_categories]

        # 3. Ngưỡng tin cậy
        raw_threshold = (
            body.get("appliedThreshold") or body.get("AppliedThreshold") or
            body.get("threshold") or body.get("Threshold")
        )
        applied_threshold = float(raw_threshold) if raw_threshold is not None else None

        logger.info(
            f"Bắt đầu OCR ngầm cho Task {task_id}, Năm {target_year}, "
            f"Danh mục ({len(categories)} mục), Ngưỡng: {applied_threshold or 'DB tự động'}..."
        )

        try:
            # BƯỚC 1: Tải file từ Cloud Storage / S3 hoặc Base64
            file_bytes, mime_type = await _get_file_bytes_and_mime(
                file_url=file_url,
                file_base64=file_base64,
                filename=original_filename
            )

            # BƯỚC 2 & 3: Gọi AI bóc tách & Lưu Database
            with get_db_context() as db:
                config_repo = SystemConfigRepository(db)
                ocr_service = ExpenseOcrService(repo=config_repo)
                result = await ocr_service.extract_and_classify(
                    file_bytes=file_bytes,
                    mime_type=mime_type,
                    target_year=target_year,
                    categories=categories,
                    applied_threshold=applied_threshold
                )

                doc: GeminiOcrOutput = result["data"]

                # Lưu vào Database (2 bảng AI_EXTRACTIONS & AI_EXTRACTIONS_Value)
                expense_repo = ExpenseOcrRepository(db)
                expense_repo.save_extraction_result(
                    document_id=task_id,
                    overall_confidence=result["overall_confidence"],
                    applied_threshold=result["applied_threshold"],
                    is_passed_threshold=result["is_passed_threshold"],
                    raw_payload=result["raw_payload"],
                    field_details=doc.fields
                )

            # Xác định trạng thái nghiệp vụ và các lỗi theo chuẩn Spec
            errors = result.get("validation_errors", [])
            has_not_tax_doc_error = any(isinstance(err, dict) and err.get("code") == "ERR_NOT_TAX_DOCUMENT" for err in errors)
            has_year_error = any(isinstance(err, dict) and err.get("code") == "ERR_YEAR_MISMATCH" for err in errors)
            has_doc_type_error = any(isinstance(err, dict) and err.get("code") == "ERR_INVALID_DOC_TYPE" for err in errors)
            has_future_date_error = any(isinstance(err, dict) and err.get("code") == "ERR_FUTURE_DATE" for err in errors)
            has_quality_error = any(isinstance(err, dict) and err.get("code") == "ERR_IMAGE_QUALITY_TOO_LOW" for err in errors)

            is_valid = (
                result["is_passed_threshold"]
                and result["is_year_valid"]
                and result["is_doc_type_valid"]
                and len(errors) == 0
            )

            if is_valid:
                doc_status = DocumentExtractionStatus.EXTRACTED
                response_message = "Document processed and validated successfully."
                status_code = 200
            else:
                doc_status = DocumentExtractionStatus.FAILED
                status_code = 422
                if has_not_tax_doc_error:
                    response_message = "Uploaded file is not recognized as a valid tax document."
                elif has_year_error:
                    response_message = "Validation failed: Document date does not match the active filing tax year."
                elif has_doc_type_error:
                    response_message = "Validation failed: Document type is not eligible for Personal Income Tax deductions."
                elif has_future_date_error:
                    response_message = "Invoice date cannot be greater than the current date."
                elif has_quality_error:
                    response_message = "Image quality is too low for accurate tax document extraction. Please capture or upload a clearer document."
                else:
                    response_message = "Validation failed for tax document."


            # BƯỚC 4: Đóng gói JSON trả về cho .NET Backend
            response_payload = {
                "statusCode": status_code,
                "message": response_message,
                "errors": errors if not is_valid else [],
                "data": {
                    "id": str(task_id),
                    "periodId": str(period_id) if period_id else None,
                    "userId": str(user_id) if user_id else None,
                    "docTypeCode": doc.docTypeCode,
                    "fileUrl": file_url,
                    "originalFilename": original_filename,
                    "invoiceSeries": doc.invoiceSeries,
                    "invoiceNumber": doc.invoiceNumber,
                    "invoiceDate": doc.invoiceDate,
                    "extractedYear": doc.extractedYear,
                    "sellerName": doc.sellerName,
                    "sellerTaxCode": doc.sellerTaxCode,
                    "sellerAddress": doc.sellerAddress,
                    "sellerPhone": doc.sellerPhone,
                    "buyerName": doc.buyerName,
                    "buyerTaxCode": doc.buyerTaxCode,
                    "buyerIdCard": doc.buyerIdCard,
                    "buyerAddress": doc.buyerAddress,
                    "paymentMethod": doc.paymentMethod,
                    "totalAmount": doc.totalAmount,
                    "totalAmountInWords": doc.totalAmountInWords,
                    "lookupUrl": doc.lookupUrl,
                    "lookupCode": doc.lookupCode,
                    "items": [item.model_dump() for item in doc.items] if hasattr(doc, "items") and doc.items else [],
                    "validationStatus": {
                        "isYearValid": result["is_year_valid"],
                        "isDocTypeValid": result["is_doc_type_valid"],
                        "isIdentityValid": True
                    },
                    "validationErrors": [err["message"] if isinstance(err, dict) else str(err) for err in errors],
                    "status": doc_status.value,
                    "createdAt": datetime.now(timezone.utc).isoformat()
                }
            }

            # BƯỚC 5: Bắn ngược sang queue response cho .NET
            await publish_expense_ocr_response(response_payload)
            logger.info(f"Đã xử lý xong Task {task_id} -> docTypeCode: {doc.docTypeCode}, Status: {doc_status.value} (HTTP {status_code})")

        except ExpenseOcrError as ocr_err:
            logger.warning(f"Lỗi nghiệp vụ OCR Task {task_id}: [{ocr_err.code}] {ocr_err.message}")
            fail_payload = {
                "statusCode": ocr_err.status_code,
                "message": ocr_err.message,
                "errors": [
                    {
                        "code": ocr_err.code,
                        "field": "file",
                        "message": ocr_err.message,
                        **ocr_err.details
                    }
                ],
                "data": {
                    "id": str(task_id) if task_id else None,
                    "periodId": str(period_id) if period_id else None,
                    "userId": str(user_id) if user_id else None,
                    "status": DocumentExtractionStatus.FAILED.value,
                    "validationErrors": [ocr_err.message]
                }
            }
            await publish_expense_ocr_response(fail_payload)

        except Exception as e:
            logger.error(f"Lỗi hệ thống bất ngờ tại Task {task_id}: {e}", exc_info=True)
            fail_payload = {
                "statusCode": 500,
                "message": f"Processing failed: {str(e)}",
                "errors": [{"code": "ERR_INTERNAL_SERVER", "message": str(e)}],
                "data": {
                    "id": str(task_id) if task_id else None,
                    "periodId": str(period_id) if period_id else None,
                    "userId": str(user_id) if user_id else None,
                    "status": DocumentExtractionStatus.FAILED.value,
                    "validationErrors": [str(e)]
                }
            }
            await publish_expense_ocr_response(fail_payload)