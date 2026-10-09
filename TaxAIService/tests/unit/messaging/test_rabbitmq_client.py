import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from app.messaging.rabbitmq_client import RabbitMQClient


def test_connect_success():
    """connect() thiết lập kết nối và channel với set_qos(1)"""
    async def _test():
        client = RabbitMQClient()
        mock_conn = MagicMock()
        mock_conn.is_closed = False
        mock_channel = AsyncMock()
        mock_conn.channel = AsyncMock(return_value=mock_channel)

        with patch("aio_pika.connect_robust", new=AsyncMock(return_value=mock_conn)):
            await client.connect()
            assert client.connection == mock_conn
            assert client.channel == mock_channel
            mock_channel.set_qos.assert_awaited_once_with(prefetch_count=1)

    asyncio.run(_test())


def test_connect_already_connected():
    """connect() không kết nối lại nếu connection đang mở"""
    async def _test():
        client = RabbitMQClient()
        mock_conn = MagicMock()
        mock_conn.is_closed = False
        client.connection = mock_conn

        with patch("aio_pika.connect_robust") as mock_connect:
            await client.connect()
            mock_connect.assert_not_called()

    asyncio.run(_test())


def test_connect_failure():
    """connect() quăng lỗi và reset connection/channel khi kết nối thất bại"""
    async def _test():
        import pytest
        client = RabbitMQClient()
        with patch("aio_pika.connect_robust", new=AsyncMock(side_effect=ConnectionError("Cannot connect"))):
            with pytest.raises(ConnectionError):
                await client.connect()
            assert client.connection is None
            assert client.channel is None

    asyncio.run(_test())


def test_close_success():
    """close() đóng channel và connection an toàn"""
    async def _test():
        client = RabbitMQClient()
        mock_conn = AsyncMock()
        mock_conn.is_closed = False
        mock_channel = AsyncMock()
        mock_channel.is_closed = False

        client.connection = mock_conn
        client.channel = mock_channel

        await client.close()
        mock_channel.close.assert_awaited_once()
        mock_conn.close.assert_awaited_once()

    asyncio.run(_test())


def test_publish_json_default_exchange():
    """publish_json() gửi payload lên default_exchange khi không truyền exchange_name"""
    async def _test():
        client = RabbitMQClient()
        mock_channel = AsyncMock()
        mock_channel.is_closed = False
        mock_default_exchange = AsyncMock()
        mock_channel.default_exchange = mock_default_exchange
        client.channel = mock_channel

        data = {"status": "SUCCESS", "id": 123}
        await client.publish_json(routing_key="test.queue", message_data=data)

        mock_default_exchange.publish.assert_awaited_once()
        args, kwargs = mock_default_exchange.publish.call_args
        assert kwargs["routing_key"] == "test.queue"
        message_arg = args[0]
        assert json.loads(message_arg.body.decode("utf-8")) == data

    asyncio.run(_test())


def test_publish_json_custom_exchange():
    """publish_json() lấy custom exchange và publish khi có exchange_name"""
    async def _test():
        client = RabbitMQClient()
        mock_channel = AsyncMock()
        mock_channel.is_closed = False
        mock_exchange = AsyncMock()
        mock_channel.get_exchange = AsyncMock(return_value=mock_exchange)
        client.channel = mock_channel

        data = {"msg": "hello"}
        await client.publish_json(routing_key="custom.key", message_data=data, exchange_name="my_exchange")

        mock_channel.get_exchange.assert_awaited_once_with("my_exchange")
        mock_exchange.publish.assert_awaited_once()
        args, kwargs = mock_exchange.publish.call_args
        assert kwargs["routing_key"] == "custom.key"

    asyncio.run(_test())


def test_publish_json_reconnects_if_channel_closed():
    """publish_json() tự động gọi connect() nếu channel chưa khởi tạo hoặc đã đóng"""
    async def _test():
        client = RabbitMQClient()
        client.connect = AsyncMock()
        mock_channel = AsyncMock()
        mock_channel.is_closed = False
        client.channel = mock_channel

        # Giả lập ban đầu channel = None
        client.channel = None

        def fake_connect():
            client.channel = mock_channel

        client.connect.side_effect = fake_connect

        await client.publish_json(routing_key="test.queue", message_data={"test": 1})
        client.connect.assert_awaited_once()

    asyncio.run(_test())

