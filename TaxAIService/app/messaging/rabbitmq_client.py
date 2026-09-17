import json
import logging
from typing import Optional, Any
import aio_pika
from app.core.config import settings

logger = logging.getLogger(__name__)


class RabbitMQClient:
    """Quản lý kết nối bất đồng bộ tới RabbitMQ bằng aio-pika."""

    def __init__(self):
        self.connection: Optional[aio_pika.RobustConnection] = None
        self.channel: Optional[aio_pika.RobustChannel] = None

    async def connect(self) -> None:
        """Khởi tạo kết nối RobustConnection tới RabbitMQ."""
        if self.connection and not self.connection.is_closed:
            return

        try:
            self.connection = await aio_pika.connect_robust(
                settings.RABBITMQ_URL,
                timeout=10
            )
            self.channel = await self.connection.channel()
            # Giới hạn mỗi consumer nhận tối đa 1 message chưa ack tại một thời điểm
            await self.channel.set_qos(prefetch_count=1)
            logger.info("RabbitMQ connection established successfully.")
        except Exception as e:
            logger.warning(f"Could not connect to RabbitMQ at {settings.RABBITMQ_URL}: {e}")
            self.connection = None
            self.channel = None
            raise

    async def close(self) -> None:
        """Đóng an toàn kết nối RabbitMQ."""
        try:
            if self.channel and not self.channel.is_closed:
                await self.channel.close()
            if self.connection and not self.connection.is_closed:
                await self.connection.close()
            logger.info("RabbitMQ connection closed.")
        except Exception as e:
            logger.error(f"Error while closing RabbitMQ connection: {e}")

    async def publish_json(self, routing_key: str, message_data: Any, exchange_name: str = "") -> None:
        """
        Gửi dữ liệu JSON tới exchange hoặc direct queue.
        """
        if not self.channel or self.channel.is_closed:
            await self.connect()
        #chuyển đổi data trong message khi lấy đc thành json => dumps
        payload_bytes = json.dumps(message_data, default=str).encode("utf-8")
        msg = aio_pika.Message(
            body=payload_bytes,
            content_type="application/json",
            delivery_mode=aio_pika.DeliveryMode.PERSISTENT
        )

        if exchange_name:
            exchange = await self.channel.get_exchange(exchange_name)
            await exchange.publish(msg, routing_key=routing_key)
        else:
            await self.channel.default_exchange.publish(msg, routing_key=routing_key)


rabbitmq_client = RabbitMQClient()
