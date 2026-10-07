# app/messaging/income_ocr/producer.py
import json
import logging
import aio_pika
from app.core.config import settings
from app.messaging.rabbitmq_client import rabbitmq_client

logger = logging.getLogger(__name__)

async def publish_income_ocr_response(payload: dict) -> None:
    """Bắn kết quả bóc tách phiếu lương về cho Backend .NET qua RabbitMQ"""
    try:
        channel = rabbitmq_client.channel
        message = aio_pika.Message(
            body=json.dumps(payload).encode("utf-8"),
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )
        # Giả sử queue response là income.ocr.ai.response.queue
        response_queue = settings.RABBITMQ_INCOME_RESPONSE_QUEUE
        await channel.default_exchange.publish(
            message,
            routing_key=response_queue
        )
        logger.info(f"Đã gửi kết quả Income OCR về queue '{response_queue}'")
    except Exception as e:
        logger.error(f"Lỗi khi publish message Income OCR: {e}", exc_info=True)