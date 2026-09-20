from enum import Enum


class ConfigDataType(str, Enum):
    """
    Kiểu dữ liệu của giá trị cấu hình (config_value).
    Giúp Backend tự động ép kiểu/validate và Frontend (Admin Web) 
    biết hiển thị đúng loại input (number, text, switch toggle, v.v.).
    """
    STRING = "STRING"              # Chuỗi ký tự thông thường
    FLOAT = "FLOAT"                # Số thực (dùng cho threshold, tỷ lệ: 0.80, 0.75...)
    INT = "INT"                    # Số nguyên (dùng cho số lần retry, số ngày...)
    BOOLEAN = "BOOLEAN"            # Logic true/false (dùng cho các cờ bật/tắt tính năng)
    LIST_STRING = "LIST_STRING"    # Danh sách chuỗi phân tách bằng dấu phẩy
    JSON = "JSON"                  # Dữ liệu dạng JSON phức tạp


class DefaultSystemConfigKey(str, Enum):
    """
    Các Key cấu hình mặc định (cốt lõi) được hệ thống code AI sử dụng sẵn.
    
    LƯU Ý: 
    Admin hoàn toàn có thể TẠO THÊM các key động mới ngoài danh sách này 
    (ví dụ: THRESHOLD_MEDICAL, THRESHOLD_TUITION...) mà không cần phải bổ sung vào Enum này.
    """
    # Ngưỡng tin cậy AI chung cho toàn hệ thống (mặc định 0.80)
    AI_CONFIDENCE_THRESHOLD = "AI_CONFIDENCE_THRESHOLD"

    # Danh sách các trường cốt lõi bắt buộc rõ nét, phân tách bằng dấu phẩy
    CRUCIAL_EXTRACTION_FIELDS = "CRUCIAL_EXTRACTION_FIELDS"

