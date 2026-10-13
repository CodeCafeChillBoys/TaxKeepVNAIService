import uuid
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
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


class ChatQuestionResponse(BaseModel):
    session_id: uuid.UUID
    question: str
    answer: str


@router.post("", response_model=ChatQuestionResponse)
def chat_with_tax_ai(request: ChatQuestionRequest, db: Session = Depends(get_db)):
    """
    API Chat tư vấn thuế có nhớ lịch sử cuộc trò chuyện (Multi-turn Session).
    """
    try:
        tax_repo = TaxChatRepository(db=db)
        history_repo = ChatHistoryRepository(db=db)
        service = TaxChatService(repository=tax_repo, history_repository=history_repo)

        result = service.ask(
            question=request.question,
            session_id=request.session_id,
            tax_year=request.tax_year
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi chat với AI: {str(e)}"
        )