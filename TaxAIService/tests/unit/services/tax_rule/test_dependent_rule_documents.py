import uuid
import pytest
from unittest.mock import MagicMock
from app.models.tax_rule import TaxRule
from app.models.tax_rule_set import TaxRuleSet
from app.models.dependent_rule import DependentRule
from app.models.dependent_rule_document import DependentRuleDocument
from app.enum import DependentType, TaxRuleStatus, RequiredDocumentType
from app.mappers.tax_rule import build_tax_rule_models, format_tax_rule_data, normalize_document_type
from app.services.tax_rule.tax_rule_service import TaxRuleService
from app.schemas.tax_rule import (
    DependentRuleCreateRequest,
    DependentRuleUpdateRequest,
    RequiredDocumentCreateRequest,
    RequiredDocumentUpdateRequest,
    RequiredDocumentItemRequest,
)


def test_build_tax_rule_models_with_required_documents():
    extracted_data = {
        "taxRuleSet": {
            "name": "Luật Thuế 2026",
            "taxYear": 2026,
            "effectiveFrom": "2026-01-01",
            "effectiveTo": None,
            "status": "Draft"
        },
        "taxRules": [
            {
                "ruleCode": "PIT_DEDUCTION_DEPENDENT",
                "ruleName": "Giảm trừ người phụ thuộc",
                "ruleType": "DEDUCTION",
                "condition": {
                    "subject": "DEPENDENT",
                    "eligibility": [
                        {
                            "type": "CHILD",
                            "name": "Con dưới 18 tuổi",
                            "maxAge": 18,
                            "maxMonthlyIncome": None,
                            "isStudying": False,
                            "isDisabled": False,
                            "conditions": ["Con chưa thành niên"],
                            "requiredDocuments": [
                                {
                                    "docType": "BIRTH_CERTIFICATE",
                                    "name": "Giấy khai sinh",
                                    "isMandatory": True,
                                    "description": "Bản sao chứng thực"
                                },
                                {
                                    "docType": "CITIZEN_ID",
                                    "name": "CCCD",
                                    "isMandatory": False,
                                    "description": "Nếu có"
                                }
                            ]
                        }
                    ]
                },
                "value": 4400000,
                "unit": "VND/person/month",
                "effectiveFrom": "2026-01-01",
                "effectiveTo": None,
                "legalDocument": "Luật Thuế",
                "article": "19",
                "clause": "1",
                "point": "b",
                "sourceUrl": "https://thuvienphapluat.vn",
                "status": "Draft"
            }
        ]
    }

    rule_set, rules, dep_rules = build_tax_rule_models(
        extracted_data=extracted_data,
        tax_year=2026,
        filename="test.pdf"
    )

    assert len(dep_rules) == 1
    dep = dep_rules[0]
    assert dep.dependent_type == "CHILD"
    assert len(dep.required_documents) == 2

    doc1 = dep.required_documents[0]
    assert isinstance(doc1, DependentRuleDocument)
    assert doc1.doc_type == "BIRTH_CERTIFICATE"
    assert doc1.name == "Giấy khai sinh"
    assert doc1.is_mandatory is True

    doc2 = dep.required_documents[1]
    assert isinstance(doc2, DependentRuleDocument)
    assert doc2.doc_type == "CITIZEN_ID"
    assert doc2.is_mandatory is False

    # Kiểm tra format_tax_rule_data
    formatted = format_tax_rule_data(rule_set, rules, dep_rules)
    assert len(formatted["dependentRules"]) == 1
    formatted_dep = formatted["dependentRules"][0]
    assert len(formatted_dep["requiredDocuments"]) == 2
    assert formatted_dep["requiredDocuments"][0]["docType"] == "BIRTH_CERTIFICATE"
    assert formatted_dep["requiredDocuments"][0]["isMandatory"] is True


