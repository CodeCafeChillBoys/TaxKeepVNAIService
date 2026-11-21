from enum import Enum


class DocumentExtractionStatus(str, Enum):
    """Trạng thái xử lý bóc tách chứng từ"""
    EXTRACTED = "EXTRACTED"           # Đã bóc tách thành công, hợp lệ, chờ User Review
    FAILED = "FAILED"                 # Lỗi trong quá trình xử lý (ảnh hỏng, sai năm, sai loại chứng từ)


class MedicalDeductionStatus(str, Enum):
    """Trạng thái giảm trừ thuế TNCN của từng dòng chi phí KCB"""
    ELIGIBLE = "ELIGIBLE"             # Hợp lệ giảm trừ thuế TNCN
    EXCLUDED = "EXCLUDED"             # Bị loại trừ (thẩm mỹ, làm đẹp, TPCN, tiện ích...)


class MedicalStatementStatus(str, Enum):
    """Trạng thái của Bảng kê chi phí KCB"""
    UPLOADED = "UPLOADED"             # Mới tải lên, chờ xử lý
    EXTRACTED = "EXTRACTED"           # Đã bóc tách và đối chiếu thành công
    FAILED = "FAILED"                 # Lỗi bóc tách hoặc đối chiếu chéo thất bại

