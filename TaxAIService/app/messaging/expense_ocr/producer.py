import logging
from typing import Union, Dict, Any, Optional
from pydantic import BaseModel
from app.core.config import settings
from app.messaging.rabbitmq_client import rabbitmq_client
from app.schemas.expense_ocr.expense_ocr_schema import ProcessDocumentResponse

logger = logging.getLogger(__name__)


async def publish_expense_ocr_response(
    response_msg: Union[ProcessDocumentResponse, Dict[str, Any]],
    routing_key: Optional[str] = None
) -> None:
    """
    Publish kết quả bóc tách OCR chứng từ chi phí (Expense OCR) về hàng đợi cho BE.Net.
    Hỗ trợ cả Pydantic model (ProcessDocumentResponse) lẫn Dict payload.
    """
    if not settings.RABBITMQ_ENABLED:
        logger.info("RabbitMQ is disabled. Skipping publish Expense OCR response.")
        return

    # Hàng đợi đích mặc định: settings.RABBITMQ_EXPENSE_OCR_RESPONSE_QUEUE
    target_queue = routing_key or settings.RABBITMQ_EXPENSE_OCR_RESPONSE_QUEUE

    # 1. Trích xuất task_id và status để phục vụ logging
    if isinstance(response_msg, BaseModel):
        # ép nó về json
        data = response_msg.model_dump(mode="json")
        # lấy data
        inner = getattr(response_msg, "data", None)
        # lấy id
        task_id = getattr(inner, "id", "UNKNOWN") if inner else "UNKNOWN"
        # lấy status
        doc_status = getattr(inner, "status", "UNKNOWN") if inner else "UNKNOWN"
    elif isinstance(response_msg, dict):
        data = response_msg
        inner = response_msg.get("data", {})
        task_id = inner.get("id", "UNKNOWN")
        doc_status = inner.get("status", "UNKNOWN")
    else:
        data = dict(response_msg)
        task_id = "UNKNOWN"
        doc_status = "UNKNOWN"

    try:
        # 2. Gửi message qua RabbitMQ
        await rabbitmq_client.publish_json(
            routing_key=target_queue,
            message_data=data
        )

        logger.info(
            f"Published Expense OCR response to '{target_queue}' "
            f"[taskId={task_id}, status={doc_status}]"
        )
    except Exception as e:
        logger.error(f"Failed to publish Expense OCR response for task {task_id}: {e}", exc_info=True)
        raise
    