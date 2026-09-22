import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.expense_ocr.expense_ocr_service import ExpenseOcrService
from app.schemas.expense_ocr.expense_ocr_schema import AdminCategoryItem
from app.errors.expense_ocr_errors import CorruptedFileError, UnreadableDocumentError


@pytest.mark.anyio
async def test_corrupted_file_error_on_empty_bytes():
    service = ExpenseOcrService()
    categories = [AdminCategoryItem(code="MEDICAL_EXPENSE_INVOICE", name="Y tế", description="Viện phí")]

    with pytest.raises(CorruptedFileError):
        await service.extract_and_classify(
            file_bytes=b"",
            mime_type="image/jpeg",
            target_year=2026,
            categories=categories
        )


@pytest.mark.anyio
async def test_validation_errors_structured():
    service = ExpenseOcrService()
    categories = [AdminCategoryItem(code="MEDICAL_EXPENSE_INVOICE", name="Y tế", description="Viện phí")]

    mock_gemini_output = """{
        "docTypeCode": "UNSUPPORTED",
        "classificationReason": "Hóa đơn ăn uống cafe",
        "extractedYear": 2025,
        "invoiceDate": "2099-01-01",
        "totalAmount": 100000.0,
        "fields": [
            {"fieldName": "total_amount", "extractedValue": "100000", "confidenceScore": 0.95}
        ]
    }"""

    mock_response = MagicMock()
    mock_response.text = mock_gemini_output

    with patch.object(service.client.models, "generate_content", return_value=mock_response):
        result = await service.extract_and_classify(
            file_bytes=b"dummy valid bytes for test purpose that is longer than 100 bytes 1234567890 1234567890 1234567890 1234567890 1234567890",
            mime_type="image/jpeg",
            target_year=2026,
            categories=categories
        )

        errors = result["validation_errors"]
        error_codes = [e["code"] for e in errors]

        # 1. Kiểm tra mã lỗi loại chứng từ không hợp lệ
        assert "ERR_INVALID_DOC_TYPE" in error_codes
        # 2. Kiểm tra mã lỗi năm không khớp
        assert "ERR_YEAR_MISMATCH" in error_codes
        # 3. Kiểm tra mã lỗi ngày ở tương lai
        assert "ERR_FUTURE_DATE" in error_codes


@pytest.mark.anyio
async def test_image_quality_too_low_structured():
    service = ExpenseOcrService()
    categories = [AdminCategoryItem(code="MEDICAL_EXPENSE_INVOICE", name="Y tế", description="Viện phí")]

    # Mô phỏng AI phát hiện ảnh bị mờ nét và lóa đèn flash
    mock_gemini_output = """{
        "docTypeCode": "MEDICAL_EXPENSE_INVOICE",
        "extractedYear": 2026,
        "invoiceDate": "2026-03-15",
        "totalAmount": 500000.0,
        "qualityIssues": ["IMAGE_BLURRY", "EXCESSIVE_GLARE"],
        "fields": [
            {"fieldName": "total_amount", "extractedValue": "500000", "confidenceScore": 0.52},
            {"fieldName": "seller_tax_code", "extractedValue": "0301234567", "confidenceScore": 0.60}
        ]
    }"""

    mock_response = MagicMock()
    mock_response.text = mock_gemini_output

    with patch.object(service.client.models, "generate_content", return_value=mock_response):
        result = await service.extract_and_classify(
            file_bytes=b"dummy valid bytes for test purpose that is longer than 100 bytes 1234567890 1234567890 1234567890 1234567890 1234567890",
            mime_type="image/jpeg",
            target_year=2026,
            categories=categories,
            applied_threshold=0.75
        )

        errors = result["validation_errors"]
        quality_err = next((e for e in errors if e["code"] == "ERR_IMAGE_QUALITY_TOO_LOW"), None)

        assert quality_err is not None
        assert quality_err["field"] == "file"
        assert quality_err["qualityScore"] == 0.56
        assert quality_err["requiredThreshold"] == 0.75
        assert "IMAGE_BLURRY" in quality_err["reasons"]
        assert "EXCESSIVE_GLARE" in quality_err["reasons"]


@pytest.mark.anyio
async def test_not_tax_document_vs_invalid_doc_type():
    service = ExpenseOcrService()
    categories = [AdminCategoryItem(code="MEDICAL_EXPENSE_INVOICE", name="Y tế", description="Viện phí")]

    # 1. Kịch bản tệp tin hoàn toàn không phải chứng từ thuế (ví dụ ảnh phong cảnh/selfie)
    mock_non_tax_output = """{
        "isTaxDocument": false,
        "docTypeCode": "NOT_TAX_DOCUMENT",
        "classificationReason": "Ảnh chụp selfie phong cảnh, không phải hóa đơn",
        "extractedYear": 2026,
        "fields": []
    }"""

    mock_resp_1 = MagicMock()
    mock_resp_1.text = mock_non_tax_output

    with patch.object(service.client.models, "generate_content", return_value=mock_resp_1):
        result_1 = await service.extract_and_classify(
            file_bytes=b"dummy valid bytes for test purpose that is longer than 100 bytes 1234567890 1234567890 1234567890 1234567890 1234567890",
            mime_type="image/jpeg",
            target_year=2026,
            categories=categories
        )

        errors_1 = result_1["validation_errors"]
        not_tax_err = next((e for e in errors_1 if e["code"] == "ERR_NOT_TAX_DOCUMENT"), None)
        assert not_tax_err is not None
        assert not_tax_err["message"] == "Uploaded file is not recognized as a valid tax document."
        # Đảm bảo không bị lẫn sang lỗi ERR_INVALID_DOC_TYPE
        assert not any(e["code"] == "ERR_INVALID_DOC_TYPE" for e in errors_1)

    # 2. Kịch bản là hóa đơn thật nhưng không thuộc danh mục khấu trừ (ví dụ hóa đơn cafe)
    mock_coffee_output = """{
        "isTaxDocument": true,
        "docTypeCode": "UNSUPPORTED",
        "classificationReason": "Hóa đơn cà phê ăn uống",
        "extractedYear": 2026,
        "fields": [
            {"fieldName": "total_amount", "extractedValue": "50000", "confidenceScore": 0.95}
        ]
    }"""

    mock_resp_2 = MagicMock()
    mock_resp_2.text = mock_coffee_output

    with patch.object(service.client.models, "generate_content", return_value=mock_resp_2):
        result_2 = await service.extract_and_classify(
            file_bytes=b"dummy valid bytes for test purpose that is longer than 100 bytes 1234567890 1234567890 1234567890 1234567890 1234567890",
            mime_type="image/jpeg",
            target_year=2026,
            categories=categories
        )

        errors_2 = result_2["validation_errors"]
        invalid_type_err = next((e for e in errors_2 if e["code"] == "ERR_INVALID_DOC_TYPE"), None)
        assert invalid_type_err is not None
        assert "not qualify for tax relief" in invalid_type_err["message"] or "Hóa đơn cà phê" in invalid_type_err["message"]
        # Đảm bảo không bị nhầm thành ERR_NOT_TAX_DOCUMENT
        assert not any(e["code"] == "ERR_NOT_TAX_DOCUMENT" for e in errors_2)


