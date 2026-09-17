import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.repositories import UrlRuleRepository
from app.services import UrlValidationService
from app.schemas import (
    UrlRuleCreateRequest,
    UrlRuleUpdateRequest,
    UrlRuleResponse,
)

router = APIRouter(prefix="/api/url-rules", tags=["URL Validation Rules"])


def get_url_validation_service(db: Session = Depends(get_db)) -> UrlValidationService:
    repo = UrlRuleRepository(db)
    return UrlValidationService(repo)


@router.get(
    "",
    response_model=List[UrlRuleResponse],
    summary="Lấy danh sách các quy tắc kiểm tra URL"
)
def get_rules(
    active_only: bool = False,
    service: UrlValidationService = Depends(get_url_validation_service)
):
    return service.get_all_rules(active_only=active_only)


@router.post(
    "",
    response_model=UrlRuleResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin thêm tên miền nguồn kiểm tra URL"
)
def create_rule(
    payload: UrlRuleCreateRequest,
    service: UrlValidationService = Depends(get_url_validation_service)
):
    return service.create_rule(payload)


@router.get(
    "/{id}",
    response_model=UrlRuleResponse,
    summary="Xem chi tiết một quy tắc URL"
)
def get_rule_by_id(
    id: uuid.UUID,
    service: UrlValidationService = Depends(get_url_validation_service)
):
    rule = service.repo.get_by_id(id)
    if not rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy quy tắc URL yêu cầu."
        )
    return rule


@router.put(
    "/{id}",
    response_model=UrlRuleResponse,
    summary="Admin cập nhật tên miền nguồn kiểm tra URL"
)
def update_rule(
    id: uuid.UUID,
    payload: UrlRuleUpdateRequest,
    service: UrlValidationService = Depends(get_url_validation_service)
):
    updated_rule = service.update_rule(rule_id=id, dto=payload)
    if not updated_rule:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy quy tắc URL để cập nhật."
        )
    return updated_rule


@router.delete(
    "/{id}",
    status_code=status.HTTP_200_OK,
    summary="Admin xóa một quy tắc kiểm tra URL"
)
def delete_rule(
    id: uuid.UUID,
    service: UrlValidationService = Depends(get_url_validation_service)
):
    success = service.delete_rule(rule_id=id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Không tìm thấy quy tắc URL để xóa."
        )
    return {"message": "Xóa quy tắc URL thành công."}
