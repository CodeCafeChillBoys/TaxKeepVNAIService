from typing import Optional, List
from pydantic import BaseModel, ConfigDict, Field


class ExtractedCertificateFieldDetail(BaseModel):
    """Độ tin cậy của từng trường phục vụ đối soát"""
    model_config = ConfigDict(populate_by_name=True)
    field_name: str = Field(..., alias="fieldName")
    extracted_value: Optional[str] = Field(None, alias="extractedValue")
    confidence_score: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        alias="confidenceScore",
        description="Độ tin cậy từ 0.0 đến 1.0 của trường thông tin"
    )


class GeminiCertificateOcrOutput(BaseModel):
    """Schema chuẩn Gemini Vision trả về dưới dạng Structured JSON"""
    model_config = ConfigDict(populate_by_name=True)

    is_certificate: bool = Field(
        ...,
        alias="isCertificate",
        description="True NẾU VÀ CHỈ NẾU tài liệu là Chứng chỉ hành nghề, Bằng cấp đại học/sau đại học, Chứng chỉ bồi dưỡng nghiệp vụ hợp lệ. False nếu là ảnh cá nhân, giấy tờ tùy thân CCCD, hóa đơn, bảng lương, CV, ảnh mờ hoặc không liên quan."
    )
    rejection_reason: Optional[str] = Field(
        None,
        alias="rejectionReason",
        description="Nếu is_certificate = False, ghi rõ lý do ngắn gọn bằng tiếng Việt (VD: 'Tài liệu tải lên là Giấy tờ tùy thân (CCCD/CMND/Hộ chiếu), không phải chứng chỉ hành nghề', 'Hình ảnh chụp chân dung/phong cảnh', 'Hình ảnh quá mờ không thể đọc được nội dung', 'Tài liệu là hóa đơn/chứng từ'). Nếu là chứng chỉ hợp lệ thì bắt buộc là null."
    )
    detected_type: Optional[str] = Field(
        None,
        alias="detectedType",
        description="Mã loại chứng chỉ nhận diện được: TAX_AGENT, CPA, ACCOUNTANT, CHIEF_ACCOUNTANT, OTHER. Bắt buộc là null nếu is_certificate = False."
    )
    certificate_name: Optional[str] = Field(
        None,
        alias="certificateName",
        description="Tên đầy đủ của chứng chỉ ghi trên văn bằng (VD: 'Chứng chỉ hành nghề dịch vụ làm thủ tục về thuế', 'Chứng chỉ Kiểm toán viên')"
    )
    certificate_number: Optional[str] = Field(
        None,
        alias="certificateNumber",
        description="Số hiệu chứng chỉ hoặc số vào sổ cấp chứng chỉ (VD: '00123/BTC-TCT', 'CPA-2023-456')"
    )
    full_name: Optional[str] = Field(
        None,
        alias="fullName",
        description="Họ và tên người được cấp chứng chỉ (in hoa, bỏ qua học hàm/học vị)"
    )
    citizen_id: Optional[str] = Field(
        None,
        alias="citizenId",
        description="Số CMND hoặc số Căn cước công dân (CCCD) gồm 9 hoặc 12 số của người được cấp (nếu có in trên văn bằng)"
    )
    date_of_birth: Optional[str] = Field(
        None,
        alias="dateOfBirth",
        description="Ngày sinh của người được cấp định dạng YYYY-MM-DD (nếu có ghi trên chứng chỉ)"
    )
    issuing_authority: Optional[str] = Field(
        None,
        alias="issuingAuthority",
        description="Đơn vị / Cơ quan cấp (VD: 'Bộ Tài chính', 'Tổng cục Thuế', 'Hội Kế toán và Kiểm toán Việt Nam')"
    )
    issue_date: Optional[str] = Field(
        None,
        alias="issueDate",
        description="Ngày cấp chứng chỉ định dạng YYYY-MM-DD"
    )
    has_expiry: bool = Field(
        False,
        alias="hasExpiry",
        description="True nếu chứng chỉ có quy định thời hạn hiệu lực, False nếu có giá trị vĩnh viễn"
    )
    expiry_date: Optional[str] = Field(
        None,
        alias="expiryDate",
        description="Ngày hết hạn hiệu lực định dạng YYYY-MM-DD (nếu có)"
    )
    fields: List[ExtractedCertificateFieldDetail] = Field(
        default_factory=list,
        alias="fields",
        description="Danh sách độ tin cậy của từng trường"
    )


class CertificateExtractedData(BaseModel):
    """Dữ liệu bóc tách chuẩn hóa gửi cho Backend ASP.NET Core đối chiếu"""
    model_config = ConfigDict(populate_by_name=True)

    detected_type: Optional[str] = Field(None, alias="detectedType")
    is_valid_type: bool = Field(False, alias="isValidType")
    certificate_name: Optional[str] = Field(None, alias="certificateName")
    certificate_number: Optional[str] = Field(None, alias="certificateNumber")
    full_name: Optional[str] = Field(None, alias="fullName")
    citizen_id: Optional[str] = Field(None, alias="citizenId")
    date_of_birth: Optional[str] = Field(None, alias="dateOfBirth")
    issuing_authority: Optional[str] = Field(None, alias="issuingAuthority")
    issue_date: Optional[str] = Field(None, alias="issueDate")
    has_expiry: bool = Field(False, alias="hasExpiry")
    expiry_date: Optional[str] = Field(None, alias="expiryDate")
    overall_confidence: float = Field(0.0, alias="overallConfidence")


class CertificateOcrResponse(BaseModel):
    """Response DTO chuẩn trả về cho REST API"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool
    status_code: int = Field(..., alias="statusCode")
    message: str
    data: Optional[CertificateExtractedData] = None
    errors: Optional[List[dict]] = None