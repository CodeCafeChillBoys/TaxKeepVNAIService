import uuid
import pytest
from unittest.mock import MagicMock

from app.models.ai_extraction_models import SystemConfig
from app.repositories.system_config.system_config_repository import SystemConfigRepository


# ==============================================================================
# 1. Test get_by_key() và get_all()
# ==============================================================================
def test_get_by_key():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)

    dummy_config = SystemConfig(config_key="THRESHOLD_OCR", config_value="0.85")
    mock_db.query.return_value.filter.return_value.filter.return_value.first.return_value = dummy_config

    result = repo.get_by_key("THRESHOLD_OCR", active_only=True)
    assert result == dummy_config

    # active_only=False
    mock_db.query.return_value.filter.return_value.first.return_value = dummy_config
    result_all = repo.get_by_key("THRESHOLD_OCR", active_only=False)
    assert result_all == dummy_config


def test_get_all():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)

    dummy_list = [SystemConfig(config_key="K1", config_value="V1")]
    mock_db.query.return_value.order_by.return_value.all.return_value = dummy_list

    # active_only=False
    res = repo.get_all(active_only=False)
    assert res == dummy_list

    # active_only=True
    mock_db.query.return_value.filter.return_value.order_by.return_value.all.return_value = dummy_list
    res_active = repo.get_all(active_only=True)
    assert res_active == dummy_list


# ==============================================================================
# 2. Test get_float_value()
# ==============================================================================
def test_get_float_value_valid_and_comma_format():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)

    # 1. Float chuẩn '0.85'
    repo.get_by_key = MagicMock(return_value=SystemConfig(config_key="KEY1", config_value="0.85"))
    assert repo.get_float_value("KEY1") == 0.85

    # 2. Float dùng dấu phẩy '0,90'
    repo.get_by_key = MagicMock(return_value=SystemConfig(config_key="KEY2", config_value="0,90"))
    assert repo.get_float_value("KEY2") == 0.90


def test_get_float_value_fallback_on_invalid_or_out_of_bounds():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)

    # 1. Không tìm thấy key -> dùng default 0.80
    repo.get_by_key = MagicMock(return_value=None)
    assert repo.get_float_value("NOT_EXIST", default=0.75) == 0.75

    # 2. Giá trị ngoài khoảng [0.0, 1.0] (ví dụ: 1.5)
    repo.get_by_key = MagicMock(return_value=SystemConfig(config_key="KEY3", config_value="1.5"))
    assert repo.get_float_value("KEY3", default=0.80) == 0.80

    # 3. Giá trị là chuỗi không hợp lệ (ví dụ: 'abc')
    repo.get_by_key = MagicMock(return_value=SystemConfig(config_key="KEY4", config_value="abc"))
    assert repo.get_float_value("KEY4", default=0.80) == 0.80


# ==============================================================================
# 3. Test get_system_threshold() theo 3 tầng ưu tiên
# ==============================================================================
def test_get_system_threshold_hierarchy():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)

    # Tầng 1: Có cấu hình riêng cho category
    repo.get_by_key = MagicMock(side_effect=lambda key, **kwargs: (
        SystemConfig(config_key="THRESHOLD_MEDICAL", config_value="0.95") if key == "THRESHOLD_MEDICAL" else None
    ))
    repo.get_float_value = MagicMock(return_value=0.95)
    assert repo.get_system_threshold(category_code="MEDICAL") == 0.95

    # Tầng 2: Không có riêng cho category, có cấu hình chung AI_CONFIDENCE_THRESHOLD
    repo.get_by_key = MagicMock(side_effect=lambda key, **kwargs: (
        SystemConfig(config_key="AI_CONFIDENCE_THRESHOLD", config_value="0.88") if key == "AI_CONFIDENCE_THRESHOLD" else None
    ))
    repo.get_float_value = MagicMock(return_value=0.88)
    assert repo.get_system_threshold(category_code="DONATION") == 0.88

    # Tầng 3: Không có gì trong DB -> fallback default 0.80
    repo.get_by_key = MagicMock(return_value=None)
    assert repo.get_system_threshold(category_code=None, default=0.80) == 0.80


# ==============================================================================
# 4. Test get_crucial_fields()
# ==============================================================================
def test_get_crucial_fields():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)

    # Có cấu hình trường theo category
    repo.get_by_key = MagicMock(return_value=SystemConfig(
        config_key="CRUCIAL_FIELDS_MEDICAL",
        config_value="hospital_name, patient_name, total_fee"
    ))
    fields = repo.get_crucial_fields("MEDICAL")
    assert fields == {"hospital_name", "patient_name", "total_fee"}

    # Không có key trong DB -> trả về bộ mặc định
    repo.get_by_key = MagicMock(return_value=None)
    default_fields = repo.get_crucial_fields(None)
    assert "total_amount" in default_fields
    assert "seller_tax_code" in default_fields

    # Category không có -> fallback về CRUCIAL_EXTRACTION_FIELDS
    repo.get_by_key = MagicMock(side_effect=lambda key, **kwargs: (
        SystemConfig(config_value="fallback_f1, fallback_f2") if key == "CRUCIAL_EXTRACTION_FIELDS" else None
    ))
    fb_fields = repo.get_crucial_fields("UNKNOWN_CAT")
    assert fb_fields == {"fallback_f1", "fallback_f2"}

    # Bị exception trong try block -> trả về mặc định
    repo.get_by_key = MagicMock(side_effect=Exception("DB error"))
    assert "total_amount" in repo.get_crucial_fields("CAT")



# ==============================================================================
# 5. Test CRUD: save(), delete(), restore()
# ==============================================================================
def test_save_config():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)
    config = SystemConfig(config_key="K1", config_value="V1")

    saved = repo.save(config)
    assert saved == config
    mock_db.add.assert_called_once_with(config)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(config)


def test_soft_delete_and_restore():
    mock_db = MagicMock()
    repo = SystemConfigRepository(db=mock_db)
    config = SystemConfig(config_key="K1", config_value="V1", is_active=True, is_deleted=False)

    # 1. Soft delete
    repo.delete(config)
    assert config.is_active is False
    assert config.is_deleted is True
    assert config.deleted_at is not None
    mock_db.commit.assert_called_once()

    # 2. Restore
    mock_db.commit.reset_mock()
    repo.restore(config)
    assert config.is_active is True
    assert config.is_deleted is False
    assert config.deleted_at is None
    mock_db.commit.assert_called_once()
