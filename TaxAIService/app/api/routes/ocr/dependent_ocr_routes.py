from typing import Optional
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from app.services.ocr import DependentOcrService
from app.schemas.ocr import OcrExtractionResponse

router = APIRouter(prefix="/api/ocr", tags=["OCR Documents"])
ocr_service = DependentOcrService()

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"
}

@router.post(
    "/extract",
    response_model=OcrExtractionResponse,
    response_model_by_alias=True,
    summary="OCR bóc tách giấy tờ tùy thân & chứng minh người phụ thuộc cho .NET"
)
async def extract_dependent_document(
    file: UploadFile = File(..., description="Ảnh giấy tờ (CCCD, Khai sinh, Kết hôn, CT07, PDF)"),
    back_file: Optional[UploadFile] = File(None, description="Mặt sau CCCD nếu gửi riêng mặt trước/sau")
):
    # 1. Kiểm tra định dạng file mặt trước
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng {file.content_type} không được hỗ trợ. Chỉ nhận JPEG, PNG, WEBP, PDF."
        )

    file_bytes = await file.read()
    files_to_process = [(file_bytes, file.content_type)]

    # 2. Nếu có gửi kèm mặt sau CCCD
    if back_file:
        back_bytes = await back_file.read()
        files_to_process.append((back_bytes, back_file.content_type))

    # 3. Gọi Gemini OCR bóc dữ liệu
    result = ocr_service.extract_document(files_to_process)
    return result