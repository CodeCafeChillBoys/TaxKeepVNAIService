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


def test_tax_chat_ask_empty_or_whitespace_question_raises_value_error(mock_repo, mock_history_repo):
    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
        
        for invalid_q in ["", "   ", "\t\n  ", None]:
            try:
                service.ask(question=invalid_q)
                assert False, f"Expected ValueError for question: {invalid_q}"
            except ValueError as e:
                assert "Vui lòng nhập câu hỏi" in str(e)


@patch("app.services.tax_rule.tax_chat_service.genai.Client")
def test_tax_chat_ask_stream_success(mock_client_class, mock_repo, mock_history_repo):
    mock_client = MagicMock()
    chunk1 = MagicMock()
    chunk1.text = "Thuế TNCN "
    chunk2 = MagicMock()
    chunk2.text = "năm 2026."
    mock_client.models.generate_content_stream.return_value = [chunk1, chunk2]
    mock_client_class.return_value = mock_client

    service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
    service.client = mock_client

    chunks = list(service.ask_stream(
        question="Tính thuế 2026",
        session_id=None,
        tax_year=2026,
        user_id=uuid.uuid4()
    ))

    assert "".join(chunks) == "Thuế TNCN năm 2026."
    mock_history_repo.save_message.assert_called()


def test_tax_chat_ask_stream_empty_question(mock_repo, mock_history_repo):
    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
        with pytest.raises(ValueError):
            list(service.ask_stream(question="   "))


def test_tax_chat_get_session_and_update_title(mock_repo, mock_history_repo):
    session_id = uuid.uuid4()
    mock_history_repo.get_session.return_value = ChatSession(id=session_id, title="Old")
    mock_history_repo.update_session_title.return_value = ChatSession(id=session_id, title="New")

    with patch("app.services.tax_rule.tax_chat_service.genai.Client"):
        service = TaxChatService(repository=mock_repo, history_repository=mock_history_repo)
        sess = service.get_session(session_id)
        assert sess is not None
        assert sess.title == "Old"

        updated = service.update_session_title(session_id, "New")
        assert updated is not None
        assert updated.title == "New"

        service_no_repo = TaxChatService(repository=mock_repo, history_repository=None)
        assert service_no_repo.get_session(session_id) is None
        assert service_no_repo.update_session_title(session_id, "New") is None


def test_tax_calculator_pit_2026():
    from app.services.tax_rule.tax_calculator import TaxCalculator
    # Lương 80 triệu, 2 người phụ thuộc, năm 2026 (giống bài toán thực tế)
    res = TaxCalculator.calculate_pit(
        monthly_salary=80_000_000,
        dependents_count=2,
        insurance_amount=8_400_000,
        tax_year=2026
    )
    assert res["personal_deduction"] == 15_500_000
    assert res["dependents_deduction"] == 12_400_000
    assert res["assessable_income"] == 43_700_000
    # Bậc 1: 10m x 5% = 500k
    # Bậc 2: 20m x 10% = 2,000k
    # Bậc 3: 13.7m x 20% = 2,740k
    # Tổng thuế = 5,240,000 VND
    assert res["total_tax"] == 5_240_000
    assert res["net_income"] == 66_360_000


def test_tax_calculator_pit_2025():
    from app.services.tax_rule.tax_calculator import TaxCalculator
    # Lương 25 triệu, không người phụ thuộc, năm 2025
    res = TaxCalculator.calculate_pit(
        monthly_salary=25_000_000,
        dependents_count=0,
        insurance_amount=2_625_000,
        tax_year=2025
    )
    assert res["personal_deduction"] == 11_000_000
    assert res["dependents_deduction"] == 0
    # TNTT = 25 - 11 - 2.625 = 11,375,000
    assert res["assessable_income"] == 11_375_000
    # Bậc 1 (đến 5tr, 5%): 250k
    # Bậc 2 (5-10tr, 10%): 500k
    # Bậc 3 (10-18tr, 15%): 1,375k x 15% = 206,250
    # Tổng = 956,250 VND
    assert res["total_tax"] == 956_250


def test_tax_calculator_zero_income():
    from app.services.tax_rule.tax_calculator import TaxCalculator
    res = TaxCalculator.calculate_pit(monthly_salary=0, dependents_count=0)
    assert res["assessable_income"] == 0
    assert res["total_tax"] == 0
    assert res["net_income"] == 0


def test_tax_chat_ask_cache_hit(mock_repo, mock_history_repo):
    mock_redis = MagicMock()
    mock_redis.get.return_value = "Câu trả lời từ Redis Cache"

    with patch("app.services.tax_rule.tax_chat_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        service = TaxChatService(
            repository=mock_repo,
            history_repository=mock_history_repo,
            redis_client=mock_redis
        )

        res = service.ask(
            question="Mức giảm trừ gia cảnh là bao nhiêu?",
            session_id=None,
            tax_year=2026
        )

        assert res["cached"] is True
        assert res["answer"] == "Câu trả lời từ Redis Cache"
        # Đảm bảo KHÔNG gọi Gemini API khi đã trúng cache
        assert not mock_client.models.generate_content.called
        # Vẫn lưu vào database của session
        assert mock_history_repo.save_message.called


def test_tax_chat_ask_cache_miss_saves_to_cache(mock_repo, mock_history_repo):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # Cache miss

    with patch("app.services.tax_rule.tax_chat_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Câu trả lời mới từ Gemini"
        mock_client.models.generate_content.return_value = mock_response
        mock_client_cls.return_value = mock_client

        service = TaxChatService(
            repository=mock_repo,
            history_repository=mock_history_repo,
            redis_client=mock_redis
        )

        res = service.ask(
            question="Mức giảm trừ gia cảnh là bao nhiêu?",
            session_id=None,
            tax_year=2026
        )

        assert res["cached"] is False
        assert res["answer"] == "Câu trả lời mới từ Gemini"
        # Đảm bảo gọi hàm setex lưu vào cache
        assert mock_redis.setex.called


def test_tax_chat_ask_stream_cache_hit(mock_repo, mock_history_repo):
    mock_redis = MagicMock()
    mock_redis.get.return_value = "Câu trả lời stream từ Redis Cache"

    with patch("app.services.tax_rule.tax_chat_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        service = TaxChatService(
            repository=mock_repo,
            history_repository=mock_history_repo,
            redis_client=mock_redis
        )

        chunks = list(service.ask_stream(
            question="Mức giảm trừ gia cảnh là bao nhiêu?",
            session_id=None,
            tax_year=2026
        ))

        assert "".join(chunks) == "Câu trả lời stream từ Redis Cache"
        assert not mock_client.models.generate_content_stream.called



