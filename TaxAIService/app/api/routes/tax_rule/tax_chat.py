import uuid
from typing import Optional, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.repositories.tax_rule.tax_chat_repository import TaxChatRepository
from app.repositories.tax_rule.chat_history_repository import ChatHistoryRepository
from app.services.tax_rule.tax_chat_service import TaxChatService

router = APIRouter(prefix="/api/tax-chat", tags=["Tư Vấn Thuế AI"])


class ChatQuestionRequest(BaseModel):
    question: str
    session_id: Optional[uuid.UUID] = None  # Để trống nếu là chat mới, truyền vào nếu là chat tiếp
    tax_year: Optional[int] = None
    user_id: Optional[uuid.UUID] = None     # Định danh người dùng từ BE


class ChatQuestionResponse(BaseModel):
    session_id: Optional[uuid.UUID]
    question: str
    answer: str


class ChatSessionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


@router.post("", response_model=ChatQuestionResponse)
def chat_with_tax_ai(request: ChatQuestionRequest, db: Session = Depends(get_db)):
    """
    API Chat tư vấn thuế có nhớ lịch sử cuộc trò chuyện (Multi-turn Session).
    """
    try:
        tax_repo = TaxChatRepository(db=db)
        history_repo = ChatHistoryRepository(db=db)
        service = TaxChatService(repository=tax_repo, history_repository=history_repo)

        tax_year = request.tax_year if (request.tax_year and request.tax_year > 1900) else None

        result = service.ask(
            question=request.question,
            session_id=request.session_id,
            tax_year=tax_year,
            user_id=request.user_id
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi chat với AI: {str(e)}"
        )


@router.get("/sessions", response_model=List[ChatSessionItemResponse])
def get_user_chat_sessions(
    user_id: Optional[uuid.UUID] = Query(None, description="Lọc theo mã người dùng"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các phiên trò chuyện của người dùng, sắp xếp mới nhất lên đầu.
    """
    history_repo = ChatHistoryRepository(db=db)
    sessions = history_repo.get_user_sessions(user_id=user_id)
    return sessions


@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageItemResponse])
def get_chat_session_messages(session_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Lấy toàn bộ tin nhắn trong một phiên trò chuyện cụ thể.
    """
    history_repo = ChatHistoryRepository(db=db)
    messages = history_repo.get_session_messages(session_id=session_id)
    return messages


@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
def delete_chat_session(session_id: uuid.UUID, db: Session = Depends(get_db)):
    """
    Xóa một phiên trò chuyện (tự động xóa toàn bộ tin nhắn liên quan).
    """
    history_repo = ChatHistoryRepository(db=db)
    success = history_repo.delete_session(session_id=session_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiên trò chuyện với mã {session_id}"
        )
    return {"message": "Đã xóa phiên trò chuyện thành công", "session_id": session_id}
