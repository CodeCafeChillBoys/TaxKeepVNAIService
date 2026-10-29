import uuid
from unittest.mock import MagicMock, patch
import pytest
from app.services.tax_rule.tax_chat_service import TaxChatService
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.models.tax_rule import TaxRule
from app.models.tax_rule_set import TaxRuleSet
from app.models.dependent_rule import DependentRule


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


@patch("app.services.tax_rule.tax_chat_service.genai.Client")
def test_tax_chat_ask_with_history_messages(mock_client_class, mock_repo, mock_history_repo):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "Câu trả lời tiếp nối."
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    msg1 = ChatMessage(session_id=uuid.uuid4(), role="user", content="Chào bạn")
    msg2 = ChatMessage(session_id=uuid.uuid4(), role="assistant", content="TaxKeep xin chào")
    mock_history_repo.get_recent_messages.return_value = [msg1, msg2]

    service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
    service.client = mock_client

    result = service.ask(
        question="Tiếp tục tính thuế",
        session_id=uuid.uuid4()
    )
    assert result["answer"] == "Câu trả lời tiếp nối."


@patch("app.services.tax_rule.tax_chat_service.genai.Client")
def test_tax_chat_ask_without_history_repo(mock_client_class, mock_repo):
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "No history answer"
    mock_client.models.generate_content.return_value = mock_response
    mock_client_class.return_value = mock_client

    service = TaxChatService(repository=mock_repo, history_repository=None)
    service.client = mock_client

    result = service.ask(question="Test question")
    assert result["session_id"] is None
    assert result["answer"] == "No history answer"


def test_build_tax_knowledge_from_db_empty(mock_repo):
    mock_repo.get_active_rules.return_value = []
    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo)
        res = service._build_tax_knowledge_from_db(tax_year=2026)
        assert "chưa có quy tắc thuế nào" in res


def test_build_tax_knowledge_from_db_with_rules(mock_repo):
    rule_set_2026 = TaxRuleSet(rule_set_id=uuid.uuid4(), tax_year=2026, name="Luật 2026")
    rule_set_2025 = TaxRuleSet(rule_set_id=uuid.uuid4(), tax_year=2025, name="Luật 2025")

    rule_id_1 = uuid.uuid4()
    rule1 = TaxRule(
        rule_id=rule_id_1,
        rule_code="GTGC_BAN_THAN",
        rule_name="Giảm trừ bản thân",
        rule_type="DEDUCTION",
        value=11000000.0,
        unit="VND/tháng",
        condition="Cư trú",
        legal_document="Nghị quyết 954",
        article="Điều 1",
        clause="Khoản 1"
    )
    rule1.rule_set = rule_set_2026

    rule2 = TaxRule(
        rule_id=uuid.uuid4(),
        rule_code="THUE_SUAT_1",
        rule_name="Bậc 1",
        rule_type="RATE",
        value=0.05,
        unit="%",
        legal_document=None
    )
    rule2.rule_set = rule_set_2026

    rule3 = TaxRule(
        rule_id=uuid.uuid4(),
        rule_code="THUE_SUAT_2",
        rule_name="Bậc 2",
        rule_type="RATE",
        value=10.5,
        unit="%",
        legal_document=None
    )
    rule3.rule_set = rule_set_2025

    rule4 = TaxRule(
        rule_id=uuid.uuid4(),
        rule_code="FLOAT_VAL",
        rule_name="Float value",
        rule_type="RATE",
        value=12.345,
        unit="USD"
    )
    rule4.rule_set = None

    dep_rule = DependentRule(
        id=uuid.uuid4(),
        rule_id=rule_id_1,
        name="Con dưới 18 tuổi",
        dependent_type="CON_DUOI_18",
        max_age=18,
        max_monthly_income=1000000.0,
        conditions="Đang sống cùng"
    )

    mock_repo.get_active_rules.return_value = [rule1, rule2, rule3, rule4]
    mock_repo.get_dependent_rules.return_value = [dep_rule]

    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo)
        knowledge = service._build_tax_knowledge_from_db(tax_year=2026)

        assert "CƠ SỞ DỮ LIỆU LUẬT THUẾ" in knowledge
        assert "GTGC_BAN_THAN" in knowledge
        assert "11,000,000 VND/tháng" in knowledge
        assert "Nghị quyết 954" in knowledge
        assert "QUY ĐỊNH CHI TIẾT VỀ ĐIỀU KIỆN NGƯỜI PHỤ THUỘC" in knowledge
        assert "Con dưới 18 tuổi" in knowledge


def test_tax_chat_get_user_sessions(mock_repo, mock_history_repo):
    user_id = uuid.uuid4()
    mock_history_repo.get_user_sessions.return_value = [ChatSession(id=uuid.uuid4(), title="Test")]
    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
        result = service.get_user_sessions(user_id=user_id)
        assert len(result) == 1

        service_no_repo = TaxChatService(repository=mock_repo, history_repository=None)
        assert service_no_repo.get_user_sessions(user_id=user_id) == []


def test_tax_chat_get_session_messages(mock_repo, mock_history_repo):
    session_id = uuid.uuid4()
    mock_history_repo.get_session_messages.return_value = [ChatMessage(session_id=session_id, role="user", content="Hi")]
    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
        messages = service.get_session_messages(session_id)
        assert len(messages) == 1

        service_no_repo = TaxChatService(repository=mock_repo, history_repository=None)
        assert service_no_repo.get_session_messages(session_id) == []


def test_tax_chat_delete_session(mock_repo, mock_history_repo):
    session_id = uuid.uuid4()
    mock_history_repo.delete_session.return_value = True
    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
        assert service.delete_session(session_id) is True

        service_no_repo = TaxChatService(repository=mock_repo, history_repository=None)
        assert service_no_repo.delete_session(session_id) is False
