import uuid
from datetime import datetime, timezone
from typing import Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class TaxRuleExtractRequestMessage(BaseModel):
    """
    Message Contract nhận từ BE.Net gửi sang TaxAIService qua RabbitMQ.
    Hỗ trợ truyền file PDF theo 3 cách:
    1. fileUrl: Đường dẫn tải file qua HTTP/S3/MinIO
    2. fileBase64: Chuỗi mã hóa Base64 nội dung file
    3. filePath: Đường dẫn file trên ổ đĩa dùng chung (Shared Storage)
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: uuid.UUID = Field(..., alias="taskId", description="ID định danh duy nhất của tác vụ từ BE.Net")
    admin_id: Optional[uuid.UUID] = Field(None, alias="adminId", description="ID của Admin khởi tạo tác vụ bên BE.Net")
    file_name: str = Field(..., alias="fileName", description="Tên file PDF (vd: LuatThue2026.pdf)")
    file_url: Optional[str] = Field(None, alias="fileUrl", description="URL tải file PDF")
    file_base64: Optional[str] = Field(None, alias="fileBase64", description="Dữ liệu file mã hóa Base64")
    file_path: Optional[str] = Field(None, alias="filePath", description="Đường dẫn file trên đĩa")
    tax_year: int = Field(..., alias="taxYear", description="Năm áp dụng luật thuế (vd: 2026)")
    name: Optional[str] = Field(None, alias="name", description="Tên bộ quy tắc thuế tùy chọn")
    source_url: Optional[str] = Field(None, alias="sourceUrl", description="URL nguồn văn bản gốc nếu có")


class TaxRuleExtractResponseMessage(BaseModel):
    """
    Message Contract gửi ngược lại từ TaxAIService sang BE.Net qua RabbitMQ.
    """
    model_config = ConfigDict(populate_by_name=True)

    task_id: uuid.UUID = Field(..., alias="taskId", description="ID tác vụ tương ứng từ request")
    admin_id: Optional[uuid.UUID] = Field(None, alias="adminId", description="ID của Admin đã tạo")
    status: str = Field(..., alias="status", description="Kết quả: SUCCESS hoặc FAILED")
    rule_set_id: Optional[uuid.UUID] = Field(None, alias="ruleSetId", description="ID bộ luật vừa tạo thành công")
    warning: Optional[str] = Field(None, alias="warning", description="Cảnh báo lệch năm hoặc thông tin cần lưu ý")
    data: Optional[Dict[str, Any]] = Field(None, alias="data", description="Toàn bộ dữ liệu trích xuất thành công")
    error_message: Optional[str] = Field(None, alias="errorMessage", description="Chi tiết lỗi nếu thất bại")
    processed_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        alias="processedAt",
        description="Thời điểm xử lý xong (ISO 8601 UTC)"
    )
