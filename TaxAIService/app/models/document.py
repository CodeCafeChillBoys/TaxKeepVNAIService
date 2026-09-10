import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Integer, String, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.infrastructure.database import Base

if TYPE_CHECKING:
    from app.models.document_chunk import DocumentChunk


class Document(Base):
    __tablename__ = "documents"

    # Primary key dạng GUID (UUID v4)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    # Mã định danh văn bản (ví dụ: "LUAT-THUE-TNCN-2026")
    document_code: Mapped[str] = mapped_column(String(100), nullable=False, unique=True, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)            # Tiêu đề văn bản luật
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)        # Tên file PDF gốc
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)        # Đường dẫn lưu file
    total_pages: Mapped[int] = mapped_column(Integer, default=0, nullable=False) # Tổng số trang PDF
    
    # Versioning & Trạng thái hiệu lực
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="Draft", nullable=False, index=True) # Draft, Active, Expired, Archived
    effective_from: Mapped[Optional[str]] = mapped_column(String(50), nullable=True) # e.g. "2026-01-01"
    effective_to: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)   # e.g. "2027-01-01"
    
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )

    # Quan hệ 1-N với DocumentChunk
    chunks: Mapped[List["DocumentChunk"]] = relationship(
        "DocumentChunk", back_populates="document", cascade="all, delete-orphan"
    )
