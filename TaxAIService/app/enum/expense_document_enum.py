from enum import Enum


class DocumentExtractionStatus(str, Enum):
    """Trạng thái xử lý bóc tách chứng từ"""
    EXTRACTED = "EXTRACTED"           # Đã bóc tách thành công, hợp lệ, chờ User Review
    FAILED = "FAILED"                 # Lỗi trong quá trình xử lý (ảnh hỏng, sai năm, sai loại chứng từ)
