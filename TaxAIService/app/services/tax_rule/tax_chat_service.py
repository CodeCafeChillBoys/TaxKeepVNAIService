import os
import uuid
import logging
import hashlib
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from app.core.config import settings
from app.models.tax_rule import TaxRule
from app.models.chat_session import ChatSession
from app.models.chat_message import ChatMessage
from app.repositories.tax_rule.tax_chat_repository import TaxChatRepository
from app.repositories.tax_rule.chat_history_repository import ChatHistoryRepository
from app.services.prompt_template.prompt_template_service import PromptTemplateService
from app.prompts.tax_rule.tax_chat_prompt import DEFAULT_TAX_CHAT_SYSTEM_PROMPT
from app.services.apiKey.ai_key_manager import AiKeyManager
from app.infrastructure.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class TaxChatService:
    CACHE_TTL_SECONDS = 86400  # Lưu cache câu hỏi phổ biến trong 24 giờ
    REDIS_CACHE_PREFIX = "ai:tax_chat:faq:"

    def __init__(
        self, 
        repository: TaxChatRepository, 
        history_repository: Optional[ChatHistoryRepository] = None,
        prompt_service: Optional[PromptTemplateService] = None,
        redis_client: Optional[Any] = None
    ):
        self.repository = repository
        self.history_repository = history_repository
        self.prompt_service = prompt_service
        self.redis_client = redis_client if redis_client is not None else get_redis_client()

        self.model = settings.GEMINI_MODEL
        self.client = None
        if settings.GEMINI_API_KEY:
            os.environ.pop("GOOGLE_API_KEY", None)
            os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)

    def _generate_cache_key(
        self, 
        question: str, 
        tax_year: Optional[int] = None, 
        history_messages: Optional[List[Any]] = None
    ) -> Optional[str]:
        """
        Tạo cache key cho câu hỏi độc lập (hoặc câu đầu tiên của phiên).
        Nếu là câu hỏi tiếp nối phụ thuộc ngữ cảnh trước (multi-turn), bỏ qua cache để tránh trả lời lệch context.
        """
        if history_messages and len(history_messages) > 0:
            return None
        normalized_q = " ".join(question.strip().lower().split())
        q_hash = hashlib.sha256(normalized_q.encode("utf-8")).hexdigest()
        year_str = str(tax_year) if tax_year else "current"
        return f"{self.REDIS_CACHE_PREFIX}{year_str}:{q_hash}"

    def _get_from_cache(
        self, 
        question: str, 
        tax_year: Optional[int], 
        history_messages: Optional[List[Any]]
    ) -> Optional[str]:
        if not self.redis_client:
            return None
        cache_key = self._generate_cache_key(question, tax_year, history_messages)
        if not cache_key:
            return None
        try:
            val = self.redis_client.get(cache_key)
            if val:
                logger.info(f"Tax Chat Cache Hit: {cache_key}")
                return val
        except Exception as e:
            logger.warning(f"Lỗi đọc cache Redis: {e}")
        return None

    def _save_to_cache(
        self, 
        question: str, 
        tax_year: Optional[int], 
        history_messages: Optional[List[Any]], 
        answer: str
    ) -> None:
        if not self.redis_client or not answer:
            return
        cache_key = self._generate_cache_key(question, tax_year, history_messages)
        if not cache_key:
            return
        try:
            self.redis_client.setex(cache_key, self.CACHE_TTL_SECONDS, answer)
            logger.info(f"Đã lưu Tax Chat Cache: {cache_key}")
        except Exception as e:
            logger.warning(f"Lỗi ghi cache Redis: {e}")

    def _build_tax_knowledge_from_db(self, tax_year: Optional[int] = None) -> str:
        rules = self.repository.get_active_rules(tax_year=tax_year)
        dep_rules = self.repository.get_dependent_rules()

        if not rules:
            return "Hiện tại cơ sở dữ liệu chưa có quy tắc thuế nào ở trạng thái Active."

        grouped_by_year: Dict[int, List[TaxRule]] = {}
        for r in rules:
            year = r.rule_set.tax_year if r.rule_set else (tax_year or 0)
            if year not in grouped_by_year:
                grouped_by_year[year] = []
            grouped_by_year[year].append(r)

        sorted_years = sorted(grouped_by_year.keys(), reverse=True)
        latest_year = sorted_years[0] if sorted_years else None

        lines = ["=== CƠ SỞ DỮ LIỆU LUẬT THUẾ THEO TỪNG KỲ ÁP DỤNG ==="]

        for year in sorted_years:
            is_latest = (year == latest_year)
            label = f"NĂM {year} (QUY ĐỊNH MỚI NHẤT / HIỆN HÀNH)" if is_latest else f"NĂM {year} (KỲ ÁP DỤNG TRƯỚC ĐÓ)"
            lines.append(f"\n--- {label} ---")
            for r in grouped_by_year[year]:
                rule_info = f"- [{r.rule_code}] {r.rule_name}:"
                if r.value is not None:
                    if r.unit and "%" in r.unit:
                        val_str = f"{r.value * 100:g}" if r.value < 1 else f"{r.value:g}"
                        unit_str = f" {r.unit}"
                        rule_info += f" Mức quy định = {val_str}{unit_str}"
                    else:
                        unit_str = f" {r.unit}" if r.unit else ""
                        val_str = f"{r.value:,.0f}" if r.value == int(r.value) else f"{r.value:,.2f}"
                        rule_info += f" Mức quy định = {val_str}{unit_str}"
                if r.condition:
                    rule_info += f" (Điều kiện: {r.condition})"
                ref_parts = []
                if r.legal_document:
                    ref_parts.append(f"Văn bản: {r.legal_document}")
                if r.article:
                    ref_parts.append(r.article)
                if r.clause:
                    ref_parts.append(r.clause)
                if ref_parts:
                    rule_info += f" | Căn cứ: {', '.join(ref_parts)}"
                lines.append(rule_info)

        if dep_rules:
            lines.append("\n=== QUY ĐỊNH CHI TIẾT VỀ ĐIỀU KIỆN NGƯỜI PHỤ THUỘC ===")
            for d in dep_rules:
                dep_info = f"- Đối tượng: {d.name} ({d.dependent_type})"
                if d.max_age:
                    dep_info += f", Độ tuổi tối đa: {d.max_age}"
                if d.max_monthly_income:
                    dep_info += f", Thu nhập tối đa: {d.max_monthly_income:,.0f} VND/tháng"
                if d.conditions:
                    dep_info += f", Điều kiện khác: {d.conditions}"
                lines.append(dep_info)

        return "\n".join(lines)

    def _prepare_chat_context(
        self,
        question: str,
        session_id: Optional[uuid.UUID] = None,
        tax_year: Optional[int] = None,
        user_id: Optional[uuid.UUID] = None
    ):
        clean_question = question.strip() if question else ""
        if not clean_question:
            raise ValueError("Vui lòng nhập câu hỏi.")

        # 1. Quản lý phiên hội thoại & Lấy lịch sử chat cũ
        active_session = None
        history_messages = []
        if self.history_repository:
            active_session = self.history_repository.get_or_create_session(
                session_id=session_id, 
                first_question=clean_question,
                user_id=user_id
            )
            # Lấy 6 tin nhắn trước đó (các lượt chat đã hoàn thành trước đó)
            history_messages = self.history_repository.get_recent_messages(
                session_id=active_session.id, 
                limit=6
            )

        # 2. Lấy dữ liệu luật từ DB
        knowledge_base = self._build_tax_knowledge_from_db(tax_year=tax_year)
        tax_year_label = f"NĂM {tax_year}" if tax_year else "QUY ĐỊNH HIỆN HÀNH MỚI NHẤT"

        # 3. Dynamic System Prompt (Lấy từ DB thông qua PromptTemplateService hoặc Fallback code)
        if self.prompt_service:
            system_instruction = self.prompt_service.get_rendered_prompt(
                prompt_key="PROMPT_TAX_CHAT_ADVISORY",
                default_template=DEFAULT_TAX_CHAT_SYSTEM_PROMPT,
                params={
                    "tax_year_label": tax_year_label,
                    "knowledge_base": knowledge_base
                }
            )
        else:
            system_instruction = DEFAULT_TAX_CHAT_SYSTEM_PROMPT.replace(
                "{tax_year_label}", tax_year_label
            ).replace(
                "{knowledge_base}", knowledge_base
            )

        # 4. Tạo mảng nội dung đa lượt (Multi-turn Contents) cho Gemini
        contents = []

        # 4.1. Đẩy các lượt chat cũ vào trước
        for msg in history_messages:
            role = "user" if msg.role == "user" else "model"
            contents.append(
                types.Content(
                    role=role, 
                    parts=[types.Part.from_text(text=msg.content)]
                )
            )

        # 4.2. Đẩy câu hỏi mới nhất hiện tại (thuần túy câu hỏi, không nhồi kiến thức vào user turn)
        contents.append(
            types.Content(
                role="user", 
                parts=[types.Part.from_text(text=clean_question)]
            )
        )

        return clean_question, active_session, system_instruction, contents, history_messages

    def ask(
        self, 
        question: str, 
        session_id: Optional[uuid.UUID] = None, 
        tax_year: Optional[int] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        clean_question, active_session, system_instruction, contents, history_messages = self._prepare_chat_context(
            question=question,
            session_id=session_id,
            tax_year=tax_year,
            user_id=user_id
        )

        # 4.3. Kiểm tra Redis Cache: nếu câu hỏi đã từng được trả lời trước đó thì trả về ngay lập tức (10ms)
        cached_answer = self._get_from_cache(clean_question, tax_year, history_messages)
        if cached_answer:
            if self.history_repository and active_session:
                self.history_repository.save_message(
                    session_id=active_session.id, 
                    role="user", 
                    content=clean_question
                )
                self.history_repository.save_message(
                    session_id=active_session.id, 
                    role="assistant", 
                    content=cached_answer
                )
            return {
                "session_id": active_session.id if active_session else None,
                "question": clean_question,
                "answer": cached_answer,
                "cached": True
            }

        # 5. Gọi Gemini API với System Instruction động (Hỗ trợ failover xoay vòng key DB & fallback .env)
        def _call_gemini(client, model):
            return client.models.generate_content(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(api_version="v1beta"),
                    system_instruction=system_instruction,
                    temperature=0.1
                )
            )

        db_session = self.repository.db if self.repository and hasattr(self.repository, "db") else None
        response = AiKeyManager.execute_with_failover(db_session, _call_gemini, default_client=self.client)
        ai_answer = (response.text or "").strip()

        # Lưu vào cache để câu hỏi tiếp theo ở bất kỳ phiên nào cũng được trả về ngay lập tức
        self._save_to_cache(clean_question, tax_year, history_messages, ai_answer)

        # 6. Lưu câu hỏi của user và câu trả lời của AI vào DB một cách an toàn sau khi AI sinh thành công
        if self.history_repository and active_session:
            self.history_repository.save_message(
                session_id=active_session.id, 
                role="user", 
                content=clean_question
            )
            self.history_repository.save_message(
                session_id=active_session.id, 
                role="assistant", 
                content=ai_answer
            )

        return {
            "session_id": active_session.id if active_session else None,
            "question": clean_question,
            "answer": ai_answer,
            "cached": False
        }

    def ask_stream(
        self,
        question: str,
        session_id: Optional[uuid.UUID] = None,
        tax_year: Optional[int] = None,
        user_id: Optional[uuid.UUID] = None
    ):
        """
        API tư vấn thuế dạng Streaming (trả từng chunk văn bản).
        Hỗ trợ đọc từ Redis Cache nếu câu hỏi đã có sẵn câu trả lời.
        """
        clean_question, active_session, system_instruction, contents, history_messages = self._prepare_chat_context(
            question=question,
            session_id=session_id,
            tax_year=tax_year,
            user_id=user_id
        )

        # Kiểm tra Cache trước
        cached_answer = self._get_from_cache(clean_question, tax_year, history_messages)
        if cached_answer:
            if self.history_repository and active_session:
                self.history_repository.save_message(
                    session_id=active_session.id, 
                    role="user", 
                    content=clean_question
                )
                self.history_repository.save_message(
                    session_id=active_session.id, 
                    role="assistant", 
                    content=cached_answer
                )
            yield cached_answer
            return

        def _call_gemini_stream(client, model):
            stream_resp = client.models.generate_content_stream(
                model=model,
                contents=contents,
                config=types.GenerateContentConfig(
                    http_options=types.HttpOptions(api_version="v1beta"),
                    system_instruction=system_instruction,
                    temperature=0.1
                )
            )
            for chunk in stream_resp:
                if chunk.text:
                    yield chunk.text

        db_session = self.repository.db if self.repository and hasattr(self.repository, "db") else None
        accumulated_chunks = []

        for chunk_text in AiKeyManager.execute_stream_with_failover(
            db_session,
            _call_gemini_stream,
            default_client=self.client
        ):
            accumulated_chunks.append(chunk_text)
            yield chunk_text

        full_ai_answer = "".join(accumulated_chunks).strip()

        # Lưu câu trả lời vào cache
        self._save_to_cache(clean_question, tax_year, history_messages, full_ai_answer)

        if self.history_repository and active_session:
            self.history_repository.save_message(
                session_id=active_session.id,
                role="user",
                content=clean_question
            )
            self.history_repository.save_message(
                session_id=active_session.id,
                role="assistant",
                content=full_ai_answer
            )

    def get_session(self, session_id: uuid.UUID) -> Optional[ChatSession]:
        if not self.history_repository:
            return None
        return self.history_repository.get_session(session_id=session_id)

    def get_user_sessions(
        self, 
        user_id: Optional[uuid.UUID] = None,
        limit: int = 50,
        skip: int = 0
    ) -> List[ChatSession]:
        if not self.history_repository:
            return []
        return self.history_repository.get_user_sessions(user_id=user_id, limit=limit, skip=skip)

    def update_session_title(self, session_id: uuid.UUID, title: str) -> Optional[ChatSession]:
        if not self.history_repository:
            return None
        return self.history_repository.update_session_title(session_id=session_id, title=title)

    def get_session_messages(self, session_id: uuid.UUID) -> List[ChatMessage]:
        if not self.history_repository:
            return []
        return self.history_repository.get_session_messages(session_id=session_id)

    def delete_session(self, session_id: uuid.UUID) -> bool:
        if not self.history_repository:
            return False
        return self.history_repository.delete_session(session_id=session_id)
