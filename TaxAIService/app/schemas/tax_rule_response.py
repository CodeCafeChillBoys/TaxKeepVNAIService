import uuid
from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class TaxRuleItemResponse(BaseModel):
    """
    Schema đại diện cho từng chi tiết quy tắc thuế (Tax Rule) trong kết quả trả về
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    rule_code: str = Field(..., alias="ruleCode", description="Mã quy tắc định danh duy nhất (vd: DED_PERSONAL_2026)")
    rule_name: str = Field(..., alias="ruleName", description="Tên mô tả quy tắc thuế")
    rule_type: str = Field(..., alias="ruleType", description="Phân loại: DEDUCTION, BRACKET, RATE, EXEMPTION")
    condition: Optional[str] = Field(None, alias="condition", description="Điều kiện áp dụng quy tắc")
    value: Optional[float] = Field(None, alias="value", description="Giá trị số thực tế (tiền VNĐ, tỷ lệ %)")
    unit: Optional[str] = Field(None, alias="unit", description="Đơn vị tính: VND/thang, %, VND/nam...")
    effective_from: Optional[str] = Field(None, alias="effectiveFrom", description="Ngày bắt đầu hiệu lực (YYYY-MM-DD)")
    effective_to: Optional[str] = Field(None, alias="effectiveTo", description="Ngày hết hiệu lực (YYYY-MM-DD)")
    legal_document: Optional[str] = Field(None, alias="legalDocument", description="Tên văn bản quy phạm pháp luật")
    article: Optional[str] = Field(None, alias="article", description="Điều luật")
    clause: Optional[str] = Field(None, alias="clause", description="Khoản luật")
    point: Optional[str] = Field(None, alias="point", description="Điểm luật")
    source_url: Optional[str] = Field(None, alias="sourceUrl", description="URL văn bản pháp luật gốc")
    status: str = Field("Draft", alias="status", description="Trạng thái quy tắc: Draft hoặc Active")
    version: int = Field(1, alias="version", description="Số phiên bản của quy tắc")


class TaxRuleSetResponse(BaseModel):
    """
    Schema đại diện cho tập bộ quy tắc thuế theo năm (Tax Rule Set)
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    rule_set_id: Optional[uuid.UUID] = Field(None, alias="ruleSetId", description="Mã định danh duy nhất bộ luật")
    name: str = Field(..., alias="name", description="Tên bộ quy tắc thuế")
    tax_year: int = Field(..., alias="taxYear", description="Năm áp dụng luật thuế")
    effective_from: Optional[str] = Field(None, alias="effectiveFrom", description="Ngày bắt đầu áp dụng (YYYY-MM-DD)")
    effective_to: Optional[str] = Field(None, alias="effectiveTo", description="Ngày kết thúc áp dụng (YYYY-MM-DD)")
    status: str = Field("Draft", alias="status", description="Trạng thái bộ luật: Draft hoặc Active")


class TaxRuleExtractionDataResponse(BaseModel):
    """
    Schema gom nhóm dữ liệu bóc tách gồm Tax Rule Set và danh sách Tax Rules
    """
    model_config = ConfigDict(populate_by_name=True)

    tax_rule_set: TaxRuleSetResponse = Field(..., alias="taxRuleSet")
    tax_rules: List[TaxRuleItemResponse] = Field(..., alias="taxRules")


class TaxRuleUploadResponse(BaseModel):
    """
    Response trả về sau khi Admin upload văn bản PDF và bóc tách thành công
    """
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field("Tax document processed successfully.", description="Thông báo kết quả xử lý")
    data: TaxRuleExtractionDataResponse = Field(..., description="Dữ liệu bộ quy tắc thuế đã bóc tách")


class TaxRuleApproveResponse(BaseModel):
    """
    Response trả về sau khi Admin bấm Approve phê duyệt bộ quy tắc thuế sang Active
    """
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field("Tax rule set approved successfully.", description="Thông báo phê duyệt thành công")
    rule_set_id: uuid.UUID = Field(..., alias="ruleSetId", description="ID của bộ quy tắc thuế đã duyệt")
    status: str = Field("Active", description="Trạng thái sau khi duyệt")
