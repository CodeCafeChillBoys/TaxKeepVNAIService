import uuid
from datetime import datetime
from sqlalchemy import Column, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector
from app.infrastructure.database import Base
from app.core.config import settings


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    # Primary key dạng UUID (GUID)
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )

    # Khóa ngoại liên kết tới Document.id (cũng là UUID)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    chunk_index = Column(Integer, nullable=False)            # Thứ tự đoạn cắt (0, 1, 2...)
    content = Column(Text, nullable=False)                   # Nội dung đoạn luật thuế cắt nhỏ
    embedding = Column(Vector(settings.EMBEDDING_DIMENSION)) # Vector 768 chiều cho pgvector
    created_at = Column(DateTime, default=datetime.utcnow)

    document = relationship("Document", back_populates="chunks")
