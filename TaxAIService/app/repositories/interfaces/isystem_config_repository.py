from abc import ABC, abstractmethod
from typing import Optional, Set, List
from app.models.ai_extraction_models import SystemConfig


class ISystemConfigRepository(ABC):
    """Interface cho Repository quản lý cấu hình hệ thống (System Config)."""

    @abstractmethod
    def get_by_key(self, config_key: str, active_only: bool = True) -> Optional[SystemConfig]:
        """Lấy cấu hình theo key (mặc định chỉ lấy bản ghi đang active và chưa xóa mềm)."""
        pass

    @abstractmethod
    def get_all(self, active_only: bool = False) -> List[SystemConfig]:
        """Lấy toàn bộ danh sách cấu hình (hỗ trợ trang Admin xem tất cả)."""
        pass

    @abstractmethod
    def get_float_value(self, config_key: str, default: float = 0.80) -> float:
        """Lấy giá trị kiểu float an toàn từ bất kỳ key nào do Admin tạo."""
        pass

    @abstractmethod
    def get_system_threshold(self, category_code: Optional[str] = None, default: float = 0.80) -> float:
        """
        Lấy ngưỡng tin cậy AI theo thứ tự ưu tiên:
        1. Ngưỡng theo category (THRESHOLD_{category_code}) nếu Admin có tạo
        2. Ngưỡng chung AI_CONFIDENCE_THRESHOLD
        3. Giá trị fallback an toàn (default)
        """
        pass

    @abstractmethod
    def get_crucial_fields(self, category_code: Optional[str] = None) -> Set[str]:
        """Lấy danh sách các trường bắt buộc rõ nét."""
        pass

    @abstractmethod
    def save(self, config: SystemConfig) -> SystemConfig:
        """Thêm mới hoặc cập nhật bản ghi cấu hình."""
        pass

    @abstractmethod
    def delete(self, config: SystemConfig) -> None:
        """Xóa mềm (Soft Delete) cấu hình."""
        pass

    @abstractmethod
    def restore(self, config: SystemConfig) -> SystemConfig:
        """Khôi phục cấu hình đã xóa mềm."""
        pass