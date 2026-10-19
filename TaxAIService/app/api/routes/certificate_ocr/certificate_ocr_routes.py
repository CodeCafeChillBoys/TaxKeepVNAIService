import json
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status
from fastapi.responses import JSONResponse

from app.services.certificate_ocr.certificate_ocr_service import CertificateOcrService
from app.schemas.certificate_ocr.certificate_ocr_schema import CertificateOcrResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/certificates/ocr", tags=["Expert Certificate OCR"])

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"
}

ocr_service = CertificateOcrService()


@router.post(
    "/extract",
    response_model=CertificateOcrResponse,
    response_model_by_alias=True,
    summary="Bóc tách OCR chứng chỉ hành nghề của chuyên gia"
)
async def extract_expert_certificate(
    file: UploadFile = File(..., description="Ảnh chụp (JPEG, PNG, WEBP) hoặc file PDF của chứng chỉ hành nghề"),
    allowed_types_json: Optional[str] = Form(
        None,
        description="Chuỗi JSON danh mục các loại chứng chỉ đang hoạt động từ Backend để AI đối chiếu phân loại"
    )
):
    """
    Endpoint nhận file chứng chỉ hành nghề và phân tích bằng Gemini Vision:
    1. Kiểm tra hình ảnh có phải là chứng chỉ hành nghề hợp lệ hay không (loại trừ CCCD, hóa đơn, selfie, CV...).
    2. Nếu không phải chứng chỉ: Trả về lỗi 400 kèm lý do chi tiết (rejectionReason).
    3. Nếu là chứng chỉ hợp lệ: Bóc tách Họ tên, Số hiệu, Số CCCD/CMND, Ngày cấp, Thời hạn và Cơ quan cấp.
    4. Phân loại mã loại chứng chỉ theo danh mục cấu hình hợp lệ của hệ thống.
    """
    # 1. Kiểm tra định dạng tệp tin
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng {file.content_type} không được hỗ trợ. Chỉ nhận JPEG, PNG, WEBP, HEIC, PDF."
        )

    # 2. Đọc nội dung file
    file_bytes = await file.read()
    mime_type = file.content_type or "image/jpeg"

    # 3. Parse JSON danh mục cấu hình nếu có gửi lên
    allowed_types = None
    if allowed_types_json:
        try:
            allowed_types = json.loads(allowed_types_json)
        except Exception as ex:
            logger.warning(f"Không thể parse allowed_types_json: {ex}")

    # 4. Thực thi bóc tách
    result = ocr_service.extract_certificate(
        file_bytes=file_bytes,
        mime_type=mime_type,
        allowed_types=allowed_types
    )

    return JSONResponse(
        status_code=result.status_code,
        content=result.model_dump(by_alias=True)
    )
