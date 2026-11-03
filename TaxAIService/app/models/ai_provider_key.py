from app.core import exclude_from_coverage
import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Boolean, DateTime, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base
from app.enum.ai_provider_enum import AiProvider,AiKeyStatus

@exclude_from_coverage
class AiProviderKey(Base):
    __tablename__ = "ai_provider_keys"
    __table_args__ = {"extend_existing": True}

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), default=AiProvider.GEMINI.value, nullable=False, index=True)
    key_name: Mapped[str] = mapped_column(String(150), nullable=False)
    api_key: Mapped[str] = mapped_column(String(255), nullable=False)
    priority: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default=AiKeyStatus.ACTIVE.value, nullable=False) # ACTIVE, QUOTA_EXCEEDED, INVALID
    request_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    cooldown_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    last_used_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False
    )