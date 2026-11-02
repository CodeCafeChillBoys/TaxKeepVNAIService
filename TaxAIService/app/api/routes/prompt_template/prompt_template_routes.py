from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.repositories.prompt_template.prompt_template_repository import PromptTemplateRepository
from app.services.prompt_template.prompt_template_service import PromptTemplateService
from app.schemas.prompt_template.prompt_template_schema import (
    PromptTemplateResponse,
    PromptTemplateCreateRequest,
    PromptTemplateUpdateRequest,
    PromptTestRenderRequest,
    PromptTestRenderResponse
)

router = APIRouter(prefix="/api/prompt-templates", tags=["AI Prompt Templates (Admin)"])


def get_prompt_service(db: Session = Depends(get_db)) -> PromptTemplateService:
    repo = PromptTemplateRepository(db)
    return PromptTemplateService(repo)


@router.get(
    "",
    response_model=List[PromptTemplateResponse],
    summary="Lấy danh sách tất cả các system prompt trong hệ thống"
)
def get_all_prompts(
    active_only: bool = Query(False, description="Chỉ lấy các prompt đang kích hoạt"),
    service: PromptTemplateService = Depends(get_prompt_service)
):
    return service.get_all(active_only=active_only)


@router.get(
    "/{prompt_key}",
    response_model=PromptTemplateResponse,
    summary="Lấy chi tiết một System Prompt theo mã khóa"
)
def get_prompt_by_key(
    prompt_key: str,
    service: PromptTemplateService = Depends(get_prompt_service)
):
    record = service.get_by_key(prompt_key)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy prompt key: {prompt_key}"
        )
    return record


@router.post(
    "",
    response_model=PromptTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Admin tạo một System Prompt mới"
)
def create_prompt(
    payload: PromptTemplateCreateRequest,
    service: PromptTemplateService = Depends(get_prompt_service)
):
    try:
        return service.create(payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


@router.put(
    "/{prompt_key}",
    response_model=PromptTemplateResponse,
    summary="Admin cập nhật nội dung System Prompt (Tự tăng Version và xóa Cache)"
)
def update_prompt(
    prompt_key: str,
    payload: PromptTemplateUpdateRequest,
    service: PromptTemplateService = Depends(get_prompt_service)
):
    try:
        return service.update(prompt_key, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete(
    "/{prompt_key}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Xóa một System Prompt khỏi hệ thống"
)
def delete_prompt(
    prompt_key: str,
    service: PromptTemplateService = Depends(get_prompt_service)
):
    success = service.delete(prompt_key)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy prompt key: {prompt_key}"
        )
    return None


@router.post(
    "/test-render",
    response_model=PromptTestRenderResponse,
    summary="[TEST] Thử nghiệm render System Prompt với các biến tham số giả lập"
)
def test_render_prompt(
    payload: PromptTestRenderRequest,
    service: PromptTemplateService = Depends(get_prompt_service)
):
    record = service.get_by_key(payload.prompt_key)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy prompt key: {payload.prompt_key}"
        )

    rendered = service.get_rendered_prompt(
        prompt_key=record.prompt_key,
        default_template=record.system_prompt,
        params=payload.params
    )

    return PromptTestRenderResponse(
        prompt_key=record.prompt_key,
        rendered_prompt=rendered,
        variables_used=list(payload.params.keys())
    )
