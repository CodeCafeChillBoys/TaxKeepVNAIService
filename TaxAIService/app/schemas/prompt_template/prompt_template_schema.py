from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class PromptTemplateResponse(BaseModel):
    prompt_key: str
    system_prompt: str
    description: Optional[str] = None
    version: int
    variables: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PromptTemplateCreateRequest(BaseModel):
    prompt_key: str = Field(..., description="Mã định danh duy nhất của prompt (VD: PROMPT_TAX_CHAT_ADVISORY)")
    system_prompt: str = Field(..., description="Nội dung system prompt template")
    description: Optional[str] = Field(None, description="Mô tả mục đích sử dụng của prompt")
    variables: Optional[List[str]] = Field(default_factory=list, description="Danh sách các biến placeholder như ['tax_year_label', 'knowledge_base']")
    is_active: bool = Field(True, description="Trạng thái kích hoạt")


class PromptTemplateUpdateRequest(BaseModel):
    system_prompt: str = Field(..., description="Nội dung system prompt mới")
    description: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = True


class PromptTestRenderRequest(BaseModel):
    prompt_key: str = Field(..., description="Mã prompt cần test")
    params: Dict[str, Any] = Field(default_factory=dict, description="Các giá trị biến truyền vào để test render")


class PromptTestRenderResponse(BaseModel):
    prompt_key: str
    rendered_prompt: str
    variables_used: List[str]