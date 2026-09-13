import json
import base64
import os
import asyncio
import logging
from typing import Optional, Tuple
import aio_pika
import httpx

from app.core.config import settings
from app.infrastructure.database import get_db_context
from app.repositories import TaxRuleRepository
from app.services import TaxRuleService, TaxRuleServiceError
from app.messaging.rabbitmq_client import rabbitmq_client
from app.messaging.schemas import (
    TaxRuleExtractRequestMessage,
    TaxRuleExtractResponseMessage,
)
from app.messaging.producer import publish_extraction_response

logger = logging.getLogger(__name__)


async def _resolve_file_bytes(req: TaxRuleExtractRequestMessage) -> bytes:
    """
    Trích xuất file bytes từ một trong 3 nguồn:
    1. Base64 string
    2. URL (HTTP/HTTPS qua httpx)
    3. Đường dẫn file nội bộ (filePath)
    """
    if req.file_base64:
        return base64.b64decode(req.file_base64)

    if req.file_url:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.get(req.file_url)
            resp.raise_for_status()
            return resp.content

    if req.file_path:
        if not os.path.exists(req.file_path):
            raise FileNotFoundError(f"File path not found: {req.file_path}")
        with open(req.file_path, "rb") as f:
            return f.read()

    raise ValueError("Request must provide at least one of: fileBase64, fileUrl, or filePath")


async def handle_tax_extract_message(message: aio_pika.IncomingMessage) -> None:
    """
    Xử lý từng message nhận được từ tax.ai.request.queue.
    """
    async with message.process(requeue=False, ignore_processed=True):
        raw_body = message.body.decode("utf-8")
        logger.info(f"Received message: {raw_body[:200]}...")

        request_msg: Optional[TaxRuleExtractRequestMessage] = None
        try:
            body_dict = json.loads(raw_body)
            request_msg = TaxRuleExtractRequestMessage.model_validate(body_dict)
        except Exception as parse_err:
            logger.error(f"Failed to parse request message JSON: {parse_err}")
            await message.ack()
            return

        task_id = request_msg.task_id
        admin_id = request_msg.admin_id

        try:
            # 1. Thu thập file bytes
            file_bytes = await _resolve_file_bytes(request_msg)

            # 2. Xử lý nghiệp vụ với get_db_context() và TaxRuleService
            with get_db_context() as db:
                repo = TaxRuleRepository(db)
                service = TaxRuleService(repo)
                result = await service.process_tax_rule_document(
                    filename=request_msg.file_name,
                    file_bytes=file_bytes,
                    tax_year=request_msg.tax_year,
                    name=request_msg.name,
                    source_url=request_msg.source_url,
                    admin_id=admin_id
                )

            # 3. Trích xuất rule_set_id từ kết quả nếu có
            data_dict = result.get("data", {})
            rule_set_info = data_dict.get("taxRuleSet", {})
            rule_set_id = rule_set_info.get("ruleSetId")

            # 4. Gửi message thành công về cho BE.Net
            success_response = TaxRuleExtractResponseMessage(
                task_id=task_id,
                admin_id=admin_id,
                status="SUCCESS",
                rule_set_id=rule_set_id,
                data=data_dict,
                error_message=None
            )
            await publish_extraction_response(success_response)
            logger.info(f"Successfully processed task {task_id} with ruleSetId={rule_set_id}")

        except TaxRuleServiceError as tse:
            logger.warning(f"Business error processing task {task_id}: {tse.message}")
            fail_response = TaxRuleExtractResponseMessage(
                task_id=task_id,
                admin_id=admin_id,
                status="FAILED",
                rule_set_id=None,
                data=None,
                error_message=tse.message
            )
            await publish_extraction_response(fail_response)

        except Exception as e:
            logger.error(f"Unexpected error processing task {task_id}: {e}", exc_info=True)
            fail_response = TaxRuleExtractResponseMessage(
                task_id=task_id,
                admin_id=admin_id,
                status="FAILED",
                rule_set_id=None,
                data=None,
                error_message=f"Internal error: {str(e)}"
            )
            await publish_extraction_response(fail_response)


async def start_rabbitmq_consumer() -> None:
    """
    Vòng lặp chạy nền để kết nối và lắng nghe messages từ RabbitMQ.
    Tự động kết nối lại nếu bị ngắt kết nối.
    """
    if not settings.RABBITMQ_ENABLED:
        logger.info("RabbitMQ is disabled by config (RABBITMQ_ENABLED=False).")
        return

    logger.info("Starting RabbitMQ Consumer Worker...")
    retry_interval = 5

    while True:
        try:
            await rabbitmq_client.connect()
            channel = rabbitmq_client.channel

            # Khởi tạo hai hàng đợi Durable
            request_queue = await channel.declare_queue(
                settings.RABBITMQ_TAX_REQUEST_QUEUE,
                durable=True
            )
            await channel.declare_queue(
                settings.RABBITMQ_TAX_RESPONSE_QUEUE,
                durable=True
            )

            logger.info(f"Consumer listening on queue: '{settings.RABBITMQ_TAX_REQUEST_QUEUE}'")

            # Bắt đầu nhận message
            await request_queue.consume(handle_tax_extract_message)

            # Giữ kết nối hoạt động
            while not rabbitmq_client.connection.is_closed:
                await asyncio.sleep(1)

        except asyncio.CancelledError:
            logger.info("RabbitMQ consumer task cancelled.")
            break
        except Exception as e:
            logger.warning(
                f"RabbitMQ consumer connection lost or failed: {e}. "
                f"Retrying in {retry_interval}s..."
            )
            await asyncio.sleep(retry_interval)
