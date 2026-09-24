import logging
from app.core.config import settings
from app.messaging.rabbitmq_client import rabbitmq_client
from app.schemas.law_changeset.contract import LawChangesetExtractResponse

logger = logging.getLogger(__name__)


async def publish_law_changeset_response(response: LawChangesetExtractResponse) -> None:
    """
    Publish response message sang hàng đợi law.changeset.response.queue.
    """
    routing_key = settings.RABBITMQ_LAW_CHANGESET_RESPONSE_QUEUE
    logger.info(
        f"Publishing LawChangeset response: taskId={response.task_id}, "
        f"changesetId={response.changeset_id}, status={response.status}, "
        f"routing_key='{routing_key}'"
    )
    payload = response.model_dump(by_alias=True)
    await rabbitmq_client.publish_json(routing_key=routing_key, message_data=payload)
