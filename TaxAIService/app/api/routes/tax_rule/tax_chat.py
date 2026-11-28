from app.core import exclude_from_coverage
import uuid
import json
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field, field_validator
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.repositories.tax_rule.tax_chat_repository import TaxChatRepository
from app.repositories.tax_rule.chat_history_repository import ChatHistoryRepository
from app.repositories.prompt_template.prompt_template_repository import PromptTemplateRepository
from app.services.prompt_template.prompt_template_service import PromptTemplateService
from app.services.tax_rule.tax_chat_service import TaxChatService
from app.services.tax_rule.tax_calculator import TaxCalculator

router = APIRouter(prefix="/api/tax-chat", tags=["Tư Vấn Thuế AI"])


@exclude_from_coverage
class ChatQuestionRequest(BaseModel):
    question: str = Field(..., description="Nội dung câu hỏi của người dùng")
    session_id: Optional[uuid.UUID] = None  # Để trống nếu là chat mới, truyền vào nếu là chat tiếp
    tax_year: Optional[int] = None
    user_id: Optional[uuid.UUID] = None     # Định danh người dùng từ BE

    @field_validator("question")
    @classmethod
    def validate_question(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Vui lòng nhập câu hỏi.")
        return v.strip()


@exclude_from_coverage
class ChatQuestionResponse(BaseModel):
    session_id: Optional[uuid.UUID]
    question: str
    answer: str
    cached: Optional[bool] = False


@exclude_from_coverage
class ChatSessionItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: Optional[uuid.UUID] = None
    title: str
    created_at: datetime
    updated_at: datetime


@exclude_from_coverage
class ChatMessageItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    created_at: datetime


@exclude_from_coverage
class UpdateSessionTitleRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255, description="Tiêu đề mới cho phiên trò chuyện")
    user_id: Optional[uuid.UUID] = Field(None, description="Mã người dùng để kiểm tra quyền sở hữu")

    @field_validator("title")
    @classmethod
    def validate_title(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Tiêu đề không được để trống.")
        return v.strip()


@exclude_from_coverage
class TaxCalculationRequest(BaseModel):
    monthly_salary: float = Field(..., gt=0, description="Mức lương gross hàng tháng (VND)")
    dependents_count: int = Field(0, ge=0, description="Số người phụ thuộc")
    insurance_amount: Optional[float] = Field(None, ge=0, description="Tiền bảo hiểm bắt buộc tự đóng (nếu không truyền sẽ tự tính 10.5% có áp trần)")
    tax_year: Optional[int] = Field(2026, description="Năm tính thuế")
    ot_salary: float = Field(0.0, ge=0, description="Tiền làm thêm giờ (OT)")
    ot_exempt_amount: float = Field(0.0, ge=0, description="Phần tiền OT được miễn thuế")
    other_deductions: float = Field(0.0, ge=0, description="Các khoản giảm trừ khác (học phí, viện phí...)")


@exclude_from_coverage
class TaxCalculationResponse(BaseModel):
    tax_year: int
    monthly_salary: float
    ot_salary: float
    ot_exempt_amount: float
    total_income: float
    insurance_deduction: float
    personal_deduction: float
    dependents_count: int
    dependents_deduction: float
    other_deductions: float
    total_deductions: float
    assessable_income: float
    bracket_details: List[Dict[str, Any]]
    total_tax: float
    net_income: float


@exclude_from_coverage
class MessageFeedbackRequest(BaseModel):
    rating: str = Field(..., description="Đánh giá: 'like' hoặc 'dislike'")
    feedback_text: Optional[str] = Field(None, max_length=500, description="Nội dung góp ý chi tiết")
    user_id: Optional[uuid.UUID] = Field(None, description="Mã người dùng thực hiện đánh giá")

    @field_validator("rating")
    @classmethod
    def validate_rating(cls, v: str) -> str:
        clean = (v or "").strip().lower()
        if clean not in ["like", "dislike"]:
            raise ValueError("Đánh giá chỉ chấp nhận 'like' hoặc 'dislike'.")
        return clean


@exclude_from_coverage
@router.post("", response_model=ChatQuestionResponse)
def chat_with_tax_ai(request: ChatQuestionRequest, db: Session = Depends(get_db)):
    """
    API Chat tư vấn thuế có nhớ lịch sử cuộc trò chuyện (Multi-turn Session).
    """
    try:
        tax_repo = TaxChatRepository(db=db)
        history_repo = ChatHistoryRepository(db=db)
        prompt_repo = PromptTemplateRepository(db=db)
        prompt_service = PromptTemplateService(repository=prompt_repo)
        service = TaxChatService(
            repository=tax_repo, 
            history_repository=history_repo,
            prompt_service=prompt_service
        )

        tax_year = request.tax_year if (request.tax_year and request.tax_year > 1900) else None

        result = service.ask(
            question=request.question,
            session_id=request.session_id,
            tax_year=tax_year,
            user_id=request.user_id
        )
        return result
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi chat với AI: {str(e)}"
        )


