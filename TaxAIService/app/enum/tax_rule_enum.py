from enum import Enum


class TaxRuleType(str, Enum):
    """Phân loại quy tắc thuế thu nhập cá nhân"""
    DEDUCTION = "DEDUCTION"    # Nhóm giảm trừ (bản thân, người phụ thuộc, bảo hiểm, từ thiện)
    BRACKET = "BRACKET"        # Biểu thuế lũy tiến từng phần
    RATE = "RATE"              # Thuế suất đặc thù (vãng lai, không cư trú)
    EXEMPTION = "EXEMPTION"    # Các khoản miễn thuế gắn liền tiền lương


class DependentType(str, Enum):
    """Phân loại nhóm người phụ thuộc chuẩn hóa phục vụ giảm trừ gia cảnh"""
    # ── Nhóm chung (Backward Compatibility) ──
    CHILD = "CHILD"                    # Con
    ADULT_CHILD = "ADULT_CHILD"        # Con thành niên
    SPOUSE = "SPOUSE"                  # Vợ hoặc chồng
    PARENT = "PARENT"                  # Cha mẹ
    OTHER = "OTHER"                    # Cá nhân khác

    # ── Nhóm chi tiết chuẩn hóa theo điều kiện pháp lý và đối soát hồ sơ ──
    # 1. Nhóm Con
    CHILD_UNDER_18 = "CHILD_UNDER_18"                    # Con chưa thành niên (dưới 18 tuổi)
    CHILD_OVER_18_STUDYING = "CHILD_OVER_18_STUDYING"    # Con từ 18 tuổi trở lên đang theo học ĐH, CĐ, THCN...
    CHILD_OVER_18_DISABLED = "CHILD_OVER_18_DISABLED"    # Con từ 18 tuổi trở lên bị khuyết tật, mất KNLĐ

    # 2. Nhóm Vợ hoặc chồng
    SPOUSE_RETIRED = "SPOUSE_RETIRED"                    # Vợ/chồng ngoài độ tuổi lao động
    SPOUSE_DISABLED = "SPOUSE_DISABLED"                  # Vợ/chồng trong độ tuổi lao động bị khuyết tật, mất KNLĐ

    # 3. Nhóm Cha, mẹ (Cha đẻ, mẹ đẻ, cha mẹ vợ/chồng, cha mẹ nuôi hợp pháp, cha dượng, mẹ kế)
    PARENT_RETIRED = "PARENT_RETIRED"                    # Cha/mẹ ngoài độ tuổi lao động
    PARENT_DISABLED = "PARENT_DISABLED"                  # Cha/mẹ trong độ tuổi lao động bị khuyết tật, mất KNLĐ

    # 4. Nhóm Cá nhân khác không nơi nương tựa
    OTHER_HELPLESS = "OTHER_HELPLESS"                    # Cá nhân khác không nơi nương tựa (ngoài độ tuổi hoặc khuyết tật)


class TaxRuleStatus(str, Enum):
    """Trạng thái của bộ quy tắc thuế và các quy tắc con"""
    DRAFT = "Draft"        # Bản nháp (chưa duyệt)
    ACTIVE = "Active"      # Đang áp dụng (đã duyệt)
    EXPIRED = "Expired"    # Hết hiệu lực
    ARCHIVED = "Archived"  # Đã lưu trữ


class RequiredDocumentType(str, Enum):
    """Mã định danh chuẩn hóa các loại giấy tờ hồ sơ chứng minh người phụ thuộc"""
    BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE"               # Giấy khai sinh (Bản chính / Bản sao trích lục)
    CITIZEN_ID = "CITIZEN_ID"                             # Căn cước công dân / Thẻ căn cước / CMND
    STUDENT_CARD = "STUDENT_CARD"                         # Thẻ học sinh, sinh viên / Giấy xác nhận đang theo học
    DISABILITY_CERTIFICATE = "DISABILITY_CERTIFICATE"     # Giấy xác nhận khuyết tật / Giấy xác nhận mất KNLĐ
    MARRIAGE_CERTIFICATE = "MARRIAGE_CERTIFICATE"         # Giấy chứng nhận đăng ký kết hôn
    RELATIONSHIP_CERTIFICATE = "RELATIONSHIP_CERTIFICATE" # Giấy tờ chứng minh quan hệ (Khai sinh NNT, sổ hộ tịch,...)
    SUPPORT_COMMITMENT_FORM = "SUPPORT_COMMITMENT_FORM"   # Bản cam kết nghĩa vụ nuôi dưỡng (Mẫu 07/XN-NPT)
    RESIDENCE_CT07 = "RESIDENCE_CT07"                     # Giấy xác nhận thông tin cư trú (Mẫu CT07)
    OTHER = "OTHER"                                       # Giấy tờ khác


class DependentRelationship(str, Enum):
    """Phân loại quan hệ người phụ thuộc phục vụ quản lý và phân loại nhóm"""
    CHILD = "CHILD"                          # Con (con đẻ, con nuôi, con riêng)
    SPOUSE = "SPOUSE"                        # Vợ hoặc chồng
    PARENT = "PARENT"                        # Cha mẹ (cha mẹ đẻ, cha mẹ vợ/chồng, cha mẹ nuôi)
    OTHER_DEPENDENT = "OTHER_DEPENDENT"      # Cá nhân khác không nơi nương tựa



