import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.repositories.interfaces import IRepository, IRepo, ITaxRuleRepository
from app.repositories import TaxRuleRepository
from app.services.interfaces import IService, ITaxRuleService
from app.services import TaxRuleService, TaxRuleServiceError


def test_interfaces_inheritance():
    assert issubclass(ITaxRuleRepository, IRepository)
    assert issubclass(ITaxRuleRepository, IRepo)
    assert issubclass(TaxRuleRepository, IRepository)
    assert issubclass(TaxRuleRepository, ITaxRuleRepository)
    assert issubclass(ITaxRuleService, IService)
    assert issubclass(TaxRuleService, IService)
    assert issubclass(TaxRuleService, ITaxRuleService)


def test_repository_get_by_id():
    mock_db = MagicMock()
    repo = TaxRuleRepository(mock_db)
    test_id = uuid.uuid4()

    repo.get_by_id(test_id)
    mock_db.query.assert_called_once_with(TaxRuleSet)


def test_repository_get_rule_set_by_year():
    mock_db = MagicMock()
    repo = TaxRuleRepository(mock_db)

    repo.get_rule_set_by_year(2026)
    mock_db.query.assert_called_once_with(TaxRuleSet)


def test_repository_get_rule_set_by_id():
    mock_db = MagicMock()
    repo = TaxRuleRepository(mock_db)
    test_id = uuid.uuid4()

    repo.get_rule_set_by_id(test_id)
    mock_db.query.assert_called_once_with(TaxRuleSet)


def test_repository_check_existing_rule_codes_empty():
    mock_db = MagicMock()
    repo = TaxRuleRepository(mock_db)
    assert repo.check_existing_rule_codes([]) is False
    mock_db.query.assert_not_called()


def test_repository_check_existing_rule_codes_found():
    mock_db = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = TaxRule(rule_code="TEST_CODE")
    mock_db.query.return_value.filter.return_value = mock_filter

    repo = TaxRuleRepository(mock_db)
    assert repo.check_existing_rule_codes(["TEST_CODE"]) is True


def test_repository_create_tax_rule_set():
    mock_db = MagicMock()
    repo = TaxRuleRepository(mock_db)

    rule_set = TaxRuleSet(name="Test 2026", tax_year=2026)
    rules = [TaxRule(rule_code="PIT_DEDUCTION_PERSONAL", rule_name="Personal", rule_type="DEDUCTION")]
    dependent_rules = [DependentRule(dependent_type="CHILD", name="Con duoi 18")]

    saved_set, saved_rules, saved_deps = repo.create_tax_rule_set(rule_set, rules, dependent_rules)
    assert mock_db.add.called
    assert mock_db.add_all.called
    assert mock_db.commit.called
    assert saved_set.name == "Test 2026"


def test_repository_approve_tax_rule_set_not_found():
    mock_db = MagicMock()
    mock_filter = MagicMock()
    mock_filter.first.return_value = None
    mock_db.query.return_value.filter.return_value = mock_filter

    repo = TaxRuleRepository(mock_db)
    result = repo.approve_tax_rule_set(uuid.uuid4())
    assert result is None


def test_repository_approve_tax_rule_set_success():
    mock_db = MagicMock()
    test_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    mock_rule_set = TaxRuleSet(rule_set_id=test_id, name="Test", tax_year=2026, status="Draft")

    mock_filter = MagicMock()
    mock_filter.first.return_value = mock_rule_set
    mock_db.query.return_value.filter.return_value = mock_filter

    repo = TaxRuleRepository(mock_db)
    result = repo.approve_tax_rule_set(test_id, admin_id=admin_id)

    assert result is not None
    assert result.status == "Active"
    assert result.approved_by == admin_id
    assert result.approved_at is not None
    assert mock_db.commit.called


