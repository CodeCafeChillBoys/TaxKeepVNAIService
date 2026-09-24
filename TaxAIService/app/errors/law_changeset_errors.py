from typing import Optional


class LawChangesetError(Exception):
    def __init__(self, error_code: str, message: str, detail: Optional[str] = None):
        super().__init__(message)
        self.error_code = error_code
        self.message = message
        self.detail = detail or message


class LawChangesetBadRequestError(LawChangesetError):
    def __init__(self, message: str = "Yêu cầu không hợp lệ hoặc sai định dạng schema."):
        super().__init__("E-AI_BAD_REQUEST", message)


class LawChangesetFileDownloadError(LawChangesetError):
    def __init__(self, message: str = "Không thể tải tệp tài liệu văn bản luật."):
        super().__init__("E-AI_FILE_DOWNLOAD", message)


class LawChangesetPdfUnreadableError(LawChangesetError):
    def __init__(self, message: str = "Tệp PDF bị hỏng hoặc không thể đọc được nội dung."):
        super().__init__("E-AI_PDF_UNREADABLE", message)


class LawChangesetTooLargeError(LawChangesetError):
    def __init__(self, message: str = "Dung lượng tệp vượt quá giới hạn tối đa cho phép."):
        super().__init__("E-AI_TOO_LARGE", message)


class LawChangesetModelError(LawChangesetError):
    def __init__(self, message: str = "Lỗi khi gọi mô hình Gemini hoặc quá thời gian xử lý."):
        super().__init__("E-AI_MODEL_ERROR", message)


class LawChangesetSchemaInvalidError(LawChangesetError):
    def __init__(self, message: str = "Kết quả từ AI không khớp với cấu trúc dữ liệu quy định."):
        super().__init__("E-AI_SCHEMA_INVALID", message)


class LawChangesetInternalError(LawChangesetError):
    def __init__(self, message: str = "Lỗi xử lý nội bộ hệ thống AI Service."):
        super().__init__("E-AI_INTERNAL", message)
