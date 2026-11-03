from enum import Enum


class AiProvider(str, Enum):
    """Danh sách các nhà cung cấp AI được hệ thống hỗ trợ"""
    GEMINI = "GEMINI"
    OPENAI = "OPENAI"
    CLAUDE = "CLAUDE"
    DEEPSEEK = "DEEPSEEK"


class AiKeyStatus(str, Enum):
    """Trạng thái hoạt động của API Key trong hệ thống"""
    ACTIVE = "ACTIVE"                  # Key hoạt động bình thường
    QUOTA_EXCEEDED = "QUOTA_EXCEEDED"  # Hết hạn ngạch / dính 429 (tự động cooldown)
    INVALID = "INVALID"                # Key sai hoặc đã bị nhà cung cấp thu hồi
    DISABLED = "DISABLED"              # Admin chủ động tắt thủ công