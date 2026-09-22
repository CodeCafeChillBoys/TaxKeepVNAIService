from enum import Enum


class TaxRuleType(str, Enum):
    """Phân loại quy tắc thuế thu nhập cá nhân"""
    DEDUCTION = "DEDUCTION"    # Nhóm giảm trừ (bản thân, người phụ thuộc, bảo hiểm, từ thiện)
    BRACKET = "BRACKET"        # Biểu thuế lũy tiến từng phần
    RATE = "RATE"              # Thuế suất đặc thù (vãng lai, không cư trú)
    EXEMPTION = "EXEMPTION"    # Các khoản miễn thuế gắn liền tiền lương


class DependentType(str, Enum):
    """Phân loại nhóm người phụ thuộc chuẩn hóa phục vụ giảm trừ gia cảnh"""
    CHILD = "CHILD"                    # Con chưa thành niên (dưới 18 tuổi)
    ADULT_CHILD = "ADULT_CHILD"        # Con thành niên đang theo học hoặc bị khuyết tật
    SPOUSE = "SPOUSE"                  # Vợ hoặc chồng không có khả năng lao động/thu nhập
    PARENT = "PARENT"                  # Cha đẻ, mẹ đẻ, cha mẹ vợ/chồng, cha mẹ nuôi hợp pháp
    OTHER = "OTHER"                    # Cá nhân khác không nơi nương tựa người nộp thuế đang nuôi dưỡng


class TaxRuleStatus(str, Enum):
    """Trạng thái của bộ quy tắc thuế và các quy tắc con"""
    DRAFT = "Draft"        # Bản nháp (chưa duyệt)
    ACTIVE = "Active"      # Đang áp dụng (đã duyệt)
    EXPIRED = "Expired"    # Hết hiệu lực
    ARCHIVED = "Archived"  # Đã lưu trữ

