import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock, patch
import pytest

from app.models.ai_provider_key import AiProviderKey
from app.schemas.apiKey.ai_provider_key_schema import AiKeyCreateRequest, AiKeyUpdateRequest
from app.services.apiKey.ai_key_manager import AiKeyManager
from app.core.config import settings


def test_mask_key():
    assert AiKeyManager.mask_key("12345") == "******"
    assert AiKeyManager.mask_key("AIzaSyD-1234567890abcdef") == "AIzaSy...cdef"


def test_to_response_dto():
    key_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    entity = AiProviderKey(
        id=key_id,
        provider="GEMINI",
        key_name="TestKey",
        api_key="AIzaSyD1234567890abcdef",
        priority=1,
        is_active=True,
        status="ACTIVE",
        request_count=5,
        created_at=now,
        updated_at=now
    )
    dto = AiKeyManager.to_response_dto(entity)
    assert dto.id == key_id
    assert dto.key_name == "TestKey"
    assert dto.masked_api_key.startswith("AIzaSy")
    assert dto.request_count == 5


@patch("app.services.apiKey.ai_key_manager.genai.Client")
def test_test_gemini_key_success(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.return_value = MagicMock(text="pong")

    assert AiKeyManager.test_gemini_key("valid-key") is True


@patch("app.services.apiKey.ai_key_manager.genai.Client")
def test_test_gemini_key_failure(mock_client_cls):
    mock_client = MagicMock()
    mock_client_cls.return_value = mock_client
    mock_client.models.generate_content.side_effect = Exception("API key invalid")

    with pytest.raises(ValueError, match="API Key không hợp lệ"):
        AiKeyManager.test_gemini_key("invalid-key")


@patch.object(AiKeyManager, "test_gemini_key", return_value=True)
def test_create_key(mock_test_key):
    mock_db = MagicMock()
    payload = AiKeyCreateRequest(
        provider="GEMINI",
        key_name="Key Alpha",
        api_key="AIzaSy1234567890abcdef",
        priority=1
    )

    result = AiKeyManager.create_key(mock_db, payload)
    assert result.key_name == "Key Alpha"
    assert mock_db.add.called
    assert mock_db.commit.called


def test_get_all_keys():
    mock_db = MagicMock()
    key1 = AiProviderKey(
        id=uuid.uuid4(), provider="GEMINI", key_name="K1", api_key="AIzaSy1234567890abcdef",
        priority=1, is_active=True, status="ACTIVE", request_count=0,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_db.query.return_value.order_by.return_value.all.return_value = [key1]

    results = AiKeyManager.get_all_keys(mock_db)
    assert len(results) == 1
    assert results[0].key_name == "K1"


def test_update_key_found():
    mock_db = MagicMock()
    key_id = uuid.uuid4()
    key1 = AiProviderKey(
        id=key_id, provider="GEMINI", key_name="OldName", api_key="AIzaSy1234567890abcdef",
        priority=2, is_active=True, status="ACTIVE", request_count=0,
        created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc)
    )
    mock_db.query.return_value.filter.return_value.first.return_value = key1

    payload = AiKeyUpdateRequest(key_name="NewName", priority=1, is_active=False)
    updated = AiKeyManager.update_key(mock_db, key_id, payload)

    assert updated is not None
    assert updated.key_name == "NewName"
    assert key1.priority == 1
    assert key1.is_active is False
    assert mock_db.commit.called


def test_update_key_not_found():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.first.return_value = None

    payload = AiKeyUpdateRequest(key_name="NewName")
    assert AiKeyManager.update_key(mock_db, uuid.uuid4(), payload) is None


def test_delete_key():
    mock_db = MagicMock()
    key1 = AiProviderKey(id=uuid.uuid4(), key_name="K", api_key="abc")
    mock_db.query.return_value.filter.return_value.first.return_value = key1

    assert AiKeyManager.delete_key(mock_db, key1.id) is True
    assert mock_db.delete.called
    assert mock_db.commit.called

    # When not found
    mock_db.query.return_value.filter.return_value.first.return_value = None
    assert AiKeyManager.delete_key(mock_db, uuid.uuid4()) is False


@patch("app.services.apiKey.ai_key_manager.genai.Client")
def test_get_client_and_model_from_db(mock_client_cls):
    mock_db = MagicMock()
    key1 = AiProviderKey(
        id=uuid.uuid4(), provider="GEMINI", key_name="K1", api_key="AIzaKeyFromDB",
        priority=1, is_active=True, status="ACTIVE"
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = key1

    client, model = AiKeyManager.get_client_and_model(mock_db)
    mock_client_cls.assert_called_with(api_key="AIzaKeyFromDB")
    assert model == settings.GEMINI_MODEL


@patch("app.services.apiKey.ai_key_manager.genai.Client")
def test_get_client_and_model_fallback_env(mock_client_cls):
    # When DB has no keys
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.order_by.return_value.first.return_value = None

    client, model = AiKeyManager.get_client_and_model(mock_db)
    mock_client_cls.assert_called_with(api_key=settings.GEMINI_API_KEY)
    assert model == settings.GEMINI_MODEL


def test_execute_with_failover_db_success():
    mock_db = MagicMock()
    key1 = AiProviderKey(
        id=uuid.uuid4(), provider="GEMINI", key_name="K1", api_key="key1",
        priority=1, is_active=True, status="ACTIVE", request_count=0
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [key1]

    with patch("app.services.apiKey.ai_key_manager.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        def dummy_op(client, model):
            return "success_result"

        res = AiKeyManager.execute_with_failover(mock_db, dummy_op)
        assert res == "success_result"
        assert key1.request_count == 1
        assert key1.status == "ACTIVE"


def test_execute_with_failover_429_quota_switches_to_next():
    mock_db = MagicMock()
    key1 = AiProviderKey(
        id=uuid.uuid4(), provider="GEMINI", key_name="KeyFail", api_key="key1",
        priority=1, is_active=True, status="ACTIVE", request_count=0
    )
    key2 = AiProviderKey(
        id=uuid.uuid4(), provider="GEMINI", key_name="KeySuccess", api_key="key2",
        priority=2, is_active=True, status="ACTIVE", request_count=0
    )
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = [key1, key2]

    with patch("app.services.apiKey.ai_key_manager.genai.Client") as mock_client_cls:
        call_count = 0

        def dummy_op(client, model):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("429 ResourceExhausted: Quota exceeded for model")
            return "recovered_result"

        res = AiKeyManager.execute_with_failover(mock_db, dummy_op)
        assert res == "recovered_result"
        assert key1.status == "QUOTA_EXCEEDED"
        assert key1.cooldown_until is not None
        assert key2.status == "ACTIVE"
        assert key2.request_count == 1


def test_execute_with_failover_fallback_to_default_client():
    mock_default = MagicMock()
    mock_db = None

    def dummy_op(client, model):
        return f"result_with_{client}"

    res = AiKeyManager.execute_with_failover(mock_db, dummy_op, default_client=mock_default)
    assert res == f"result_with_{mock_default}"