@exclude_from_coverage
@router.post("/stream")
def chat_with_tax_ai_stream(request: ChatQuestionRequest, db: Session = Depends(get_db)):
    """
    API Chat tư vấn thuế thời gian thực qua Server-Sent Events (SSE Streaming).
    Phản hồi từng từ (chunk) theo thời gian thực giúp giảm độ trễ trải nghiệm (dưới 500ms).
    """
    try:
        tax_repo = TaxChatRepository(db=db)
        history_repo = ChatHistoryRepository(db=db)
        prompt_repo = PromptTemplateRepository(db=db)
        prompt_service = PromptTemplateService(repository=prompt_repo)
        service = TaxChatService(
            repository=tax_repo, 
            history_repository=history_repo,
            prompt_service=prompt_service
        )

        tax_year = request.tax_year if (request.tax_year and request.tax_year > 1900) else None

        active_session = history_repo.get_or_create_session(
            session_id=request.session_id,
            first_question=request.question,
            user_id=request.user_id
        )

        def event_stream():
            # 1. Phát sự kiện mở đầu với session_id
            yield f"data: {json.dumps({'event': 'start', 'session_id': str(active_session.id)}, ensure_ascii=False)}\n\n"
            
            # 2. Phát từng chunk văn bản
            stream_gen = service.ask_stream(
                question=request.question,
                session_id=active_session.id,
                tax_year=tax_year,
                user_id=request.user_id
            )
            for chunk in stream_gen:
                yield f"data: {json.dumps({'event': 'chunk', 'text': chunk}, ensure_ascii=False)}\n\n"

            # 3. Phát sự kiện hoàn tất
            yield f"data: {json.dumps({'event': 'done', 'session_id': str(active_session.id)}, ensure_ascii=False)}\n\n"

        return StreamingResponse(
            event_stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no"
            }
        )
    except HTTPException:
        raise
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi stream chat với AI: {str(e)}"
        )


@exclude_from_coverage
@router.get("/sessions", response_model=List[ChatSessionItemResponse])
def get_user_chat_sessions(
    user_id: Optional[uuid.UUID] = Query(None, description="Lọc theo mã người dùng"),
    limit: int = Query(50, ge=1, le=100, description="Số lượng phiên tối đa"),
    skip: int = Query(0, ge=0, description="Vị trí bắt đầu (phân trang)"),
    db: Session = Depends(get_db)
):
    """
    Lấy danh sách các phiên trò chuyện của người dùng, sắp xếp mới nhất lên đầu (có phân trang).
    Bảo mật: Nếu không cung cấp user_id sẽ trả về danh sách rỗng để tránh rò rỉ dữ liệu.
    """
    if not user_id:
        return []
    history_repo = ChatHistoryRepository(db=db)
    sessions = history_repo.get_user_sessions(user_id=user_id, limit=limit, skip=skip)
    return sessions


