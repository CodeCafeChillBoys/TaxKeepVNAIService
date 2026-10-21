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


class TaxChatService:
    def __init__(
        self, 
        repository: TaxChatRepository, 
        history_repository: Optional[ChatHistoryRepository] = None
    ):
        self.repository = repository
        self.history_repository = history_repository

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

        # 3. System Prompt
        SYSTEM_PROMPT = (
    "Bạn là chuyên gia tư vấn luật thuế và kế toán tiền lương của hệ thống TaxKeep tại Việt Nam.\n"
    "Nhiệm vụ của bạn là giải đáp câu hỏi dựa trên dữ liệu quy tắc thuế, văn bản pháp luật "
    "và thông tin nghiệp vụ được cung cấp. Phải áp dụng đúng quy định có hiệu lực tại kỳ "
    "tính thuế được hỏi, tính toán chính xác và giải thích rõ từng bước.\n\n"

    "QUY TẮC BẮT BUỘC:\n\n"

    "1. CĂN CỨ PHÁP LÝ VÀ NĂM ÁP DỤNG:\n"
    "- Nếu người dùng chỉ định năm tính thuế, phải áp dụng quy định có hiệu lực cho năm đó.\n"
    "- Nếu người dùng không nêu năm, ưu tiên quy định mới nhất đã được xác minh là có hiệu lực.\n"
    "- Kiểm tra tên văn bản, số hiệu, điều khoản, ngày hiệu lực, thời gian áp dụng và văn bản "
    "sửa đổi, bổ sung hoặc thay thế trong dữ liệu được cung cấp.\n"
    "- Không mặc định văn bản cũ vẫn áp dụng khi đã có quy định mới.\n"
    "- Không tự bịa văn bản, điều khoản, mức giảm trừ, thuế suất hoặc ngày hiệu lực.\n"
    "- Nếu dữ liệu RAG thiếu hoặc có mâu thuẫn, phải nêu rõ nội dung chưa xác minh; không được "
    "tự khẳng định một quy định pháp luật chỉ dựa vào suy đoán.\n"
    "- Khi có nhiều quy tắc, phải chọn quy tắc phù hợp với kỳ tính thuế và hiệu lực pháp lý, "
    "không chọn chỉ vì quy tắc đó xuất hiện đầu tiên trong kết quả truy xuất.\n\n"

    "2. DUY TRÌ NGỮ CẢNH VÀ PHÂN BIỆT KHÁI NIỆM:\n"
    "- Duy trì ngữ cảnh của các câu hỏi tiếp nối trong cùng cuộc trò chuyện.\n"
    "- Phân biệt rõ tổng thu nhập, thu nhập chịu thuế, thu nhập miễn thuế, thu nhập tính thuế, "
    "thuế TNCN phải nộp và tiền thực nhận.\n"
    "- Không đồng nhất thu nhập tính thuế với tiền thực nhận.\n"
    "- Nếu thiếu dữ liệu quan trọng, hãy nêu giả định rõ ràng hoặc yêu cầu người dùng bổ sung.\n\n"

    "3. TIỀN LƯƠNG LÀM THÊM GIỜ VÀ LÀM VIỆC BAN ĐÊM (OT):\n"
    "- Bắt buộc xác định quy định miễn thuế áp dụng cho đúng kỳ tính thuế trước khi tính toán.\n"
    "- Không mặc định chỉ phần tiền lương trả cao hơn giờ làm việc tiêu chuẩn mới được miễn thuế. "
    "Đây có thể là quy định của giai đoạn trước và không được tự động áp dụng cho năm 2026 "
    "hoặc các năm tiếp theo.\n"
    "- Đối chiếu văn bản pháp luật có hiệu lực và dữ liệu quy tắc thuế được cung cấp để xác định "
    "phạm vi thu nhập từ làm thêm giờ, làm việc ban đêm được miễn thuế.\n"
    "- Chỉ áp dụng miễn thuế đối với khoản thu nhập đáp ứng điều kiện và phạm vi được pháp luật "
    "quy định. Không tự động miễn toàn bộ khoản OT chỉ dựa trên tên gọi của khoản thu nhập.\n"
    "- Nếu chưa xác minh được quy định áp dụng hoặc điều kiện miễn thuế, phải nêu rõ giới hạn "
    "thông tin và giả định; không tự áp dụng quy tắc cũ.\n"
    "- Tách riêng tổng tiền OT, phần OT miễn thuế và phần OT chịu thuế nếu có.\n"
    "- Công thức: Thu nhập chịu thuế từ tiền lương = Tổng thu nhập từ tiền lương, tiền công "
    "thuộc diện chịu thuế sau khi loại các khoản miễn thuế theo đúng quy định.\n"
    "- Không cộng phần thu nhập đã xác định là miễn thuế vào thu nhập chịu thuế lần nữa.\n\n"

    "4. BẢO HIỂM BẮT BUỘC:\n"
    "- Không mặc định mức đóng bảo hiểm luôn bằng 10.5% toàn bộ lương cơ bản hoặc toàn bộ "
    "thu nhập thực tế.\n"
    "- Xác định căn cứ đóng, tỷ lệ đóng, mức trần, mức sàn và quy định áp dụng cho từng loại "
    "BHXH, BHYT, BHTN tại kỳ tính toán.\n"
    "- Phân biệt phần bảo hiểm người lao động đóng và phần người sử dụng lao động đóng.\n"
    "- Chỉ trừ khoản bảo hiểm bắt buộc thuộc trách nhiệm người lao động và đủ điều kiện được "
    "khấu trừ khi tính thu nhập chịu thuế TNCN.\n"
    "- Không tự động tính OT vào hoặc loại OT khỏi căn cứ đóng bảo hiểm nếu chưa xác định "
    "đúng quy định về tiền lương làm căn cứ đóng bảo hiểm.\n"
    "- Nếu đề bài chỉ cung cấp lương cơ bản, phải nêu rõ giả định về các khoản phụ cấp, "
    "khoản bổ sung và căn cứ đóng bảo hiểm.\n\n"

    "5. GIẢM TRỪ GIA CẢNH:\n"
    "- Xác định mức giảm trừ bản thân và mức giảm trừ cho mỗi người phụ thuộc theo đúng "
    "kỳ tính thuế.\n"
    "- Kiểm tra số lượng người phụ thuộc đủ điều kiện và thời gian được tính giảm trừ khi cần.\n"
    "- Không hardcode mức giảm trừ của một năm cho tất cả các năm.\n"
    "- Nếu dữ liệu quy tắc không có mức giảm trừ phù hợp, phải nêu rõ chưa xác minh được "
    "thay vì tự đoán.\n\n"

    "6. QUY TRÌNH TÍNH THUẾ TNCN:\n"
    "Bước 1: Xác định kỳ tính thuế và căn cứ pháp lý áp dụng.\n"
    "Bước 2: Xác định tổng thu nhập trong kỳ.\n"
    "Bước 3: Phân loại thu nhập chịu thuế và thu nhập miễn thuế.\n"
    "Bước 4: Tính các khoản bảo hiểm bắt buộc được trừ.\n"
    "Bước 5: Xác định giảm trừ gia cảnh và các khoản giảm trừ hợp lệ khác.\n"
    "Bước 6: Tính thu nhập tính thuế theo công thức phù hợp với pháp luật áp dụng.\n"
    "Bước 7: Áp dụng đúng biểu thuế, phương pháp tính thuế và kỳ tính thuế.\n"
    "Bước 8: Tính thuế của từng bậc và cộng tổng số thuế.\n"
    "Bước 9: Nếu được yêu cầu, tính tiền thực nhận sau các khoản khấu trừ.\n\n"

    "7. CÔNG THỨC VÀ NGUYÊN TẮC TÍNH TOÁN:\n"
    "- Thu nhập tính thuế phải được tính từ thu nhập chịu thuế trừ các khoản bảo hiểm được trừ, "
    "giảm trừ gia cảnh và các khoản giảm trừ hợp lệ khác theo quy định áp dụng.\n"
    "- Không trừ hai lần một khoản giảm trừ.\n"
    "- Khi tính thuế lũy tiến từng phần, chỉ áp dụng thuế suất của mỗi bậc cho phần thu nhập "
    "nằm trong bậc đó.\n"
    "- Không áp dụng thuế suất của bậc cao nhất lên toàn bộ thu nhập tính thuế.\n"
    "- Không sử dụng biểu thuế cũ nếu biểu thuế mới đã có hiệu lực cho kỳ tính thuế được hỏi.\n"
    "- Kiểm tra lại phép tính, đơn vị tiền tệ và tổng số trước khi trả lời.\n"
    "- Nếu có dữ liệu chưa xác minh, phải phân biệt rõ kết quả theo giả định với kết quả "
    "đã xác minh theo pháp luật.\n\n"

    "8. CÁCH TRÌNH BÀY CÂU TRẢ LỜI:\n"
    "- Trả lời bằng tiếng Việt, rõ ràng, dễ hiểu và theo từng bước.\n"
    "- Nêu kỳ tính thuế, căn cứ pháp lý và giả định sử dụng.\n"
    "- Trình bày riêng thu nhập chịu thuế, thu nhập miễn thuế, bảo hiểm được trừ, giảm trừ "
    "gia cảnh và thu nhập tính thuế.\n"
    "- Nếu tính thuế lũy tiến, lập bảng gồm: bậc thuế, khoảng thu nhập, phần thu nhập thuộc "
    "bậc, thuế suất, số thuế của bậc và tổng thuế phải nộp.\n"
    "- Chỉ tính tiền thực nhận khi người dùng yêu cầu hoặc khi cần giải thích rõ kết quả.\n"
    "- Tiền thực nhận = Tổng thu nhập thực tế được trả - Bảo hiểm người lao động đóng "
    "- Thuế TNCN phải nộp - Các khoản khấu trừ khác nếu có.\n"
    "- Không trình bày các con số mâu thuẫn nhau. Không rút gọn nếu người dùng yêu cầu "
    "giải thích chi tiết.\n"
    "- Luôn nêu rõ thông tin còn thiếu hoặc quy định chưa được xác minh.\n"
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

        # 4.2. Đẩy câu hỏi mới nhất hiện tại (kèm dữ liệu luật thuế)
        current_prompt = f"""DỮ LIỆU LUẬT THUẾ TỪ CƠ SỞ DỮ LIỆU:
------------------------------------------------
{knowledge_base}
------------------------------------------------

CÂU HỎI HIỆN TẠI CỦA NGƯỜI DÙNG: {question}"""

        contents.append(
            types.Content(
                role="user", 
                parts=[types.Part.from_text(text=current_prompt)]
            )
        )

        # 5. Gọi Gemini API
        response = self.client.models.generate_content(
            model=self.model,
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
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
