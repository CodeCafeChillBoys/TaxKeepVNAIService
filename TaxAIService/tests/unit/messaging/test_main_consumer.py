import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from app.messaging.consumer import start_rabbitmq_consumer


def test_start_consumer_when_disabled(monkeypatch):
    """Khi RABBITMQ_ENABLED=False, hàm dừng ngay lập tức mà không kết nối broker"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "RABBITMQ_ENABLED", False)

    async def _test():
        with patch("app.messaging.consumer.rabbitmq_client") as mock_client:
            await start_rabbitmq_consumer()
            mock_client.connect.assert_not_called()

    asyncio.run(_test())


def test_start_consumer_cancelled(monkeypatch):
    """Khi task bị cancel (asyncio.CancelledError), worker dừng vòng lặp an toàn"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "RABBITMQ_ENABLED", True)

    async def _test():
        with patch("app.messaging.consumer.rabbitmq_client") as mock_client:
            mock_client.connect = AsyncMock()
            mock_conn = MagicMock()
            mock_conn.is_closed = False
            mock_client.connection = mock_conn

            mock_channel = AsyncMock()
            mock_client.channel = mock_channel
            mock_queue = AsyncMock()
            mock_channel.declare_queue = AsyncMock(return_value=mock_queue)

            task = asyncio.create_task(start_rabbitmq_consumer())
            # Cho event loop chạy 1 tick để worker hoàn thành việc khởi tạo queue và consume
            await asyncio.sleep(0.01)
            # Hủy task
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass

            mock_client.connect.assert_called_once()
            assert mock_channel.declare_queue.await_count == 8  # 4 request queues + 4 response queues
            assert mock_queue.consume.await_count == 4


    asyncio.run(_test())
