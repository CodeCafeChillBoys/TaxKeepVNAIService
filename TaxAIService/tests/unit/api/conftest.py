"""
Fixtures dành riêng cho tầng API test.
"""
from unittest.mock import patch, AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Tạo client ảo để gửi request trực tiếp tới FastAPI app mà không gọi network thật."""
    mock_conn = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.__exit__.return_value = None

    with patch("app.infrastructure.database.engine.connect", return_value=mock_conn), \
         patch("app.main.start_rabbitmq_consumer", new=AsyncMock()), \
         patch("app.main.rabbitmq_client.close", new=AsyncMock()):
        with TestClient(app) as c:
            yield c
    app.dependency_overrides.clear()
