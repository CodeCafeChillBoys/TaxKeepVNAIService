import os
import uuid
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.services.tax_rule.tax_rule_document_service import TaxRuleDocumentService
from app.errors.tax_rule_errors import TaxRuleErrorMessages, TaxRuleServiceError
from app.errors.pdf_errors import PDFProcessingError


# ==============================================================================
# 1. Test Khởi tạo Service (Constructor fallback)
# ==============================================================================
def test_document_service_init_with_repo_db_fallback():
    """Nếu không truyền url_validation_service nhưng repo có thuộc tính db, tự khởi tạo service url."""
    mock_repo = MagicMock()
    mock_repo.db = MagicMock()

    service = TaxRuleDocumentService(repository=mock_repo)
    assert service.url_validation_service is not None


# ==============================================================================
# 2. Test Step 0: Kiểm tra Source URL (Kết nối giữa URL Service và TaxRule)
# ==============================================================================
@pytest.mark.anyio
async def test_process_document_invalid_source_url():
    """Nếu source_url không hợp lệ hoặc chưa được duyệt, ném lỗi 400 Bad Request."""
    mock_repo = MagicMock()
    mock_url_service = MagicMock()
    mock_url_service.validate_url.return_value = (False, "Tên miền chưa được phê duyệt.", None)

    service = TaxRuleDocumentService(
        repository=mock_repo,
        url_validation_service=mock_url_service
    )

    with pytest.raises(TaxRuleServiceError) as exc_info:
        await service.process_tax_rule_document(
            filename="luat_thue.pdf",
            file_bytes=b"fake_pdf_content",
            tax_year=2026,
            source_url="https://evil.com/fake_law.pdf"
        )

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == "Tên miền chưa được phê duyệt."
    mock_url_service.validate_url.assert_called_once_with("https://evil.com/fake_law.pdf")
    # Không được gọi các bước tiếp theo
    mock_repo.get_rule_set_by_year.assert_not_called()


@pytest.mark.anyio
async def test_process_document_invalid_source_url_default_message():
    """Nếu source_url không hợp lệ và url_service không trả message cụ thể, dùng thông báo mặc định."""
    mock_repo = MagicMock()
    mock_url_service = MagicMock()
    mock_url_service.validate_url.return_value = (False, None, None)

    service = TaxRuleDocumentService(
        repository=mock_repo,
        url_validation_service=mock_url_service
    )

    with pytest.raises(TaxRuleServiceError) as exc_info:
        await service.process_tax_rule_document(
            filename="luat_thue.pdf",
            file_bytes=b"fake_pdf_content",
            tax_year=2026,
            source_url="https://unapproved.com"
        )

    assert exc_info.value.status_code == 400
    assert "không thuộc danh sách được phê duyệt" in exc_info.value.message


# ==============================================================================
# 3. Test Step 1: Kiểm tra trùng lặp Tax Year
# ==============================================================================
@pytest.mark.anyio
async def test_process_document_duplicate_tax_year():
    """Nếu tax_year đã tồn tại trong database, ném lỗi 409 Conflict."""
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = TaxRuleSet(rule_set_id=uuid.uuid4(), tax_year=2026)

    service = TaxRuleDocumentService(repository=mock_repo)

    with pytest.raises(TaxRuleServiceError) as exc_info:
        await service.process_tax_rule_document(
            filename="luat_thue.pdf",
            file_bytes=b"fake_pdf_content",
            tax_year=2026,
            source_url=None
        )

    assert exc_info.value.status_code == 409
    assert exc_info.value.message == TaxRuleErrorMessages.TAX_RULE_SET_EXISTS


# ==============================================================================
# 4. Test Step 2 & 3: Xử lý PDF và Dọn dẹp File tạm
# ==============================================================================
@pytest.mark.anyio
async def test_process_document_pdf_processing_error():
    """Khi file PDF lỗi (PDFProcessingError), ném lỗi 400 và đảm bảo file tạm đã bị xóa."""
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = None

    service = TaxRuleDocumentService(repository=mock_repo)

    with patch("app.services.tax_rule.tax_rule_document_service.pdf_service.prepare_pdf_for_ai", side_effect=PDFProcessingError("Corrupted file")):
        with pytest.raises(TaxRuleServiceError) as exc_info:
            await service.process_tax_rule_document(
                filename="corrupt.pdf",
                file_bytes=b"bad_bytes",
                tax_year=2026
            )

    assert exc_info.value.status_code == 400
    assert exc_info.value.message == TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED


