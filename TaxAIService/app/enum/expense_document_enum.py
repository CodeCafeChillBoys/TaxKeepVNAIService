from enum import Enum


class DocumentExtractionStatus(str, Enum):
    """Trạng thái xử lý bóc tách chứng từ"""
    PENDING = "PENDING"               # Đang chờ xử lý trong queue
    PROCESSING = "PROCESSING"         # AI đang đọc và bóc tách ngầm
    EXTRACTED = "EXTRACTED"           # Đã bóc tách thành công, chờ User Review
    NEEDS_REVIEW = "NEEDS_REVIEW"     # Bóc tách xong nhưng có trường confidence thấp cần chú ý
    CONFIRMED = "CONFIRMED"           # Người dùng đã duyệt và lưu chính thức
    FAILED = "FAILED"                 # Lỗi trong quá trình xử lý (ảnh hỏng, lỗi hệ thống)
    REJECTED = "REJECTED"             # Người dùng từ chối / xóa hóa đơn này


class DefaultExpenseDocTypeCode(str, Enum):
    """Mã loại chứng từ chi phí chuẩn mực (Admin có thể mở rộng thêm)"""
    MEDICAL_EXPENSE_INVOICE = "MEDICAL_EXPENSE_INVOICE"     # Hóa đơn viện phí, khám chữa bệnh
    TUITION_FEE_INVOICE = "TUITION_FEE_INVOICE"             # Hóa đơn/biên lai học phí giáo dục
    CHARITY_DONATION_RECEIPT = "CHARITY_DONATION_RECEIPT"   # Biên lai đóng góp từ thiện, nhân đạo
    UNSUPPORTED = "UNSUPPORTED"                             # Hóa đơn rác, không hợp lệ hoặc ngoài danh mục


class PaymentMethod(str, Enum):
    """Hình thức thanh toán phổ biến trên hóa đơn"""
    QR = "QR"
    BANK_TRANSFER = "Chuyển khoản"
    CASH = "Tiền mặt"
    CREDIT_CARD = "Thẻ tín dụng / POS"
    OTHER = "Khác"
