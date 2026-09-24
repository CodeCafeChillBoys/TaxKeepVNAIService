from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Literal, Optional
import pymupdf

from app.core.config import settings
from app.errors.law_changeset_errors import (
    LawChangesetPdfUnreadableError,
    LawChangesetTooLargeError,
)

logger = logging.getLogger(__name__)


@dataclass
class PreparedChunk:
    chunk_index: int
    mode: Literal["TEXT", "PDF"]
    text_content: Optional[str] = None
    pdf_bytes: Optional[bytes] = None
    start_page: int = 1   # 1-indexed
    end_page: int = 1     # 1-indexed
    is_last_5_pages: bool = False


@dataclass
class PreparedPdfResult:
    total_pages: int
    pages_read: int
    mode: Literal["TEXT", "PDF"]
    chunks: List[PreparedChunk] = field(default_factory=list)


class LawPdfPreparer:
    """
    Chuẩn bị dữ liệu PDF cho Gemini theo đặc tả §8:
    - Đọc đủ 100% trang (không cắt 30 trang).
    - Tự động nhận diện TEXT (mọi trang >= 15 ký tự) hoặc PDF scan (< 15 ký tự).
    - Hỗ trợ chia file theo cụm trang nếu vượt ngưỡng cấu hình, luôn có lượt riêng cho 5 trang cuối.
    """

    def prepare(self, file_bytes: bytes, file_name: str = "") -> PreparedPdfResult:
        # 1. Kiểm tra kích thước tệp
        max_bytes = settings.LAW_CHANGESET_MAX_FILE_MB * 1024 * 1024
        if len(file_bytes) > max_bytes:
            mb = len(file_bytes) / (1024 * 1024)
            raise LawChangesetTooLargeError(
                f"Kích thước tệp ({mb:.1f} MB) vượt quá giới hạn tối đa "
                f"cho phép ({settings.LAW_CHANGESET_MAX_FILE_MB} MB)."
            )

        # 2. Mở file PDF bằng PyMuPDF
        try:
            doc = pymupdf.open(stream=file_bytes, filetype="pdf")
        except Exception as e:
            logger.error(f"Cannot open PDF with pymupdf: {e}")
            raise LawChangesetPdfUnreadableError(f"Không thể mở tệp PDF: {e}")

        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            raise LawChangesetPdfUnreadableError("Tệp PDF rỗng (0 trang).")

        # 3. Phân tích từng trang để chọn mode
        has_scanned_or_empty_page = False
        page_texts: List[str] = []

        for idx, page in enumerate(doc):
            txt = (page.get_text("text") or "").strip()
            if len(txt) < 15:
                has_scanned_or_empty_page = True
            page_texts.append(txt)

        mode: Literal["TEXT", "PDF"] = "PDF" if has_scanned_or_empty_page else "TEXT"
        logger.info(
            f"PDF analysis for '{file_name}': total_pages={total_pages}, "
            f"mode={mode} (has_scanned_or_empty={has_scanned_or_empty_page})"
        )

        max_pages_per_call = settings.LAW_CHANGESET_MAX_PAGES_PER_CALL
        max_chars_per_call = settings.LAW_CHANGESET_TEXT_MAX_CHARS_PER_CALL

        chunks: List[PreparedChunk] = []

        # 4. Phân chia cụm (Chunking logic)
        if mode == "TEXT":
            full_text = "\n\n".join(
                f"--- [Trang {i + 1}] ---\n{t}" for i, t in enumerate(page_texts)
            )
            # Kiểm tra xem có cần chia không
            needs_split = (total_pages > max_pages_per_call) or (len(full_text) > max_chars_per_call)
            if not needs_split or total_pages <= 5:
                chunks.append(
                    PreparedChunk(
                        chunk_index=0,
                        mode="TEXT",
                        text_content=full_text,
                        start_page=1,
                        end_page=total_pages,
                        is_last_5_pages=False,
                    )
                )
            else:
                # Cần chia cụm: thân văn bản (1 .. total_pages - 5) + 5 trang cuối
                last_5_start = max(1, total_pages - 4)
                main_end = last_5_start - 1

                # Chia phần thân
                current_start = 1
                chunk_idx = 0
                while current_start <= main_end:
                    current_end = min(current_start + max_pages_per_call - 1, main_end)
                    chunk_text = "\n\n".join(
                        f"--- [Trang {i + 1}] ---\n{page_texts[i]}"
                        for i in range(current_start - 1, current_end)
                    )
                    chunks.append(
                        PreparedChunk(
                            chunk_index=chunk_idx,
                            mode="TEXT",
                            text_content=chunk_text,
                            start_page=current_start,
                            end_page=current_end,
                            is_last_5_pages=False,
                        )
                    )
                    chunk_idx += 1
                    current_start = current_end + 1

                # Cụm 5 trang cuối
                last_5_text = "\n\n".join(
                    f"--- [Trang {i + 1}] ---\n{page_texts[i]}"
                    for i in range(last_5_start - 1, total_pages)
                )
                chunks.append(
                    PreparedChunk(
                        chunk_index=chunk_idx,
                        mode="TEXT",
                        text_content=last_5_text,
                        start_page=last_5_start,
                        end_page=total_pages,
                        is_last_5_pages=True,
                    )
                )
        else:
            # Mode = PDF
            needs_split = total_pages > max_pages_per_call
            if not needs_split or total_pages <= 5:
                chunks.append(
                    PreparedChunk(
                        chunk_index=0,
                        mode="PDF",
                        pdf_bytes=file_bytes,
                        start_page=1,
                        end_page=total_pages,
                        is_last_5_pages=False,
                    )
                )
            else:
                last_5_start = max(1, total_pages - 4)
                main_end = last_5_start - 1

                current_start = 1
                chunk_idx = 0
                while current_start <= main_end:
                    current_end = min(current_start + max_pages_per_call - 1, main_end)
                    new_doc = pymupdf.open()
                    new_doc.insert_pdf(doc, from_page=current_start - 1, to_page=current_end - 1)
                    chunk_bytes = new_doc.write()
                    new_doc.close()

                    chunks.append(
                        PreparedChunk(
                            chunk_index=chunk_idx,
                            mode="PDF",
                            pdf_bytes=chunk_bytes,
                            start_page=current_start,
                            end_page=current_end,
                            is_last_5_pages=False,
                        )
                    )
                    chunk_idx += 1
                    current_start = current_end + 1

                # Cụm 5 trang cuối
                last_doc = pymupdf.open()
                last_doc.insert_pdf(doc, from_page=last_5_start - 1, to_page=total_pages - 1)
                last_5_bytes = last_doc.write()
                last_doc.close()

                chunks.append(
                    PreparedChunk(
                        chunk_index=chunk_idx,
                        mode="PDF",
                        pdf_bytes=last_5_bytes,
                        start_page=last_5_start,
                        end_page=total_pages,
                        is_last_5_pages=True,
                    )
                )

        doc.close()

        pages_read = total_pages
        return PreparedPdfResult(
            total_pages=total_pages,
            pages_read=pages_read,
            mode=mode,
            chunks=chunks,
        )


pdf_preparer = LawPdfPreparer()
