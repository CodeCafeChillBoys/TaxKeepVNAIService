import uuid
import pytest
from pydantic import ValidationError

from app.schemas.tax_rule.tax_rule_request import (
    TaxRuleUploadRequest,
    TaxRuleApproveRequest,
    TaxRuleItemUpdateRequest,
    TaxRuleUpdateRequest
)
from app.schemas.url_rule.url_rule_schema import (
    UrlRuleCreateRequest,
    UrlRuleUpdateRequest
)
from app.schemas.system_config.system_config_schema import (
    SystemConfigCreateRequest,
    SystemConfigUpdateRequest
)
from app.schemas.ocr.ocr_document_schema import (
    DependentRuleItem,
    RuleValidationResult,
    ConfidenceScores,
    ThresholdValidationResult
)
from app.schemas.expense_ocr.expense_ocr_schema import (
    AdminCategoryItem,
    BoundingBox,
    ExtractedFieldDetail,
    InvoiceLineItem
)


# ==============================================================================
# 1. Tax Rule Schemas Validation
# ==============================================================================
def test_tax_rule_upload_request_valid():
    req = TaxRuleUploadRequest(
        taxYear=2026,
        name="Luật Thuế 2026",
        sourceUrl="https://chinhphu.vn/luat.pdf"
    )
    assert req.tax_year == 2026
    assert req.name == "Luật Thuế 2026"
    assert req.source_url == "https://chinhphu.vn/luat.pdf"


def test_tax_rule_upload_request_boundary_years():
    # Biên dưới 1900
    req_min = TaxRuleUploadRequest(taxYear=1900)
    assert req_min.tax_year == 1900

    # Biên trên 2100
    req_max = TaxRuleUploadRequest(taxYear=2100)
    assert req_max.tax_year == 2100

    # Ngoài biên < 1900
    with pytest.raises(ValidationError):
        TaxRuleUploadRequest(taxYear=1899)

    # Ngoài biên > 2100
    with pytest.raises(ValidationError):
        TaxRuleUploadRequest(taxYear=2101)


def test_tax_rule_approve_request():
    admin_id = uuid.uuid4()
    req = TaxRuleApproveRequest(adminId=admin_id)
    assert req.admin_id == admin_id

    # Sai format UUID
    with pytest.raises(ValidationError):
        TaxRuleApproveRequest(adminId="not-a-valid-uuid")


def test_tax_rule_item_update_request_alias():
    req = TaxRuleItemUpdateRequest(
        ruleCode="PIT_01",
        ruleName="Giảm trừ",
        value=11000000.0,
        unit="VND"
    )
    assert req.rule_code == "PIT_01"
    assert req.rule_name == "Giảm trừ"
    assert req.value == 11000000.0


# ==============================================================================
# 2. URL Rule Schemas Validation
# ==============================================================================
def test_url_rule_create_request_valid():
    req = UrlRuleCreateRequest(
        name="Cổng Chính Phủ",
        domain="chinhphu.vn",
        description="Nguồn văn bản",
        isActive=True
    )
    assert req.name == "Cổng Chính Phủ"
    assert req.domain == "chinhphu.vn"
    assert req.is_active is True


def test_url_rule_create_request_missing_required():
    # Thiếu domain
    with pytest.raises(ValidationError):
        UrlRuleCreateRequest(name="Tên")


def test_url_rule_update_request_partial():
    req = UrlRuleUpdateRequest(name="Tên mới", isActive=False)
    assert req.name == "Tên mới"
    assert req.is_active is False
    assert req.domain is None


# ==============================================================================
# 3. System Config Schemas Validation
# ==============================================================================
def test_system_config_create_request():
    req = SystemConfigCreateRequest(
        config_key="THRESHOLD_OCR",
        config_value="0.85",
        description="Ngưỡng OCR"
    )
    assert req.config_key == "THRESHOLD_OCR"
    assert req.config_value == "0.85"


def test_system_config_create_request_min_length():
    # config_key < 3 ký tự phải bắn lỗi
    with pytest.raises(ValidationError):
        SystemConfigCreateRequest(
            config_key="AB",
            config_value="10"
        )


def test_system_config_update_request():
    req = SystemConfigUpdateRequest(config_value="0.90", is_active=True)
    assert req.config_value == "0.90"
    assert req.is_active is True


# ==============================================================================
# 4. OCR Document Schemas Validation
# ==============================================================================
def test_dependent_rule_item():
    item = DependentRuleItem(
        docType="BIRTH_CERTIFICATE",
        isMandatory=True,
        description="Giấy khai sinh bản gốc"
    )
    assert item.doc_type == "BIRTH_CERTIFICATE"
    assert item.is_mandatory is True


def test_rule_validation_result():
    res = RuleValidationResult(
        isMatchedRule=True,
        matchedDocType="BIRTH_CERTIFICATE",
        isCompliantWithDescription=True,
        notes="Hợp lệ"
    )
    assert res.is_matched_rule is True
    assert res.matched_doc_type == "BIRTH_CERTIFICATE"


def test_confidence_scores_and_threshold_validation():
    scores = ConfidenceScores(
        overall=0.92,
        citizenId=0.95,
        fullName=0.90
    )
    assert scores.overall == 0.92
    assert scores.citizen_id == 0.95

    t_res = ThresholdValidationResult(
        appliedThreshold=0.80,
        overallConfidence=0.92,
        isPassedThreshold=True
    )
    assert t_res.is_passed_threshold is True


# ==============================================================================
# 5. Expense OCR Schemas Validation
# ==============================================================================
def test_expense_ocr_models():
    cat = AdminCategoryItem(
        code="MEDICAL",
        name="Chi phí y tế",
        description="Hóa đơn khám chữa bệnh"
    )
    assert cat.code == "MEDICAL"

    box = BoundingBox(x=10, y=20, w=100, h=50)
    assert box.x == 10
    assert box.w == 100

    field = ExtractedFieldDetail(
        fieldName="totalAmount",
        extractedValue="500,000",
        confidenceScore=0.95,
        boundingBox=box
    )
    assert field.fieldName == "totalAmount"
    assert field.confidenceScore == 0.95
    assert field.boundingBox.h == 50

    line_item = InvoiceLineItem(
        itemOrder=1,
        itemName="Thuốc kháng sinh",
        quantity=2.0,
        unitPrice=50000.0,
        totalPrice=100000.0
    )
    assert line_item.totalPrice == 100000.0
