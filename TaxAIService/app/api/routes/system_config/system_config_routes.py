import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.repositories.system_config.system_config_repository import SystemConfigRepository
from app.services.system_config.system_config_service import SystemConfigService
from app.schemas.system_config.system_config_schema import (
    SystemConfigCreateRequest,
    SystemConfigUpdateRequest,
    SystemConfigResponse,
)

router = APIRouter(prefix="/api/system-configs", tags=["System Configs (Admin)"])


def get_config_service(db: Session = Depends(get_db)) -> SystemConfigService:
    repo = SystemConfigRepository(db)
    return SystemConfigService(repo)


@router.get(
    "",
    response_model=List[SystemConfigResponse],
    summary="Lấy danh sách tất cả các cấu hình hệ thống"
)
def get_all_configs(
    active_only: bool = Query(False, description="Chỉ lấy các cấu hình đang active và chưa xóa mềm"),
    service: SystemConfigService = Depends(get_config_service)
):
    return service.get_all_configs(active_only=active_only)


@router.post(
    "",
    response_model=SystemConfigResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin tạo cấu hình / ngưỡng mới (hoàn toàn động)"
)
def create_config(
    payload: SystemConfigCreateRequest,
    service: SystemConfigService = Depends(get_config_service)
):
    try:
        return service.create_config(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.get(
    "/threshold/test-resolve",
    summary="[TEST] Kiểm tra xem AI sẽ áp dụng ngưỡng nào cho danh mục này"
)
def test_threshold_resolve(
    category_code: Optional[str] = Query(None, example="MEDICAL_EXPENSE_INVOICE", description="Mã danh mục cần test"),
    service: SystemConfigService = Depends(get_config_service)
):
    """
    Giúp Admin / Tester kiểm tra trực tiếp logic 3 tầng:
    - Nếu có THRESHOLD_{category_code} -> Dùng ngưỡng riêng
    - Nếu không -> Dùng AI_CONFIDENCE_THRESHOLD
    - Nếu không -> Dùng 0.80
    """
    return service.test_resolve_threshold(category_code=category_code)


@router.get(
    "/{key}",
    response_model=SystemConfigResponse,
    summary="Xem chi tiết một cấu hình theo key"
)
def get_config_by_key(
    key: str,
    service: SystemConfigService = Depends(get_config_service)
):
    config = service.get_config_by_key(key)
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cấu hình với key '{key}'."
        )
    return config


@router.put(
    "/{key}",
    response_model=SystemConfigResponse,
    summary="Admin cập nhật giá trị hoặc trạng thái cấu hình"
)
def update_config(
    key: str,
    payload: SystemConfigUpdateRequest,
    service: SystemConfigService = Depends(get_config_service)
):
    try:
        updated = service.update_config(key=key, dto=payload)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy cấu hình '{key}' để cập nhật."
            )
        return updated
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.delete(
    "/{key}",
    status_code=status.HTTP_200_OK,
    summary="Admin xóa mềm một cấu hình (Soft Delete)"
)
def delete_config(
    key: str,
    admin_id: Optional[uuid.UUID] = Query(None, description="Mã Admin thực hiện xóa"),
    service: SystemConfigService = Depends(get_config_service)
):
    success = service.delete_config(key=key, admin_id=admin_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy cấu hình '{key}' hoặc cấu hình đã bị xóa trước đó."
        )
    return {"message": f"Đã xóa mềm cấu hình '{key.upper()}' thành công."}


@router.patch(
    "/{key}/restore",
    response_model=SystemConfigResponse,
    summary="Admin khôi phục cấu hình đã bị xóa mềm"
)
def restore_config(
    key: str,
    admin_id: Optional[uuid.UUID] = Query(None, description="Mã Admin thực hiện khôi phục"),
    service: SystemConfigService = Depends(get_config_service)
):
    try:
        restored = service.restore_config(key=key, admin_id=admin_id)
        if not restored:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Cấu hình '{key}' không tồn tại trong hệ thống."
            )
        return restored
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))