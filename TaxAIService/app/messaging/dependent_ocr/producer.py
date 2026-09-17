import logging
from app.core.config import settings
from app.messaging.rabbitmq_client import rabbitmq_client
from app.messaging.dependent_ocr.schemas import OcrExtractResponseMessage

logger = logging.getLogger(__name__)


async def publish_ocr_response(response_msg: OcrExtractResponseMessage) -> None:
    """
    Publish kết quả bóc tách OCR về hàng đợi ocr.ai.response.queue cho BE.Net.
    """
    try:
        data = response_msg.model_dump(by_alias=True)
        await rabbitmq_client.publish_json(
            routing_key=settings.RABBITMQ_EXPENSE_OCR_RESPONSE_QUEUE,
            message_data=data
        )
        logger.info(
            f"Published OCR response to {settings.RABBITMQ_EXPENSE_OCR_RESPONSE_QUEUE} "
            f"[taskId={response_msg.task_id}, success={response_msg.success}]"
        )
    except Exception as e:
        logger.error(f"Failed to publish OCR response for task {response_msg.task_id}: {e}")