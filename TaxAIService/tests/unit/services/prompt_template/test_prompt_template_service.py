from unittest.mock import MagicMock, patch
import pytest

from app.models.ai_prompt_template import AiPromptTemplate
from app.schemas.prompt_template.prompt_template_schema import (
    PromptTemplateCreateRequest,
    PromptTemplateUpdateRequest
)
from app.services.prompt_template.prompt_template_service import PromptTemplateService


@pytest.fixture
def mock_repo():
    return MagicMock()


@pytest.fixture
def service(mock_repo):
    return PromptTemplateService(repository=mock_repo)


@patch("app.services.prompt_template.prompt_template_service.get_redis_client")
def test_get_rendered_prompt_from_redis(mock_redis_getter, service, mock_repo):
    mock_redis = MagicMock()
    mock_redis.get.return_value = "Hello {name}, tax year is {year}."
    mock_redis_getter.return_value = mock_redis

    rendered = service.get_rendered_prompt(
        prompt_key="TEST_PROMPT",
        default_template="Default {name}",
        params={"name": "Alice", "year": 2026}
    )

    assert rendered == "Hello Alice, tax year is 2026."
    mock_repo.get_by_key.assert_not_called()


@patch("app.services.prompt_template.prompt_template_service.get_redis_client")
def test_get_rendered_prompt_from_db_and_cached(mock_redis_getter, service, mock_repo):
    mock_redis = MagicMock()
    mock_redis.get.return_value = None  # Cache miss
    mock_redis_getter.return_value = mock_redis

    template_record = AiPromptTemplate(
        prompt_key="TEST_PROMPT",
        system_prompt="DB Prompt for {role}: {detail}",
        is_active=True
    )
    mock_repo.get_by_key.return_value = template_record

    rendered = service.get_rendered_prompt(
        prompt_key="TEST_PROMPT",
        default_template="Default",
        params={"role": "User", "detail": "Test Detail"}
    )

    assert rendered == "DB Prompt for User: Test Detail"
    mock_repo.get_by_key.assert_called_with("TEST_PROMPT", active_only=True)
    mock_redis.setex.assert_called_once()


@patch("app.services.prompt_template.prompt_template_service.get_redis_client")
def test_get_rendered_prompt_fallback_default(mock_redis_getter, service, mock_repo):
    mock_redis_getter.return_value = None
    mock_repo.get_by_key.return_value = None

    rendered = service.get_rendered_prompt(
        prompt_key="UNKNOWN",
        default_template="Default fallback {val}",
        params={"val": 123}
    )

    assert rendered == "Default fallback 123"


def test_get_all(service, mock_repo):
    mock_repo.get_all.return_value = [AiPromptTemplate(prompt_key="P1")]
    res = service.get_all(active_only=True)
    assert len(res) == 1
    mock_repo.get_all.assert_called_with(active_only=True)


def test_get_by_key(service, mock_repo):
    mock_repo.get_by_key.return_value = AiPromptTemplate(prompt_key="P1")
    res = service.get_by_key("P1")
    assert res.prompt_key == "P1"
    mock_repo.get_by_key.assert_called_with("P1", active_only=False)


@patch.object(PromptTemplateService, "clear_cache")
def test_create_success(mock_clear_cache, service, mock_repo):
    mock_repo.get_by_key.return_value = None  # Not existing
    created_tpl = AiPromptTemplate(prompt_key="NEW_KEY", system_prompt="Content", is_active=True, version=1)
    mock_repo.save.return_value = created_tpl

    payload = PromptTemplateCreateRequest(
        prompt_key="new_key",
        system_prompt="Content",
        description="Desc",
        variables=["var1"],
        is_active=True
    )
    result = service.create(payload)

    assert result.prompt_key == "NEW_KEY"
    mock_clear_cache.assert_called_with("NEW_KEY")


def test_create_duplicate_raises_error(service, mock_repo):
    mock_repo.get_by_key.return_value = AiPromptTemplate(prompt_key="EXISTING")
    payload = PromptTemplateCreateRequest(prompt_key="EXISTING", system_prompt="Content")

    with pytest.raises(ValueError, match="đã tồn tại"):
        service.create(payload)


@patch.object(PromptTemplateService, "clear_cache")
def test_update_success(mock_clear_cache, service, mock_repo):
    existing = AiPromptTemplate(prompt_key="P1", system_prompt="Old", version=1)
    mock_repo.get_by_key.return_value = existing
    mock_repo.save.side_effect = lambda x: x

    payload = PromptTemplateUpdateRequest(system_prompt="New content", description="New desc", is_active=False)
    updated = service.update("P1", payload)

    assert updated.system_prompt == "New content"
    assert updated.version == 2
    assert updated.is_active is False
    mock_clear_cache.assert_called_with("P1")


def test_update_not_found(service, mock_repo):
    mock_repo.get_by_key.return_value = None
    payload = PromptTemplateUpdateRequest(system_prompt="New content")

    with pytest.raises(ValueError, match="Không tìm thấy"):
        service.update("UNKNOWN", payload)


@patch.object(PromptTemplateService, "clear_cache")
def test_delete_success(mock_clear_cache, service, mock_repo):
    existing = AiPromptTemplate(prompt_key="P1")
    mock_repo.get_by_key.return_value = existing

    res = service.delete("P1")
    assert res is True
    mock_repo.delete.assert_called_with(existing)
    mock_clear_cache.assert_called_with("P1")


def test_delete_not_found(service, mock_repo):
    mock_repo.get_by_key.return_value = None
    assert service.delete("UNKNOWN") is False


@patch("app.services.prompt_template.prompt_template_service.get_redis_client")
def test_clear_cache(mock_redis_getter, service):
    mock_redis = MagicMock()
    mock_redis_getter.return_value = mock_redis

    service.clear_cache("KEY1")
    mock_redis.delete.assert_called_with("ai:prompt:KEY1")

    # Clear all
    mock_redis.keys.return_value = ["ai:prompt:KEY1", "ai:prompt:KEY2"]
    service.clear_cache(None)
    mock_redis.delete.assert_called_with("ai:prompt:KEY1", "ai:prompt:KEY2")
