import json
from datetime import datetime, timezone, timedelta
import pytest
from unittest.mock import MagicMock, patch
from google.genai.errors import APIError

from app.schemas.expense_ocr.expense_ocr_schema import (
    AdminCategoryItem,
    GeminiOcrOutput
)
from app.services.expense_ocr.expense_ocr_service import ExpenseOcrService
from app.errors.expense_ocr_errors import CorruptedFileError, UnreadableDocumentError


@pytest.mark.anyio
async def test_extract_and_classify_file_too_small():
    service = ExpenseOcrService()
    with pytest.raises(CorruptedFileError, match="Dữ liệu tệp tin rỗng"):
        await service.extract_and_classify(
            file_bytes=b"too_short",
            mime_type="image/jpeg",
            target_year=2026,
            categories=[]
        )


@pytest.mark.anyio
async def test_extract_and_classify_empty_ai_response():
    service = ExpenseOcrService()
    mock_resp = MagicMock()
    mock_resp.text = ""

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        with pytest.raises(UnreadableDocumentError):
            await service.extract_and_classify(
                file_bytes=b"x" * 150,
                mime_type="image/jpeg",
                target_year=2026,
                categories=[]
            )


@pytest.mark.anyio
async def test_extract_and_classify_api_error():
    service = ExpenseOcrService()

    with patch.object(service.client.models, "generate_content", side_effect=APIError(500, "Quota exceeded", {})):
        with pytest.raises(CorruptedFileError):
            await service.extract_and_classify(
                file_bytes=b"x" * 150,
                mime_type="image/jpeg",
                target_year=2026,
                categories=[]
            )


@pytest.mark.anyio
async def test_extract_and_classify_not_tax_document():
    service = ExpenseOcrService()

    fake_output = {
        "isTaxDocument": False,
        "docTypeCode": "NOT_TAX_DOCUMENT",
        "fields": []
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_output)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = await service.extract_and_classify(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_year=2026,
            categories=[AdminCategoryItem(code="MEDICAL", name="Y tế", description="Hóa đơn y tế")]
        )

    assert result["is_doc_type_valid"] is False
    errors = [e["code"] for e in result["validation_errors"]]
    assert "ERR_NOT_TAX_DOCUMENT" in errors


@pytest.mark.anyio
async def test_extract_and_classify_year_mismatch_and_future_date():
    service = ExpenseOcrService()

    # Tạo ngày mai trong tương lai
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=2)).strftime("%Y-%m-%d")

    fake_output = {
        "isTaxDocument": True,
        "docTypeCode": "MEDICAL",
        "extractedYear": 2025,
        "invoiceDate": tomorrow,
        "fields": [
            {"fieldName": "total_amount", "extractedValue": "500000", "confidenceScore": 0.95}
        ]
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_output)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = await service.extract_and_classify(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_year=2026,
            categories=[AdminCategoryItem(code="MEDICAL", name="Y tế", description="Hóa đơn y tế")]
        )

    assert result["is_year_valid"] is False
    errors = [e["code"] for e in result["validation_errors"]]
    assert "ERR_YEAR_MISMATCH" in errors
    assert "ERR_FUTURE_DATE" in errors


@pytest.mark.anyio
async def test_extract_and_classify_success():
    mock_repo = MagicMock()
    mock_repo.get_system_threshold.return_value = 0.85
    mock_repo.get_crucial_fields.return_value = {"total_amount"}

    service = ExpenseOcrService(repo=mock_repo)

    fake_output = {
        "isTaxDocument": True,
        "docTypeCode": "MEDICAL",
        "extractedYear": 2026,
        "invoiceDate": "2026-01-15",
        "fields": [
            {"fieldName": "total_amount", "extractedValue": "1000000", "confidenceScore": 0.95},
            {"fieldName": "seller_name", "extractedValue": "Bệnh viện", "confidenceScore": 0.90}
        ]
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_output)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = await service.extract_and_classify(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_year=2026,
            categories=[AdminCategoryItem(code="MEDICAL", name="Y tế", description="Hóa đơn y tế")]
        )

    assert result["is_doc_type_valid"] is True
    assert result["is_year_valid"] is True
    assert result["is_passed_threshold"] is True
    assert result["overall_confidence"] == 0.93
    assert len(result["validation_errors"]) == 0


@pytest.mark.anyio
async def test_withholding_voucher_validates_income_year_not_issue_year():
    service = ExpenseOcrService()
    fake_output = {
        "isTaxDocument": True,
        "docTypeCode": "WITHHOLDING_VOUCHER",
        "invoiceDate": "2025-01-10",
        "extractedYear": 2025,
        "incomeYear": 2024,
        "fields": [
            {"fieldName": "income_year", "extractedValue": "2024", "confidenceScore": 0.95}
        ]
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_output)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp):
        result = await service.extract_and_classify(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_year=2024,
            categories=[AdminCategoryItem(
                code="WITHHOLDING_VOUCHER",
                name="Chứng từ khấu trừ thuế",
                description="Chứng từ khấu trừ thuế TNCN"
            )]
        )

    assert result["is_year_valid"] is True
    assert not any(error["code"] == "ERR_YEAR_MISMATCH" for error in result["validation_errors"])
