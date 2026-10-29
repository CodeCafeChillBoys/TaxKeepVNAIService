import logging
from datetime import datetime
from typing import Optional, Set, List
from sqlalchemy.orm import Session
from app.models.ai_extraction_models import SystemConfig
from app.repositories.interfaces.isystem_config_repository import ISystemConfigRepository

logger = logging.getLogger(__name__)


class SystemConfigRepository(ISystemConfigRepository):
    """
    Repository truy vấn và quản lý cấu hình hệ thống (System Config) từ Database.
    Hỗ trợ cấu hình động, kiểm tra kiểu dữ liệu an toàn và Xóa mềm (Soft Delete).
    """

    def __init__(self, db: Session):
        self.db = db

    def get_by_key(self, config_key: str, active_only: bool = True) -> Optional[SystemConfig]:
        """
        Lấy bản ghi SystemConfig theo khóa.
        Nếu active_only=True: Chỉ lấy khi is_active=True và is_deleted=False.
        """
        query = self.db.query(SystemConfig).filter(SystemConfig.config_key == config_key)
        if active_only:
            query = query.filter(
                SystemConfig.is_active.is_(True),
                SystemConfig.is_deleted.is_(False)
            )
        return query.first()

    def get_all(self, active_only: bool = False) -> List[SystemConfig]:
        """Lấy danh sách cấu hình (phục vụ màn hình Admin xem cấu hình)."""
        query = self.db.query(SystemConfig)
        if active_only:
            query = query.filter(
                SystemConfig.is_active.is_(True),
                SystemConfig.is_deleted.is_(False)
            )
        return query.order_by(SystemConfig.config_key.asc()).all()

    def get_float_value(self, config_key: str, default: float = 0.80) -> float:
        """
        Lấy giá trị kiểu số float an toàn từ bất kỳ key nào do Admin tạo.
        Tự động fallback về default nếu:
        1. Key không tồn tại hoặc đã bị xóa mềm / tắt active.
        2. Admin nhập sai định dạng (ví dụ chữ 'abc').
        3. Giá trị nằm ngoài khoảng hợp lệ [0.0, 1.0].
        """
        try:
            config_row = self.get_by_key(config_key, active_only=True)
            if config_row and config_row.config_value:
                # Chấp nhận cả dấu phẩy lẫn dấu chấm (vd: '0,85' -> '0.85')
                raw_str = config_row.config_value.strip().replace(",", ".")
                val = float(raw_str)
                if 0.0 <= val <= 1.0:
                    return val
                logger.warning(
                    f"Cấu hình '{config_key}' có giá trị {val} nằm ngoài khoảng [0.0, 1.0]. Dùng mặc định {default}."
                )
        except Exception as e:
            logger.warning(f"Không thể đọc float từ key '{config_key}' ({e}). Dùng mặc định {default}.")
        return default

    # Mục tiêu hàm này dùng để check ngưỡng mà admin đã cấu hình từng ngưỡng theo danh mục nếu ko có xài ngưỡng chung
    def get_system_threshold(self, category_code: Optional[str] = None, default: float = 0.80) -> float:
        """
        Lấy ngưỡng tin cậy theo thứ tự ưu tiên 3 tầng:
        1. Ngưỡng riêng theo danh mục (vd: THRESHOLD_MEDICAL_EXPENSE_INVOICE) nếu Admin có cài
        2. Ngưỡng chung toàn hệ thống AI_CONFIDENCE_THRESHOLD
        3. Fallback mặc định an toàn (0.80)
        """
        # Tầng 1: Kiểm tra ngưỡng riêng của danh mục (nếu có)
        if category_code:
            specific_key = f"THRESHOLD_{category_code.strip().upper()}"
            specific_row = self.get_by_key(specific_key, active_only=True)
            if specific_row:
                return self.get_float_value(specific_key, default=default)

        # Tầng 2: Kiểm tra ngưỡng chung
        general_row = self.get_by_key("AI_CONFIDENCE_THRESHOLD", active_only=True)
        if general_row:
            return self.get_float_value("AI_CONFIDENCE_THRESHOLD", default=default)

        # Tầng 3: Giá trị mặc định trong code
        return default

    # Mục tiêu dùng để kiểm tra các trường cốt lõi của cái loại danh mục đó
    def get_crucial_fields(self, category_code: Optional[str] = None) -> Set[str]:
        """
        Lấy danh sách các trường cốt lõi bắt buộc rõ nét.
        Hỗ trợ đọc key riêng theo category hoặc key chung CRUCIAL_EXTRACTION_FIELDS.
        """
        # lấy lên các trường trong loại danh mục mà admin thêm vào
        target_key = f"CRUCIAL_FIELDS_{category_code.strip().upper()}" if category_code else "CRUCIAL_EXTRACTION_FIELDS"
        try:
            # Check key với status true
            config_row = self.get_by_key(target_key, active_only=True)
            if not config_row and category_code:
                # Nếu category chưa có, fallback về key chung
                config_row = self.get_by_key("CRUCIAL_EXTRACTION_FIELDS", active_only=True)
                
            if config_row and config_row.config_value:
                return {f.strip() for f in config_row.config_value.split(",") if f.strip()}
        except Exception as e:
            logger.warning(f"Không thể đọc trường cốt lõi từ DB ({e}), dùng mặc định.")

        return {"total_amount", "seller_tax_code", "buyer_id_card", "invoice_number"}

    def save(self, config: SystemConfig) -> SystemConfig:
        """Thêm mới hoặc cập nhật bản ghi cấu hình."""
        self.db.add(config)
        self.db.commit()
        self.db.refresh(config)
        return config

    def delete(self, config: SystemConfig) -> None:
        """
        Xóa mềm (Soft Delete):
        Không xóa dòng khỏi DB, chỉ set is_deleted=True, is_active=False và lưu thời điểm deleted_at.
        """
        config.is_active = False
        config.is_deleted = True
        config.deleted_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(config)

    def restore(self, config: SystemConfig) -> SystemConfig:
        """Khôi phục cấu hình đã bị xóa mềm."""
        config.is_active = True
        config.is_deleted = False
        config.deleted_at = None
        self.db.commit()
        self.db.refresh(config)
        return config