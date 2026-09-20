import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from sqlalchemy import String, DateTime, Numeric, Boolean, BigInteger, Text, ForeignKey, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base


class SystemConfig(Base):
    """Bảng cấu hình hệ thống (ngưỡng threshold do Admin cài)"""
    __tablename__ = "system_configs"

    config_key: Mapped[str] = mapped_column(String(100), primary_key=True)
    config_value: Mapped[str] = mapped_column(String(255), nullable=False)
    data_type: Mapped[str] = mapped_column(String(20), default="STRING", nullable=False) # FLOAT, INT, STRING, BOOLEAN, LIST_STRING
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)        # Mô tả ý nghĩa cho Admin
    admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True
    )

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, index=True)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)

class AiExtraction(Base):
    """Bảng cha: Lưu tổng quan 1 lần bóc tách cho 1 chứng từ"""
    __tablename__ = "ai_extractions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, index=True)
    overall_confidence: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)    # VD: 0.92


    applied_threshold: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)     # VD: 0.80
    is_passed_threshold: Mapped[bool] = mapped_column(Boolean, nullable=False)          # True/False
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSONB, nullable=False)          # JSON thô Gemini trả về
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    # Quan hệ 1 - N với bảng chi tiết
    values: Mapped[List["AiExtractionValue"]] = relationship(
        "AiExtractionValue", back_populates="extraction", cascade="all, delete-orphan"
    )


class AiExtractionValue(Base):
    """Bảng con: Lưu chi tiết từng trường bóc tách, confidence và bounding_box"""
    __tablename__ = "ai_extractions_value"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    extraction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_extractions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)                # seller_name, total_amount...
    extracted_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)         # Giá trị AI đọc được
    user_corrected_value: Mapped[Optional[str]] = mapped_column(Text, nullable=True)    # Giá trị User sửa lại (nếu có)
    confidence_score: Mapped[float] = mapped_column(Numeric(4, 2), nullable=False)      # VD: 0.95
    bounding_box: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSONB, nullable=True) # {"x": .., "y": .., "w": .., "h": ..}

    extraction: Mapped["AiExtraction"] = relationship("AiExtraction", back_populates="values")