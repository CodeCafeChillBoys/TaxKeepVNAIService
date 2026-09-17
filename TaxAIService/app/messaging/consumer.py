import asyncio
import logging
import aio_pika

from app.core.config import settings
from app.messaging.rabbitmq_client import rabbitmq_client
from app.messaging.tax_rule.consumer import handle_tax_extract_message
from app.messaging.dependent_ocr.consumer import handle_ocr_extract_message
from app.messaging.expense_ocr.expense_consumer import handle_expense_ocr_job

logger = logging.getLogger(__name__)


async def start_rabbitmq_consumer() -> None:
    """
    Vòng lặp chạy nền để kết nối và lắng nghe messages từ RabbitMQ.
    Khởi chạy các Consumer: TaxRule, Dependent OCR, Expense OCR.
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

            # 1. Hàng đợi cho TaxRule
            tax_request_queue = await channel.declare_queue(
                settings.RABBITMQ_TAX_REQUEST_QUEUE,
                durable=True
            )
            await channel.declare_queue(
                settings.RABBITMQ_TAX_RESPONSE_QUEUE,
                durable=True
            )

            # 2. Hàng đợi cho Dependent OCR (CCCD, Giấy khai sinh)
            ocr_request_queue = await channel.declare_queue(
                settings.RABBITMQ_OCR_REQUEST_QUEUE, 
                durable=True
            )
            await channel.declare_queue(
                settings.RABBITMQ_OCR_RESPONSE_QUEUE, 
                durable=True
            )

            # 3. Hàng đợi cho Expense OCR (Hóa đơn viện phí, học phí, từ thiện)
            expense_ocr_request_queue = await channel.declare_queue(
                settings.RABBITMQ_EXPENSE_OCR_REQUEST_QUEUE, 
                durable=True
            )
            await channel.declare_queue(
                settings.RABBITMQ_EXPENSE_OCR_RESPONSE_QUEUE, 
                durable=True
            )

            logger.info(f"Consumer listening on Tax Queue: '{settings.RABBITMQ_TAX_REQUEST_QUEUE}'")
            logger.info(f"Consumer listening on OCR Queue: '{settings.RABBITMQ_OCR_REQUEST_QUEUE}'")
            logger.info(f"Consumer listening on Expense OCR Queue: '{settings.RABBITMQ_EXPENSE_OCR_REQUEST_QUEUE}'")

            await tax_request_queue.consume(handle_tax_extract_message)
            await ocr_request_queue.consume(handle_ocr_extract_message)
            await expense_ocr_request_queue.consume(handle_expense_ocr_job)


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
