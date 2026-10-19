import uuid
from datetime import datetime, timezone
from typing import Optional, Any, List, Dict
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.certificate_ocr.certificate_ocr_schema import CertificateExtractedData


class CertificateOcrRequestMessage(BaseModel):
    """
    Message Contract nhận từ BE .NET gửi sang TaxAIService qua RabbitMQ (certificate.ocr.ai.request.queue).
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: uuid.UUID = Field(..., alias="taskId", description="ID định danh tác vụ từ BE .NET")
    user_id: Optional[uuid.UUID] = Field(None, alias="userId", description="ID của Chuyên gia (User)")
    application_id: Optional[uuid.UUID] = Field(None, alias="applicationId", description="ID của Hồ sơ chuyên gia")
    certificate_id: Optional[uuid.UUID] = Field(None, alias="certificateId", description="ID của Chứng chỉ chuyên gia")
    file_name: str = Field(..., alias="fileName", description="Tên file ảnh/PDF")
    file_url: Optional[str] = Field(None, alias="fileUrl", description="URL tải file (Supabase/S3)")
    file_base64: Optional[str] = Field(None, alias="fileBase64", description="Chuỗi mã hóa Base64 của file")
    file_path: Optional[str] = Field(None, alias="filePath", description="Đường dẫn file trên ổ đĩa nội bộ")

    # Danh mục mã loại chứng chỉ đang active từ DB để AI đối chiếu
    allowed_types: Optional[List[Dict[str, str]]] = Field(
        None,
        alias="allowedTypes",
        description="Danh sách các loại chứng chỉ đang hoạt động do Admin cấu hình"
    )


class CertificateOcrResponseMessage(BaseModel):
    """
    Message Contract gửi từ TaxAIService về BE .NET qua RabbitMQ (certificate.ocr.ai.response.queue).
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: uuid.UUID = Field(..., alias="taskId", description="ID tác vụ từ request")
    user_id: Optional[uuid.UUID] = Field(None, alias="userId", description="ID của Chuyên gia")
    application_id: Optional[uuid.UUID] = Field(None, alias="applicationId", description="ID của Hồ sơ")
    certificate_id: Optional[uuid.UUID] = Field(None, alias="certificateId", description="ID của Chứng chỉ")
    success: bool = Field(..., alias="success", description="Bóc tách thành công hay thất bại")
    status_code: int = Field(200, alias="statusCode", description="Mã trạng thái HTTP (200, 400, 422, 500)")
    message: str = Field(..., alias="message", description="Thông báo kết quả hoặc lý do từ chối")
    data: Optional[CertificateExtractedData] = Field(None, alias="data", description="Dữ liệu bóc tách chứng chỉ")
    errors: Optional[Any] = Field(None, alias="errors", description="Chi tiết lỗi nếu thất bại")
    processed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        alias="processedAt",
        description="Thời điểm xử lý xong (ISO 8601 UTC)"
    )
