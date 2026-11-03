from app.core import exclude_from_coverage
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.enum.ai_provider_enum import AiProvider, AiKeyStatus


@exclude_from_coverage
class AiKeyCreateRequest(BaseModel):
    key_name: str = Field(..., description="Tên gợi nhớ của Key, ví dụ: Key Cá Nhân Cuong")
    api_key: str = Field(..., description="API Key")
    provider: AiProvider = Field(default=AiProvider.GEMINI, description="Nhà cung cấp AI")
    priority: int = Field(1, ge=1, description="Độ ưu tiên: 1 là cao nhất")


@exclude_from_coverage
class AiKeyUpdateRequest(BaseModel):
    key_name: Optional[str] = None
    priority: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None
    status: Optional[AiKeyStatus] = None


@exclude_from_coverage
class AiKeyResponse(BaseModel):
    id: uuid.UUID
    provider: AiProvider
    key_name: str
    masked_api_key: str
    priority: int
    is_active: bool
    status: AiKeyStatus
    request_count: int
    last_used_at: Optional[datetime] = None
    cooldown_until: Optional[datetime] = None
    created_at: datetime

    @exclude_from_coverage
    class Config:
        from_attributes = True