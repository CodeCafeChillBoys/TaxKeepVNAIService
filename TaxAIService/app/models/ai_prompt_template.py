from app.core import exclude_from_coverage
# app/models/ai_prompt_template.py
from datetime import datetime
from typing import Optional, List
from sqlalchemy import String, DateTime, Boolean, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column
from app.infrastructure.database import Base


@exclude_from_coverage
class AiPromptTemplate(Base):
    """
    Bảng quản lý các System Prompt động trong hệ thống.
    Cho phép Admin tinh chỉnh hành vi của AI mà không cần sửa code hay redeploy.
    """
    __tablename__ = "ai_prompt_templates"
    __table_args__ = {"extend_existing": True}

    prompt_key: Mapped[str] = mapped_column(String(100), primary_key=True, index=True)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    
    # Danh sách các biến cần truyền vào template, ví dụ: ["tax_year", "knowledge_base"]
    variables: Mapped[Optional[List[str]]] = mapped_column(JSONB, nullable=True)
    
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now(), nullable=False)