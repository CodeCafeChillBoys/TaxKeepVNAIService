import pytest
from sqlalchemy import text
from app.infrastructure.database import engine, get_db_context
from app.infrastructure.database import get_db


def test_database_conection_ping():
    """
    Test 1: Kiểm tra kết nối trực tiếp thông qua Engine.
    Gửi câu lệnh 'SELECT 1' lên PostgreSQL để kiểm tra DB có phản hồi không.
    
    """
     # 1. Arrange & Act: Mở connection từ Engine và thực thi SELECT 1
    with engine.connect() as connection:
         result = connection.execute(text("SELECT 1")).scalar()
    
    assert result == 1
    
    
def test_database_session_context():
    """
    Test 2: Kiểm tra hàm `get_db_context()` (thường dùng trong Service/Worker).
    Đảm bảo session mở và đóng an toàn.
    """
    with get_db_context() as session:
        result = session.execute(text("SELECT 1")).scalar()
    assert result == 1
    


# ==============================================================================
# Test 3: Bao phủ hàm get_db() (Dòng 31-35)
# ==============================================================================
def test_get_db_generator():
    """
    get_db() là một Generator function (dùng yield).
    Ta gọi next() để lấy session ra và kiểm tra, sau đó cho generator chạy hết để close.
    """
    db_gen = get_db()
    db_session = next(db_gen)

    # Đảm bảo session lấy ra hoạt động được
    assert db_session is not None

    # Đóng generator (kích hoạt khối finally: db.close())
    try:
        next(db_gen)
    except StopIteration:
        pass  # Generator kết thúc bình thường


# ==============================================================================
# Test 4: Bao phủ nhánh Rollback khi gặp lỗi (Dòng 46-48)
# ==============================================================================
def test_get_db_context_rollback_on_error():
    """
    Cố tình ném Exception bên trong `with get_db_context()`
    để ép code phải chạy qua nhánh except: db.rollback() và raise.
    """
    with pytest.raises(RuntimeError, match="Lỗi giả lập để test rollback"):
        with get_db_context() as session:
            # Cố tình quăng lỗi bên trong context
            raise RuntimeError("Lỗi giả lập để test rollback")