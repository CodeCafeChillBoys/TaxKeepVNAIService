from enum import Enum


class DocumentType(str, Enum):
    CCCD_FRONT = "CCCD_FRONT"                     # Căn cước công dân (Mặt trước)
    CCCD_BACK = "CCCD_BACK"                       # Căn cước công dân (Mặt sau)
    CCCD_BOTH = "CCCD_BOTH"                       # Ghép cả 2 mặt CCCD
    BIRTH_CERTIFICATE = "BIRTH_CERTIFICATE"       # Giấy khai sinh (Bản chính/Sao trích lục)
    MARRIAGE_CERTIFICATE = "MARRIAGE_CERTIFICATE" # Giấy chứng nhận kết hôn
    RESIDENCE_CT07 = "RESIDENCE_CT07"             # Giấy xác nhận thông tin cư trú (Mẫu CT07)
    DISABILITY_CERT = "DISABILITY_CERTIFICATE"   # Giấy xác nhận khuyết tật / mất sức LĐ
    UNKNOWN = "UNKNOWN"                           # Không nhận diện được
