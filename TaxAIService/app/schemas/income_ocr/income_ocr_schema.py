from typing import Optional,List,Dict,Any
from pydantic import BaseModel, ConfigDict, Field  # lớp trung gian giúp fastAPI kiểm tra và chuyển đổi dữ liệu request / reponse theo schemae mặc định

# BaseModel dùng tạo model định nghĩa các cấu trúc dữ liệu
# Optional cho phép truyền vào biến có hoăc ko có dữ liệu điều đc
# Field đặt thêm rule vào field
# model_dump → model → dict

class BoundingBox(BaseModel):
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0
    
class ExtractedIncomeFieldDetail(BaseModel):
    """Chi tiết bóc tách từng trường để phục vụ thẩm định và lưu log"""
    field_name: str = Field(..., alias="fieldName")
    extracted_value: Optional[str] = Field(None, alias="extractedValue")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        alias="confidenceScore",
        description="Độ tin cậy từ 0.0 đến 1.0 dựa trên độ sắc nét của chữ trên ảnh"
    )
    bounding_box: Optional[BoundingBox] = Field(None, alias="boundingBox")
    model_config = ConfigDict(populate_by_name=True)
    

    # -------------------------------------------------------------------------
# 2. Schema AI Gemini trả về (Ép kiểu Structured Output)
# -------------------------------------------------------------------------
class GeminiIncomeOcrOutput(BaseModel):
    """Schema chuẩn Gemini 2.5 Flash trả về dưới dạng JSON"""
    model_config = ConfigDict(populate_by_name=True)
    # Phân loại chứng từ
    is_income_document: bool = Field(
        True,
        alias="isIncomeDocument",
        description="True nếu là phiếu lương, bảng thanh toán lương, sao kê thu nhập hoặc chứng từ khấu trừ thuế TNCN; False nếu là ảnh khác."
    )
    doc_type_description: Optional[str] = Field(
        None,
        alias="docTypeDescription",
        description="Mô tả loại chứng từ: PHIEU_LUONG, BANG_LUONG, SAO_KE_THU_NHAP, CHUNG_TU_KHAU_TRU_THUE"
    )
    # 1. Các trường ánh xạ trực tiếp sang bảng incomes
    organization_name: Optional[str] = Field(
        None,
        alias="organizationName",
        description="Tên công ty / đơn vị chi trả thu nhập ghi trên phiếu lương"
    )
    tax_id_number: Optional[str] = Field(
        None,
        alias="taxIdNumber",
        description="Mã số thuế của công ty hoặc Mã số thuế cá nhân của người lao động ghi trên phiếu"
    )
    month: Optional[int] = Field(
        None,
        alias="month",
        description="Tháng tính lương (từ 1 đến 12)"
    )
    year: Optional[int] = Field(
        None,
        alias="year",
        description="Năm tính lương (Ví dụ: 2024, 2025, 2026)"
    )
    total_taxable_income: float = Field(
        0.0,
        alias="totalTaxableIncome",
        description="Tổng thu nhập chịu thuế TNCN (hoặc tổng thu nhập sau khi trừ phụ cấp miễn thuế; nếu không có thì là tổng lương gộp)"
    )
    insurance_deducted: float = Field(
        0.0,
        alias="insuranceDeducted",
        description="Tổng các khoản bảo hiểm bắt buộc đã trừ vào lương (BHXH + BHYT + BHTN)"
    )
    tax_already_deducted: float = Field(
        0.0,
        alias="taxAlreadyDeducted",
        description="Thuế thu nhập cá nhân đã tạm khấu trừ trong kỳ lương"
    )
    # 2. Các trường chi tiết mở rộng để hỗ trợ kiểm tra chéo và đối soát
    employee_name: Optional[str] = Field(
        None,
        alias="employeeName",
        description="Họ và tên nhân viên nhận lương"
    )
    employee_id: Optional[str] = Field(
        None,
        alias="employeeId",
        description="Mã nhân viên (nếu có)"
    )
    gross_salary: Optional[float] = Field(
        None,
        alias="grossSalary",
        description="Tổng thu nhập trước thuế (Lương Gross)"
    )
    net_salary: Optional[float] = Field(
        None,
        alias="netSalary",
        description="Thu nhập thực lĩnh / Lương thực nhận chuyển khoản"
    )
    # Chi tiết bảo hiểm tách riêng (nếu phiếu có phân rã)
    bhxh_amount: Optional[float] = Field(None, alias="bhxhAmount", description="BHXH (8%)")
    bhyt_amount: Optional[float] = Field(None, alias="bhytAmount", description="BHYT (1.5%)")
    bhtn_amount: Optional[float] = Field(None, alias="bhtnAmount", description="BHTN (1%)")
    # Đánh giá chất lượng ảnh
    quality_issues: List[str] = Field(
        default_factory=list,
        alias="qualityIssues",
        description="Các lỗi quang học: 'IMAGE_BLURRY', 'LOW_RESOLUTION', 'CROPPED_EDGES', 'EXCESSIVE_GLARE'"
    )
    # Danh sách chấm điểm từng trường
    fields: List[ExtractedIncomeFieldDetail] = Field(
        default_factory=list,
        alias="fields",
        description="Danh sách độ tin cậy của từng trường phục vụ lưu DB và tính threshold"
    )

# -------------------------------------------------------------------------
# 3. Kết quả thẩm định ngưỡng (Threshold Validation)
# -------------------------------------------------------------------------
class IncomeThresholdValidationResult(BaseModel):
    model_config = ConfigDict(populate_by_name=True)
    applied_threshold: float = Field(..., alias="appliedThreshold")
    overall_confidence: float = Field(..., alias="overallConfidence")
    is_passed_threshold: bool = Field(..., alias="isPassedThreshold")
    low_confidence_fields: List[str] = Field(default_factory=list, alias="lowConfidenceFields")
    warning_message: Optional[str] = Field(None, alias="warningMessage")
    
    
# -------------------------------------------------------------------------
# 4. Response DTO trả về cho REST API và RabbitMQ
# -------------------------------------------------------------------------
class IncomeExtractedData(BaseModel):
    """Dữ liệu bóc tách chuẩn hóa tương thích bảng incomes"""
    model_config = ConfigDict(populate_by_name=True)
    organization_name: str = Field(..., alias="organizationName")
    tax_id_number: Optional[str] = Field(None, alias="taxIdNumber")
    month: int = Field(..., alias="month")
    year: int = Field(..., alias="year")
    total_taxable_income: float = Field(..., alias="totalTaxableIncome")
    insurance_deducted: float = Field(..., alias="insuranceDeducted")
    tax_already_deducted: float = Field(..., alias="taxAlreadyDeducted")
    payslip_file_url: Optional[str] = Field(None, alias="payslipFileUrl")
    # Bổ trợ
    employee_name: Optional[str] = Field(None, alias="employeeName")
    gross_salary: Optional[float] = Field(None, alias="grossSalary")
    net_salary: Optional[float] = Field(None, alias="netSalary")
    threshold_validation: IncomeThresholdValidationResult = Field(..., alias="thresholdValidation")
    
    
class IncomeOcrResponse(BaseModel):
    """Payload phản hồi HTTP chuẩn cho .NET Backend"""
    model_config = ConfigDict(populate_by_name=True)
    success: bool = Field(True, alias="success")
    status_code: int = Field(200, alias="statusCode")
    message: str = Field("Bóc tách báo cáo lương thành công.", alias="message")
    data: Optional[IncomeExtractedData] = Field(None, alias="data")
    errors: Optional[List[Dict[str, Any]]] = Field(default_factory=list, alias="errors")
    
    
