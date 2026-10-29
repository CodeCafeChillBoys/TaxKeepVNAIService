import uuid
import json
import logging
from typing import List, Optional
from app.models.ai_extraction_models import SystemConfig
from app.repositories.interfaces.isystem_config_repository import ISystemConfigRepository
from app.schemas.system_config.system_config_schema import (
    SystemConfigCreateRequest,
    SystemConfigUpdateRequest,
)
from app.enum.system_config_enum import ConfigDataType

logger = logging.getLogger(__name__)


class SystemConfigService:
    def __init__(self, repo: ISystemConfigRepository):
        self.repo = repo

    def _detect_data_type(self, value: str) -> ConfigDataType:
        """
        Tự động suy đoán kiểu dữ liệu dựa trên giá trị nhập vào:
        - 'true', 'false' -> BOOLEAN
        - Số nguyên (vd: 3, 10) -> INT
        - Số thực (vd: 0.85, 0,85) -> FLOAT
        - Cấu trúc JSON -> JSON
        - Có chứa dấu phẩy ',' -> LIST_STRING
        - Còn lại -> STRING
        """
        val = value.strip()
        lower_val = val.lower()

        # 1. BOOLEAN
        if lower_val in ("true", "false"):
            return ConfigDataType.BOOLEAN

        # 2. INT: số nguyên
        if val.isdigit() or (val.startswith("-") and val[1:].isdigit()):
            return ConfigDataType.INT

        # 3. FLOAT: số thực (chấp nhận cả dấu chấm và phẩy: 0.85 hoặc 0,85)
        normalized_float = val.replace(",", ".")
        try:
            float(normalized_float)
            if "." in normalized_float:
                return ConfigDataType.FLOAT
        except ValueError:
            pass

        # 4. JSON
        if (val.startswith("{") and val.endswith("}")) or (val.startswith("[") and val.endswith("]")):
            try:
                json.loads(val)
                return ConfigDataType.JSON
            except Exception:
                pass

        # 5. LIST_STRING: có dấu phẩy
        if "," in val:
            return ConfigDataType.LIST_STRING

        # 6. Mặc định là STRING
        return ConfigDataType.STRING

    def _validate_value_by_type(self, value: str, data_type: ConfigDataType) -> str:
        """
        Validate xem giá trị nhập vào có đúng với kiểu data_type không.
        Nếu sai sẽ văng ValueError kèm message tiếng Việt rõ ràng cho Admin.
        """
        val_str = value.strip()

        if data_type == ConfigDataType.FLOAT:
            try:
                # Chấp nhận cả dấu phẩy lẫn chấm: 0,85 -> 0.85
                num = float(val_str.replace(",", "."))
                return str(num)
            except ValueError:
                raise ValueError(f"Giá trị '{value}' không phải là số thực (FLOAT) hợp lệ.")

        elif data_type == ConfigDataType.INT:
            try:
                int(val_str)
                return val_str
            except ValueError:
                raise ValueError(f"Giá trị '{value}' không phải là số nguyên (INT) hợp lệ.")

        elif data_type == ConfigDataType.BOOLEAN:
            if val_str.lower() not in ("true", "false", "1", "0"):
                raise ValueError(f"Giá trị BOOLEAN phải là 'true' hoặc 'false'.")
            return "true" if val_str.lower() in ("true", "1") else "false"

        elif data_type == ConfigDataType.JSON:
            try:
                json.loads(val_str)
                return val_str
            except Exception as e:
                raise ValueError(f"Giá trị không đúng cấu trúc JSON hợp lệ: {str(e)}")

        return val_str

    # --- CÁC HÀM NGHIỆP VỤ ---

    def get_all_configs(self, active_only: bool = False) -> List[SystemConfig]:
        """Lấy toàn bộ danh sách cấu hình"""
        return self.repo.get_all(active_only=active_only)

    def get_config_by_key(self, key: str) -> Optional[SystemConfig]:
        """Lấy chi tiết 1 cấu hình"""
        return self.repo.get_by_key(key.strip().upper(), active_only=False)

    def create_config(self, dto: SystemConfigCreateRequest) -> SystemConfig:
        """Admin thêm mới 1 key cấu hình (Tự động đoán kiểu 100% từ config_value)"""
        clean_key = dto.config_key.strip().upper()

        # Tự động suy đoán data_type từ giá trị Admin nhập
        effective_data_type = self._detect_data_type(dto.config_value)

        # Kiểm tra key đã tồn tại trong DB chưa (kể cả đã bị xóa mềm)
        existing = self.repo.get_by_key(clean_key, active_only=False)
        if existing:
            if existing.is_deleted:
                # Nếu đã từng bị xóa mềm -> Kích hoạt khôi phục lại với giá trị mới
                existing.config_value = self._validate_value_by_type(dto.config_value, effective_data_type)
                existing.data_type = effective_data_type.value
                existing.description = dto.description
                existing.admin_id = dto.admin_id
                return self.repo.restore(existing)
            else:
                raise ValueError(f"Cấu hình với key '{clean_key}' đã tồn tại trong hệ thống.")

        # Validate giá trị
        validated_val = self._validate_value_by_type(dto.config_value, effective_data_type)

        new_config = SystemConfig(
            config_key=clean_key,
            config_value=validated_val,
            data_type=effective_data_type.value,
            description=dto.description,
            is_active=True,
            is_deleted=False,
            admin_id=dto.admin_id
        )
        return self.repo.save(new_config)

    def update_config(self, key: str, dto: SystemConfigUpdateRequest) -> Optional[SystemConfig]:
        """Admin cập nhật cấu hình"""
        clean_key = key.strip().upper()
        config = self.repo.get_by_key(clean_key, active_only=False)
        if not config or config.is_deleted:
            return None

        # Nếu Admin sửa config_value -> Tự động nhận diện lại kiểu dữ liệu mới
        if dto.config_value is not None:
            target_data_type = self._detect_data_type(dto.config_value)
            config.config_value = self._validate_value_by_type(dto.config_value, target_data_type)
            config.data_type = target_data_type.value

        if dto.description is not None:
            config.description = dto.description

        if dto.is_active is not None:
            config.is_active = dto.is_active

        if dto.admin_id is not None:
            config.admin_id = dto.admin_id

        return self.repo.save(config)

    def delete_config(self, key: str, admin_id: Optional[uuid.UUID] = None) -> bool:
        """Admin xóa mềm một cấu hình"""
        clean_key = key.strip().upper()
        config = self.repo.get_by_key(clean_key, active_only=False)
        if not config or config.is_deleted:
            return False

        if admin_id:
            config.admin_id = admin_id

        self.repo.delete(config)
        return True

    def restore_config(self, key: str, admin_id: Optional[uuid.UUID] = None) -> Optional[SystemConfig]:
        """Khôi phục cấu hình đã bị xóa mềm"""
        clean_key = key.strip().upper()
        config = self.repo.get_by_key(clean_key, active_only=False)
        if not config:
            return None

        if not config.is_deleted:
            raise ValueError(f"Cấu hình '{clean_key}' đang hoạt động bình thường, không cần khôi phục.")

        if admin_id:
            config.admin_id = admin_id

        return self.repo.restore(config)

    def test_resolve_threshold(self, category_code: Optional[str] = None) -> dict:
        """Endpoint hỗ trợ test xem hệ thống AI đang áp dụng ngưỡng nào"""
        threshold = self.repo.get_system_threshold(category_code=category_code)
        return {
            "category_code": category_code,
            "resolved_threshold": threshold,
            "note": f"Hệ thống sẽ dùng ngưỡng {threshold} khi bóc tách chứng từ loại {category_code or 'Mặc định'}"
        }



    