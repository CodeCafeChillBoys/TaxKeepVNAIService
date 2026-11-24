import uuid
import pytest
from unittest.mock import MagicMock
from app.models.tax_rule import TaxRule
from app.models.tax_rule_set import TaxRuleSet
from app.models.dependent_rule import DependentRule
from app.models.dependent_rule_document import DependentRuleDocument
from app.enum import (
    DependentType,
    TaxRuleStatus,
    RequiredDocumentType,
    DependentRelationship,
)
from app.mappers.tax_rule import (
    build_tax_rule_models,
    format_tax_rule_data,
    normalize_document_type,
    normalize_dependent_type,
    normalize_relationship,
    normalize_alternative_group,
)
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


def test_build_tax_rule_models_with_relationship_and_alternative_group():
    extracted_data = {
        "taxRuleSet": {
            "name": "Luật Thuế TNCN 2026",
            "taxYear": 2026,
            "effectiveFrom": "2026-01-01",
            "effectiveTo": None,
            "status": "Draft"
        },
        "taxRules": [
            {
                "ruleCode": "PIT_DEDUCTION_DEPENDENT",
                "ruleName": "Giảm trừ gia cảnh cho người phụ thuộc",
                "ruleType": "DEDUCTION",
                "condition": {
                    "subject": "DEPENDENT",
                    "eligibility": [
                        {
                            "type": "PARENT_RETIRED",
                            "relationship": "PARENT",
                            "name": "Cha/mẹ ngoài độ tuổi lao động",
                            "maxAge": None,
                            "maxMonthlyIncome": 1000000.0,
                            "isStudying": False,
                            "isDisabled": False,
                            "conditions": ["Ngoài độ tuổi lao động", "Thu nhập không quá 1 triệu đồng/tháng"],
                            "requiredDocuments": [
                                {
                                    "docType": "CITIZEN_ID",
                                    "name": "CCCD của cha/mẹ",
                                    "isMandatory": True,
                                    "alternativeGroup": None,
                                    "description": "Chứng minh độ tuổi"
                                },
                                {
                                    "docType": "RELATIONSHIP_CERTIFICATE",
                                    "name": "Giấy xác nhận quan hệ",
                                    "isMandatory": True,
                                    "alternativeGroup": "RELATION_PROOF",
                                    "description": "Xác nhận quan hệ cha/mẹ"
                                },
                                {
                                    "docType": "BIRTH_CERTIFICATE",
                                    "name": "Giấy khai sinh của NNT",
                                    "isMandatory": True,
                                    "alternativeGroup": "RELATION_PROOF",
                                    "description": "Giấy khai sinh chứng minh quan hệ thay thế"
                                }
                            ]
                        }
                    ]
                },
                "value": 4400000,
                "unit": "VND/person/month",
                "effectiveFrom": "2026-01-01",
                "effectiveTo": None,
                "legalDocument": "Thông tư 111/2013/TT-BTC",
                "article": "9",
                "clause": "1",
                "point": "g",
                "sourceUrl": "https://thuvienphapluat.vn",
                "status": "Draft"
            }
        ]
    }

    rule_set, rules, dep_rules = build_tax_rule_models(
        extracted_data=extracted_data,
        tax_year=2026,
        filename="tt111_2013.pdf"
    )

    assert len(dep_rules) == 1
    dep = dep_rules[0]
    assert dep.dependent_type == "PARENT_RETIRED"
    assert dep.relationship == "PARENT"
    assert len(dep.required_documents) == 3

    # Doc 1: CITIZEN_ID, alternativeGroup: None
    doc1 = dep.required_documents[0]
    assert doc1.doc_type == "CITIZEN_ID"
    assert doc1.is_mandatory is True
    assert doc1.alternative_group is None

    # Doc 2: RELATIONSHIP_CERTIFICATE, alternativeGroup: RELATION_PROOF
    doc2 = dep.required_documents[1]
    assert doc2.doc_type == "RELATIONSHIP_CERTIFICATE"
    assert doc2.is_mandatory is True
    assert doc2.alternative_group == "RELATION_PROOF"

    # Doc 3: BIRTH_CERTIFICATE, alternativeGroup: RELATION_PROOF
    doc3 = dep.required_documents[2]
    assert doc3.doc_type == "BIRTH_CERTIFICATE"
    assert doc3.is_mandatory is True
    assert doc3.alternative_group == "RELATION_PROOF"

    # Format tax rule data
    formatted = format_tax_rule_data(rule_set, rules, dep_rules)
    formatted_dep = formatted["dependentRules"][0]
    assert formatted_dep["dependentType"] == "PARENT_RETIRED"
    assert formatted_dep["relationship"] == "PARENT"
    docs_formatted = formatted_dep["requiredDocuments"]
    assert len(docs_formatted) == 3
    assert docs_formatted[0]["docType"] == "CITIZEN_ID"
    assert docs_formatted[0]["alternativeGroup"] is None
    assert docs_formatted[1]["docType"] == "RELATIONSHIP_CERTIFICATE"
    assert docs_formatted[1]["alternativeGroup"] == "RELATION_PROOF"
    assert docs_formatted[2]["docType"] == "BIRTH_CERTIFICATE"
    assert docs_formatted[2]["alternativeGroup"] == "RELATION_PROOF"


