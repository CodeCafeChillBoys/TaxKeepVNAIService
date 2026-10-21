import uuid
from unittest.mock import MagicMock
import pytest
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.repositories.tax_rule.chat_history_repository import ChatHistoryRepository


@pytest.fixture
def mock_db():
    db = MagicMock()
    return db


def test_get_or_create_session_existing(mock_db):
    session_id = uuid.uuid4()
    existing_session = ChatSession(id=session_id, title="Test Session")
    mock_db.query.return_value.filter.return_value.first.return_value = existing_session

    repo = ChatHistoryRepository(db=mock_db)
    result = repo.get_or_create_session(session_id=session_id)

    assert result == existing_session
    mock_db.add.assert_not_called()


def test_get_or_create_session_new(mock_db):
    mock_db.query.return_value.filter.return_value.first.return_value = None

    repo = ChatHistoryRepository(db=mock_db)
    user_id = uuid.uuid4()
    result = repo.get_or_create_session(first_question="Lương 20 triệu đóng thuế bao nhiêu?", user_id=user_id)

    assert result is not None
    assert result.user_id == user_id
    assert "Lương 20 triệu" in result.title
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_save_message(mock_db):
    session_id = uuid.uuid4()
    mock_session = ChatSession(id=session_id, title="Test")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    repo = ChatHistoryRepository(db=mock_db)
    msg = repo.save_message(session_id=session_id, role="user", content="Hello AI")

    assert msg.session_id == session_id
    assert msg.role == "user"
    assert msg.content == "Hello AI"
    mock_db.add.assert_called_once()
    mock_db.commit.assert_called_once()


def test_get_user_sessions(mock_db):
    user_id = uuid.uuid4()
    sessions = [ChatSession(id=uuid.uuid4(), user_id=user_id, title="S1")]
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = sessions

    repo = ChatHistoryRepository(db=mock_db)
    result = repo.get_user_sessions(user_id=user_id)

    assert len(result) == 1
    assert result[0].title == "S1"


def test_delete_session(mock_db):
    session_id = uuid.uuid4()
    mock_session = ChatSession(id=session_id, title="To delete")
    mock_db.query.return_value.filter.return_value.first.return_value = mock_session

    repo = ChatHistoryRepository(db=mock_db)
    success = repo.delete_session(session_id=session_id)

    assert success is True
    mock_db.delete.assert_called_once_with(mock_session)
    mock_db.commit.assert_called_once()
