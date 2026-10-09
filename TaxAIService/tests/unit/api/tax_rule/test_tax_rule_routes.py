import io
import uuid
from unittest.mock import MagicMock, AsyncMock
import pytest
from app.api.routes.tax_rule.tax_rule_routes import get_tax_rule_service, get_url_validation_service
from app.services.tax_rule.tax_rule_service import TaxRuleServiceError
from app.enum import TaxRuleType, DependentType, TaxRuleStatus
from app.main import app


@pytest.fixture
def mock_tax_service():
    service = MagicMock()
    app.dependency_overrides[get_tax_rule_service] = lambda: service
    return service


@pytest.fixture
def mock_url_service():
    service = MagicMock()
    app.dependency_overrides[get_url_validation_service] = lambda: service
    return service


def _build_dummy_detail_payload():
    rule_set_id = uuid.uuid4()
    return {
        "message": "Success",
        "data": {
            "taxRuleSet": {
                "ruleSetId": str(rule_set_id),
                "name": "Luật Thuế TNCN 2026",
                "taxYear": 2026,
                "status": TaxRuleStatus.DRAFT.value,
            },
            "taxRules": [
                {
                    "ruleCode": "DED_PERSONAL_2026",
                    "ruleName": "Giảm trừ bản thân",
                    "ruleType": "DEDUCTION",
                    "value": 11000000.0,
                    "unit": "VND/thang",
                    "status": TaxRuleStatus.DRAFT.value,
                }
            ],
            "dependentRules": [],
        },
    }


# ==============================================================================
# 1. Tests cho POST /api/tax-rules/documents/upload
# ==============================================================================

def test_upload_missing_file(client, mock_tax_service, mock_url_service):
    """Upload thiếu trường file trả về 400 Bad Request"""
    response = client.post(
        "/api/tax-rules/documents/upload",
        data={"taxYear": "2026"}
    )
    assert response.status_code == 400
    assert response.json()["message"] == "The file field is required."


def test_upload_non_pdf_file(client, mock_tax_service, mock_url_service):
    """Upload file không phải định dạng PDF trả về 400 Bad Request"""
    file_content = b"fake image"
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("document.txt", io.BytesIO(file_content), "text/plain")},
        data={"taxYear": "2026"}
    )
    assert response.status_code == 400
    assert response.json()["message"] == "The file must be a PDF."


def test_upload_missing_tax_year(client, mock_tax_service, mock_url_service):
    """Upload thiếu taxYear trả về 400 Bad Request"""
    pdf_content = b"%PDF-1.4 test"
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("luat_thue.pdf", io.BytesIO(pdf_content), "application/pdf")},
    )
    assert response.status_code == 400
    assert "TaxYear field is required" in response.json()["TaxYear"]


def test_upload_invalid_tax_year_number(client, mock_tax_service, mock_url_service):
    """Upload taxYear không hợp lệ (< 1900 hoặc > 2100 hoặc chữ) trả về 400"""
    pdf_content = b"%PDF-1.4 test"
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("luat_thue.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"taxYear": "1800"}
    )
    assert response.status_code == 400
    assert "Tax year must be a valid year." in response.json()["message"]


def test_upload_invalid_source_url(client, mock_tax_service, mock_url_service):
    """Upload có sourceUrl vi phạm quy tắc URL validation trả về 400"""
    mock_url_service.validate_url.return_value = (False, "Domain not allowed", None)
    pdf_content = b"%PDF-1.4 test"

    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("luat_thue.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"taxYear": "2026", "sourceUrl": "https://malicious.com/law"}
    )
    assert response.status_code == 400
    assert response.json()["SourceUrl"] == "Domain not allowed"


def test_upload_invalid_admin_id(client, mock_tax_service, mock_url_service):
    """Upload truyền adminId không đúng định dạng UUID trả về 400"""
    pdf_content = b"%PDF-1.4 test"
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("luat_thue.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"taxYear": "2026", "adminId": "not-a-valid-uuid"}
    )
    assert response.status_code == 400
    assert "adminId must be a valid UUID." in response.json()["message"]


