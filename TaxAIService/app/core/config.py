import os
from functools import lru_cache
from typing import Optional
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

    # AI / Gemini API Config
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "gemini-embedding-001"

    # AI / OpenAI API Config (Dùng cho đọc chứng từ)
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Upload & File Limits
    UPLOAD_DIR: str = "data/pdf"
    MAX_FILE_SIZE_MB: int = 20

    # Message Broker (RabbitMQ) Config
    RABBITMQ_ENABLED: bool = True
    RABBITMQ_URL: str = "amqp://guest:guest@localhost:5672/"
    RABBITMQ_TAX_REQUEST_QUEUE: str = "tax.ai.request.queue"
    RABBITMQ_TAX_RESPONSE_QUEUE: str = "tax.ai.response.queue"
    RABBITMQ_EXCHANGE_NAME: str = "tax.ai.exchange"
    
    RABBITMQ_OCR_REQUEST_QUEUE: str = "ocr.ai.request.queue"
    RABBITMQ_OCR_RESPONSE_QUEUE: str = "ocr.ai.response.queue"

    RABBITMQ_EXPENSE_OCR_REQUEST_QUEUE: str = "expense.ocr.ai.request.queue"
    RABBITMQ_EXPENSE_OCR_RESPONSE_QUEUE: str = "expense.ocr.ai.response.queue"


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
