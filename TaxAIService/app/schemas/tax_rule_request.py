import uuid
from typing import Optional, Any, List, Union
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


class TaxRuleItemUpdateRequest(BaseModel):
    """
    Schema cập nhật cho từng quy tắc thuế con
    """
    model_config = ConfigDict(populate_by_name=True)

    rule_id: Optional[uuid.UUID] = Field(None, alias="ruleId")
    rule_code: Optional[str] = Field(None, alias="ruleCode")
    rule_name: Optional[str] = Field(None, alias="ruleName")
    rule_type: Optional[str] = Field(None, alias="ruleType")
    condition: Optional[Any] = Field(None, alias="condition")
    value: Optional[float] = Field(None, alias="value")
    unit: Optional[str] = Field(None, alias="unit")
    effective_from: Optional[str] = Field(None, alias="effectiveFrom")
    effective_to: Optional[str] = Field(None, alias="effectiveTo")
    legal_document: Optional[str] = Field(None, alias="legalDocument")
    article: Optional[str] = Field(None, alias="article")
    clause: Optional[str] = Field(None, alias="clause")
    point: Optional[str] = Field(None, alias="point")
    source_url: Optional[str] = Field(None, alias="sourceUrl")
    status: Optional[str] = Field(None, alias="status")
    version: Optional[int] = Field(None, alias="version")


class DependentRuleUpdateRequest(BaseModel):
    """
    Schema cập nhật cho từng quy tắc người phụ thuộc
    """
    model_config = ConfigDict(populate_by_name=True)

    id: Optional[uuid.UUID] = Field(None, alias="id")
    rule_id: Optional[uuid.UUID] = Field(None, alias="ruleId")
    dependent_type: Optional[str] = Field(None, alias="dependentType")
    name: Optional[str] = Field(None, alias="name")
    max_age: Optional[int] = Field(None, alias="maxAge")
    max_monthly_income: Optional[float] = Field(None, alias="maxMonthlyIncome")
    is_studying: Optional[bool] = Field(None, alias="isStudying")
    is_disabled: Optional[bool] = Field(None, alias="isDisabled")
    conditions: Optional[Any] = Field(None, alias="conditions")
    status: Optional[str] = Field(None, alias="status")


class TaxRuleUpdateRequest(BaseModel):
    """
    Schema đại diện cho dữ liệu yêu cầu chỉnh sửa toàn bộ nội dung của Tax Rule Set
    """
    model_config = ConfigDict(populate_by_name=True)

    name: Optional[str] = Field(None, alias="name", description="Tên bộ quy tắc thuế")
    tax_year: Optional[int] = Field(None, alias="taxYear", description="Năm tính thuế áp dụng", ge=1900, le=2100)
    effective_from: Optional[str] = Field(None, alias="effectiveFrom")
    effective_to: Optional[str] = Field(None, alias="effectiveTo")
    status: Optional[str] = Field(None, alias="status", description="Trạng thái (Draft, Active, Expired)")
    tax_rules: Optional[list[TaxRuleItemUpdateRequest]] = Field(None, alias="taxRules", description="Danh sách quy tắc thuế cập nhật")
    dependent_rules: Optional[list[DependentRuleUpdateRequest]] = Field(None, alias="dependentRules", description="Danh sách người phụ thuộc cập nhật")