def test_upload_file_too_large(client, mock_tax_service, mock_url_service, monkeypatch):
    """Upload file vượt quá giới hạn MAX_FILE_SIZE_MB trả về 400"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 0.0001)  # Giới hạn ~100 bytes

    big_pdf = b"%PDF-1.4" + b"A" * 500
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("luat_thue.pdf", io.BytesIO(big_pdf), "application/pdf")},
        data={"taxYear": "2026"}
    )
    assert response.status_code == 400
    assert "file size must not exceed" in response.json()["message"]


def test_upload_success(client, mock_tax_service, mock_url_service):
    """Upload hợp lệ xử lý bóc tách thành công trả về 200 OK"""
    mock_url_service.validate_url.return_value = (True, None, None)
    dummy_result = _build_dummy_detail_payload()
    mock_tax_service.process_tax_rule_document = AsyncMock(return_value=dummy_result)

    pdf_content = b"%PDF-1.4 test content"
    admin_id = uuid.uuid4()
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("luat_thue.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={
            "taxYear": "2026",
            "name": "Luật Thuế 2026",
            "sourceUrl": "https://chinhphu.vn/law.pdf",
            "adminId": str(admin_id),
        }
    )
    assert response.status_code == 200
    assert response.json()["message"] == "Success"
    mock_tax_service.process_tax_rule_document.assert_awaited_once()


def test_upload_service_error(client, mock_tax_service, mock_url_service):
    """Upload khi service quăng TaxRuleServiceError trả về status_code tương ứng"""
    mock_url_service.validate_url.return_value = (True, None, None)
    mock_tax_service.process_tax_rule_document = AsyncMock(
        side_effect=TaxRuleServiceError(status_code=500, message="AI Extraction timed out")
    )

    pdf_content = b"%PDF-1.4 test"
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("luat_thue.pdf", io.BytesIO(pdf_content), "application/pdf")},
        data={"taxYear": "2026"}
    )
    assert response.status_code == 500
    assert response.json()["message"] == "AI Extraction timed out"


# ==============================================================================
# 2. Tests cho GET /api/tax-rules
# ==============================================================================

def test_get_all_tax_rule_sets(client, mock_tax_service):
    """GET /api/tax-rules trả về danh sách các TaxRuleSet"""
    rule_set_id = uuid.uuid4()
    mock_tax_service.get_all_rule_sets.return_value = [
        {
            "ruleSetId": rule_set_id,
            "name": "Luật Thuế 2026",
            "taxYear": 2026,
            "status": TaxRuleStatus.DRAFT.value,
        }
    ]

    response = client.get("/api/tax-rules")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["taxYear"] == 2026
    mock_tax_service.get_all_rule_sets.assert_called_once()


# ==============================================================================
# 3. Tests cho GET /api/tax-rules/year/{taxYear}
# ==============================================================================

def test_get_tax_rule_set_by_year(client, mock_tax_service):
    """GET /api/tax-rules/year/{taxYear} trả về chi tiết theo năm"""
    dummy_result = _build_dummy_detail_payload()
    mock_tax_service.get_tax_rule_set_detail_by_year.return_value = dummy_result

    response = client.get("/api/tax-rules/year/2026")
    assert response.status_code == 200
    assert response.json()["data"]["taxRuleSet"]["taxYear"] == 2026
    mock_tax_service.get_tax_rule_set_detail_by_year.assert_called_once_with(tax_year=2026)


# ==============================================================================
# 4. Tests cho GET /api/tax-rules/{id}
# ==============================================================================

def test_get_tax_rule_set_by_id(client, mock_tax_service):
    """GET /api/tax-rules/{id} trả về chi tiết theo UUID"""
    rule_set_id = uuid.uuid4()
    dummy_result = _build_dummy_detail_payload()
    dummy_result["data"]["taxRuleSet"]["ruleSetId"] = str(rule_set_id)
    mock_tax_service.get_tax_rule_set_detail.return_value = dummy_result

    response = client.get(f"/api/tax-rules/{rule_set_id}")
    assert response.status_code == 200
    assert response.json()["data"]["taxRuleSet"]["ruleSetId"] == str(rule_set_id)
    mock_tax_service.get_tax_rule_set_detail.assert_called_once_with(rule_set_id=rule_set_id)


# ==============================================================================
# 5. Tests cho PUT /api/tax-rules/{id}
# ==============================================================================

def test_update_tax_rule_set_success(client, mock_tax_service):
    """PUT /api/tax-rules/{id} cập nhật thành công trả về 200 OK"""
    rule_set_id = uuid.uuid4()
    dummy_result = _build_dummy_detail_payload()
    mock_tax_service.update_tax_rule_set.return_value = dummy_result

    payload = {
        "taxYear": 2026,
        "name": "Luật Thuế 2026 Đã Sửa",
        "taxRules": [],
        "dependentRules": [],
    }
    response = client.put(f"/api/tax-rules/{rule_set_id}", json=payload)
    assert response.status_code == 200
    mock_tax_service.update_tax_rule_set.assert_called_once()


def test_update_tax_rule_set_error(client, mock_tax_service):
    """PUT /api/tax-rules/{id} khi xảy ra TaxRuleServiceError trả về status tương ứng"""
    rule_set_id = uuid.uuid4()
    mock_tax_service.update_tax_rule_set.side_effect = TaxRuleServiceError(
        status_code=404, message="Không tìm thấy TaxRuleSet"
    )

    payload = {"taxYear": 2026, "name": "Test"}
    response = client.put(f"/api/tax-rules/{rule_set_id}", json=payload)
    assert response.status_code == 404
    assert response.json()["message"] == "Không tìm thấy TaxRuleSet"


# ==============================================================================
# 6. Tests cho POST /api/tax-rules/{id}/approve
# ==============================================================================

def test_approve_tax_rule_set_success(client, mock_tax_service):
    """POST /api/tax-rules/{id}/approve phê duyệt thành công trả về 200 OK"""
    rule_set_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    mock_tax_service.approve_tax_rule_set.return_value = {
        "message": "Approved",
        "ruleSetId": rule_set_id,
        "status": TaxRuleStatus.ACTIVE.value,
        "approvedBy": admin_id,
    }

    payload = {"adminId": str(admin_id)}
    response = client.post(f"/api/tax-rules/{rule_set_id}/approve", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == TaxRuleStatus.ACTIVE.value
    mock_tax_service.approve_tax_rule_set.assert_called_once_with(
        rule_set_id=rule_set_id,
        admin_id=admin_id,
    )


def test_tax_rule_di_factories():
    """Kiểm tra các dependency provider helper functions trong tax_rule_routes"""
    from app.api.routes.tax_rule.tax_rule_routes import (
        get_tax_rule_repository,
        get_tax_rule_service,
        get_url_validation_service as get_tax_url_service,
    )
    mock_db = MagicMock()
    repo = get_tax_rule_repository(db=mock_db)
    assert repo is not None

    service = get_tax_rule_service(repo=repo)
    assert service is not None

    url_svc = get_tax_url_service(db=mock_db)
    assert url_svc is not None

