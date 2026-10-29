import uuid
import pytest
from unittest.mock import MagicMock
from app.models.url_validation_rule import UrlValidationRule
from app.repositories.url_rule.url_rule_repository import UrlRuleRepository

# ==============================================================================
# Test 1: Hàm create() - Thêm mới rule
# ==============================================================================
def test_create_url_rule():
    """
    Khi gọi repo.create(rule):
    - db.add(rule) phải được gọi 1 lần
    - db.commit() phải được gọi 1 lần
    - db.refresh(rule) phải được gọi 1 lần
    - Kết quả trả về chính là rule đó
    """
    # Arrange
    mock_db = MagicMock()
    repo = UrlRuleRepository(db=mock_db)
    dummy_rule = UrlValidationRule(name="Domain chính phủ", domain="chinhphu.vn", description="Domain chính phủ")
    
    # 2. Act: Gọi hàm create
    result = repo.create(dummy_rule)
    
    # 3. Assert: Kiểm tra xem các hàm của SQLAlchemy đã được gọi đúng chưa
    mock_db.add.assert_called_once_with(dummy_rule)
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(dummy_rule)
    assert result == dummy_rule
    
    
# ==============================================================================
# Test 2: Hàm get_by_id() - Tìm kiếm theo ID
# ==============================================================================
def test_get_by_id():
    """
    Khi gọi repo.get_by_id(rule_id):
    - db.query() phải truy vấn đúng Model UrlValidationRule
    """
    # Arrange
    mock_db = MagicMock()
    repo = UrlRuleRepository(db=mock_db)
    test_id = uuid.uuid4()
    # Act
    repo.get_by_id(test_id)
    
    # Assert: Xác nhận query đúng bảng UrlValidationRule
    mock_db.query.assert_called_once_with(UrlValidationRule)
    
    
# ==============================================================================
# Test 3: Hàm delete() - Xóa mềm (Soft Delete)
# ==============================================================================

def test_delete_url_rule_soft_delete():
    """
    Trong url_rule_repository.py, hàm delete() không xóa vĩnh viễn khỏi DB,
    mà thực hiện soft delete:
    - is_active chuyển thành False
    - is_deleted chuyển thành True
    - deleted_at được gán thời gian
    - Gọi db.commit() và db.refresh()
    """
    # Arrange
    mock_db = MagicMock()
    repo = UrlRuleRepository(db=mock_db)
    rule = UrlValidationRule(is_active=True, is_deleted=False)
    
    # Act
    repo.delete(rule)
    
    # Assert
    assert rule.is_active is False
    assert rule.is_deleted is True
    assert rule.deleted_at is not None
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(rule)
    
# ==============================================================================
# Test 4: Hàm update() - Cập nhật thay đổi
# ==============================================================================
def test_update_url_rule():
    """
    Khi gọi repo.update(rule):
    - Phải gọi db.commit() và db.refresh(rule)
    - Trả về chính rule đã được cập nhật
    """
    # 1. Arrange
    mock_db = MagicMock()
    repo = UrlRuleRepository(db=mock_db)
    rule = UrlValidationRule(name="Luật cũ", domain="old-domain.com")
    rule.domain = "new-domain.com"  # Giả sử vừa thay đổi domain
    
    # 2. Act
    result = repo.update(rule)
    # 3. Assert
    mock_db.commit.assert_called_once()
    mock_db.refresh.assert_called_once_with(rule)
    assert result == rule
    assert result.domain == "new-domain.com"
    
# ==============================================================================
# Test 5: Hàm get_all() với active_only = False (Mặc định)
# ==============================================================================
def test_get_all_url_rules_without_filter():
    """
    Khi active_only=False:
    - KHÔNG ĐƯỢC gọi filter()
    - Phải gọi order_by() và all()
    """
    # 1. Arrange
    mock_db = MagicMock()
    repo = UrlRuleRepository(db=mock_db)
    dummy_list = [
        UrlValidationRule(name="Domain 1", domain="domain1.com"),
        UrlValidationRule(name="Domain 2", domain="domain2.com")
    ]
    # Giả lập kết quả trả về của chuỗi gọi hàm .order_by().all()
    mock_db.query.return_value.order_by.return_value.all.return_value = dummy_list
    # 2. Act
    result = repo.get_all(active_only=False)
    # 3. Assert
    mock_db.query.assert_called_once_with(UrlValidationRule)
    # Xác nhận KHÔNG gọi filter
    mock_db.query.return_value.filter.assert_not_called()
    assert result == dummy_list
    assert len(result) == 2
    
# ==============================================================================
# Test 6: Hàm get_all() với active_only = True
# ==============================================================================
def test_get_all_url_rules_active_only():
    """
    Khi active_only=True:
    - BẮT BUỘC phải gọi filter(UrlValidationRule.is_active.is_(True))
    """
    # 1. Arrange
    mock_db = MagicMock()
    repo = UrlRuleRepository(db=mock_db)
    dummy_active_list = [UrlValidationRule(name="Active Domain", domain="active.com", is_active=True)]
    
    # Giả lập chuỗi query.filter().order_by().all()
    mock_query = mock_db.query.return_value
    mock_query.filter.return_value.order_by.return_value.all.return_value = dummy_active_list
    # 2. Act
    result = repo.get_all(active_only=True)
    # 3. Assert
    mock_db.query.assert_called_once_with(UrlValidationRule)
    # Xác nhận ĐÃ gọi filter
    mock_query.filter.assert_called_once()
    assert result == dummy_active_list


# ==============================================================================
# Test 7: Hàm get_active_rules()
# ==============================================================================
def test_get_active_rules():
    """
    Kiểm tra get_active_rules():
    - Truy vấn UrlValidationRule
    - Gọi filter() và all()
    """
    # 1. Arrange
    mock_db = MagicMock()
    repo = UrlRuleRepository(db=mock_db)
    expected_rules = [UrlValidationRule(name="Legal Domain", domain="legal.gov.vn", is_active=True)]
    
    # Giả lập query.filter().all()
    mock_db.query.return_value.filter.return_value.all.return_value = expected_rules
    # 2. Act
    result = repo.get_active_rules()
    # 3. Assert
    mock_db.query.assert_called_once_with(UrlValidationRule)
    mock_db.query.return_value.filter.return_value.all.assert_called_once()
    assert result == expected_rules

    



