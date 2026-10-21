import uuid
from typing import List, Optional
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage


class ChatHistoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_session(
        self, 
        session_id: Optional[uuid.UUID] = None, 
        first_question: str = "", 
        user_id: Optional[uuid.UUID] = None
    ) -> ChatSession:
        """Nếu truyền session_id thì tìm trong DB; nếu không thì tạo phiên mới."""
        if session_id:
            session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                # Cập nhật user_id nếu trước đó chưa có mà bây giờ được cung cấp
                if user_id and not session.user_id:
                    session.user_id = user_id
                    self.db.commit()
                return session

        # Tự sinh tiêu đề ngắn từ câu hỏi đầu tiên
        title = (first_question[:50] + "...") if len(first_question) > 50 else (first_question or "Cuộc trò chuyện mới")
        new_session = ChatSession(id=session_id or uuid.uuid4(), user_id=user_id, title=title)
        self.db.add(new_session)
        self.db.commit()
        self.db.refresh(new_session)
        return new_session

    def save_message(self, session_id: uuid.UUID, role: str, content: str) -> ChatMessage:
        """Lưu một tin nhắn mới (user hoặc assistant) vào DB và cập nhật updated_at của session."""
        message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            role=role,
            content=content
        )
        self.db.add(message)

        # Cập nhật updated_at cho session
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            session.updated_at = datetime.now(timezone.utc)

        self.db.commit()
        self.db.refresh(message)
        return message

    def get_recent_messages(self, session_id: uuid.UUID, limit: int = 6) -> List[ChatMessage]:
        """
        Lấy tối đa N tin nhắn gần nhất của phiên này để làm ngữ cảnh.
        Sắp xếp tăng dần theo thời gian để gửi cho AI đọc theo đúng trình tự.
        """
        messages = (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
            .all()
        )
        messages.reverse()
        return messages

    def get_user_sessions(self, user_id: Optional[uuid.UUID] = None, limit: int = 50) -> List[ChatSession]:
        """Lấy danh sách các phiên chat của user (sắp xếp mới nhất lên đầu)."""
        query = self.db.query(ChatSession)
        if user_id:
            query = query.filter(ChatSession.user_id == user_id)
        return query.order_by(ChatSession.updated_at.desc()).limit(limit).all()

    def get_session_messages(self, session_id: uuid.UUID) -> List[ChatMessage]:
        """Lấy toàn bộ tin nhắn trong một phiên trò chuyện theo thứ tự thời gian."""
        return (
            self.db.query(ChatMessage)
            .filter(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
            .all()
        )

    def delete_session(self, session_id: uuid.UUID) -> bool:
        """Xóa một phiên trò chuyện cùng toàn bộ tin nhắn thuộc phiên đó."""
        session = self.db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if session:
            self.db.delete(session)
            self.db.commit()
            return True
        return False
