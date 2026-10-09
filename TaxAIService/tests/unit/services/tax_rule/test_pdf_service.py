import os
import io
import pytest
import pymupdf
from unittest.mock import patch, MagicMock

from app.services.tax_rule.pdf_service import PDFService, pdf_service
from app.errors.pdf_errors import PDFProcessingError, PDFErrorMessages


def test_pdf_service_file_not_found():
    with pytest.raises(PDFProcessingError) as exc_info:
        pdf_service.prepare_pdf_for_ai("/path/that/does/not/exist.pdf")
    assert exc_info.value.detail == PDFErrorMessages.FILE_NOT_FOUND


def test_pdf_service_empty_pages():
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 0

    with patch("os.path.exists", return_value=True):
        with patch("pymupdf.open", return_value=mock_doc):
            with pytest.raises(PDFProcessingError) as exc_info:
                pdf_service.prepare_pdf_for_ai("dummy.pdf")
            assert exc_info.value.detail == PDFErrorMessages.NO_EXTRACTABLE_TEXT
            mock_doc.close.assert_called_once()


def test_pdf_service_text_only(tmp_path):
    text_pdf = tmp_path / "text.pdf"
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((50, 50), "This is a tax rule legal document with more than 15 characters to test text layer.")
    doc.save(str(text_pdf))
    doc.close()

    is_scanned, text_content, scan_bytes = pdf_service.prepare_pdf_for_ai(str(text_pdf))

    assert is_scanned is False
    assert "tax rule legal document" in text_content
    assert scan_bytes == b""


def test_pdf_service_scanned_or_empty_page(tmp_path):
    scanned_pdf = tmp_path / "scanned.pdf"
    doc = pymupdf.open()
    # Trang 1: Text ngắn dưới 15 ký tự -> coi như ảnh scan/trang rỗng
    page1 = doc.new_page()
    page1.insert_text((50, 50), "Ngắn")
    doc.save(str(scanned_pdf))
    doc.close()

    is_scanned, text_content, scan_bytes = pdf_service.prepare_pdf_for_ai(str(scanned_pdf), max_scan_pages=5)

    assert is_scanned is True
    assert text_content == ""
    assert len(scan_bytes) > 0
