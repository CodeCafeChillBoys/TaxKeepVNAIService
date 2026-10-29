import uuid
import pytest
from unittest.mock import MagicMock

from app.models.url_validation_rule import UrlValidationRule
from app.services.url_rule.url_validation_service import UrlValidationService
from app.schemas.url_rule import UrlRuleCreateRequest, UrlRuleUpdateRequest


# ==============================================================================
# 1. Test hàm tiện ích _clean_domain()
# ==============================================================================
def test_clean_domain_utility():
    """
    Hàm _clean_domain phải loại bỏ http://, https://, www., path phía sau và port.
    """
    mock_repo = MagicMock()
    service = UrlValidationService(repo=mock_repo)

    assert service._clean_domain("https://www.chinhphu.vn/van-ban") == "chinhphu.vn"
    assert service._clean_domain("http://thuvienphapluat.vn:8080/home") == "thuvienphapluat.vn"
    assert service._clean_domain("   WWW.MOF.GOV.VN   ") == "mof.gov.vn"


# ==============================================================================
# 2. Test hàm nghiệp vụ chính: validate_url()
# ==============================================================================
def test_validate_url_empty_or_whitespace():
    """URL rỗng hoặc toàn khoảng trắng phải báo lỗi."""
    mock_repo = MagicMock()
    service = UrlValidationService(repo=mock_repo)

    is_valid, err_msg, rule = service.validate_url("")
    assert is_valid is False
    assert err_msg == "URL không được để trống."
    assert rule is None

    is_valid, err_msg, rule = service.validate_url("   ")
    assert is_valid is False
    assert err_msg == "URL không được để trống."


def test_validate_url_invalid_format_or_scheme():
    """URL không bắt đầu bằng http:// hoặc https:// phải báo lỗi định dạng."""
    mock_repo = MagicMock()
    service = UrlValidationService(repo=mock_repo)

    # Thiếu scheme http/https
    is_valid, err_msg, _ = service.validate_url("chinhphu.vn/van-ban")
    assert is_valid is False
    assert "URL không đúng định dạng" in err_msg

    # Dùng scheme ftp://
    is_valid, err_msg, _ = service.validate_url("ftp://chinhphu.vn/file.pdf")
    assert is_valid is False
    assert "URL không đúng định dạng" in err_msg


from unittest.mock import patch

def test_validate_url_parsing_exception():
    """Khi thư viện urlparse văng ngoại lệ bất ngờ, trả về thông báo không thể phân tích cú pháp."""
    mock_repo = MagicMock()
    service = UrlValidationService(repo=mock_repo)

    with patch("app.services.url_rule.url_validation_service.urlparse", side_effect=Exception("Crash")):
        is_valid, err_msg, _ = service.validate_url("https://anything.com")
        assert is_valid is False
        assert err_msg == "Không thể phân tích cú pháp URL."



def test_validate_url_no_active_rules_in_db():
    """Nếu trong DB chưa cấu hình rule nào, mặc định cho qua nếu đúng cú pháp URL."""
    mock_repo = MagicMock()
    mock_repo.get_active_rules.return_value = []
    service = UrlValidationService(repo=mock_repo)

    is_valid, err_msg, rule = service.validate_url("https://example.com/law.pdf")
    assert is_valid is True
    assert err_msg is None
    assert rule is None


def test_validate_url_matched_exact_domain():
    """URL khớp chính xác domain đã được cấp phép."""
    mock_repo = MagicMock()
    approved_rule = UrlValidationRule(name="Thư viện pháp luật", domain="thuvienphapluat.vn")
    mock_repo.get_active_rules.return_value = [approved_rule]
    service = UrlValidationService(repo=mock_repo)

    is_valid, err_msg, rule = service.validate_url("https://www.thuvienphapluat.vn/van-ban/thue-2026.pdf")
    assert is_valid is True
    assert err_msg is None
    assert rule == approved_rule



def test_validate_url_matched_subdomain():
    """URL là subdomain của domain đã duyệt (vd: vanban.chinhphu.vn khớp chinhphu.vn)."""
    mock_repo = MagicMock()
    approved_rule = UrlValidationRule(name="Cổng chính phủ", domain="chinhphu.vn")
    mock_repo.get_active_rules.return_value = [approved_rule]
    service = UrlValidationService(repo=mock_repo)

    is_valid, err_msg, rule = service.validate_url("https://vanban.chinhphu.vn/thong-tu-01")
    assert is_valid is True
    assert err_msg is None
    assert rule == approved_rule


