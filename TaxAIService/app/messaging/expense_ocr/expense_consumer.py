import json
import uuid
import logging
import httpx
import aio_pika
from datetime import datetime, timezone
from app.infrastructure.database import get_db_context
from app.repositories.expense_ocr import ExpenseOcrRepository
from app.repositories.system_config import SystemConfigRepository
from app.schemas.expense_ocr.expense_ocr_schema import AdminCategoryItem, GeminiOcrOutput
from app.services.expense_ocr.expense_ocr_service import ExpenseOcrService
from app.messaging.expense_ocr.producer import publish_expense_ocr_response
from app.enum.expense_document_enum import DocumentExtractionStatus 

logger = logging.getLogger(__name__)



async def handle_expense_ocr_job(message: aio_pika.IncomingMessage):
    """Lắng nghe message từ tax.ai.request.queue của .NET"""
    async with message.process(requeue=False, ignore_processed=True):
        raw_body = message.body.decode("utf-8")
        body = json.loads(raw_body)

        task_id = body["taskId"]               # Mã chứng từ
        period_id = body["periodId"]           # Mã Năm/Kỳ thuế
        user_id = body["userId"]               # Mã User
        target_year = body.get("targetYear", 2026)
        file_url = body["fileUrl"]

        original_filename = body.get("originalFilename", "invoice.jpg")
        
        # Danh mục động Admin gửi kèm
        raw_categories = body.get("categories", [])
        categories = [AdminCategoryItem(**c) for c in raw_categories]

        # Ngưỡng tin cậy (nếu .NET truyền vào; nếu không có thì Service sẽ tự lấy từ DB SYSTEM_CONFIGS)
        raw_threshold = body.get("appliedThreshold") or body.get("threshold")
        applied_threshold = float(raw_threshold) if raw_threshold is not None else None

        logger.info(f"Bắt đầu OCR ngầm cho Task {task_id}, Năm {target_year} (ngưỡng: {applied_threshold or 'DB mặc định'})...")

        try:
            # BƯỚC 1: Tải file từ Cloud Storage / S3
            async with httpx.AsyncClient(timeout=30.0) as client:
                file_resp = await client.get(file_url)
                file_resp.raise_for_status()
                file_bytes = file_resp.content
                mime_type = file_resp.headers.get("content-type", "image/jpeg")

            # BƯỚC 2 & 3: Gọi AI phân loại, bóc tách và Lưu Database qua Repository
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

            # BƯỚC 4: Đóng gói JSON trả về cho .NET Backend
            response_payload = {
              "message": "Document processed and validated successfully.",
              "data": {
                "id": task_id,
                "periodId": period_id,
                "userId": user_id,
                "docTypeCode": doc.docTypeCode,  # Mã danh mục AI đã tự xếp vào

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
                "validationStatus": {
                  "isYearValid": result["is_year_valid"],
                  "isDocTypeValid": result["is_doc_type_valid"],
                  "isIdentityValid": True
                },
                "validationErrors": result["validation_errors"],
                "status":  DocumentExtractionStatus.EXTRACTED,
                "createdAt": datetime.now(timezone.utc).isoformat()
              }
            }

            # BƯỚC 5: Bắn ngược sang queue tax.ai.response.queue
            await publish_expense_ocr_response(response_payload)
            logger.info(f"Đã xử lý xong Task {task_id} -> docTypeCode: {doc.docTypeCode}")

        except Exception as e:
            logger.error(f"Lỗi khi OCR task {task_id}: {e}", exc_info=True)
            # Bắn thông báo thất bại về cho .NET
            fail_payload = {
                "message": f"Processing failed: {str(e)}",
                "data": {
                    "id": task_id,
                    "periodId": period_id,
                    "userId": user_id,
                    "status": "FAILED",
                    "validationErrors": [str(e)]
                }

            }
            await publish_expense_ocr_response(fail_payload)