from fastapi import HTTPException, status


class PDFErrorMessages:
    """Bảng thông báo lỗi chuẩn cho tính năng Xử lý File PDF."""
    FILE_NOT_FOUND = "File not found."
    NO_EXTRACTABLE_TEXT = "PDF does not contain extractable text."
    INVALID_FORMAT = "The file must be a PDF."
    FILE_FIELD_REQUIRED = "The file field is required."

    @staticmethod
    def cannot_open_pdf(detail: str) -> str:
        return f"Cannot open PDF file: {detail}"

    @staticmethod
    def file_too_large(max_mb: int) -> str:
        return f"The file size must not exceed {max_mb} MB."


class PDFProcessingError(HTTPException):
    """Exception khi gặp sự cố bóc tách hoặc đọc tài liệu PDF."""
    def __init__(self, detail: str = PDFErrorMessages.NO_EXTRACTABLE_TEXT):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