# ==============================================================================
# 5. Test Step 4: Gọi AI trích xuất (Gemini AI)
# ==============================================================================
@pytest.mark.anyio
async def test_process_document_ai_extraction_http_error():
    """Khi dịch vụ AI ném HTTPException (vd: 503 Service Unavailable), chuyển tiếp lỗi tương ứng."""
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = None

    service = TaxRuleDocumentService(repository=mock_repo)

    with patch("app.services.tax_rule.tax_rule_document_service.pdf_service.prepare_pdf_for_ai", return_value=(False, "Text content", None)):
        with patch("app.services.tax_rule.tax_rule_document_service.tax_rule_extraction_service.extract_tax_rules", side_effect=HTTPException(status_code=503, detail="Gemini Overloaded")):
            with pytest.raises(TaxRuleServiceError) as exc_info:
                await service.process_tax_rule_document(
                    filename="luat.pdf",
                    file_bytes=b"pdf_bytes",
                    tax_year=2026
                )

    assert exc_info.value.status_code == 503
    assert exc_info.value.message == "Gemini Overloaded"


# ==============================================================================
# 6. Test Step 5: Kiểm tra trùng mã Rule Code
# ==============================================================================
@pytest.mark.anyio
async def test_process_document_duplicate_rule_code():
    """Nếu ruleCode bóc tách được đã tồn tại trong DB, ném lỗi 409 Conflict."""
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = None
    mock_repo.check_existing_rule_codes.return_value = True

    service = TaxRuleDocumentService(repository=mock_repo)

    fake_extracted = {
        "taxRules": [{"ruleCode": "PIT_DEDUCTION_01"}]
    }

    with patch("app.services.tax_rule.tax_rule_document_service.pdf_service.prepare_pdf_for_ai", return_value=(False, "Text content", None)):
        with patch("app.services.tax_rule.tax_rule_document_service.tax_rule_extraction_service.extract_tax_rules", return_value=fake_extracted):
            with pytest.raises(TaxRuleServiceError) as exc_info:
                await service.process_tax_rule_document(
                    filename="luat.pdf",
                    file_bytes=b"pdf_bytes",
                    tax_year=2026
                )

    assert exc_info.value.status_code == 409
    assert exc_info.value.message == "The rule code already exists."


