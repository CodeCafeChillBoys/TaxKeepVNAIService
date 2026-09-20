from enum import Enum


class DocumentType(str, Enum):
    # Các loại giấy tờ chuẩn đồng bộ với hệ thống .NET & quy định hồ sơ giảm trừ gia cảnh
    BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE"               # Giấy khai sinh (Bản chính / Sao trích lục)
    CITIZEN_ID = "CITIZEN_ID"                             # Căn cước công dân / Thẻ căn cước / CMND
    STUDENT_CARD = "STUDENT_CARD"                         # Thẻ học sinh, sinh viên / Giấy xác nhận đang theo học
    DISABILITY_CERTIFICATE = "DISABILITY_CERTIFICATE"     # Giấy xác nhận khuyết tật / Giấy xác nhận mất KNLĐ
    DISABILITY_CERT = "DISABILITY_CERTIFICATE"           # Alias tương thích ngược cho DISABILITY_CERTIFICATE
    MARRIAGE_CERTIFICATE = "MARRIAGE_CERTIFICATE"         # Giấy chứng nhận đăng ký kết hôn
    RELATIONSHIP_CERTIFICATE = "RELATIONSHIP_CERTIFICATE" # Giấy tờ chứng minh quan hệ (Khai sinh NNT, sổ hộ tịch,...)
    SUPPORT_COMMITMENT_FORM = "SUPPORT_COMMITMENT_FORM"   # Bản cam kết nghĩa vụ nuôi dưỡng (Mẫu 07/XN-NPT)
    RESIDENCE_CT07 = "RESIDENCE_CT07"                     # Giấy xác nhận thông tin cư trú (Mẫu CT07)
    OTHER = "OTHER"                                       # Giấy tờ khác
    UNKNOWN = "UNKNOWN"                                   # Không nhận diện được

    # Các loại phụ trợ / chi tiết mặt thẻ CCCD (hỗ trợ bóc tách OCR 2 mặt)
    CCCD_FRONT = "CCCD_FRONT"                             # Căn cước công dân (Mặt trước)
    CCCD_BACK = "CCCD_BACK"                               # Căn cước công dân (Mặt sau)
    CCCD_BOTH = "CCCD_BOTH"                               # Ghép cả 2 mặt CCCD


class DependentGroup(str, Enum):
    # Nhóm 1: Con của người nộp thuế
    CHILD_UNDER_18 = "CHILD_UNDER_18"
    CHILD_OVER_18_STUDYING = "CHILD_OVER_18_STUDYING"
    CHILD_OVER_18_DISABLED = "CHILD_OVER_18_DISABLED"

    # Nhóm 2: Vợ hoặc chồng
    SPOUSE_DISABLED = "SPOUSE_DISABLED"
    SPOUSE_RETIRED = "SPOUSE_RETIRED"

    # Nhóm 3: Cha, mẹ
    PARENT_DISABLED = "PARENT_DISABLED"
    PARENT_RETIRED = "PARENT_RETIRED"

    # Nhóm 4: Cá nhân khác không nơi nương tựa
    OTHER_HELPLESS = "OTHER_HELPLESS"
    OTHER = "OTHER"

