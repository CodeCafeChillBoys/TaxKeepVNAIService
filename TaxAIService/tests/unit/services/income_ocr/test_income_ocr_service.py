import json
import pytest
from unittest.mock import MagicMock, patch

from app.schemas.income_ocr.income_ocr_schema import (
    GeminiIncomeOcrOutput,
    ExtractedIncomeFieldDetail
)
from app.services.income_ocr.income_ocr_service import (
    evaluate_income_threshold,
    IncomeOcrService
)


# ==============================================================================
# 1. Test evaluate_income_threshold()
# ==============================================================================
def test_evaluate_income_threshold_passed():
    doc = GeminiIncomeOcrOutput(
        isIncomeDocument=True,
        fields=[
            ExtractedIncomeFieldDetail(fieldName="organization_name", extractedValue="Công ty A", confidenceScore=0.95),
            ExtractedIncomeFieldDetail(fieldName="month", extractedValue="1", confidenceScore=0.90),
            ExtractedIncomeFieldDetail(fieldName="year", extractedValue="2026", confidenceScore=0.92),
            ExtractedIncomeFieldDetail(fieldName="total_taxable_income", extractedValue="20000000", confidenceScore=0.90)
        ]
    )

    res = evaluate_income_threshold(doc, applied_threshold=0.80)
    assert res.is_passed_threshold is True
    assert res.overall_confidence == 0.92
    assert res.warning_message is None


def test_evaluate_income_threshold_crucial_low_confidence():
    doc = GeminiIncomeOcrOutput(
        isIncomeDocument=True,
        fields=[
            ExtractedIncomeFieldDetail(fieldName="organization_name", extractedValue="Công ty A", confidenceScore=0.50), # Crucial field thấp
            ExtractedIncomeFieldDetail(fieldName="other_field", extractedValue="123", confidenceScore=0.99)
        ]
    )

    res = evaluate_income_threshold(doc, applied_threshold=0.80)
    assert res.is_passed_threshold is False
    assert "Các trường cốt lõi của phiếu lương bị mờ" in res.warning_message


# ==============================================================================
# 2. Test IncomeOcrService.extract_payslip()
# ==============================================================================
def test_extract_payslip_file_too_small():
    service = IncomeOcrService()
    res = service.extract_payslip(file_bytes=b"short", mime_type="image/jpeg")

    assert res.success is False
    assert res.status_code == 400
    assert res.errors[0]["code"] == "ERR_CORRUPTED_FILE"


def test_extract_payslip_empty_ai_response():
    service = IncomeOcrService()
    mock_resp = MagicMock()
    mock_resp.text = ""

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        res = service.extract_payslip(file_bytes=b"x" * 150, mime_type="image/jpeg")

    assert res.success is False
    assert res.status_code == 422
    assert res.errors[0]["code"] == "ERR_UNREADABLE"


def test_extract_payslip_invalid_month_and_year_mismatch():
    service = IncomeOcrService()

    fake_json = {
        "isIncomeDocument": True,
        "organizationName": "Công ty B",
        "month": 15,       # Sai tháng (phải từ 1-12)
        "year": 2024,      # Lệch năm so với target_year 2026
        "fields": []
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_json)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        res = service.extract_payslip(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_year=2026
        )

    assert res.success is False
    assert res.status_code == 422
    err_codes = [e["code"] for e in res.errors]
    assert "ERR_INVALID_MONTH" in err_codes
    assert "ERR_YEAR_MISMATCH" in err_codes


def test_extract_payslip_success():
    mock_repo = MagicMock()
    mock_repo.get_system_threshold.return_value = 0.85
    service = IncomeOcrService(repo=mock_repo)

    fake_json = {
        "isIncomeDocument": True,
        "organizationName": "Công ty C",
        "employeeName": "Trần Văn B",
        "month": 5,
        "year": 2026,
        "totalTaxableIncome": 25000000.0,
        "fields": [
            {"fieldName": "organization_name", "extractedValue": "Công ty C", "confidenceScore": 0.95},
            {"fieldName": "month", "extractedValue": "5", "confidenceScore": 0.90},
            {"fieldName": "year", "extractedValue": "2026", "confidenceScore": 0.90},
            {"fieldName": "total_taxable_income", "extractedValue": "25000000", "confidenceScore": 0.95}
        ]
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_json)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        res = service.extract_payslip(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_month=5,
            target_year=2026
        )

    assert res.success is True
    assert res.status_code == 200
    assert res.data.organization_name == "Công ty C"
    assert res.data.total_taxable_income == 25000000.0
    assert res.data.threshold_validation.is_passed_threshold is True
    mock_repo.get_system_threshold.assert_called_once()
