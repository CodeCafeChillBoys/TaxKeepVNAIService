import uuid
import pytest
from unittest.mock import MagicMock

from app.models.ai_extraction_models import SystemConfig
from app.services.system_config.system_config_service import SystemConfigService
from app.schemas.system_config.system_config_schema import (
    SystemConfigCreateRequest,
    SystemConfigUpdateRequest
)
from app.enum.system_config_enum import ConfigDataType


# ==============================================================================
# 1. Test _detect_data_type() & _validate_value_by_type()
# ==============================================================================
def test_detect_data_type():
    service = SystemConfigService(repo=MagicMock())

    assert service._detect_data_type("true") == ConfigDataType.BOOLEAN
    assert service._detect_data_type("FALSE") == ConfigDataType.BOOLEAN
    assert service._detect_data_type("123") == ConfigDataType.INT
    assert service._detect_data_type("-10") == ConfigDataType.INT
    assert service._detect_data_type("0.85") == ConfigDataType.FLOAT
    assert service._detect_data_type("0,95") == ConfigDataType.FLOAT
    assert service._detect_data_type('{"key": "value"}') == ConfigDataType.JSON
    assert service._detect_data_type('["item1", "item2"]') == ConfigDataType.JSON
    assert service._detect_data_type("doc1, doc2, doc3") == ConfigDataType.LIST_STRING
    assert service._detect_data_type("Normal plain text") == ConfigDataType.STRING


def test_validate_value_by_type_success():
    service = SystemConfigService(repo=MagicMock())

    assert service._validate_value_by_type("0,85", ConfigDataType.FLOAT) == "0.85"
    assert service._validate_value_by_type("100", ConfigDataType.INT) == "100"
    assert service._validate_value_by_type("TRUE", ConfigDataType.BOOLEAN) == "true"
    assert service._validate_value_by_type("0", ConfigDataType.BOOLEAN) == "false"
    assert service._validate_value_by_type('{"valid": true}', ConfigDataType.JSON) == '{"valid": true}'
    assert service._validate_value_by_type("raw", ConfigDataType.STRING) == "raw"


def test_validate_value_by_type_errors():
    service = SystemConfigService(repo=MagicMock())

    with pytest.raises(ValueError, match="không phải là số thực"):
        service._validate_value_by_type("abc", ConfigDataType.FLOAT)

    with pytest.raises(ValueError, match="không phải là số nguyên"):
        service._validate_value_by_type("12.5", ConfigDataType.INT)

    with pytest.raises(ValueError, match="Giá trị BOOLEAN phải là"):
        service._validate_value_by_type("not_bool", ConfigDataType.BOOLEAN)

    with pytest.raises(ValueError, match="không đúng cấu trúc JSON"):
        service._validate_value_by_type("{broken json", ConfigDataType.JSON)


# ==============================================================================
# 2. Test create_config()
# ==============================================================================
def test_create_config_success():
    mock_repo = MagicMock()
    mock_repo.get_by_key.return_value = None
    mock_repo.save.side_effect = lambda cfg: cfg
    service = SystemConfigService(repo=mock_repo)

    dto = SystemConfigCreateRequest(
        config_key="THRESHOLD_OCR",
        config_value="0.90",
        description="Ngưỡng OCR"
    )

    created = service.create_config(dto)
    assert created.config_key == "THRESHOLD_OCR"
    assert created.config_value == "0.9"
    assert created.data_type == ConfigDataType.FLOAT.value
    mock_repo.save.assert_called_once()


def test_create_config_duplicate_active():
    mock_repo = MagicMock()
    existing = SystemConfig(config_key="KEY", is_deleted=False)
    mock_repo.get_by_key.return_value = existing
    service = SystemConfigService(repo=mock_repo)

    dto = SystemConfigCreateRequest(config_key="KEY", config_value="10")
    with pytest.raises(ValueError, match="đã tồn tại"):
        service.create_config(dto)


def test_create_config_restore_previously_deleted():
    mock_repo = MagicMock()
    existing = SystemConfig(config_key="KEY", is_deleted=True, config_value="old")
    mock_repo.get_by_key.return_value = existing
    mock_repo.restore.side_effect = lambda cfg: cfg
    service = SystemConfigService(repo=mock_repo)

    dto = SystemConfigCreateRequest(config_key="KEY", config_value="new_val")
    restored = service.create_config(dto)

    assert restored.config_value == "new_val"
    mock_repo.restore.assert_called_once_with(existing)


# ==============================================================================
# 3. Test update_config()
# ==============================================================================
def test_update_config_not_found_or_deleted():
    mock_repo = MagicMock()
    mock_repo.get_by_key.return_value = None
    service = SystemConfigService(repo=mock_repo)

    assert service.update_config("NOT_EXIST", SystemConfigUpdateRequest(config_value="1")) is None

    # Đã bị xóa mềm
    mock_repo.get_by_key.return_value = SystemConfig(config_key="DEL", is_deleted=True)
    assert service.update_config("DEL", SystemConfigUpdateRequest(config_value="1")) is None


def test_update_config_success():
    mock_repo = MagicMock()
    config = SystemConfig(config_key="KEY", config_value="0.80", data_type="FLOAT", is_deleted=False)
    mock_repo.get_by_key.return_value = config
    mock_repo.save.side_effect = lambda cfg: cfg
    service = SystemConfigService(repo=mock_repo)

    dto = SystemConfigUpdateRequest(
        config_value="true",
        description="Đổi thành boolean",
        is_active=False
    )

    updated = service.update_config("KEY", dto)
    assert updated.config_value == "true"
    assert updated.data_type == ConfigDataType.BOOLEAN.value
    assert updated.description == "Đổi thành boolean"
    assert updated.is_active is False
    mock_repo.save.assert_called_once()


# ==============================================================================
# 4. Test delete_config() & restore_config()
# ==============================================================================
def test_delete_config():
    mock_repo = MagicMock()
    mock_repo.get_by_key.return_value = None
    service = SystemConfigService(repo=mock_repo)
    assert service.delete_config("KEY") is False

    config = SystemConfig(config_key="KEY", is_deleted=False)
    mock_repo.get_by_key.return_value = config
    assert service.delete_config("KEY") is True
    mock_repo.delete.assert_called_once_with(config)


def test_restore_config():
    mock_repo = MagicMock()
    mock_repo.get_by_key.return_value = None
    service = SystemConfigService(repo=mock_repo)
    assert service.restore_config("KEY") is None

    # Không bị xóa mềm -> ném ValueError
    active_config = SystemConfig(config_key="KEY", is_deleted=False)
    mock_repo.get_by_key.return_value = active_config
    with pytest.raises(ValueError, match="đang hoạt động bình thường"):
        service.restore_config("KEY")

    # Bị xóa mềm -> restore thành công
    deleted_config = SystemConfig(config_key="KEY", is_deleted=True)
    mock_repo.get_by_key.return_value = deleted_config
    mock_repo.restore.side_effect = lambda cfg: cfg
    restored = service.restore_config("KEY")
    assert restored == deleted_config


def test_get_all_get_by_key_and_test_resolve_threshold():
    mock_repo = MagicMock()
    mock_repo.get_all.return_value = ["cfg1"]
    mock_repo.get_by_key.return_value = "cfg1"
    mock_repo.get_system_threshold.return_value = 0.85
    service = SystemConfigService(repo=mock_repo)

    assert service.get_all_configs(active_only=True) == ["cfg1"]
    assert service.get_config_by_key("KEY") == "cfg1"

    res = service.test_resolve_threshold("MEDICAL")
    assert res["resolved_threshold"] == 0.85
    assert res["category_code"] == "MEDICAL"
