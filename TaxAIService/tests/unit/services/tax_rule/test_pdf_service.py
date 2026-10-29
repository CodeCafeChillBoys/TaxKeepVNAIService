import os
import io
import pytest
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
        with patch("app.services.tax_rule.pdf_service.pymupdf.open", return_value=mock_doc):
            with pytest.raises(PDFProcessingError) as exc_info:
                pdf_service.prepare_pdf_for_ai("dummy.pdf")
            assert exc_info.value.detail == PDFErrorMessages.NO_EXTRACTABLE_TEXT
            mock_doc.close.assert_called_once()


def test_pdf_service_text_only():
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = "This is a tax rule legal document with more than 15 characters to test text layer."
    mock_doc.__iter__.return_value = iter([mock_page])

    with patch("os.path.exists", return_value=True):
        with patch("app.services.tax_rule.pdf_service.pymupdf.open", return_value=mock_doc):
            is_scanned, text_content, scan_bytes = pdf_service.prepare_pdf_for_ai("dummy.pdf")

    assert is_scanned is False
    assert "tax rule legal document" in text_content
    assert scan_bytes == b""
    mock_doc.close.assert_called_once()


def test_pdf_service_scanned_or_empty_page():
    mock_doc = MagicMock()
    mock_doc.__len__.return_value = 1
    mock_page = MagicMock()
    mock_page.get_text.return_value = "Ngắn"
    mock_doc.__iter__.return_value = iter([mock_page])

    mock_new_doc = MagicMock()
    mock_new_doc.write.return_value = b"sample_scan_bytes"

    with patch("os.path.exists", return_value=True):
        with patch("app.services.tax_rule.pdf_service.pymupdf.open", side_effect=[mock_doc, mock_new_doc]):
            is_scanned, text_content, scan_bytes = pdf_service.prepare_pdf_for_ai("dummy.pdf", max_scan_pages=5)

    assert is_scanned is True
    assert text_content == ""
    assert len(scan_bytes) > 0
    mock_new_doc.insert_pdf.assert_called_once()
    mock_new_doc.close.assert_called_once()
    mock_doc.close.assert_called_once()
