import os
from functools import lru_cache
from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Bắt buộc nạp .env với override=True để ghi đè các biến môi trường cũ trong hệ thống Windows
load_dotenv(override=True)

# Xóa GOOGLE_API_KEY cũ của hệ thống (nếu có) để tránh xung đột với GEMINI_API_KEY trong .env
if "GOOGLE_API_KEY" in os.environ and os.environ["GOOGLE_API_KEY"] != os.environ.get("GEMINI_API_KEY"):
    del os.environ["GOOGLE_API_KEY"]


class Settings(BaseSettings):
    # App config
    APP_NAME: str = "TaxAIService"
    APP_ENV: str = "development"
    DEBUG: bool = True

    # Database config
    DATABASE_URL: str
    EMBEDDING_DIMENSION: int = 768

    # AI / Gemini API Key
    GEMINI_API_KEY: str
    EMBEDDING_MODEL: str = "gemini-embedding-001"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
