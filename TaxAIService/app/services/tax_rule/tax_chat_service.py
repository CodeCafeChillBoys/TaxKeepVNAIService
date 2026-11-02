import os
import uuid
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


class TaxChatService:
    def __init__(
        self, 
        repository: TaxChatRepository, 
        history_repository: Optional[ChatHistoryRepository] = None,
        prompt_service: Optional[PromptTemplateService] = None
    ):
        self.repository = repository
        self.history_repository = history_repository
        self.prompt_service = prompt_service

        if not settings.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY chưa được thiết lập!")

        os.environ.pop("GOOGLE_API_KEY", None)
        os.environ["GEMINI_API_KEY"] = settings.GEMINI_API_KEY

        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

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

    def ask(
        self, 
        question: str, 
        session_id: Optional[uuid.UUID] = None, 
        tax_year: Optional[int] = None,
        user_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        # 1. Quản lý phiên hội thoại & Lấy lịch sử chat cũ
        active_session = None
        history_messages = []
        if self.history_repository:
            active_session = self.history_repository.get_or_create_session(
                session_id=session_id, 
                first_question=question,
                user_id=user_id
            )
            # Lấy 6 tin nhắn trước đó (chưa bao gồm câu hỏi hiện tại)
            history_messages = self.history_repository.get_recent_messages(
                session_id=active_session.id, 
                limit=6
            )
            # Lưu ngay câu hỏi hiện tại của user vào DB
            self.history_repository.save_message(
                session_id=active_session.id, 
                role="user", 
                content=question
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
                parts=[types.Part.from_text(text=question)]
            )
        )

        # 5. Gọi Gemini API với System Instruction động
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                temperature=0.1
            )
        )
        ai_answer = (response.text or "").strip()

        # 6. Lưu câu trả lời của AI vào DB
        if self.history_repository and active_session:
            self.history_repository.save_message(
                session_id=active_session.id, 
                role="assistant", 
                content=ai_answer
            )

        return {
            "session_id": active_session.id if active_session else None,
            "question": question,
            "answer": ai_answer
        }

    def get_user_sessions(self, user_id: Optional[uuid.UUID] = None) -> List[ChatSession]:
        if not self.history_repository:
            return []
        return self.history_repository.get_user_sessions(user_id=user_id)

    def get_session_messages(self, session_id: uuid.UUID) -> List[ChatMessage]:
        if not self.history_repository:
            return []
        return self.history_repository.get_session_messages(session_id=session_id)

    def delete_session(self, session_id: uuid.UUID) -> bool:
        if not self.history_repository:
            return False
        return self.history_repository.delete_session(session_id=session_id)
