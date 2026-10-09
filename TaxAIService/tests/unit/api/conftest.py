"""
Fixtures dành riêng cho tầng API test.
"""
import pytest
@pytest.fixture
def client():
    """Tạo client ảo để gửi request trực tiếp tới FastAPI app."""
    from fastapi.testclient import TestClient
    from app.main import app
    yield TestClient(app)
    app.dependency_overrides.clear()

