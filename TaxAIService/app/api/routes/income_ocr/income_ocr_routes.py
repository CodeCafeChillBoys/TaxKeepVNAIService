from app.core import exclude_from_coverage
# app/api/routes/income_ocr/income_ocr_routes.py
import logging
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Depends, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.repositories.system_config.system_config_repository import SystemConfigRepository
from app.repositories.prompt_template.prompt_template_repository import PromptTemplateRepository
from app.services.prompt_template.prompt_template_service import PromptTemplateService
from app.services.income_ocr.income_ocr_service import IncomeOcrService
from app.schemas.income_ocr.income_ocr_schema import IncomeOcrResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/incomes/ocr", tags=["Income / Payslip OCR"])

ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"
}


@exclude_from_coverage
@router.post(
    "/extract",
    response_model=IncomeOcrResponse,
    response_model_by_alias=True,
    summary="Bóc tách OCR phiếu lương / báo cáo thu nhập cá nhân"
)
async def extract_income_payslip(
    file: UploadFile = File(..., description="Ảnh chụp phiếu lương (JPEG, PNG) hoặc file PDF bảng lương"),
    target_month: Optional[int] = Form(None, description="Tháng kê khai dự kiến (1 - 12)"),
    target_year: Optional[int] = Form(None, description="Năm kê khai dự kiến (VD: 2024, 2025, 2026)"),
    applied_threshold: Optional[float] = Form(
        None,
        description="Ngưỡng tin cậy áp dụng (nếu bỏ trống sẽ tự lấy từ cấu hình database system_configs)"
    ),
    db: Session = Depends(get_db)
):
    """
    Endpoint nhận file phiếu lương, gọi Gemini 2.5 Flash Vision để bóc tách:
    - organization_name
    - tax_id_number
    - month & year
    - total_taxable_income
    - insurance_deducted
    - tax_already_deducted
    """
    # 1. Kiểm tra định dạng tệp tin
    if file.content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng {file.content_type} không được hỗ trợ. Chỉ nhận JPEG, PNG, WEBP, HEIC, PDF."
        )

    # 2. Đọc nội dung file
    file_bytes = await file.read()

    # 3. Khởi tạo service và thực thi bóc tách
    config_repo = SystemConfigRepository(db)
    prompt_repo = PromptTemplateRepository(db)
    prompt_service = PromptTemplateService(repository=prompt_repo)
    service = IncomeOcrService(repo=config_repo, prompt_service=prompt_service)

    result = service.extract_payslip(
        file_bytes=file_bytes,
        mime_type=file.content_type,
        target_month=target_month,
        target_year=target_year,
        applied_threshold=applied_threshold
    )

    return result