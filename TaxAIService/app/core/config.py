from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # App config
    APP_NAME: str = "TaxAIService"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database config
    DATABASE_URL: str
    EMBEDDING_DIMENSION: int = 768

    # AI / Gemini API Key
    GEMINI_API_KEY: str = ""

    # Đọc tự động từ file .env ở thư mục gốc
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

"""Decorator @lru_cache biến hàm get_settings() thành một dạng Singleton Pattern"""
@lru_cache
def get_settings() -> Settings:
    """Sử dụng lru_cache để chỉ nạp cấu hình một lần duy nhất trong toàn bộ vòng đời app."""
    return Settings()


settings = get_settings()
