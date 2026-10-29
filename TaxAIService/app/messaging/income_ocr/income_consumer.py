# app/messaging/income_ocr/income_consumer.py
import json
import logging
import base64
import mimetypes
import httpx
import aio_pika
from datetime import datetime, timezone

from app.infrastructure.database import get_db_context
from app.repositories.system_config import SystemConfigRepository
from app.services.income_ocr.income_ocr_service import IncomeOcrService
from app.messaging.income_ocr.producer import publish_income_ocr_response

logger = logging.getLogger(__name__)


async def _download_file_bytes(file_url: str = None, file_base64: str = None):
    """Tải bytes file từ URL hoặc giải mã Base64"""
    file_bytes = None
    mime_type = "image/jpeg"

    if file_base64:
        file_bytes = base64.b64decode(file_base64)
    elif file_url:
        async with httpx.AsyncClient(timeout=60.0, verify=False) as client:
            resp = await client.get(file_url)
            resp.raise_for_status()
            file_bytes = resp.content
            raw_mime = resp.headers.get("content-type", "")
            if raw_mime:
                mime_type = raw_mime.split(";")[0].strip().lower()

    return file_bytes, mime_type


async def handle_income_ocr_job(message: aio_pika.IncomingMessage):
    """Lắng nghe message bóc tách phiếu lương từ .NET Backend"""
    async with message.process(requeue=False, ignore_processed=True):
        raw_body = message.body.decode("utf-8")
        body = json.loads(raw_body)

        task_id = body.get("taskId") or body.get("id")
        user_id = body.get("userId")
        target_month = body.get("targetMonth") or body.get("month")
        target_year = body.get("targetYear") or body.get("year")
        file_url = body.get("fileUrl")
        file_base64 = body.get("fileBase64")

        try:
            file_bytes, mime_type = await _download_file_bytes(file_url, file_base64)

            with get_db_context() as db:
                config_repo = SystemConfigRepository(db)
                service = IncomeOcrService(repo=config_repo)
                result = service.extract_payslip(
                    file_bytes=file_bytes,
                    mime_type=mime_type,
                    target_month=int(target_month) if target_month else None,
                    target_year=int(target_year) if target_year else None
                )

            # Đóng gói response bắn ngược lại .NET
            response_payload = {
                "taskId": task_id,
                "userId": user_id,
                "fileUrl": file_url,
                "statusCode": result.status_code,
                "message": result.message,
                "data": result.data.model_dump(by_alias=True) if result.data else None,
                "errors": result.errors,
                "processedAt": datetime.now(timezone.utc).isoformat()
            }
            await publish_income_ocr_response(response_payload)

        except Exception as ex:
            logger.error(f"Lỗi xử lý Income OCR Worker Task {task_id}: {ex}", exc_info=True)
            await publish_income_ocr_response({
                "taskId": task_id,
                "userId": user_id,
                "statusCode": 500,
                "message": f"Processing failed: {str(ex)}",
                "errors": [{"code": "ERR_SYSTEM", "message": str(ex)}]
            })