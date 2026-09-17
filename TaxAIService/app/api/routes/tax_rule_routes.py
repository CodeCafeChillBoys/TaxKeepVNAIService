import uuid
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.core.config import settings
from app.schemas import (
    TaxRuleSetResponse,
    TaxRuleUploadResponse,
    TaxRuleApproveResponse,
    TaxRuleApproveRequest,
    TaxRuleUpdateRequest,
    TaxRuleDetailResponse,
)
from app.repositories.interfaces import ITaxRuleRepository
from app.repositories import TaxRuleRepository, UrlRuleRepository
from app.services.interfaces import ITaxRuleService
from app.services import TaxRuleService, TaxRuleServiceError, UrlValidationService

router = APIRouter(prefix="/api/tax-rules", tags=["Tax Rules Extraction"])


def get_tax_rule_repository(db: Session = Depends(get_db)) -> ITaxRuleRepository:
    """Dependency injection cho ITaxRuleRepository."""
    return TaxRuleRepository(db)


def get_tax_rule_service(
    repo: ITaxRuleRepository = Depends(get_tax_rule_repository)
) -> ITaxRuleService:
    """Dependency injection cho ITaxRuleService."""
    return TaxRuleService(repo)


def get_url_validation_service(db: Session = Depends(get_db)) -> UrlValidationService:
    """Dependency injection cho UrlValidationService."""
    return UrlValidationService(UrlRuleRepository(db))



@router.post(
    "/documents/upload",
    response_model=TaxRuleUploadResponse,
    summary="Upload văn bản PDF luật thuế và AI trích xuất Tax Rules"
)
async def upload_and_extract_tax_rules(
    file: Optional[UploadFile] = File(None),
    taxYear: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    sourceUrl: Optional[str] = Form(None),
    adminId: Optional[str] = Form(None),
    service: ITaxRuleService = Depends(get_tax_rule_service),
    url_service: UrlValidationService = Depends(get_url_validation_service)
):
    # 1. Kiểm tra trường file bắt buộc
    if file is None or not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "The file field is required."}
        )

    # 2. Kiểm tra định dạng PDF
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "The file must be a PDF."}
        )

    # 3. Kiểm tra trường taxYear bắt buộc
    if taxYear is None or str(taxYear).strip() == "":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"TaxYear": "The TaxYear field is required."}
        )

    # 4. Kiểm tra taxYear hợp lệ (phải là số nguyên, 4 chữ số)
    try:
        tax_year_int = int(str(taxYear).strip())
        if tax_year_int < 1900 or tax_year_int > 2100:
            raise ValueError()
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Tax year must be a valid year."}
        )

    # 5. Kiểm tra SourceUrl nếu có truyền vào qua Dynamic URL Validation Rules
    if sourceUrl and sourceUrl.strip():
        is_valid, err_msg, _ = url_service.validate_url(sourceUrl.strip())
        if not is_valid:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"SourceUrl": err_msg or "The SourceUrl is not allowed by active URL validation rules."}
            )

    # 6. Kiểm tra adminId hợp lệ nếu có truyền vào
    admin_id_uuid: Optional[uuid.UUID] = None
    if adminId and str(adminId).strip():
        try:
            admin_id_uuid = uuid.UUID(str(adminId).strip())
        except (ValueError, TypeError):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "adminId must be a valid UUID."}
            )

    # 7. Kiểm tra kích thước file (tối đa 20 MB)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"The file size must not exceed {settings.MAX_FILE_SIZE_MB} MB."}
        )

    # 8. Gọi TaxRuleService để xử lý toàn bộ quy trình nghiệp vụ
    try:
        result = await service.process_tax_rule_document(
            filename=file.filename,
            file_bytes=file_bytes,
            tax_year=tax_year_int,
            name=name,
            source_url=sourceUrl,
            admin_id=admin_id_uuid
        )
        return JSONResponse(status_code=status.HTTP_200_OK, content=result)
    except TaxRuleServiceError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"message": e.message}
        )


@router.get(
    "",
    response_model=List[TaxRuleSetResponse],
    summary="Lấy danh sách tất cả các bộ quy tắc thuế đã tạo/bóc tách"
)
def get_all_tax_rule_sets(
    service: ITaxRuleService = Depends(get_tax_rule_service)
):
    return service.get_all_rule_sets()


@router.get(
    "/year/{taxYear}",
    response_model=TaxRuleDetailResponse,
    summary="Lấy toàn bộ thông tin AI đã bóc tách theo năm tính thuế (vd: 2026)"
)
def get_tax_rule_set_by_year(
    taxYear: int,
    service: ITaxRuleService = Depends(get_tax_rule_service)
):
    return service.get_tax_rule_set_detail_by_year(tax_year=taxYear)


@router.get(
    "/{id}",
    response_model=TaxRuleDetailResponse,
    summary="Review chi tiết toàn bộ nội dung của Tax Rule Set (Rules & Dependent Rules) theo UUID"
)
def get_tax_rule_set(
    id: uuid.UUID,
    service: ITaxRuleService = Depends(get_tax_rule_service)
):
    return service.get_tax_rule_set_detail(rule_set_id=id)


@router.put(
    "/{id}",
    response_model=TaxRuleDetailResponse,
    summary="Chỉnh sửa toàn bộ nội dung Tax Rule Set, Tax Rules và cập nhật taxYear"
)
def update_tax_rule_set(
    id: uuid.UUID,
    payload: TaxRuleUpdateRequest,
    service: ITaxRuleService = Depends(get_tax_rule_service)
):
    try:
        return service.update_tax_rule_set(rule_set_id=id, payload=payload)
    except TaxRuleServiceError as e:
        return JSONResponse(
            status_code=e.status_code,
            content={"message": e.message}
        )


@router.post(
    "/{id}/approve",
    response_model=TaxRuleApproveResponse,
    summary="Phê duyệt Tax Rule Set sang Active"
)
def approve_tax_rule_set(
    id: uuid.UUID,
    payload: TaxRuleApproveRequest,
    service: ITaxRuleService = Depends(get_tax_rule_service)
):
    return service.approve_tax_rule_set(
        rule_set_id=id,
        admin_id=payload.admin_id
    )

