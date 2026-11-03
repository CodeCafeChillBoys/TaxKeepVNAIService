from app.core import exclude_from_coverage
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.infrastructure.database import get_db
from app.schemas.apiKey.ai_provider_key_schema import AiKeyCreateRequest, AiKeyUpdateRequest, AiKeyResponse
from app.services.apiKey.ai_key_manager import AiKeyManager

router = APIRouter(prefix="/api/ai-keys", tags=["AI Provider Keys (Admin)"])

@exclude_from_coverage
@router.get("", response_model=List[AiKeyResponse], summary="Lấy danh sách các Key AI")
def get_all_keys(db: Session = Depends(get_db)):
    return AiKeyManager.get_all_keys(db)

@exclude_from_coverage
@router.post("", response_model=AiKeyResponse, status_code=status.HTTP_201_CREATED, summary="Admin thêm Key mới")
def create_key(payload: AiKeyCreateRequest, db: Session = Depends(get_db)):
    try:
        return AiKeyManager.create_key(db, payload)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@exclude_from_coverage
@router.put("/{key_id}", response_model=AiKeyResponse, summary="Admin cập nhật Key (bật/tắt, priority)")
def update_key(key_id: uuid.UUID, payload: AiKeyUpdateRequest, db: Session = Depends(get_db)):
    result = AiKeyManager.update_key(db, key_id, payload)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Key này.")
    return result

@exclude_from_coverage
@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Xóa Key")
def delete_key(key_id: uuid.UUID, db: Session = Depends(get_db)):
    success = AiKeyManager.delete_key(db, key_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Không tìm thấy Key để xóa.")
    return None