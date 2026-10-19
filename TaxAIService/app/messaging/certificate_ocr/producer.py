import logging
from app.core.config import settings
from app.messaging.rabbitmq_client import rabbitmq_client
from app.messaging.certificate_ocr.schemas import CertificateOcrResponseMessage

logger = logging.getLogger(__name__)


async def publish_certificate_ocr_response(response_msg: CertificateOcrResponseMessage) -> None:
    """
    Publish kết quả bóc tách chứng chỉ hành nghề về hàng đợi certificate.ocr.ai.response.queue cho BE .NET.
    """
    try:
        data = response_msg.model_dump(by_alias=True)
        await rabbitmq_client.publish_json(
            routing_key=settings.RABBITMQ_CERTIFICATE_OCR_RESPONSE_QUEUE,
            message_data=data
        )
        logger.info(
            f"Published Certificate OCR response to {settings.RABBITMQ_CERTIFICATE_OCR_RESPONSE_QUEUE} "
            f"[taskId={response_msg.task_id}, success={response_msg.success}]"
        )
    except Exception as e:
        logger.error(f"Failed to publish Certificate OCR response for task {response_msg.task_id}: {e}")
