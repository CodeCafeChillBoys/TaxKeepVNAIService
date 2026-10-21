import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch
import pytest
from app.infrastructure.database import get_db
from app.main import app


@pytest.fixture
def mock_db():
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    yield db
    app.dependency_overrides.pop(get_db, None)


@patch("app.api.routes.tax_rule.tax_chat.TaxChatService")
def test_chat_with_tax_ai_endpoint(mock_service_class, client, mock_db):
    session_id = uuid.uuid4()
    mock_service = MagicMock()
    mock_service.ask.return_value = {
        "session_id": session_id,
        "question": "Giảm trừ gia cảnh?",
        "answer": "Giảm trừ 11 triệu VND/tháng."
    }
    mock_service_class.return_value = mock_service

    payload = {
        "question": "Giảm trừ gia cảnh?",
        "tax_year": 2026
    }
    response = client.post("/api/tax-chat", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == str(session_id)
    assert data["answer"] == "Giảm trừ 11 triệu VND/tháng."


@patch("app.api.routes.tax_rule.tax_chat.ChatHistoryRepository")
def test_get_user_chat_sessions_endpoint(mock_repo_class, client, mock_db):
    session_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_session = MagicMock()
    mock_session.id = session_id
    mock_session.user_id = uuid.uuid4()
    mock_session.title = "Phiên 1"
    mock_session.created_at = datetime.utcnow()
    mock_session.updated_at = datetime.utcnow()
    mock_repo.get_user_sessions.return_value = [mock_session]
    mock_repo_class.return_value = mock_repo

    response = client.get(f"/api/tax-chat/sessions?user_id={mock_session.user_id}")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == str(session_id)
    assert data[0]["title"] == "Phiên 1"


@patch("app.api.routes.tax_rule.tax_chat.ChatHistoryRepository")
def test_delete_chat_session_endpoint(mock_repo_class, client, mock_db):
    session_id = uuid.uuid4()
    mock_repo = MagicMock()
    mock_repo.delete_session.return_value = True
    mock_repo_class.return_value = mock_repo

    response = client.delete(f"/api/tax-chat/sessions/{session_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["session_id"] == str(session_id)
