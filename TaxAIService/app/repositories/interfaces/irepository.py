import uuid
from abc import ABC, abstractmethod
from typing import TypeVar, Generic, Optional, List, Any

T = TypeVar("T")


class IRepository(ABC, Generic[T]):
    """Base Interface cho toàn bộ Repositories trong hệ thống (IRepo)."""

    @abstractmethod
    def get_by_id(self, id: Any) -> Optional[T]:
        """Truy vấn thực thể theo định danh khóa chính."""
        pass


# Bí danh ngắn gọn thường dùng
IRepo = IRepository
