import os
from typing import List, Dict, Any, Tuple
import pymupdf
from fastapi import HTTPException, status


class PDFProcessingError(HTTPException):
    def __init__(self, detail: str = "PDF does not contain extractable text."):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)


class PDFService:
    @staticmethod
    def extract_text_pages(file_path: str) -> List[Dict[str, Any]]:
        """
        Bóc tách text từng trang từ file PDF bằng PyMuPDF.
        """
        if not os.path.exists(file_path):
            raise PDFProcessingError(detail="File not found.")

        try:
            doc = pymupdf.open(file_path)
        except Exception as e:
            raise PDFProcessingError(detail=f"Cannot open PDF file: {str(e)}")

        if len(doc) == 0:
            doc.close()
            raise PDFProcessingError(detail="PDF does not contain extractable text.")

        pages_data = []
        for page_idx, page in enumerate(doc):
            page_text = (page.get_text("text") or "").strip()
            pages_data.append({
                "page_number": page_idx + 1,
                "text": page_text
            })

        doc.close()
        return pages_data

    @staticmethod
    def extract_full_text(file_path: str) -> str:
        pages = PDFService.extract_text_pages(file_path)
        combined_text = []
        for p in pages:
            if p["text"]:
                combined_text.append(f"--- [Trang {p['page_number']}] ---\n{p['text']}")
        return "\n\n".join(combined_text)

    @staticmethod
    def prepare_pdf_for_ai(file_path: str, max_scan_pages: int = 30) -> Tuple[bool, str, bytes]:
        """
        Phát hiện thông minh:
        - Nếu 100% các trang đều có text đầy đủ: Dùng text layer bóc tách bằng PyMuPDF.
        - Nếu có bất kỳ trang nào là ảnh scan (hoặc toàn bộ là scan, hoặc file hỗn hợp nửa text nửa scan):
          Cắt tối đa max_scan_pages trang đầu để gửi dữ liệu nhị phân sang Gemini Multimodal Vision.
        """
        if not os.path.exists(file_path):
            raise PDFProcessingError(detail="File not found.")

        doc = pymupdf.open(file_path)
        total_pages = len(doc)
        if total_pages == 0:
            doc.close()
            raise PDFProcessingError(detail="PDF does not contain extractable text.")

        empty_or_scanned_pages = 0
        pages_text = []

        for idx, page in enumerate(doc):
            txt = (page.get_text("text") or "").strip()
            # Nếu trang có dưới 15 ký tự thì xem như là trang ảnh scan hoặc trang trống
            if len(txt) < 15:
                empty_or_scanned_pages += 1
            else:
                pages_text.append(f"--- [Trang {idx + 1}] ---\n{txt}")

        # Nếu toàn bộ các trang đều có text (không có trang nào là ảnh scan)
        if empty_or_scanned_pages == 0:
            doc.close()
            return False, "\n\n".join(pages_text), b""

        # Nếu có trang là ảnh scan (kể cả file hỗn hợp nửa text nửa scan như 112-VBHN)
        # Gửi dữ liệu PDF sang Gemini Vision để AI nhìn và đọc được cả trang ảnh
        new_doc = pymupdf.open()
        pages_to_take = min(max_scan_pages, total_pages)
        for i in range(pages_to_take):
            new_doc.insert_pdf(doc, from_page=i, to_page=i)
        sample_bytes = new_doc.write()
        new_doc.close()
        doc.close()

        return True, "", sample_bytes


pdf_service = PDFService()
