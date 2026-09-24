import pytest
import pymupdf
from app.services.law_changeset.pdf_preparer import pdf_preparer, LawPdfPreparer
from app.errors.law_changeset_errors import LawChangesetTooLargeError, LawChangesetPdfUnreadableError
from app.core.config import settings


def _create_dummy_pdf(num_pages: int, with_text: bool = True) -> bytes:
    doc = pymupdf.open()
    for i in range(num_pages):
        page = doc.new_page(width=595, height=842)
        if with_text:
            page.insert_text(
                (50, 50),
                f"Day la trang thu {i + 1} voi noi dung quy dinh phap luat day du ve thue thu nhap ca nhan."
            )
    pdf_bytes = doc.write()
    doc.close()
    return pdf_bytes


def test_pdf_preparer_text_mode_61_pages():
    pdf_bytes = _create_dummy_pdf(61, with_text=True)
    res = pdf_preparer.prepare(pdf_bytes, "test_text_61.pdf")
    assert res.total_pages == 61
    assert res.pages_read == 61
    assert res.mode == "TEXT"
    assert len(res.chunks) == 1
    assert "--- [Trang 61] ---" in res.chunks[0].text_content


def test_pdf_preparer_scanned_mode_61_pages():
    # 60 trang có chữ nhưng 1 trang trống (< 15 ký tự)
    doc = pymupdf.open()
    for i in range(60):
        p = doc.new_page(width=595, height=842)
        p.insert_text((50, 50), f"Noi dung trang {i + 1} day du ky tu tren 15 chu.")
    # Trang 61 trống
    doc.new_page(width=595, height=842)
    pdf_bytes = doc.write()
    doc.close()

    res = pdf_preparer.prepare(pdf_bytes, "test_scanned_61.pdf")
    assert res.total_pages == 61
    assert res.pages_read == 61
    assert res.mode == "PDF"
    assert len(res.chunks) == 1
    assert res.chunks[0].pdf_bytes is not None


def test_pdf_preparer_split_chunks_with_last_5_pages(monkeypatch):
    # Hạ tạm cấu hình xuống 10 trang / call để test chia file
    monkeypatch.setattr(settings, "LAW_CHANGESET_MAX_PAGES_PER_CALL", 10)
    pdf_bytes = _create_dummy_pdf(25, with_text=True)

    res = pdf_preparer.prepare(pdf_bytes, "test_split.pdf")
    assert res.total_pages == 25
    assert res.pages_read == 25
    assert len(res.chunks) > 1
    # Chunk cuối cùng phải là 5 trang cuối (21..25)
    last_chunk = res.chunks[-1]
    assert last_chunk.is_last_5_pages is True
    assert last_chunk.start_page == 21
    assert last_chunk.end_page == 25


def test_pdf_preparer_too_large_error(monkeypatch):
    # Hạ giới hạn max MB xuống 0 MB để test lỗi
    monkeypatch.setattr(settings, "LAW_CHANGESET_MAX_FILE_MB", 0)
    pdf_bytes = _create_dummy_pdf(2, with_text=True)
    with pytest.raises(LawChangesetTooLargeError):
        pdf_preparer.prepare(pdf_bytes, "large.pdf")


def test_pdf_preparer_invalid_pdf_error():
    with pytest.raises(LawChangesetPdfUnreadableError):
        pdf_preparer.prepare(b"not a valid pdf content", "corrupt.pdf")
