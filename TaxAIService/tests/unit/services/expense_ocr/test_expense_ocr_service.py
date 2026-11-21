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


@pytest.mark.anyio
async def test_medical_statement_uses_prompt_service_when_available():
    mock_prompt_service = MagicMock()
    mock_prompt_service.get_rendered_prompt.return_value = "RENDERED_PROMPT_FROM_DB"

    service = ExpenseOcrService(prompt_service=mock_prompt_service)
    fake_output = {
        "isTaxDocument": True,
        "docTypeCode": "MEDICAL_STATEMENT",
        "extractedYear": 2026,
        "fields": []
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_output)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp) as mock_gen:
        await service.extract_and_classify(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_year=2026,
            categories=[
                AdminCategoryItem(code="MEDICAL_STATEMENT", name="Bảng kê KCB", description="Bảng kê", isMedicalStatement=True)
            ],
            is_medical_statement_request=True,
            expected_doc_type="MEDICAL_STATEMENT"
        )

    mock_prompt_service.get_rendered_prompt.assert_called_once()
    call_args = mock_prompt_service.get_rendered_prompt.call_args
    assert call_args.kwargs["prompt_key"] == "PROMPT_MEDICAL_STATEMENT_OCR"
    assert call_args.kwargs["params"]["medical_doc_type_code"] == "MEDICAL_STATEMENT"


@pytest.mark.anyio
async def test_medical_statement_fallback_without_prompt_service():
    service = ExpenseOcrService(prompt_service=None)
    fake_output = {
        "isTaxDocument": True,
        "docTypeCode": "MEDICAL_COST_STATEMENT",
        "extractedYear": 2026,
        "fields": []
    }
    mock_resp = MagicMock()
    mock_resp.text = json.dumps(fake_output)

    with patch.object(service.client.models, "generate_content", return_value=mock_resp) as mock_gen:
        await service.extract_and_classify(
            file_bytes=b"x" * 150,
            mime_type="image/jpeg",
            target_year=2026,
            categories=[],
            is_medical_statement_request=True
        )

    # config.system_instruction was passed to generate_content
    call_args = mock_gen.call_args
    config = call_args.kwargs.get("config")
    assert config is not None
    assert "BẢNG KÊ CHI PHÍ KHÁM BỆNH, CHỮA BỆNH" in config.system_instruction


def test_build_expense_ocr_prompt_dynamic():
    from app.prompts.expense_ocr import build_expense_ocr_prompt

    mock_service = MagicMock()
    mock_service.get_rendered_prompt.side_effect = lambda prompt_key, default_template, params: f"RENDERED_{prompt_key}"

    categories = [
        AdminCategoryItem(code="MEDICAL_COST_STATEMENT", name="Bảng kê KCB", description="Bảng kê", isMedicalStatement=True)
    ]
    prompt = build_expense_ocr_prompt(categories=categories, prompt_service=mock_service)
    assert "RENDERED_PROMPT_EXPENSE_OCR" in prompt
    assert mock_service.get_rendered_prompt.call_count >= 1


def test_build_medical_statement_prompt_dynamic():
    from app.prompts.expense_ocr import build_medical_statement_prompt

    mock_service = MagicMock()
    mock_service.get_rendered_prompt.return_value = "RENDERED_PROMPT_MEDICAL_STATEMENT_OCR"

    prompt = build_medical_statement_prompt(
        medical_doc_type="TEST_DOC",
        categories_text="Test categories",
        prompt_service=mock_service,
    )
    assert "RENDERED_PROMPT_MEDICAL_STATEMENT_OCR" in prompt
    call_args = mock_service.get_rendered_prompt.call_args
    assert call_args.kwargs["prompt_key"] == "PROMPT_MEDICAL_STATEMENT_OCR"
    assert call_args.kwargs["params"]["medical_doc_type_code"] == "TEST_DOC"

