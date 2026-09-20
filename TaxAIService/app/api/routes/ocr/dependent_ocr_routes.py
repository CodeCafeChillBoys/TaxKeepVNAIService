import json
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.repositories.system_config.system_config_repository import SystemConfigRepository
from app.services.ocr import DependentOcrService
from app.schemas.ocr import OcrExtractionResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/ocr", tags=["OCR Documents"])

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"
}


@router.post(
    "/extract",
    response_model=OcrExtractionResponse,
    response_model_by_alias=True,
    summary="OCR bóc tách giấy tờ tùy thân & đối chiếu quy tắc người phụ thuộc cho .NET"
)
async def extract_dependent_document(
    file: UploadFile = File(..., description="Ảnh giấy tờ (CCCD, Khai sinh, Thẻ SV, Kết hôn, CT07, PDF)"),
    back_file: Optional[UploadFile] = File(None, description="Mặt sau CCCD nếu gửi riêng mặt trước/sau"),
    target_group: Optional[str] = Form(None, description="Nhóm đối tượng (vd: CHILD_UNDER_18, CHILD_OVER_18_STUDYING)"),
    rules_json: Optional[str] = Form(None, description="Danh sách JSON rules động từ bảng dependent_document_rules"),
    applied_threshold: Optional[float] = Form(
        None, 
        description="Ngưỡng tin cậy áp dụng (nếu để trống, service sẽ tự động lấy ngưỡng từ bảng system_configs trong DB)"
    ),
    db: Session = Depends(get_db)
):
    # 1. Kiểm tra định dạng file
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng {file.content_type} không được hỗ trợ. Chỉ nhận JPEG, PNG, WEBP, HEIC, PDF."
        )

    rules = None
    if rules_json:
        try:
            parsed = json.loads(rules_json)
            if isinstance(parsed, list):
                rules = parsed
            elif isinstance(parsed, dict) and "rules" in parsed:
                rules = parsed["rules"]
        except Exception as e:
            logger.warning(f"Không thể parse rules_json: {e}")

    # Nếu Swagger UI gửi 0 hoặc số <= 0, reset về None để tự động lấy từ DB system_configs
    if applied_threshold is not None and applied_threshold <= 0:
        applied_threshold = None

    file_bytes = await file.read()
    files_to_process = [(file_bytes, file.content_type)]


    # 2. Nếu có gửi kèm mặt sau CCCD
    if back_file:
        back_bytes = await back_file.read()
        files_to_process.append((back_bytes, back_file.content_type))

    # 3. Khởi tạo service với SystemConfigRepository kết nối DB
    config_repo = SystemConfigRepository(db)
    ocr_service = DependentOcrService(repo=config_repo)

    # 4. Gọi Gemini OCR bóc dữ liệu, đối chiếu rules & kiểm tra ngưỡng tự động
    result = ocr_service.extract_document(
        files=files_to_process,
        target_group=target_group,
        rules=rules,
        applied_threshold=applied_threshold
    )
    return result