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

logger = logging.getLogger(__name__)


async def _get_file_bytes_and_mime(file_url: str = None, file_base64: str = None, filename: str = "invoice.jpg"):
    """Tải file từ URL, file local hoặc giải mã Base64 an toàn"""
    file_bytes = None
    mime_type = "image/jpeg"

    # file dưới dạng chuỗi binary
    if file_base64:
        file_bytes = base64.b64decode(file_base64)
    elif file_url:
        # 1. Nếu là HTTP / HTTPS URL
        if file_url.startswith("http://") or file_url.startswith("https://"):
            async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
                file_resp = await client.get(file_url)
                file_resp.raise_for_status()
                file_bytes = file_resp.content
                raw_content_type = file_resp.headers.get("content-type", "")
                if raw_content_type:
                    mime_type = raw_content_type.split(";")[0].strip().lower()

        
    if not file_bytes:
        raise ValueError("Không thể lấy dữ liệu file từ fileUrl hoặc fileBase64")

    # Nếu mime_type là octet-stream hoặc không rõ ràng, tự đoán từ tên file
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
        
        # 3. Ngưỡng tin cậy (nếu .NET truyền vào; nếu không có thì Service tự lấy từ DB SYSTEM_CONFIGS)
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

            # Xác định trạng thái nghiệp vụ:
            # - Chỉ khi tài liệu hợp lệ (đúng loại chứng từ, đúng năm quyết toán) và đọc rõ ràng đạt ngưỡng -> EXTRACTED (để User Review/Confirm)
            # - Nếu không đạt yêu cầu (sai năm, sai loại chứng từ, hoặc ảnh mờ không đạt ngưỡng) -> FAILED kèm thông báo bắt người dùng tải lại/nhập lại
            is_valid = (
                result["is_passed_threshold"]
                and result["is_year_valid"]
                and result["is_doc_type_valid"]
            )

            if is_valid:
                doc_status = DocumentExtractionStatus.EXTRACTED
                response_message = "Document processed and validated successfully."
            else:
                doc_status = DocumentExtractionStatus.FAILED
                error_msg = "; ".join(result["validation_errors"]) if result.get("validation_errors") else "Chứng từ không đạt yêu cầu hoặc không đọc rõ dữ liệu."
                response_message = f"Xử lý chứng từ thất bại: {error_msg}. Vui lòng kiểm tra, tải lại ảnh rõ nét hoặc nhập lại thủ công."

            # BƯỚC 4: Đóng gói JSON trả về cho .NET Backend
            response_payload = {
              "message": response_message,
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
                "validationErrors": result["validation_errors"],
                "status": doc_status.value,
                "createdAt": datetime.now(timezone.utc).isoformat()
              }
            }

            # BƯỚC 5: Bắn ngược sang queue response cho .NET
            await publish_expense_ocr_response(response_payload)
            logger.info(f"Đã xử lý xong Task {task_id} -> docTypeCode: {doc.docTypeCode}, Status: {doc_status.value}")

        except Exception as e:
            logger.error(f"Lỗi khi OCR task {task_id}: {e}", exc_info=True)
            fail_payload = {
                "message": f"Processing failed: {str(e)}",
                "data": {
                    "id": str(task_id) if task_id else None,
                    "periodId": str(period_id) if period_id else None,
                    "userId": str(user_id) if user_id else None,
                    "status": DocumentExtractionStatus.FAILED.value,
                    "validationErrors": [str(e)]
                }
            }
            await publish_expense_ocr_response(fail_payload)