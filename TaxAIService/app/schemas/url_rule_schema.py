# app/schemas/url_rule_schema.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class UrlRuleCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., max_length=100, description="Tên nguồn, vd: Thư viện Pháp luật")
    domain: str = Field(..., max_length=255, description="Tên miền được phép, vd: thuvienphapluat.vn")
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = Field(True, alias="isActive", description="Trạng thái kích hoạt")
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy", description="ID của Admin tạo quy tắc")

class UrlRuleUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    domain: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = Field(None, alias="isActive")
    updated_by: Optional[uuid.UUID] = Field(None, alias="updatedBy", description="ID của Admin cập nhật quy tắc")

class UrlRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    domain: str
    description: Optional[str] = None
    is_active: bool = Field(..., alias="isActive")
    created_by: Optional[uuid.UUID] = Field(None, alias="createdBy")
    updated_by: Optional[uuid.UUID] = Field(None, alias="updatedBy")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
