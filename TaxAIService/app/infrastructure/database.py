from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from app.core.config import settings

# 1. Khởi tạo Database Engine tối ưu cho PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    pool_size=10,          # Giữ tối đa 10 kết nối thường trực trong Pool
    max_overflow=20,       # Cho phép tạo thêm tối đa 20 kết nối khi lượng truy cập tăng đột biến
    pool_pre_ping=True,    # Kiểm tra kết nối trước khi query để tránh lỗi "connection dropped"
    pool_recycle=1800,     # Tự động refresh kết nối sau 30 phút
    echo=settings.DEBUG    # In câu lệnh SQL ra terminal khi ở chế độ DEBUG
)

# 2. Tạo SessionFactory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

# 3. Base class cho toàn bộ Models trong thư mục app/models
Base = declarative_base()


# 4. Cách dùng 1: Dành cho FastAPI Endpoint (Dependency Injection)
# Mỗi request HTTP đến sẽ mở 1 session, xử lý xong tự động đóng
def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# 5. Cách dùng 2: Dành cho Services / Worker / CLI script
# Sử dụng theo cú pháp: `with get_db_context() as db:` (tự commit khi thành công, rollback nếu có lỗi)
@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
