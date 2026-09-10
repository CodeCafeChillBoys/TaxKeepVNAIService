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
    mock_rule_set = TaxRuleSet(rule_set_id=test_id, name="Test", tax_year=2026, status="Draft")

    mock_filter = MagicMock()
    mock_filter.first.return_value = mock_rule_set
    mock_db.query.return_value.filter.return_value = mock_filter

    repo = TaxRuleRepository(mock_db)
    result = repo.approve_tax_rule_set(test_id)

    assert result is not None
    assert result.status == "Active"
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
        service.approve_tax_rule_set(uuid.uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Tax rule set not found."


def test_service_approve_tax_rule_set_success():
    mock_repo = MagicMock()
    test_id = uuid.uuid4()
    mock_repo.approve_tax_rule_set.return_value = TaxRuleSet(
        rule_set_id=test_id,
        name="Test",
        tax_year=2026,
        status="Active"
    )
    service = TaxRuleService(mock_repo)

    result = service.approve_tax_rule_set(test_id)
    assert result["status"] == "Active"
    assert result["ruleSetId"] == str(test_id)
    assert result["message"] == "Tax rule set approved successfully."


def test_route_approve_success():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes.tax_rule_routes import get_tax_rule_service

    test_id = uuid.uuid4()
    mock_service = MagicMock()
    mock_service.approve_tax_rule_set.return_value = {
        "message": "Tax rule set approved successfully.",
        "ruleSetId": str(test_id),
        "status": "Active"
    }

    app.dependency_overrides[get_tax_rule_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.post(f"/api/tax-rules/{test_id}/approve")
        assert response.status_code == 200
        assert response.json()["status"] == "Active"
        assert response.json()["ruleSetId"] == str(test_id)
    finally:
        app.dependency_overrides.clear()


def test_route_approve_not_found():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes.tax_rule_routes import get_tax_rule_service

    test_id = uuid.uuid4()
    mock_service = MagicMock()
    mock_service.approve_tax_rule_set.side_effect = HTTPException(status_code=404, detail="Tax rule set not found.")

    app.dependency_overrides[get_tax_rule_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.post(f"/api/tax-rules/{test_id}/approve")
        assert response.status_code == 404
        assert response.json()["detail"] == "Tax rule set not found."
    finally:
        app.dependency_overrides.clear()