def test_service_with_custom_dependent_type_and_alternative_group():
    mock_repo = MagicMock()
    service = TaxRuleService(repository=mock_repo)

    rule_id = uuid.uuid4()
    dep_id = uuid.uuid4()
    doc_id = uuid.uuid4()

    fake_doc = DependentRuleDocument(
        id=doc_id,
        dependent_rule_id=dep_id,
        doc_type="BIRTH_CERTIFICATE",
        name="Giấy khai sinh con nuôi",
        is_mandatory=True,
        alternative_group="IDENTITY_PROOF",
        description="Bản sao"
    )
    fake_dep = DependentRule(
        id=dep_id,
        rule_id=rule_id,
        dependent_type="FOSTER_CHILD",
        relationship="CHILD",
        name="Con nuôi dưới 18 tuổi",
        max_age=18,
        conditions='["Con nuôi hợp pháp"]',
        status="Draft"
    )
    fake_dep.required_documents = [fake_doc]

    mock_repo.create_dependent_rule.return_value = fake_dep

    # 1. Test create with custom dependent_type (no 422 validation error)
    payload = DependentRuleCreateRequest(
        ruleId=rule_id,
        dependentType="FOSTER_CHILD",
        relationship="CHILD",
        name="Con nuôi dưới 18 tuổi",
        maxAge=18,
        requiredDocuments=[
            RequiredDocumentItemRequest(
                docType="BIRTH_CERTIFICATE",
                name="Giấy khai sinh con nuôi",
                isMandatory=True,
                alternativeGroup="IDENTITY_PROOF",
                description="Bản sao"
            )
        ]
    )

    res = service.create_dependent_rule(rule_id=rule_id, payload=payload)
    assert res["message"] == "Dependent rule created successfully."
    assert res["data"]["dependentType"] == "FOSTER_CHILD"
    assert res["data"]["relationship"] == "CHILD"
    assert res["data"]["requiredDocuments"][0]["alternativeGroup"] == "IDENTITY_PROOF"

    # 2. Test update with custom dependent_type
    mock_repo.update_dependent_rule.return_value = fake_dep
    update_payload = DependentRuleUpdateRequest(
        dependentType="FOSTER_CHILD_CUSTOM",
        relationship="CHILD",
        name="Con nuôi cập nhật",
        maxAge=17
    )
    update_res = service.update_dependent_rule(dep_id=dep_id, payload=update_payload)
    assert update_res["message"] == "Dependent rule updated successfully."
    assert update_res["data"]["relationship"] == "CHILD"

    # 3. Test add required document with alternativeGroup
    mock_repo.add_required_document.return_value = fake_doc
    add_doc_payload = RequiredDocumentCreateRequest(
        docType="RELATIONSHIP_CERTIFICATE",
        name="Quyết định công nhận con nuôi",
        isMandatory=True,
        alternativeGroup="IDENTITY_PROOF"
    )
    add_doc_res = service.add_required_document(dependent_rule_id=dep_id, payload=add_doc_payload)
    assert add_doc_res["data"]["alternativeGroup"] == "IDENTITY_PROOF"


def test_dependent_type_and_relationship_normalization():
    # 1. normalize_dependent_type
    assert normalize_dependent_type("child_under_18") == "CHILD_UNDER_18"
    assert normalize_dependent_type("FOSTER_CHILD") == "FOSTER_CHILD"
    assert normalize_dependent_type("con_nuoi") == "CON_NUOI"
    assert normalize_dependent_type(None) == "OTHER_HELPLESS"
    assert normalize_dependent_type("") == "OTHER_HELPLESS"

    # 2. normalize_relationship
    assert normalize_relationship("CHILD") == "CHILD"
    assert normalize_relationship("child") == "CHILD"
    assert normalize_relationship("con") == "CHILD"
    assert normalize_relationship("PARENT") == "PARENT"
    assert normalize_relationship("cha_me") == "PARENT"
    assert normalize_relationship("SPOUSE") == "SPOUSE"
    assert normalize_relationship("vo_chong") == "SPOUSE"
    assert normalize_relationship("OTHER_DEPENDENT") == "OTHER_DEPENDENT"
    assert normalize_relationship("khac") == "OTHER_DEPENDENT"
    assert normalize_relationship(None) is None
    assert normalize_relationship("") is None

    # 3. normalize_alternative_group
    assert normalize_alternative_group("relation_proof") == "RELATION_PROOF"
    assert normalize_alternative_group("IDENTITY PROOF") == "IDENTITY_PROOF"
    assert normalize_alternative_group(None) is None
    assert normalize_alternative_group("") is None