def test_validate_url_unapproved_domain():
    """URL hợp lệ nhưng không nằm trong danh sách được cấp phép."""
    mock_repo = MagicMock()
    approved_rule = UrlValidationRule(name="Cổng chính phủ", domain="chinhphu.vn")
    # Có 1 rule nhưng domain rỗng để test nhánh if not target_domain: continue
    empty_domain_rule = UrlValidationRule(name="Rule rỗng", domain="")
    mock_repo.get_active_rules.return_value = [empty_domain_rule, approved_rule]
    service = UrlValidationService(repo=mock_repo)

    is_valid, err_msg, rule = service.validate_url("https://facebook.com/fake-law")
    assert is_valid is False
    assert "URL nguồn không thuộc danh sách tên miền/nguồn được phê duyệt" in err_msg
    assert rule is None


# ==============================================================================
# 3. Test các hàm CRUD của Admin
# ==============================================================================
def test_get_all_rules():
    """get_all_rules() ủy quyền gọi sang repo.get_all()."""
    mock_repo = MagicMock()
    service = UrlValidationService(repo=mock_repo)
    dummy_rules = [UrlValidationRule(name="R1", domain="d1.com")]
    mock_repo.get_all.return_value = dummy_rules

    result = service.get_all_rules(active_only=True)
    assert result == dummy_rules
    mock_repo.get_all.assert_called_once_with(active_only=True)


def test_create_rule():
    """create_rule() chuẩn hóa domain và gọi repo.create()."""
    mock_repo = MagicMock()
    service = UrlValidationService(repo=mock_repo)
    dto = UrlRuleCreateRequest(
        name="Thư viện pháp luật",
        domain="https://www.thuvienphapluat.vn/home",
        description="Nguồn luật",
        isActive=True
    )

    service.create_rule(dto)

    mock_repo.create.assert_called_once()
    saved_rule = mock_repo.create.call_args[0][0]
    assert saved_rule.name == "Thư viện pháp luật"
    # Domain phải được chuẩn hóa bỏ https và www
    assert saved_rule.domain == "thuvienphapluat.vn"


def test_update_rule_not_found():
    """Khi ID không tồn tại trong repo, trả về None."""
    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = None
    service = UrlValidationService(repo=mock_repo)

    dto = UrlRuleUpdateRequest(name="Tên mới")
    result = service.update_rule(uuid.uuid4(), dto)
    assert result is None
    mock_repo.update.assert_not_called()


def test_update_rule_success():
    """Cập nhật các trường của rule và gọi repo.update()."""
    mock_repo = MagicMock()
    rule_id = uuid.uuid4()
    existing_rule = UrlValidationRule(id=rule_id, name="Cũ", domain="old.com")
    mock_repo.get_by_id.return_value = existing_rule
    mock_repo.update.return_value = existing_rule
    service = UrlValidationService(repo=mock_repo)

    dto = UrlRuleUpdateRequest(
        name="Mới",
        domain="https://new.com/path",
        description="Mô tả mới",
        isActive=False,
        updatedBy=uuid.uuid4()
    )

    result = service.update_rule(rule_id, dto)

    assert result == existing_rule
    assert existing_rule.name == "Mới"
    assert existing_rule.domain == "new.com"
    assert existing_rule.description == "Mô tả mới"
    assert existing_rule.is_active is False
    mock_repo.update.assert_called_once_with(existing_rule)


def test_delete_rule_not_found():
    """delete_rule() trả về False nếu không tìm thấy ID."""
    mock_repo = MagicMock()
    mock_repo.get_by_id.return_value = None
    service = UrlValidationService(repo=mock_repo)

    assert service.delete_rule(uuid.uuid4()) is False
    mock_repo.delete.assert_not_called()


def test_delete_rule_success():
    """delete_rule() gọi repo.delete() và trả về True khi tìm thấy ID."""
    mock_repo = MagicMock()
    rule_id = uuid.uuid4()
    existing_rule = UrlValidationRule(id=rule_id, name="R1", domain="d.com")
    mock_repo.get_by_id.return_value = existing_rule
    service = UrlValidationService(repo=mock_repo)

    assert service.delete_rule(rule_id) is True
    mock_repo.delete.assert_called_once_with(existing_rule)
