from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class DependentRuleItem(BaseModel):
    """Quy tắc giấy tờ từ bảng dependent_document_rules của .NET truyền sang"""
    #cho phép model nhận dữ liệu bằng tên field Python hoặc alias của field.
    model_config = ConfigDict(populate_by_name=True)

    doc_type: str = Field(..., alias="docType", description="Mã loại giấy tờ trong DB")
    is_mandatory: bool = Field(True, alias="isMandatory", description="Bắt buộc hay không")
    description: Optional[str] = Field(None, alias="description", description="Tiêu chí/hướng dẫn của Admin")


class RuleValidationResult(BaseModel):
    """Kết quả AI đối chiếu giấy tờ thực tế với Rule của Admin"""
    model_config = ConfigDict(populate_by_name=True)

    is_matched_rule: bool = Field(
        True, 
        alias="isMatchedRule", 
        description="Giấy tờ có khớp với một trong các rule trong DB không"
    )
    matched_doc_type: Optional[str] = Field(
        None, 
        alias="matchedDocType", 
        description="Mã doc_type trong DB mà AI nhận diện được"
    )
    is_compliant_with_description: bool = Field(
        True, 
        alias="isCompliantWithDescription", 
        description="Ảnh có thỏa mãn các tiêu chí Admin ghi trong description không"
    )
    notes: Optional[str] = Field(
        None, 
        alias="notes", 
        description="Đánh giá chi tiết của AI theo mô tả của Admin"
    )


class ConfidenceScores(BaseModel):
    """Độ tin cậy trích xuất của từng trường dữ liệu (từ 0.0 đến 1.0)"""
    model_config = ConfigDict(populate_by_name=True)

    overall: float = Field(default=0.95, alias="overall", description="Độ tin cậy tổng thể của tài liệu")

    # 1. Thông tin cá nhân
    citizen_id: Optional[float] = Field(None, alias="citizenId")
    full_name: Optional[float] = Field(None, alias="fullName")
    birth_date: Optional[float] = Field(None, alias="birthDate")
    gender: Optional[float] = Field(None, alias="gender")
    nationality: Optional[float] = Field(None, alias="nationality")
    origin_place: Optional[float] = Field(None, alias="originPlace")
    residence_place: Optional[float] = Field(None, alias="residencePlace")
    expiry_date: Optional[float] = Field(None, alias="expiryDate")
    issue_date: Optional[float] = Field(None, alias="issueDate")

    # 2. Thông tin thân nhân
    father_full_name: Optional[float] = Field(None, alias="fatherFullName")
    father_id_number: Optional[float] = Field(None, alias="fatherIdNumber")
    mother_full_name: Optional[float] = Field(None, alias="motherFullName")
    mother_id_number: Optional[float] = Field(None, alias="motherIdNumber")
    spouse_full_name: Optional[float] = Field(None, alias="spouseFullName")

    # 3. Thông tin văn bản pháp lý
    document_type: Optional[float] = Field(None, alias="documentType")
    document_number: Optional[float] = Field(None, alias="documentNumber")
    issuing_authority: Optional[float] = Field(None, alias="issuingAuthority")

class ThresholdValidationResult(BaseModel):
    """Kết quả đối soát ngưỡng động từ Database/Admin - KHÔNG HARDCODE"""
    model_config = ConfigDict(populate_by_name=True)
    applied_threshold: float = Field(
        ..., 
        alias="appliedThreshold", 
        description="Ngưỡng tin cậy áp dụng (lấy động từ DB system_configs hoặc request)"
    )
    overall_confidence: float = Field(
        ..., 
        alias="overallConfidence", 
        description="Điểm tin cậy trung bình tính từ tổng điểm / độ dài các trường hiện có"
    )
    is_passed_threshold: bool = Field(
        ..., 
        alias="isPassedThreshold", 
        description="True nếu đạt ngưỡng, False nếu nhỏ hơn ngưỡng và cần nhập lại"
    )
    low_confidence_fields: List[str] = Field(
        default_factory=list, 
        alias="lowConfidenceFields", 
        description="Tự động chứa danh sách các trường có điểm thấp hơn ngưỡng"
    )
    warning_message: Optional[str] = Field(
        None, 
        alias="warningMessage", 
        description="Thông báo cảnh báo động nếu không đạt ngưỡng"
    )

    



class RequiredDocument(BaseModel):
    """Cấu trúc giấy tờ cần nộp, tương thích với Gemini Developer API schema."""
    model_config = ConfigDict(populate_by_name=True)

    doc_type: Optional[str] = Field(None, alias="docType")
    name: Optional[str] = Field(None, alias="name")
    is_mandatory: Optional[bool] = Field(None, alias="isMandatory")
    description: Optional[str] = Field(None, alias="description")


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
        description="Nhóm đối tượng được gợi ý khớp với target_group trong DB"
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
    rule_validation: Optional[RuleValidationResult] = Field(
        None, 
        alias="ruleValidation", 
        description="Đánh giá tính hợp lệ theo cấu hình của Admin"
    )

    threshold_validation: Optional[ThresholdValidationResult] = Field(
        None, 
        alias="thresholdValidation", 
        description="Kết quả kiểm tra ngưỡng động"
    )

    required_documents: Optional[List[RequiredDocument]] = Field(
        default_factory=list,
        alias="requiredDocuments",
        description="Danh sách các loại giấy tờ cần upload cho nhóm đối tượng này"
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
    document_type: Optional[str] = Field(
        None, 
        alias="documentType", 
        description="Mã loại giấy tờ khớp với doc_type trong DB (vd: CITIZEN_ID, BIRTH_CERTIFICATE,...) hoặc chuỗi tự do"
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


