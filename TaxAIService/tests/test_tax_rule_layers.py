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
    mock_repo.approve_tax_rule_set.assert_called_once_with(rule_set_id=test_id, admin_id=admin_id)


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


def test_extraction_service_year_mismatch_warning():
    import json
    from app.services.tax_rule_extraction_service import TaxRuleExtractionService

    service = TaxRuleExtractionService()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "verification": {
            "inputTaxYear": 2026,
            "extractedTaxYear": 2020,
            "isTaxYearMatched": False,
            "mismatchReason": "Văn bản thuộc năm 2020, không áp dụng cho năm 2026"
        },
        "taxRuleSet": {"name": "Luat Thue 2020"},
        "taxRules": [{"ruleCode": "PIT_DED_1", "ruleName": "Rule 1", "ruleType": "DEDUCTION"}]
    })

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = service.extract_tax_rules(
            document_text="Sample text",
            tax_year=2026
        )
        assert result["verification"]["isTaxYearMatched"] is False
        assert "warning" in result
        assert "2020" in result["warning"]
        assert "2026" in result["warning"]
        assert len(result["taxRules"]) == 1


def test_extraction_service_year_mismatch_different_year():
    import json
    from app.services.tax_rule_extraction_service import TaxRuleExtractionService

    service = TaxRuleExtractionService()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "verification": {
            "inputTaxYear": 2026,
            "extractedTaxYear": 2024,
            "isTaxYearMatched": True,
            "mismatchReason": None
        },
        "taxRuleSet": {"name": "Luat Thue 2024"},
        "taxRules": [{"ruleCode": "PIT_DED_1", "ruleName": "Rule 1", "ruleType": "DEDUCTION"}]
    })

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = service.extract_tax_rules(
            document_text="Sample text",
            tax_year=2026
        )
        assert result["verification"]["isTaxYearMatched"] is False
        assert "warning" in result
        assert "2024" in result["warning"]
        assert len(result["taxRules"]) == 1


def test_extraction_service_year_matched_success():
    import json
    from app.services.tax_rule_extraction_service import TaxRuleExtractionService

    service = TaxRuleExtractionService()
    mock_resp = MagicMock()
    mock_resp.text = json.dumps({
        "verification": {
            "inputTaxYear": 2026,
            "extractedTaxYear": 2026,
            "isTaxYearMatched": True,
            "mismatchReason": None
        },
        "taxRuleSet": {"name": "Luat Thue 2026"},
        "taxRules": [{"ruleCode": "PIT_DED_1", "ruleName": "Rule 1", "ruleType": "DEDUCTION"}]
    })

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = service.extract_tax_rules(
            document_text="Sample text",
            tax_year=2026
        )
        assert result["taxRuleSet"]["taxYear"] == 2026
        assert result["verification"]["isTaxYearMatched"] is True
        assert result.get("warning") is None
        assert len(result["taxRules"]) == 1


@pytest.mark.anyio
async def test_service_process_year_mismatch_saves_draft_with_warning():
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = None
    mock_repo.check_existing_rule_codes.return_value = False

    saved_rule_set = TaxRuleSet(
        rule_set_id=uuid.uuid4(),
        name="Luat Thue 2025",
        tax_year=2025,
        status="Draft"
    )
    mock_repo.create_tax_rule_set.return_value = (saved_rule_set, [], [])

    service = TaxRuleService(mock_repo)

    with patch("app.services.tax_rule_service.pdf_service.prepare_pdf_for_ai") as mock_pdf, \
         patch("app.services.tax_rule_service.tax_rule_extraction_service.extract_tax_rules") as mock_extract:
        mock_pdf.return_value = (False, "PDF Content", None)
        mock_extract.return_value = {
            "verification": {
                "inputTaxYear": 2025,
                "extractedTaxYear": 2026,
                "isTaxYearMatched": False,
                "warningMessage": "Năm áp dụng trong văn bản (2026) không khớp với năm tính thuế nhập vào (2025)."
            },
            "warning": "Năm áp dụng trong văn bản (2026) không khớp với năm tính thuế nhập vào (2025).",
            "taxRuleSet": {"name": "Luat Thue 2025"},
            "taxRules": []
        }

        res = await service.process_tax_rule_document(
            filename="test.pdf",
            file_bytes=b"%PDF-1.4 dummy",
            tax_year=2025
        )

        assert res["warning"] is not None
        assert "2026" in res["warning"]
        assert res["data"]["verification"]["isTaxYearMatched"] is False
        assert res["data"]["taxRuleSet"]["taxYear"] == 2025


