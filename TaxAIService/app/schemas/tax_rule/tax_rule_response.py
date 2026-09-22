import uuid
from datetime import datetime
from typing import Optional, List, Union, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class TaxRuleItemResponse(BaseModel):
    """
    Schema đại diện cho từng chi tiết quy tắc thuế (Tax Rule) trong kết quả trả về
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    rule_code: str = Field(..., alias="ruleCode", description="Mã quy tắc định danh duy nhất (vd: DED_PERSONAL_2026)")
    rule_name: str = Field(..., alias="ruleName", description="Tên mô tả quy tắc thuế")
    rule_type: str = Field(..., alias="ruleType", description="Phân loại: DEDUCTION, BRACKET, RATE, EXEMPTION")
    condition: Optional[Union[str, Dict[str, Any]]] = Field(None, alias="condition", description="Điều kiện áp dụng quy tắc (text hoặc JSON object)")
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


class TaxRuleSetResponse(BaseModel):
    """
    Schema đại diện cho tập bộ quy tắc thuế theo năm (Tax Rule Set)
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    rule_set_id: Optional[uuid.UUID] = Field(None, alias="ruleSetId", description="Mã định danh duy nhất bộ luật")
    admin_id: Optional[uuid.UUID] = Field(None, alias="adminId", description="Mã định danh Admin khởi tạo bộ quy tắc")
    name: str = Field(..., alias="name", description="Tên bộ quy tắc thuế")
    tax_year: int = Field(..., alias="taxYear", description="Năm áp dụng luật thuế")
    effective_from: Optional[str] = Field(None, alias="effectiveFrom", description="Ngày bắt đầu áp dụng (YYYY-MM-DD)")
    effective_to: Optional[str] = Field(None, alias="effectiveTo", description="Ngày kết thúc áp dụng (YYYY-MM-DD)")
    status: str = Field("Draft", alias="status", description="Trạng thái bộ luật: Draft hoặc Active")
    approved_by: Optional[uuid.UUID] = Field(None, alias="approvedBy", description="Mã định danh Admin phê duyệt bộ quy tắc")
    approved_at: Optional[datetime] = Field(None, alias="approvedAt", description="Thời điểm phê duyệt bộ quy tắc")


class DependentRuleResponse(BaseModel):
    """
    Schema đại diện cho từng loại điều kiện người phụ thuộc
    """
    model_config = ConfigDict(populate_by_name=True, from_attributes=True)

    id: Optional[uuid.UUID] = Field(None, alias="id")
    rule_id: Optional[uuid.UUID] = Field(None, alias="ruleId")
    rule_set_id: Optional[uuid.UUID] = Field(None, alias="ruleSetId")
    dependent_type: str = Field(..., alias="dependentType", description="CHILD, ADULT_CHILD, SPOUSE, PARENT, OTHER")
    name: str = Field(..., alias="name")
    max_age: Optional[int] = Field(None, alias="maxAge")
    max_monthly_income: Optional[float] = Field(None, alias="maxMonthlyIncome")
    # Có đang học hay ko is_studying
    is_studying: bool = Field(False, alias="isStudying")
    # Có đang khuyết tật hay ko is_disabled
    is_disabled: bool = Field(False, alias="isDisabled")
    conditions: Optional[Union[str, List[str], Dict[str, Any]]] = Field(None, alias="conditions")
    required_documents: Optional[List[Dict[str, Any]]] = Field(
        default_factory=list, 
        alias="requiredDocuments",
        description="Danh sách các loại giấy tờ cần nộp của nhóm đối tượng này"
    )
    status: str = Field("Draft", alias="status")


class TaxRuleExtractionDataResponse(BaseModel):
    """
    Schema gom nhóm dữ liệu bóc tách gồm Tax Rule Set, danh sách Tax Rules và Dependent Rules
    """
    model_config = ConfigDict(populate_by_name=True)

    tax_rule_set: TaxRuleSetResponse = Field(..., alias="taxRuleSet")
    tax_rules: List[TaxRuleItemResponse] = Field(..., alias="taxRules")
    dependent_rules: Optional[List[DependentRuleResponse]] = Field(default_factory=list, alias="dependentRules")
    verification: Optional[Dict[str, Any]] = Field(None, alias="verification", description="Thông tin đối soát năm tính thuế")
    warning: Optional[str] = Field(None, alias="warning", description="Cảnh báo lệch năm nếu có")


class TaxRuleUploadResponse(BaseModel):
    """
    Response trả về sau khi Admin upload văn bản PDF và bóc tách thành công
    """
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field("Tax document processed successfully.", description="Thông báo kết quả xử lý")
    warning: Optional[str] = Field(None, alias="warning", description="Cảnh báo nếu có")
    data: TaxRuleExtractionDataResponse = Field(..., description="Dữ liệu bộ quy tắc thuế đã bóc tách")


class TaxRuleApproveResponse(BaseModel):
    """
    Response trả về sau khi Admin bấm Approve phê duyệt bộ quy tắc thuế sang Active
    """
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field("Tax rule set approved successfully.", description="Thông báo phê duyệt thành công")
    rule_set_id: uuid.UUID = Field(..., alias="ruleSetId", description="ID của bộ quy tắc thuế đã duyệt")
    status: str = Field("Active", description="Trạng thái sau khi duyệt")
    approved_by: Optional[uuid.UUID] = Field(None, alias="approvedBy", description="ID của Admin đã phê duyệt")
    approved_at: Optional[datetime] = Field(None, alias="approvedAt", description="Thời điểm phê duyệt")


class TaxRuleDetailResponse(BaseModel):
    """
    Response trả về khi Admin Review (GET) hoặc Edit (PUT) toàn bộ nội dung bộ quy tắc thuế
    """
    model_config = ConfigDict(populate_by_name=True)

    message: str = Field("Tax rule set retrieved successfully.", description="Thông báo kết quả")
    warning: Optional[str] = Field(None, alias="warning", description="Cảnh báo nếu có")
    data: TaxRuleExtractionDataResponse = Field(..., description="Dữ liệu chi tiết của bộ quy tắc thuế")
