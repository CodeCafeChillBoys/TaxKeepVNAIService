import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.services.tax_rule.tax_chat_service import TaxChatService
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage


@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_active_rules.return_value = []
    repo.get_dependent_rules.return_value = []
    return repo


@pytest.fixture
def mock_history_repo():
    repo = MagicMock()
    session_id = uuid.uuid4()
    session = ChatSession(id=session_id, title="Test")
    repo.get_or_create_session.return_value = session
    repo.get_recent_messages.return_value = []
    return repo


@patch("app.services.tax_rule.tax_chat_service.genai.Client")
def test_tax_chat_ask_success(mock_client_class, mock_repo, mock_history_repo):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Bạn cần giảm trừ gia cảnh 11 triệu."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
    service.client = mock_client

    result = service.ask(
        question="Mức giảm trừ gia cảnh là bao nhiêu?",
        session_id=None,
        tax_year=2026,
        user_id=uuid.uuid4()
    )

    assert result["answer"] == "Bạn cần giảm trừ gia cảnh 11 triệu."
    assert result["question"] == "Mức giảm trừ gia cảnh là bao nhiêu?"
    assert result["session_id"] is not None
    mock_history_repo.save_message.assert_called()


def test_tax_chat_get_user_sessions(mock_repo, mock_history_repo):
    user_id = uuid.uuid4()
    mock_history_repo.get_user_sessions.return_value = [ChatSession(id=uuid.uuid4(), title="Test")]
    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
        result = service.get_user_sessions(user_id=user_id)
        assert len(result) == 1
