import json
import base64
import os
import logging
import mimetypes
from typing import Optional, List, Tuple
import aio_pika
import httpx

from app.services.ocr import DependentOcrService
from app.infrastructure.database import get_db_context
from app.repositories.system_config.system_config_repository import SystemConfigRepository
from app.messaging.dependent_ocr.schemas import (
    OcrExtractRequestMessage,
    OcrExtractResponseMessage,
)
from app.messaging.dependent_ocr.producer import publish_ocr_response

logger = logging.getLogger(__name__)



async def _download_or_decode_bytes(file_base64: Optional[str], file_url: Optional[str], file_path: Optional[str]) -> bytes:
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


async def handle_ocr_extract_message(message: aio_pika.IncomingMessage) -> None:
    """
    Xử lý message OCR nhận được từ ocr.ai.request.queue.
    """
    async with message.process(requeue=False, ignore_processed=True):
        raw_body = message.body.decode("utf-8")
        logger.info(f"Received OCR request message: {raw_body[:200]}...")

        request_msg: Optional[OcrExtractRequestMessage] = None
        try:
            body_dict = json.loads(raw_body)
            request_msg = OcrExtractRequestMessage.model_validate(body_dict)
        except Exception as parse_err:
            logger.error(f"Failed to parse OCR request JSON: {parse_err}")
            await message.ack()
            return

        task_id = request_msg.task_id
        user_id = request_msg.user_id

        try:
            # 1. Lấy dữ liệu ảnh mặt trước
            front_bytes = await _download_or_decode_bytes(
                request_msg.file_base64,
                request_msg.file_url,
                request_msg.file_path
            )
            mime_type, _ = mimetypes.guess_type(request_msg.file_name)
            mime_type = mime_type or "image/jpeg"

            files_to_process: List[Tuple[bytes, str]] = [(front_bytes, mime_type)]

            # 2. Lấy dữ liệu ảnh mặt sau nếu có
            if request_msg.back_file_base64 or request_msg.back_file_url:
                back_bytes = await _download_or_decode_bytes(
                    request_msg.back_file_base64,
                    request_msg.back_file_url,
                    None
                )
                files_to_process.append((back_bytes, mime_type))

            # 3. Gọi Gemini OCR bóc tách dữ liệu & đối chiếu rules kèm kiểm tra ngưỡng tự động từ DB
            with get_db_context() as db:
                config_repo = SystemConfigRepository(db)
                service = DependentOcrService(repo=config_repo)
                ocr_result = service.extract_document(
                    files=files_to_process,
                    target_group=request_msg.target_group,
                    rules=request_msg.rules,
                    applied_threshold=request_msg.applied_threshold
                )


            # 4. Đóng gói phản hồi thành công
            success_response = OcrExtractResponseMessage(
                task_id=task_id,
                user_id=user_id,
                success=ocr_result.success,
                status_code=ocr_result.status_code,
                message=ocr_result.message,
                data=ocr_result.data,
                errors=ocr_result.errors
            )
            await publish_ocr_response(success_response)
            logger.info(f"Successfully processed OCR task {task_id}")

        except Exception as e:
            logger.error(f"Error processing OCR task {task_id}: {e}", exc_info=True)
            fail_response = OcrExtractResponseMessage(
                task_id=task_id,
                user_id=user_id,
                success=False,
                status_code=500,
                message="Xử lý OCR thất bại.",
                data=None,
                errors=str(e)
            )
            await publish_ocr_response(fail_response)