def test_service_create_and_update_dependent_rule():
    mock_repo = MagicMock()
    service = TaxRuleService(repository=mock_repo)

    rule_id = uuid.uuid4()
    dep_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    fake_doc = DependentRuleDocument(
        id=doc_id,
        dependent_rule_id=dep_id,
        doc_type="BIRTH_CERTIFICATE",
        name="Giấy khai sinh",
        is_mandatory=True,
        description="Bản sao"
    )
    fake_dep = DependentRule(
        id=dep_id,
        rule_id=rule_id,
        dependent_type="CHILD",
        name="Con dưới 18 tuổi",
        max_age=18,
        conditions='["Con chưa thành niên"]',
        status="Draft"
    )
    fake_dep.required_documents = [fake_doc]

    mock_repo.create_dependent_rule.return_value = fake_dep

    payload = DependentRuleCreateRequest(
        ruleId=rule_id,
        dependentType=DependentType.CHILD,
        name="Con dưới 18 tuổi",
        maxAge=18,
        requiredDocuments=[
            RequiredDocumentItemRequest(
                docType="BIRTH_CERTIFICATE",
                name="Giấy khai sinh",
                isMandatory=True,
                description="Bản sao"
            )
        ]
    )

    res = service.create_dependent_rule(rule_id=rule_id, payload=payload)
    assert res["message"] == "Dependent rule created successfully."
    assert res["data"]["id"] == str(dep_id)
    assert len(res["data"]["requiredDocuments"]) == 1
    assert res["data"]["requiredDocuments"][0]["docType"] == "BIRTH_CERTIFICATE"

    # Test update
    mock_repo.update_dependent_rule.return_value = fake_dep
    update_payload = DependentRuleUpdateRequest(
        name="Con dưới 18 tuổi cập nhật",
        maxAge=17
    )
    update_res = service.update_dependent_rule(dep_id=dep_id, payload=update_payload)
    assert update_res["message"] == "Dependent rule updated successfully."

    # Test delete
    mock_repo.delete_dependent_rule.return_value = True
    del_res = service.delete_dependent_rule(dep_id=dep_id)
    assert del_res["message"] == "Dependent rule deleted successfully."


def test_service_add_and_update_required_document():
    mock_repo = MagicMock()
    service = TaxRuleService(repository=mock_repo)

    dep_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    fake_doc = DependentRuleDocument(
        id=doc_id,
        dependent_rule_id=dep_id,
        doc_type="STUDENT_CARD",
        name="Thẻ sinh viên",
        is_mandatory=True,
        description="Còn hạn sử dụng"
    )
    mock_repo.add_required_document.return_value = fake_doc

    doc_create_payload = RequiredDocumentCreateRequest(
        docType="STUDENT_CARD",
        name="Thẻ sinh viên",
        isMandatory=True,
        description="Còn hạn sử dụng"
    )
    add_res = service.add_required_document(dependent_rule_id=dep_id, payload=doc_create_payload)
    assert add_res["message"] == "Required document added successfully."
    assert add_res["data"]["id"] == str(doc_id)
    assert add_res["data"]["docType"] == "STUDENT_CARD"

    # Test update doc
    mock_repo.update_required_document.return_value = fake_doc
    doc_update_payload = RequiredDocumentUpdateRequest(
        name="Thẻ sinh viên công chứng",
        isMandatory=False
    )
    update_res = service.update_required_document(doc_id=doc_id, payload=doc_update_payload)
    assert update_res["message"] == "Required document updated successfully."

    # Test delete doc
    mock_repo.delete_required_document.return_value = True
    del_res = service.delete_required_document(doc_id=doc_id)
    assert del_res["message"] == "Required document deleted successfully."


def test_required_document_type_enum_and_normalization():
    # 1. Kiểm tra 9 mã enum chuẩn hóa
    expected_types = [
        "BIRTH_CERTIFICATE",
        "CITIZEN_ID",
        "STUDENT_CARD",
        "DISABILITY_CERTIFICATE",
        "MARRIAGE_CERTIFICATE",
        "RELATIONSHIP_CERTIFICATE",
        "SUPPORT_COMMITMENT_FORM",
        "RESIDENCE_CT07",
        "OTHER",
    ]
    for doc_type in expected_types:
        enum_val = RequiredDocumentType(doc_type)
        assert enum_val.value == doc_type

    # 2. Kiểm tra normalize_document_type
    assert normalize_document_type("birth_certificate") == "BIRTH_CERTIFICATE"
    assert normalize_document_type("CCCD") == "CITIZEN_ID"
    assert normalize_document_type("CMND") == "CITIZEN_ID"
    assert normalize_document_type("DISABILITY_CERT") == "DISABILITY_CERTIFICATE"
    assert normalize_document_type("CUSTOM_VNEID_LEVEL_2") == "CUSTOM_VNEID_LEVEL_2"
    assert normalize_document_type("") == "OTHER"
    assert normalize_document_type(None) == "OTHER"

    # 3. Kiểm tra Pydantic request model với Enum và chuỗi custom
    req = RequiredDocumentCreateRequest(
        docType=RequiredDocumentType.RESIDENCE_CT07,
        name="Giấy xác nhận cư trú CT07",
        isMandatory=True
    )
    assert req.doc_type == RequiredDocumentType.RESIDENCE_CT07
    assert req.model_dump(by_alias=True)["docType"] == "RESIDENCE_CT07"

    # Hỗ trợ nhận mã custom linh hoạt từ Admin trên UI
    req_custom = RequiredDocumentCreateRequest(
        docType="CUSTOM_VNEID_LEVEL_2",
        name="Định danh VNeID mức 2",
        isMandatory=True
    )
    assert req_custom.doc_type == "CUSTOM_VNEID_LEVEL_2"