def test_service_get_tax_rule_set_detail_success():
    mock_repo = MagicMock()
    test_id = uuid.uuid4()
    mock_set = TaxRuleSet(rule_set_id=test_id, name="Test Set", tax_year=2026, status="Draft")
    mock_rule = TaxRule(rule_id=uuid.uuid4(), rule_set_id=test_id, rule_code="PIT_BRACKET_1", rule_name="Bậc 1", rule_type="BRACKET")
    mock_dep = DependentRule(id=uuid.uuid4(), rule_id=mock_rule.rule_id, dependent_type="CHILD", name="Con nhỏ")

    mock_repo.get_tax_rule_set_detail.return_value = (mock_set, [mock_rule], [mock_dep])

    service = TaxRuleService(mock_repo)
    result = service.get_tax_rule_set_detail(test_id)

    assert result["message"] == "Tax rule set retrieved successfully."
    assert result["data"]["taxRuleSet"]["ruleSetId"] == test_id
    assert len(result["data"]["taxRules"]) == 1
    assert len(result["data"]["dependentRules"]) == 1


def test_service_get_tax_rule_set_detail_not_found():
    mock_repo = MagicMock()
    mock_repo.get_tax_rule_set_detail.return_value = None

    service = TaxRuleService(mock_repo)
    with pytest.raises(HTTPException) as exc_info:
        service.get_tax_rule_set_detail(uuid.uuid4())

    assert exc_info.value.status_code == 404
    assert exc_info.value.detail == "Tax rule set not found."


def test_service_update_tax_rule_set_success():
    mock_repo = MagicMock()
    test_id = uuid.uuid4()

    curr_set = TaxRuleSet(rule_set_id=test_id, name="Old Name", tax_year=2025, status="Draft")
    mock_repo.get_tax_rule_set_detail.return_value = (curr_set, [], [])
    mock_repo.get_rule_set_by_year.return_value = None

    updated_set = TaxRuleSet(rule_set_id=test_id, name="New Name", tax_year=2026, status="Draft")
    updated_rule = TaxRule(rule_id=uuid.uuid4(), rule_set_id=test_id, rule_code="PIT_DED_1", rule_name="Giảm trừ", rule_type="DEDUCTION")
    mock_repo.update_tax_rule_set.return_value = (updated_set, [updated_rule], [])

    service = TaxRuleService(mock_repo)
    result = service.update_tax_rule_set(
        rule_set_id=test_id,
        payload={"name": "New Name", "tax_year": 2026}
    )

    assert result["message"] == "Tax rule set updated successfully."
    assert result["data"]["taxRuleSet"]["name"] == "New Name"
    assert result["data"]["taxRuleSet"]["taxYear"] == 2026


