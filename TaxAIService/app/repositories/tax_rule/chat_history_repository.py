import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage


class ChatHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(self, session_id: Optional[uuid.UUID] = None, first_question: str = "") -> ChatSession:
        """Nếu truyền session_id thì tìm trong DB; nếu không thì tạo phiên mới."""
        if session_id:
            session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                return session

        # Tự sinh tiêu đề ngắn từ câu hỏi đầu tiên
        title = (first_question[:50] + "...") if len(first_question) > 50 else (first_question or "Cuộc trò chuyện mới")
        new_session = ChatSession(id=uuid.uuid4(), title=title)
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        return new_session

    def save_message(self, session_id: uuid.UUID, role: str, content: str) -> ChatMessage:
        """Lưu một tin nhắn mới (user hoặc assistant) vào DB."""
        message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role,
            content=content
        )
        self.db.add(message)
        self.db.commit()
        self.db.refresh(message)
        return message

    def get_recent_messages(self, session_id: uuid.UUID, limit: int = 6) -> List[ChatMessage]:
        """
        Lấy tối đa N tin nhắn gần nhất của phiên này để làm ngữ cảnh.
        Sắp xếp tăng dần theo thời gian để gửi cho AI đọc theo đúng trình tự.
        """
        # Lấy N tin mới nhất (DESC) rồi đảo ngược lại (ASC)
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()
        return messages