import uuid
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class TaxRuleUploadRequest(BaseModel):
    """
    Schema đại diện cho dữ liệu yêu cầu khi upload văn bản PDF luật thuế
    """
    model_config = ConfigDict(populate_by_name=True)

    tax_year: int = Field(
        ...,
        alias="taxYear",
        description="Năm tính thuế (ví dụ: 2026, từ 1900 đến 2100)",
        ge=1900,
        le=2100
    )
    name: Optional[str] = Field(
        None,
        alias="name",
        description="Tên tùy chỉnh cho bộ quy tắc thuế (Tax Rule Set)"
    )
    source_url: Optional[str] = Field(
        None,
        alias="sourceUrl",
        description="Đường dẫn URL nguồn pháp luật chính thức (bắt đầu bằng http/https)"
    )


class TaxRuleApproveRequest(BaseModel):
    """
    Schema đại diện cho dữ liệu yêu cầu khi phê duyệt bộ quy tắc thuế (Tax Rule Set)
    """
    model_config = ConfigDict(populate_by_name=True)

    admin_id: uuid.UUID = Field(
        ...,
        alias="adminId",
        description="ID của Admin thực hiện phê duyệt (UUID)"
    )
