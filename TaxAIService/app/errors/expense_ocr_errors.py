from typing import Optional, List, Dict, Any


class ExpenseOcrError(Exception):
    """Lớp lỗi cơ sở cho phân hệ Expense OCR"""
    def __init__(self, code: str, message: str, status_code: int = 422, details: Optional[Dict[str, Any]] = None):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class CorruptedFileError(ExpenseOcrError):
    """File tải về rỗng, byte hỏng, base64 sai hoặc định dạng ảnh/PDF bị lỗi"""
    def __init__(self, message: str = "Tệp tin bị hỏng hoặc định dạng không hợp lệ, không thể đọc dữ liệu."):
        super().__init__(
            code="ERR_CORRUPTED_FILE",
            message=message,
            status_code=422
        )


class UnreadableDocumentError(ExpenseOcrError):
    """AI Engine không thể đọc hoặc parse được văn bản (ảnh quá mờ, lóa đèn, mất nét)"""
    def __init__(
        self,
        message: str = "AI Engine could not parse the document. The image quality may be too blurry or illegible.",
        reasons: Optional[List[str]] = None
    ):
        super().__init__(
            code="ERR_IMAGE_QUALITY_TOO_LOW",
            message=message,
            status_code=422,
            details={"reasons": reasons or ["IMAGE_BLURRY", "EXCESSIVE_GLARE"]}
        )