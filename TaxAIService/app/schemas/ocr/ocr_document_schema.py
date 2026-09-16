from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from app.enum.ocr_document_enum import DocumentType


class ConfidenceScores(BaseModel):
    """Độ tin cậy trích xuất của từng trường"""
    model_config = ConfigDict(populate_by_name=True)

    overall: float = Field(default=0.95, alias="overall")
    citizen_id: Optional[float] = Field(default=0.95, alias="citizenId")
    full_name: Optional[float] = Field(default=0.95, alias="fullName")
    birth_date: Optional[float] = Field(default=0.95, alias="birthDate")


class ExtractedDependentData(BaseModel):
    """Toàn bộ thông tin bóc tách chi tiết từ CCCD hoặc giấy tờ người phụ thuộc"""
    model_config = ConfigDict(populate_by_name=True)

    # 1. Thông tin định danh của người trên giấy tờ
    citizen_id: Optional[str] = Field(
        None, 
        alias="citizenId", 
        description="Số CCCD/CMND (12 hoặc 9 số) hoặc Mã số định danh cá nhân"
    )
    full_name: Optional[str] = Field(
        None, 
        alias="fullName", 
        description="Họ và tên đầy đủ viết IN HOA có dấu (vd: NGUYỄN VĂN AN)"
    )
    birth_date: Optional[str] = Field(
        None, 
        alias="birthDate", 
        description="Ngày sinh chuẩn hóa YYYY-MM-DD"
    )
    gender: Optional[str] = Field(
        None, 
        alias="gender", 
        description="Giới tính: MALE hoặc FEMALE"
    )
    nationality: Optional[str] = Field(
        "Việt Nam", 
        alias="nationality", 
        description="Quốc tịch"
    )
    origin_place: Optional[str] = Field(
        None, 
        alias="originPlace", 
        description="Quê quán"
    )
    residence_place: Optional[str] = Field(
        None, 
        alias="residencePlace", 
        description="Nơi thường trú / Địa chỉ cư trú"
    )
    expiry_date: Optional[str] = Field(
        None, 
        alias="expiryDate", 
        description="Ngày hết hạn của CCCD YYYY-MM-DD"
    )
    issue_date: Optional[str] = Field(
        None, 
        alias="issueDate", 
        description="Ngày cấp giấy tờ YYYY-MM-DD"
    )
    suggested_group: Optional[str] = Field(
        None, 
        alias="suggestedGroup", 
        description="Gợi ý nhóm đối tượng: CHILD_UNDER_18, CHILD_OVER_18_STUDENT, ELDERLY_PARENT, SPOUSE, OTHER"
    )
    is_readable: bool = Field(
        True, 
        alias="isReadable", 
        description="Ảnh có rõ ràng để đọc không"
    )
    unreadable_reason: Optional[str] = Field(
        None, 
        alias="unreadableReason", 
        description="Lý do nếu mờ/lóa"
    )
    confidence_scores: Optional[ConfidenceScores] = Field(
        None, 
        alias="confidenceScores", 
        description="Độ tin cậy trích xuất"
    )

    # 2. Thông tin thân nhân (Dành cho Giấy khai sinh / Kết hôn / CT07 nếu quét)
    father_full_name: Optional[str] = Field(
        None, 
        alias="fatherFullName", 
        description="Họ và tên người cha"
    )
    father_id_number: Optional[str] = Field(
        None, 
        alias="fatherIdNumber", 
        description="Số CCCD/Định danh của cha"
    )
    mother_full_name: Optional[str] = Field(
        None, 
        alias="motherFullName", 
        description="Họ và tên người mẹ"
    )
    mother_id_number: Optional[str] = Field(
        None, 
        alias="motherIdNumber", 
        description="Số CCCD/Định danh của mẹ"
    )
    spouse_full_name: Optional[str] = Field(
        None, 
        alias="spouseFullName", 
        description="Họ tên vợ/chồng"
    )

    # 3. Thông tin văn bản pháp lý khác
    document_type: Optional[DocumentType] = Field(
        None, 
        alias="documentType", 
        description="Loại giấy tờ nhận diện được"
    )
    document_number: Optional[str] = Field(
        None, 
        alias="documentNumber", 
        description="Số giấy tờ, số vào sổ hộ tịch (vd: 45/2020/TLKS-BS)"
    )
    issuing_authority: Optional[str] = Field(
        None, 
        alias="issuingAuthority", 
        description="Cơ quan cấp (vd: Cục Cảnh sát QLHC về TTXH, UBND...)"
    )


# Alias để tương thích ngược nếu cần
DependentOcrData = ExtractedDependentData


class OcrExtractionResponse(BaseModel):
    """Response chuẩn trả về cho .NET"""
    model_config = ConfigDict(populate_by_name=True)

    success: bool = Field(True, alias="success")
    status_code: int = Field(200, alias="statusCode")
    message: str = Field("Trích xuất thông tin CCCD thành công.", alias="message")
    data: Optional[ExtractedDependentData] = Field(None, alias="data")
    errors: Optional[Any] = Field(None, alias="errors")