# ==============================================================================
# 7. Test Thành Công: PDF dạng Scanned và PDF văn bản thông thường
# ==============================================================================
@pytest.mark.anyio
async def test_process_document_success_with_valid_url_and_warnings():
    """
    Quy trình thành công trọn vẹn:
    - URL hợp lệ
    - PDF Scanned (truyền bytes sang AI)
    - Trích xuất thành công và có cảnh báo cảnh giác (warning, verification)
    - Lưu vào DB thành công
    """
    mock_repo = MagicMock()
    mock_url_service = MagicMock()
    mock_url_service.validate_url.return_value = (True, None, MagicMock())

    mock_repo.get_rule_set_by_year.return_value = None
    mock_repo.check_existing_rule_codes.return_value = False

    rule_set_id = uuid.uuid4()
    saved_rs = TaxRuleSet(rule_set_id=rule_set_id, name="Luật Thuế TNCN 2026", tax_year=2026, status="DRAFT")
    saved_rule = TaxRule(rule_id=uuid.uuid4(), rule_code="PIT_01", rule_name="Giảm trừ gia cảnh", rule_type="DEDUCTION")
    mock_repo.create_tax_rule_set.return_value = (saved_rs, [saved_rule], [])

    service = TaxRuleDocumentService(
        repository=mock_repo,
        url_validation_service=mock_url_service
    )

    fake_extracted = {
        "taxRuleSet": {"name": "Luật Thuế TNCN 2026", "taxYear": 2026},
        "taxRules": [{"ruleCode": "PIT_01", "ruleName": "Giảm trừ gia cảnh", "ruleType": "DEDUCTION"}],
        "warning": "Cần kiểm tra kỹ khoản 3 điều 5",
        "verification": {"accuracy": 0.95}
    }

    # Giả lập PDF dạng Scanned (is_scanned=True, scan_bytes=b"scan_data")
    with patch("app.services.tax_rule.tax_rule_document_service.pdf_service.prepare_pdf_for_ai", return_value=(True, None, b"scan_data")):
        with patch("app.services.tax_rule.tax_rule_document_service.tax_rule_extraction_service.extract_tax_rules", return_value=fake_extracted) as mock_extract:
            result = await service.process_tax_rule_document(
                filename="luat_scanned.pdf",
                file_bytes=b"pdf_file_bytes",
                tax_year=2026,
                name="Luật Thuế TNCN 2026",
                source_url="https://thuvienphapluat.vn/van-ban/luat.pdf"
            )

    # Đảm bảo hàm AI được gọi với scan_bytes khi is_scanned=True
    mock_extract.assert_called_once()
    assert mock_extract.call_args.kwargs["pdf_bytes"] == b"scan_data"
    assert mock_extract.call_args.kwargs["document_text"] is None

    # Kiểm tra cấu trúc trả về
    assert "Tax document processed with warning" in result["message"]
    assert result["warning"] == "Cần kiểm tra kỹ khoản 3 điều 5"
    assert result["data"]["warning"] == "Cần kiểm tra kỹ khoản 3 điều 5"
    assert result["data"]["verification"] == {"accuracy": 0.95}
    assert result["data"]["taxRuleSet"]["name"] == "Luật Thuế TNCN 2026"
    mock_repo.create_tax_rule_set.assert_called_once()


@pytest.mark.anyio
async def test_process_document_success_standard_no_warning():
    """Quy trình thành công với PDF thông thường (không scan, không warning)."""
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = None
    mock_repo.check_existing_rule_codes.return_value = False

    rule_set_id = uuid.uuid4()
    saved_rs = TaxRuleSet(rule_set_id=rule_set_id, name="Luật 2026", tax_year=2026, status="DRAFT")
    saved_rule = TaxRule(rule_id=uuid.uuid4(), rule_code="PIT_02", rule_name="Biểu thuế", rule_type="TAX_BRACKET")
    mock_repo.create_tax_rule_set.return_value = (saved_rs, [saved_rule], [])

    service = TaxRuleDocumentService(repository=mock_repo)

    fake_extracted = {
        "taxRuleSet": {"name": "Luật 2026", "taxYear": 2026},
        "taxRules": [{"ruleCode": "PIT_02", "ruleName": "Biểu thuế", "ruleType": "TAX_BRACKET"}]
    }

    with patch("app.services.tax_rule.tax_rule_document_service.pdf_service.prepare_pdf_for_ai", return_value=(False, "Text", None)):
        with patch("app.services.tax_rule.tax_rule_document_service.tax_rule_extraction_service.extract_tax_rules", return_value=fake_extracted):
            result = await service.process_tax_rule_document(
                filename="luat_2026.pdf",
                file_bytes=b"normal_pdf_bytes",
                tax_year=2026
            )

    assert result["message"] == "Tax document processed successfully."
    assert result["warning"] is None
    assert "data" in result
    assert result["data"]["taxRuleSet"]["name"] == "Luật 2026"


@pytest.mark.anyio
async def test_process_document_cleanup_os_error():
    """Nếu os.remove ném OSError khi dọn file tạm, khối finally vẫn pass và không làm crash ứng dụng."""
    mock_repo = MagicMock()
    mock_repo.get_rule_set_by_year.return_value = None
    service = TaxRuleDocumentService(repository=mock_repo)

    with patch("os.remove", side_effect=OSError("Permission denied")):
        with patch("app.services.tax_rule.tax_rule_document_service.pdf_service.prepare_pdf_for_ai", side_effect=PDFProcessingError("Corrupt")):
            with pytest.raises(TaxRuleServiceError):
                await service.process_tax_rule_document(
                    filename="bad.pdf",
                    file_bytes=b"bytes",
                    tax_year=2026
                )


