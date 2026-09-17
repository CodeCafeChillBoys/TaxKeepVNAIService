import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field
from app.enum.system_config_enum import ConfigDataType


class SystemConfigCreateRequest(BaseModel):
    """Payload khi Admin tạo cấu hình mới (Admin không cần biết về data_type)"""
    config_key: str = Field(
        ..., 
        min_length=3, 
        max_length=100, 
        example="THRESHOLD_MEDICAL_EXPENSE_INVOICE",
        description="Khóa cấu hình viết hoa, không dấu (ví dụ: AI_CONFIDENCE_THRESHOLD, THRESHOLD_MEDICAL...)"
    )
    config_value: str = Field(
        ..., 
        example="0.85",
        description="Giá trị của cấu hình (0.85, 3, true, hoặc chuỗi)"
    )
    description: Optional[str] = Field(
        None, 
        max_length=255, 
        example="Ngưỡng tin cậy riêng cho hóa đơn viện phí",
        description="Mô tả công dụng cấu hình cho người quản trị"
    )
    admin_id: Optional[uuid.UUID] = Field(
        None, 
        example="b3d87a41-3b7c-486a-a2ef-95b86377e80d",
        description="ID tài khoản Admin thực hiện"
    )


class SystemConfigUpdateRequest(BaseModel):
    """Payload khi Admin chỉnh sửa cấu hình"""
    config_value: Optional[str] = Field(None, example="0.90", description="Giá trị mới")
    description: Optional[str] = Field(None, example="Cập nhật lại ngưỡng")
    is_active: Optional[bool] = Field(None, example=True, description="Bật hoặc tắt cấu hình")
    admin_id: Optional[uuid.UUID] = Field(None, example="b3d87a41-3b7c-486a-a2ef-95b86377e80d")


class SystemConfigResponse(BaseModel):
    """Dữ liệu trả về cho Frontend"""
    config_key: str
    config_value: str
    data_type: str
    description: Optional[str] = None
    is_active: bool
    is_deleted: bool
    deleted_at: Optional[datetime] = None
    updated_at: datetime
    created_at: datetime
    admin_id: Optional[uuid.UUID] = None

    class Config:
        from_attributes = True