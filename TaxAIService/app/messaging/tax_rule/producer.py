import logging
from app.core.config import settings
from app.messaging.rabbitmq_client import rabbitmq_client
from app.messaging.tax_rule.schemas import TaxRuleExtractResponseMessage

logger = logging.getLogger(__name__)


async def publish_extraction_response(response_msg: TaxRuleExtractResponseMessage) -> None:
    """
    Publish kết quả xử lý bóc tách văn bản luật thuế về hàng đợi response cho BE.Net.
    """
    try:
        data = response_msg.model_dump(by_alias=True)
        await rabbitmq_client.publish_json(
            routing_key=settings.RABBITMQ_TAX_RESPONSE_QUEUE,
            message_data=data
        )
        logger.info(
            f"Published extraction response to {settings.RABBITMQ_TAX_RESPONSE_QUEUE} "
            f"[taskId={response_msg.task_id}, status={response_msg.status}]"
        )
    except Exception as e:
        logger.error(f"Failed to publish extraction response: {e}")
