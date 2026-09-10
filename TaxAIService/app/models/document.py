import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.infrastructure.database import Base


class Document(Base):
    __tablename__ = "documents"

    # Primary key dạng UUID (GUID) v4 tự động sinh ngẫu nhiên
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        index=True
    )
    title = Column(String(255), nullable=False)            # Tiêu đề tài liệu
    file_name = Column(String(255), nullable=False)        # Tên file gốc
    file_path = Column(String(500), nullable=False)        # Đường dẫn lưu file
    created_at = Column(DateTime, default=datetime.utcnow)

    # Quan hệ 1-N với DocumentChunk
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")
