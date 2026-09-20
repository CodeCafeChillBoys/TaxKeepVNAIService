import uuid
from datetime import datetime, timezone
from typing import Optional, Any
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.ocr import ExtractedDependentData


class OcrExtractRequestMessage(BaseModel):
    """
    Message Contract nhận từ BE.Net gửi sang TaxAIService qua RabbitMQ.
    Hỗ trợ truyền ảnh qua 3 hình thức: URL, Base64 hoặc Đường dẫn File.
    Hỗ trợ cả trường hợp gửi kèm ảnh mặt sau của CCCD.
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: uuid.UUID = Field(..., alias="taskId", description="ID định danh duy nhất của tác vụ từ BE.Net")
    user_id: Optional[uuid.UUID] = Field(None, alias="userId", description="ID của User hoặc Admin bên .NET")
    file_name: str = Field(..., alias="fileName", description="Tên file ảnh (vd: cccd_mat_truoc.jpg)")
    file_url: Optional[str] = Field(None, alias="fileUrl", description="URL tải ảnh (S3, MinIO, Blob Storage)")
    file_base64: Optional[str] = Field(None, alias="fileBase64", description="Chuỗi mã hóa Base64 ảnh mặt trước")
    file_path: Optional[str] = Field(None, alias="filePath", description="Đường dẫn file trên ổ đĩa nội bộ")

    # Tùy chọn gửi kèm mặt sau (dành cho CCCD 2 mặt)
    back_file_url: Optional[str] = Field(None, alias="backFileUrl", description="URL tải ảnh mặt sau nếu có")
    back_file_base64: Optional[str] = Field(None, alias="backFileBase64", description="Base64 ảnh mặt sau nếu có")

    # Quy tắc động từ DB (dependent_document_rules)
    target_group: Optional[str] = Field(None, alias="targetGroup", description="Nhóm đối tượng người phụ thuộc")
    rules: Optional[list] = Field(None, alias="rules", description="Danh sách rules từ bảng dependent_document_rules")
    applied_threshold: Optional[float] = Field(None, alias="appliedThreshold", description="Ngưỡng tin cậy áp dụng")


class OcrExtractResponseMessage(BaseModel):
    """
    Message Contract gửi ngược lại từ TaxAIService sang BE.Net qua RabbitMQ.
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: uuid.UUID = Field(..., alias="taskId", description="ID tác vụ tương ứng từ request")
    user_id: Optional[uuid.UUID] = Field(None, alias="userId", description="ID user từ request")
    success: bool = Field(..., alias="success", description="Trạng thái bóc tách thành công hay thất bại")
    status_code: int = Field(200, alias="statusCode", description="HTTP Status code tương ứng (200, 400, 500)")
    message: str = Field(..., alias="message", description="Thông báo kết quả")
    data: Optional[ExtractedDependentData] = Field(None, alias="data", description="Dữ liệu CCCD/NPT chi tiết")
    errors: Optional[Any] = Field(None, alias="errors", description="Chi tiết lỗi nếu thất bại")
    processed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        alias="processedAt",
        description="Thời điểm xử lý xong (ISO 8601 UTC)"
    )