# app/infrastructure/redis_client.py
import logging
from typing import Optional
import redis
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> Optional[redis.Redis]:
    """
    Khởi tạo và trả về Redis Client dạng Singleton.
    Tự động xử lý bảo mật SSL với URL của Upstash.
    Nếu Redis lỗi hoặc tắt, trả về None để hệ thống không bị crash.
    """
    global _redis_client

    if not settings.REDIS_ENABLED or not settings.REDIS_URL:
        return None

    if _redis_client is None:
        try:
            client = redis.from_url(
                url=settings.REDIS_URL,
                decode_responses=True,  # Đọc string UTF-8 thay vì bytes
                socket_timeout=3.0,
                socket_connect_timeout=3.0
            )
            # Kiểm tra ping thử tới Upstash
            client.ping()
            _redis_client = client
            logger.info(" Kết nối tới Upstash Redis thành công!")
        except Exception as e:
            logger.warning(f"Không thể kết nối Upstash Redis ({e}). Tự động fallback về RAM/DB.")
            _redis_client = None

    return _redis_client