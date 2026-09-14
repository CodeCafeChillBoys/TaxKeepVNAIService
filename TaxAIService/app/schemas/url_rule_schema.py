# app/schemas/url_rule_schema.py
import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict

class UrlRuleCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., max_length=100, description="Tên quy tắc, vd: Thư viện Pháp luật")
    rule_type: str = Field(..., alias="ruleType", description="Loại so khớp: DOMAIN, PREFIX, REGEX, EXACT")
    pattern: str = Field(..., max_length=500, description="Giá trị quy tắc, vd: thuvienphapluat.vn")
    description: Optional[str] = Field(None, max_length=255)
    is_active: bool = Field(True, alias="isActive", description="Trạng thái kích hoạt")

class UrlRuleUpdateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = None
    rule_type: Optional[str] = Field(None, alias="ruleType")
    pattern: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = Field(None, alias="isActive")

class UrlRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: uuid.UUID
    name: str
    rule_type: str = Field(..., alias="ruleType")
    pattern: str
    description: Optional[str] = None
    is_active: bool = Field(..., alias="isActive")
    created_at: datetime = Field(..., alias="createdAt")
    updated_at: datetime = Field(..., alias="updatedAt")
