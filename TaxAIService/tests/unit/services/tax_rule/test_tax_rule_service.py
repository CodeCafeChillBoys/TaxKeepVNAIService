import uuid
import pytest
from unittest.mock import MagicMock, AsyncMock
from fastapi import HTTPException

from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.services.tax_rule.tax_rule_service import TaxRuleService
from app.errors.tax_rule_errors import TaxRuleErrorMessages, TaxRuleServiceError
from app.enum import TaxRuleStatus


# ==============================================================================
# 1. Test get_all_rule_sets()
# ==============================================================================
def test_service_get_all_rule_sets():
    """Lấy danh sách tất cả bộ quy tắc thuế và format đúng trường."""
    mock_repo = MagicMock()
    service = TaxRuleService(repository=mock_repo)

    rs = TaxRuleSet(
        rule_set_id=uuid.uuid4(),
        admin_id=uuid.uuid4(),
        name="Luật 2026",
        tax_year=2026,
        status="DRAFT"
    )
    mock_repo.get_all_rule_sets.return_value = [rs]

    result = service.get_all_rule_sets()

    assert len(result) == 1
    assert result[0]["name"] == "Luật 2026"
    assert result[0]["taxYear"] == 2026
    assert result[0]["ruleSetId"] == rs.rule_set_id


