import uuid
from datetime import datetime
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Integer, String, Text, ForeignKey, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from pgvector.sqlalchemy import Vector
from app.infrastructure.database import Base
from app.core.config import settings

if TYPE_CHECKING:
    from app.models.document import Document


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    # Primary key dạng GUID (UUID)
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Khóa ngoại liên kết tới Document.id (UUID)
    document_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)            # Thứ tự đoạn cắt (0, 1, 2...)
    content: Mapped[str] = mapped_column(Text, nullable=False)                   # Nội dung đoạn luật thuế cắt nhỏ

    # Metadata pháp lý & trích dẫn (Legal Citations)
    page_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False) # Số trang thực tế trong PDF (1-based)
    article: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)   # Ví dụ: "Điều 5"
    clause: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)    # Ví dụ: "Khoản 1"
    point: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)     # Ví dụ: "Điểm a"

    # Versioning & Trạng thái để filter nhanh khi search pgvector mà không cần JOIN
    status: Mapped[str] = mapped_column(String(50), default="Active", nullable=False, index=True) # Active, Expired
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Vector 768 chiều cho pgvector similarity search
    embedding = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    document: Mapped["Document"] = relationship("Document", back_populates="chunks")