def test_service_update_tax_rule_set_conflict():
    mock_repo = MagicMock()
    test_id = uuid.uuid4()
    other_id = uuid.uuid4()

    curr_set = TaxRuleSet(rule_set_id=test_id, name="Old Name", tax_year=2025, status="Draft")
    mock_repo.get_tax_rule_set_detail.return_value = (curr_set, [], [])

    conflict_set = TaxRuleSet(rule_set_id=other_id, name="Conflict Set", tax_year=2026, status="Active")
    mock_repo.get_rule_set_by_year.return_value = conflict_set

    service = TaxRuleService(mock_repo)
    with pytest.raises(TaxRuleServiceError) as exc_info:
        service.update_tax_rule_set(
            rule_set_id=test_id,
            payload={"tax_year": 2026}
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.message == "A tax rule set for this tax year already exists."


def test_route_get_tax_rule_set_success():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes.tax_rule_routes import get_tax_rule_service

    test_id = uuid.uuid4()
    mock_service = MagicMock()
    mock_service.get_tax_rule_set_detail.return_value = {
        "message": "Tax rule set retrieved successfully.",
        "data": {
            "taxRuleSet": {
                "ruleSetId": str(test_id),
                "name": "Luat Thue 2026",
                "taxYear": 2026,
                "status": "Draft"
            },
            "taxRules": [],
            "dependentRules": []
        }
    }

    app.dependency_overrides[get_tax_rule_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.get(f"/api/tax-rules/{test_id}")
        assert response.status_code == 200
        assert response.json()["data"]["taxRuleSet"]["taxYear"] == 2026
        mock_service.get_tax_rule_set_detail.assert_called_once_with(rule_set_id=test_id)
    finally:
        app.dependency_overrides.clear()


def test_route_update_tax_rule_set_success():
    from fastapi.testclient import TestClient
    from app.main import app
    from app.api.routes.tax_rule_routes import get_tax_rule_service

    test_id = uuid.uuid4()
    mock_service = MagicMock()
    mock_service.update_tax_rule_set.return_value = {
        "message": "Tax rule set updated successfully.",
        "data": {
            "taxRuleSet": {
                "ruleSetId": str(test_id),
                "name": "Updated 2026",
                "taxYear": 2026,
                "status": "Draft"
            },
            "taxRules": [],
            "dependentRules": []
        }
    }

    app.dependency_overrides[get_tax_rule_service] = lambda: mock_service
    try:
        client = TestClient(app)
        response = client.put(
            f"/api/tax-rules/{test_id}",
            json={"name": "Updated 2026", "taxYear": 2026}
        )
        assert response.status_code == 200
        assert response.json()["data"]["taxRuleSet"]["name"] == "Updated 2026"
    finally:
        app.dependency_overrides.clear()


def test_extraction_service_filters_business_and_non_employment_rules():
    import json
    from app.services.tax_rule_extraction_service import tax_rule_extraction_service

    mock_ai_response = MagicMock()
    mock_ai_response.text = json.dumps({
        "verification": {
            "inputTaxYear": 2026,
            "extractedTaxYear": 2026,
            "isTaxYearMatched": True,
            "mismatchReason": None
        },
        "taxRuleSet": {"name": "Luật Thuế TNCN 2026"},
        "taxRules": [
            {
                "ruleCode": "PERSONAL_DEDUCTION",
                "ruleName": "Giảm trừ gia cảnh bản thân từ tiền lương",
                "ruleType": "Deduction",
                "description": "11 triệu/tháng",
                "rate": 0,
                "bracketOrder": 0
            },
            {
                "ruleCode": "PIT_BUSINESS_INCOME",
                "ruleName": "Thuế thu nhập từ kinh doanh",
                "ruleType": "Rate",
                "description": "Tỷ lệ thuế cá nhân kinh doanh",
                "rate": 0.05,
                "bracketOrder": 0
            },
            {
                "ruleCode": "PIT_REAL_ESTATE_TRANSFER",
                "ruleName": "Chuyển nhượng bất động sản",
                "ruleType": "Rate",
                "description": "Thuế BĐS",
                "rate": 0.02,
                "bracketOrder": 0
            }
        ],
        "dependentRules": []
    })

    with patch.object(tax_rule_extraction_service.client.models, "generate_content") as mock_generate:
        mock_generate.return_value = mock_ai_response
        result = tax_rule_extraction_service.extract_tax_rules(document_text="dummy text", tax_year=2026)

        assert len(result["taxRules"]) == 1
        assert result["taxRules"][0]["ruleCode"] == "PERSONAL_DEDUCTION"


def test_extraction_service_raises_when_all_rules_disallowed():
    import json
    from app.services.tax_rule_extraction_service import tax_rule_extraction_service, TaxRuleExtractionError
    from app.errors.tax_rule_errors import TaxRuleErrorMessages

    mock_ai_response = MagicMock()
    mock_ai_response.text = json.dumps({
        "verification": {
            "inputTaxYear": 2026,
            "extractedTaxYear": 2026,
            "isTaxYearMatched": True,
            "mismatchReason": None
        },
        "taxRuleSet": {"name": "Luật Thuế Kinh Doanh 2026"},
        "taxRules": [
            {
                "ruleCode": "PIT_BUSINESS_INCOME",
                "ruleName": "Thuế kinh doanh",
                "ruleType": "Rate",
                "rate": 0.05
            }
        ],
        "dependentRules": []
    })

    with patch.object(tax_rule_extraction_service.client.models, "generate_content") as mock_generate:
        mock_generate.return_value = mock_ai_response
        with pytest.raises(TaxRuleExtractionError) as exc_info:
            tax_rule_extraction_service.extract_tax_rules(document_text="dummy text", tax_year=2026)
        assert exc_info.value.detail == TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED


def test_repository_update_tax_rule_set_all_fields():
    mock_db = MagicMock()
    test_id = uuid.uuid4()
    rule_id = uuid.uuid4()
    dep_id = uuid.uuid4()

    mock_rule_set = TaxRuleSet(rule_set_id=test_id, name="Old", tax_year=2025, status="Draft")
    mock_rule = TaxRule(rule_id=rule_id, rule_set_id=test_id, rule_code="PIT_DEDUCTION_PERSONAL", rule_name="Old", rule_type="DEDUCTION", status="Draft", version=1)
    mock_dep = DependentRule(id=dep_id, rule_id=rule_id, dependent_type="CHILD", name="Old", status="Draft")

    repo = TaxRuleRepository(mock_db)
    repo.get_rule_set_by_id = MagicMock(return_value=mock_rule_set)
    repo.get_tax_rule_set_detail = MagicMock(return_value=(mock_rule_set, [mock_rule], [mock_dep]))

    mock_filter_rules = MagicMock()
    mock_filter_rules.all.return_value = [mock_rule]
    mock_filter_dep = MagicMock()
    mock_filter_dep.all.return_value = [mock_dep]
    mock_filter_first = MagicMock()
    mock_filter_first.first.return_value = mock_rule

    mock_db.query.return_value.filter.side_effect = [
        mock_filter_rules,  # current_rules
        mock_filter_rules,  # all_rules for dependent rules
        mock_filter_dep,    # existing_dep_rules
    ]

    result = repo.update_tax_rule_set(
        rule_set_id=test_id,
        name="New Name",
        tax_year=2026,
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        status="Active",
        tax_rules=[{
            "rule_id": rule_id,
            "rule_code": "PIT_DEDUCTION_PERSONAL",
            "rule_name": "New Personal",
            "rule_type": "DEDUCTION",
            "value": 11000000.0,
            "unit": "VND/month",
            "status": "Active",
            "version": 2
        }],
        dependent_rules=[{
            "id": dep_id,
            "rule_id": rule_id,
            "dependent_type": "CHILD",
            "name": "Con dưới 18 tuổi",
            "max_age": 18,
            "status": "Active"
        }]
    )
    assert result is not None
    assert mock_rule_set.name == "New Name"
    assert mock_rule_set.tax_year == 2026
    assert mock_rule_set.status == "Active"
    assert mock_rule.rule_name == "New Personal"
    assert mock_rule.version == 2
    assert mock_dep.name == "Con dưới 18 tuổi"
    assert mock_dep.max_age == 18


def test_extraction_service_year_mismatch_preserves_draft_without_raising():
    import json
    from app.services.tax_rule_extraction_service import tax_rule_extraction_service

    mock_ai_response = MagicMock()
    mock_ai_response.text = json.dumps({
        "verification": {
            "inputTaxYear": 2026,
            "extractedTaxYear": 2020,
            "isTaxYearMatched": False,
            "mismatchReason": "Văn bản này ban hành và áp dụng cho năm 2020, không phải năm 2026"
        },
        "taxRuleSet": {"name": "Nghị quyết 954/2020/UBTVQH14"},
        "taxRules": [],
        "dependentRules": []
    })

    with patch.object(tax_rule_extraction_service.client.models, "generate_content") as mock_generate:
        mock_generate.return_value = mock_ai_response
        result = tax_rule_extraction_service.extract_tax_rules(document_text="Nghị quyết 2020", tax_year=2026)

        assert result["verification"]["isTaxYearMatched"] is False
        assert "warning" in result
        assert result["taxRuleSet"]["taxYear"] == 2026
        assert result["taxRuleSet"]["status"] == "Draft"







