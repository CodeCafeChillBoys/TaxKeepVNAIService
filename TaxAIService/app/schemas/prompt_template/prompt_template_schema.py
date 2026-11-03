from app.core import exclude_from_coverage
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


@exclude_from_coverage
class PromptTemplateResponse(BaseModel):
    prompt_key: str
    system_prompt: str
    description: Optional[str] = None
    version: int
    variables: Optional[List[str]] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    @exclude_from_coverage
    class Config:
        from_attributes = True


@exclude_from_coverage
class PromptTemplateCreateRequest(BaseModel):
    prompt_key: str = Field(..., description="Mã định danh duy nhất của prompt (VD: PROMPT_TAX_CHAT_ADVISORY)")
    system_prompt: str = Field(..., description="Nội dung system prompt template")
    description: Optional[str] = Field(None, description="Mô tả mục đích sử dụng của prompt")
    variables: Optional[List[str]] = Field(default_factory=list, description="Danh sách các biến placeholder như ['tax_year_label', 'knowledge_base']")
    is_active: bool = Field(True, description="Trạng thái kích hoạt")


@exclude_from_coverage
class PromptTemplateUpdateRequest(BaseModel):
    system_prompt: str = Field(..., description="Nội dung system prompt mới")
    description: Optional[str] = None
    variables: Optional[List[str]] = None
    is_active: Optional[bool] = True


@exclude_from_coverage
class PromptTestRenderRequest(BaseModel):
    prompt_key: str = Field(..., description="Mã prompt cần test")
    params: Dict[str, Any] = Field(default_factory=dict, description="Các giá trị biến truyền vào để test render")


@exclude_from_coverage
class PromptTestRenderResponse(BaseModel):
    prompt_key: str
    rendered_prompt: str
    variables_used: List[str]