@exclude_from_coverage
@router.get("/sessions/{session_id}/messages", response_model=List[ChatMessageItemResponse])
def get_chat_session_messages(
    session_id: uuid.UUID, 
    user_id: Optional[uuid.UUID] = Query(None, description="Mã người dùng để xác thực quyền sở hữu"),
    db: Session = Depends(get_db)
):
    """
    Lấy toàn bộ tin nhắn trong một phiên trò chuyện cụ thể (có kiểm tra quyền sở hữu IDOR).
    """
    history_repo = ChatHistoryRepository(db=db)
    session = history_repo.get_session(session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiên trò chuyện với mã {session_id}"
        )
    if user_id and session.user_id and session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền truy cập phiên trò chuyện này."
        )

    messages = history_repo.get_session_messages(session_id=session_id)
    return messages


@exclude_from_coverage
@router.patch("/sessions/{session_id}", response_model=ChatSessionItemResponse)
def update_chat_session_title(
    session_id: uuid.UUID,
    payload: UpdateSessionTitleRequest,
    db: Session = Depends(get_db)
):
    """
    Đổi tên tiêu đề của phiên trò chuyện.
    """
    history_repo = ChatHistoryRepository(db=db)
    session = history_repo.get_session(session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiên trò chuyện với mã {session_id}"
        )
    if payload.user_id and session.user_id and session.user_id != payload.user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền sửa phiên trò chuyện này."
        )

    updated = history_repo.update_session_title(session_id=session_id, title=payload.title)
    return updated


@exclude_from_coverage
@router.delete("/sessions/{session_id}", status_code=status.HTTP_200_OK)
def delete_chat_session(
    session_id: uuid.UUID, 
    user_id: Optional[uuid.UUID] = Query(None, description="Mã người dùng để xác thực quyền sở hữu"),
    db: Session = Depends(get_db)
):
    """
    Xóa một phiên trò chuyện (có kiểm tra quyền sở hữu IDOR, tự động xóa toàn bộ tin nhắn liên quan).
    """
    history_repo = ChatHistoryRepository(db=db)
    session = history_repo.get_session(session_id=session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy phiên trò chuyện với mã {session_id}"
        )
    if user_id and session.user_id and session.user_id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bạn không có quyền xóa phiên trò chuyện này."
        )

    success = history_repo.delete_session(session_id=session_id)
    return {"message": "Đã xóa phiên trò chuyện thành công", "session_id": session_id}


@exclude_from_coverage
@router.post("/calculate-tax", response_model=TaxCalculationResponse)
def calculate_personal_income_tax(request: TaxCalculationRequest):
    """
    Công cụ tính thuế TNCN chính xác 100% bằng thuật toán Python (không qua suy đoán của LLM).
    Hỗ trợ kỳ tính thuế 2026 (luật mới) và các năm trước đó.
    """
    try:
        result = TaxCalculator.calculate_pit(
            monthly_salary=request.monthly_salary,
            dependents_count=request.dependents_count,
            insurance_amount=request.insurance_amount,
            tax_year=request.tax_year or 2026,
            ot_salary=request.ot_salary,
            ot_exempt_amount=request.ot_exempt_amount,
            other_deductions=request.other_deductions
        )
        return result
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Lỗi tính thuế: {str(e)}"
        )


@exclude_from_coverage
@router.post("/messages/{message_id}/feedback")
def submit_message_feedback(
    message_id: uuid.UUID,
    payload: MessageFeedbackRequest,
    db: Session = Depends(get_db)
):
    """
    Gửi đánh giá hữu ích (like / dislike) và góp ý cho một câu trả lời của AI.
    """
    from app.models.chat_message import ChatMessage
    msg = db.query(ChatMessage).filter(ChatMessage.id == message_id).first()
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Không tìm thấy tin nhắn với mã {message_id}"
        )

    return {
        "message": "Cảm ơn bạn đã gửi đánh giá cho câu trả lời của AI!",
        "message_id": message_id,
        "rating": payload.rating,
        "feedback_text": payload.feedback_text
    }