@pytest.mark.anyio
async def test_service_duplicate_tax_year():
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = TaxRuleSet(name="Exists", tax_year=2026)

    service = TaxRuleService(mock_repo)

    with pytest.raises(TaxRuleServiceError) as exc_info:
        await service.process_tax_rule_document(
            filename="test.pdf",
            file_bytes=b"%PDF-1.4 dummy",
            tax_year=2026
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.message == "A tax rule set for this tax year already exists."


def test_service_approve_tax_rule_set_not_found():
    mock_repo = MagicMock()
    mock_repo.approve_tax_rule_set.return_value = None
    service = TaxRuleService(mock_repo)

    with pytest.raises(HTTPException) as exc_info:
        service.approve_tax_rule_set(uuid.uuid4(), admin_id=uuid.uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Tax rule set not found."


def test_service_approve_tax_rule_set_success():
    from datetime import datetime
    mock_repo = MagicMock()
    test_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    now = datetime.now()
    mock_repo.approve_tax_rule_set.return_value = TaxRuleSet(
        rule_set_id=test_id,
        name="Test",
        tax_year=2026,
        status="Active",
        approved_by=admin_id,
        approved_at=now
    )
    service = TaxRuleService(mock_repo)

    result = service.approve_tax_rule_set(test_id, admin_id=admin_id)
    assert result["status"] == "Active"
    assert result["ruleSetId"] == str(test_id)
    assert result["approvedBy"] == admin_id
    assert result["approvedAt"] == now
    assert result["message"] == "Tax rule set approved successfully."
    mock_repo.approve_tax_rule_set.assert_called_once_with(test_id, admin_id=admin_id)


def test_route_approve_success():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes.tax_rule_routes import get_tax_rule_service

    test_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    mock_service = MagicMock()
    mock_service.approve_tax_rule_set.return_value = {
        "message": "Tax rule set approved successfully.",
        "ruleSetId": str(test_id),
        "status": "Active",
        "approvedBy": str(admin_id),
        "approvedAt": "2026-09-13T00:00:00"
    }

    app.dependency_overrides[get_tax_rule_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/tax-rules/{test_id}/approve",
            json={"adminId": str(admin_id)}
        )
        assert response.status_code == 200
        assert response.json()["status"] == "Active"
        assert response.json()["ruleSetId"] == str(test_id)
        assert response.json()["approvedBy"] == str(admin_id)
        mock_service.approve_tax_rule_set.assert_called_once_with(rule_set_id=test_id, admin_id=admin_id)
    finally:
        app.dependency_overrides.clear()


def test_route_approve_validation_error():
    from fastapi.testclient import TestClient
    from app.main import app

    test_id = uuid.uuid4()
    client = TestClient(app)
    # Thiếu adminId trong body
    response = client.post(f"/api/tax-rules/{test_id}/approve", json={})
    assert response.status_code == 422


def test_route_approve_not_found():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes.tax_rule_routes import get_tax_rule_service

    test_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    mock_service = MagicMock()
    mock_service.approve_tax_rule_set.side_effect = HTTPException(status_code=404, detail="Tax rule set not found.")

    app.dependency_overrides[get_tax_rule_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.post(
            f"/api/tax-rules/{test_id}/approve",
            json={"adminId": str(admin_id)}
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Tax rule set not found."
    finally:
        app.dependency_overrides.clear()


@pytest.mark.anyio
async def test_service_process_with_admin_id():
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = None
    mock_repo.check_existing_rule_codes.return_value = False

    admin_id = uuid.uuid4()
    saved_rule_set = TaxRuleSet(
        rule_set_id=uuid.uuid4(),
        admin_id=admin_id,
        name="Luat Thue 2026",
        tax_year=2026,
        status="Draft"
    )
    mock_repo.create_tax_rule_set.return_value = (saved_rule_set, [], [])

    service = TaxRuleService(mock_repo)

    with patch("app.services.tax_rule_service.pdf_service.prepare_pdf_for_ai") as mock_pdf, \
         patch("app.services.tax_rule_service.tax_rule_extraction_service.extract_tax_rules") as mock_extract:
        mock_pdf.return_value = (False, "PDF Content", None)
        mock_extract.return_value = {
            "taxRuleSet": {"name": "Luat Thue 2026"},
            "taxRules": []
        }

        res = await service.process_tax_rule_document(
            filename="test.pdf",
            file_bytes=b"%PDF-1.4 dummy",
            tax_year=2026,
            admin_id=admin_id
        )

        assert res["data"]["taxRuleSet"]["adminId"] == admin_id
        # Kiểm tra instance TaxRuleSet gửi vào repository có admin_id chuẩn xác
        created_rule_set = mock_repo.create_tax_rule_set.call_args[1]["rule_set"]
        assert created_rule_set.admin_id == admin_id


def test_route_upload_invalid_admin_id():
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/api/tax-rules/documents/upload",
        data={"taxYear": "2026", "adminId": "invalid-uuid-string"},
        files={"file": ("test.pdf", b"%PDF-1.4 dummy", "application/pdf")}
    )
    assert response.status_code == 400
    assert response.json()["message"] == "adminId must be a valid UUID."