# ==============================================================================
# 2. Test get_tax_rule_set_detail() & by_year()
# ==============================================================================
def test_service_get_detail_not_found():
    """Khi ID không tồn tại trong repo, bắn HTTPException 404."""
    mock_repo = MagicMock()
    mock_repo.get_tax_rule_set_detail.return_value = None
    service = TaxRuleService(repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        service.get_tax_rule_set_detail(uuid.uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == TaxRuleErrorMessages.RULE_SET_NOT_FOUND


def test_service_get_detail_by_year_not_found():
    """Khi năm tính thuế không tồn tại trong repo, bắn HTTPException 404."""
    mock_repo = MagicMock()
    mock_repo.get_tax_rule_set_detail_by_year.return_value = None
    service = TaxRuleService(repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        service.get_tax_rule_set_detail_by_year(2099)

    assert exc_info.value.status_code == 404
    assert "2099" in exc_info.value.detail


def test_service_get_detail_success():
    """Khi tìm thấy, trả về message thành công và data đã được format."""
    mock_repo = MagicMock()
    rule_set_id = uuid.uuid4()
    rs = TaxRuleSet(rule_set_id=rule_set_id, name="Luật 2026", tax_year=2026, status="DRAFT")
    rule = TaxRule(rule_id=uuid.uuid4(), rule_code="PIT_01", rule_name="Giảm trừ", rule_type="DEDUCTION")

    mock_repo.get_tax_rule_set_detail.return_value = (rs, [rule], [])
    service = TaxRuleService(repository=mock_repo)

    res = service.get_tax_rule_set_detail(rule_set_id)

    assert res["message"] == "Tax rule set retrieved successfully."
    assert "data" in res
    assert res["data"]["taxRuleSet"]["name"] == "Luật 2026"


def test_service_get_detail_by_year_success():
    """Khi tìm thấy theo năm, trả về message thành công và data đã được format."""
    mock_repo = MagicMock()
    rs = TaxRuleSet(rule_set_id=uuid.uuid4(), name="Luật 2026", tax_year=2026, status="DRAFT")
    rule = TaxRule(rule_id=uuid.uuid4(), rule_code="PIT_01", rule_name="Giảm trừ", rule_type="DEDUCTION")

    mock_repo.get_tax_rule_set_detail_by_year.return_value = (rs, [rule], [])
    service = TaxRuleService(repository=mock_repo)

    res = service.get_tax_rule_set_detail_by_year(2026)

    assert res["message"] == "Tax rule set for year 2026 retrieved successfully."
    assert "data" in res
    assert res["data"]["taxRuleSet"]["name"] == "Luật 2026"


# ==============================================================================
# 3. Test approve_tax_rule_set()
# ==============================================================================
def test_service_approve_not_found():
    """Khi approve ID không tồn tại, bắn 404."""
    mock_repo = MagicMock()
    mock_repo.approve_tax_rule_set.return_value = None
    service = TaxRuleService(repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        service.approve_tax_rule_set(uuid.uuid4())

    assert exc_info.value.status_code == 404


def test_service_approve_success():
    """Phê duyệt thành công trả về thông tin active."""
    mock_repo = MagicMock()
    rule_set_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    rs = TaxRuleSet(rule_set_id=rule_set_id, status="ACTIVE", approved_by=admin_id)
    mock_repo.approve_tax_rule_set.return_value = rs
    service = TaxRuleService(repository=mock_repo)

    res = service.approve_tax_rule_set(rule_set_id, admin_id=admin_id)

    assert res["status"] == TaxRuleStatus.ACTIVE.value
    assert res["approvedBy"] == admin_id


# ==============================================================================
# 4. Test update_tax_rule_set() - Các quy tắc nghiệp vụ quan trọng
# ==============================================================================
def test_service_update_not_found():
    """Khi bộ luật cần sửa không tồn tại trong DB, bắn HTTPException 404."""
    mock_repo = MagicMock()
    mock_repo.get_tax_rule_set_detail.return_value = None
    service = TaxRuleService(repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        service.update_tax_rule_set(uuid.uuid4(), {"name": "Tên mới"})

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == TaxRuleErrorMessages.RULE_SET_NOT_FOUND


def test_service_update_cannot_update_active_rule_set():
    """Nghiệp vụ: KHÔNG CHO PHÉP sửa bộ luật nếu trạng thái đang là ACTIVE (bắn lỗi 400)."""
    mock_repo = MagicMock()
    rule_set_id = uuid.uuid4()
    # Bộ luật đang ACTIVE
    active_rs = TaxRuleSet(rule_set_id=rule_set_id, status=TaxRuleStatus.ACTIVE.value, tax_year=2026)
    mock_repo.get_tax_rule_set_detail.return_value = (active_rs, [], [])

    service = TaxRuleService(repository=mock_repo)

    with pytest.raises(TaxRuleServiceError) as exc_info:
        service.update_tax_rule_set(rule_set_id, {"name": "Tên mới"})

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == TaxRuleErrorMessages.CANNOT_UPDATE_ACTIVE_RULE_SET


def test_service_update_conflict_tax_year():
    """Nghiệp vụ: Khi đổi tax_year sang năm đã tồn tại ở bộ luật khác, bắn lỗi 409 Conflict."""
    mock_repo = MagicMock()
    rule_set_id = uuid.uuid4()
    other_rule_set_id = uuid.uuid4()

    curr_rs = TaxRuleSet(rule_set_id=rule_set_id, status=TaxRuleStatus.DRAFT.value, tax_year=2025)
    conflict_rs = TaxRuleSet(rule_set_id=other_rule_set_id, tax_year=2026)

    mock_repo.get_tax_rule_set_detail.return_value = (curr_rs, [], [])
    # Khi tìm năm 2026 trong DB thì thấy đã bị bộ luật khác (other_rule_set_id) chiếm
    mock_repo.get_rule_set_by_year.return_value = conflict_rs

    service = TaxRuleService(repository=mock_repo)

    with pytest.raises(TaxRuleServiceError) as exc_info:
        service.update_tax_rule_set(rule_set_id, {"tax_year": 2026})

    assert exc_info.value.status_code == 409
    assert exc_info.value.message == TaxRuleErrorMessages.TAX_RULE_SET_EXISTS


def test_service_update_success():
    """Cập nhật thành công khi ở trạng thái Draft và không trùng năm."""
    mock_repo = MagicMock()
    rule_set_id = uuid.uuid4()
    curr_rs = TaxRuleSet(rule_set_id=rule_set_id, status=TaxRuleStatus.DRAFT.value, tax_year=2026)
    mock_repo.get_tax_rule_set_detail.return_value = (curr_rs, [], [])

    updated_rs = TaxRuleSet(rule_set_id=rule_set_id, name="Đã sửa", tax_year=2026, status="DRAFT")
    mock_repo.update_tax_rule_set.return_value = (updated_rs, [], [])

    service = TaxRuleService(repository=mock_repo)

    res = service.update_tax_rule_set(rule_set_id, {"name": "Đã sửa"})

    assert res["message"] == "Tax rule set updated successfully."
    assert res["data"]["taxRuleSet"]["name"] == "Đã sửa"


def test_service_update_repo_returns_none():
    """Khi repo.update_tax_rule_set trả về None, ném lỗi HTTPException 404."""
    mock_repo = MagicMock()
    rule_set_id = uuid.uuid4()
    curr_rs = TaxRuleSet(rule_set_id=rule_set_id, status=TaxRuleStatus.DRAFT.value, tax_year=2026)
    mock_repo.get_tax_rule_set_detail.return_value = (curr_rs, [], [])
    mock_repo.update_tax_rule_set.return_value = None

    service = TaxRuleService(repository=mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        service.update_tax_rule_set(rule_set_id, {"name": "Đã sửa"})

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == TaxRuleErrorMessages.RULE_SET_NOT_FOUND



# ==============================================================================
# 5. Test process_tax_rule_document() - Ủy quyền cho document_service
# ==============================================================================
@pytest.mark.anyio
async def test_service_process_tax_rule_document_delegation():
    """Hàm process_tax_rule_document ủy quyền gọi sang document_service."""
    mock_repo = MagicMock()
    mock_doc_service = MagicMock()
    mock_doc_service.process_tax_rule_document = AsyncMock(return_value={"status": "PROCESSED"})

    service = TaxRuleService(
        repository=mock_repo,
        document_service=mock_doc_service
    )

    result = await service.process_tax_rule_document(
        filename="test.pdf",
        file_bytes=b"pdf_bytes",
        tax_year=2026
    )

    assert result == {"status": "PROCESSED"}
    mock_doc_service.process_tax_rule_document.assert_awaited_once()
