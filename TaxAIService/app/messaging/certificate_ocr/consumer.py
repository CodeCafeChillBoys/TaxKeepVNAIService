import json
import base64
import os
import logging
import mimetypes
from typing import Optional
import aio_pika
import httpx

from app.services.certificate_ocr.certificate_ocr_service import CertificateOcrService
from app.messaging.certificate_ocr.schemas import (
    CertificateOcrRequestMessage,
    CertificateOcrResponseMessage
)
from app.messaging.certificate_ocr.producer import publish_certificate_ocr_response

logger = logging.getLogger(__name__)


async def _download_or_decode_bytes(
    file_base64: Optional[str],
    file_url: Optional[str],
    file_path: Optional[str]
) -> bytes:
    """Hỗ trợ lấy file bytes từ Base64, URL hoặc Local Path"""
    if file_base64:
        return base64.b64decode(file_base64)

    if file_url:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(file_url)
            resp.raise_for_status()
            return resp.content

    if file_path:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File path not found: {file_path}")
        with open(file_path, "rb") as f:
            return f.read()

    raise ValueError("Cần cung cấp ít nhất một trong ba: fileBase64, fileUrl hoặc filePath")


async def handle_certificate_ocr_job(message: aio_pika.IncomingMessage) -> None:
    """
    Xử lý message bóc tách chứng chỉ nhận được từ certificate.ocr.ai.request.queue.
    """
    async with message.process(requeue=False, ignore_processed=True):
        raw_body = message.body.decode("utf-8")
        logger.info(f"Received Certificate OCR request: {raw_body[:200]}...")

        request_msg: Optional[CertificateOcrRequestMessage] = None
        try:
            body_dict = json.loads(raw_body)
            request_msg = CertificateOcrRequestMessage.model_validate(body_dict)
        except Exception as parse_err:
            logger.error(f"Failed to parse Certificate OCR request JSON: {parse_err}")
            await message.ack()
            return

        task_id = request_msg.task_id
        user_id = request_msg.user_id
        application_id = request_msg.application_id
        certificate_id = request_msg.certificate_id

        try:
            # 1. Lấy dữ liệu file (ảnh/PDF)
            file_bytes = await _download_or_decode_bytes(
                request_msg.file_base64,
                request_msg.file_url,
                request_msg.file_path
            )
            mime_type, _ = mimetypes.guess_type(request_msg.file_name)
            mime_type = mime_type or "image/jpeg"

            # 2. Gọi Service bóc tách chứng chỉ bằng Gemini Vision
            service = CertificateOcrService()
            ocr_result = service.extract_certificate(
                file_bytes=file_bytes,
                mime_type=mime_type,
                allowed_types=request_msg.allowed_types
            )

            # 3. Đóng gói response message
            response_msg = CertificateOcrResponseMessage(
                task_id=task_id,
                user_id=user_id,
                application_id=application_id,
                certificate_id=certificate_id,
                success=ocr_result.success,
                status_code=ocr_result.status_code,
                message=ocr_result.message,
                data=ocr_result.data,
                errors=ocr_result.errors
            )

            # 4. Gửi về hàng đợi certificate.ocr.ai.response.queue cho BE .NET
            await publish_certificate_ocr_response(response_msg)

        except Exception as ex:
            logger.error(f"Error processing Certificate OCR task {task_id}: {ex}", exc_info=True)
            error_response = CertificateOcrResponseMessage(
                task_id=task_id,
                user_id=user_id,
                application_id=application_id,
                certificate_id=certificate_id,
                success=False,
                status_code=500,
                message=f"Lỗi hệ thống khi bóc tách chứng chỉ: {str(ex)}",
                errors=[{"code": "ERR_CONSUMER_EXCEPTION", "message": str(ex)}]
            )
            await publish_certificate_ocr_response(error_response)
