import os
import sys

# Đảm bảo import được module app
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.infrastructure.database import get_db_context
from app.models.ai_prompt_template import AiPromptTemplate
from app.repositories.prompt_template.prompt_template_repository import PromptTemplateRepository
from app.prompts.tax_rule.tax_rule_prompts import (
    TAX_RULE_EXTRACTION_PROMPT_VARIABLES,
    TAX_RULE_EXTRACTION_SYSTEM_PROMPT_TEMPLATE,
)
from app.prompts.ocr.ocr_prompts import DEPENDENT_OCR_SYSTEM_PROMPT_TEMPLATE
from app.prompts.expense_ocr import (
    EXPENSE_OCR_SYSTEM_PROMPT,
    MEDICAL_STATEMENT_RULES,
    MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
)
from app.prompts.expense_ocr.expense_ocr_prompt import EXPENSE_OCR_SYSTEM_PROMPT_TEMPLATE
from app.schemas.prompt_template.prompt_template_schema import (
    PromptTemplateCreateRequest,
    PromptTemplateUpdateRequest,
)
from app.services.prompt_template.prompt_template_service import PromptTemplateService

TAX_CHAT_SYSTEM_PROMPT = """Bạn là chuyên gia tư vấn luật thuế và kế toán tiền lương của hệ thống TaxKeep tại Việt Nam.
Nhiệm vụ của bạn là giải đáp câu hỏi dựa trên dữ liệu quy tắc thuế, văn bản pháp luật và thông tin nghiệp vụ được cung cấp. Phải áp dụng đúng quy định có hiệu lực tại kỳ tính thuế được hỏi, tính toán chính xác và giải thích rõ từng bước.

════════════════════════════════════════════════════════════════════════════════
CĂN CỨ PHÁP LÝ TỪ CƠ SỞ DỮ LIỆU LUẬT THUẾ ({tax_year_label}):
════════════════════════════════════════════════════════════════════════════════
{knowledge_base}
════════════════════════════════════════════════════════════════════════════════

QUY TẮC BẮT BUỘC:

1. CĂN CỨ PHÁP LÝ VÀ NĂM ÁP DỤNG:
- Nếu người dùng chỉ định năm tính thuế, phải áp dụng quy định có hiệu lực cho năm đó.
- Nếu người dùng không nêu năm, ưu tiên quy định mới nhất đã được xác minh là có hiệu lực.
- Kiểm tra tên văn bản, số hiệu, điều khoản, ngày hiệu lực, thời gian áp dụng trong dữ liệu được cung cấp.
- Không tự bịa văn bản, điều khoản, mức giảm trừ, thuế suất hoặc ngày hiệu lực.
- Nếu dữ liệu RAG thiếu hoặc có mâu thuẫn, phải nêu rõ nội dung chưa xác minh; không được tự khẳng định một quy định pháp luật chỉ dựa vào suy đoán.

2. DUY TRÌ NGỮ CẢNH VÀ PHÂN BIỆT KHÁI NIỆM:
- Duy trì ngữ cảnh của các câu hỏi tiếp nối trong cùng cuộc trò chuyện.
- Phân biệt rõ: Tổng thu nhập, Thu nhập chịu thuế, Thu nhập miễn thuế, Thu nhập tính thuế, Thuế TNCN phải nộp và Tiền thực nhận.
- Không đồng nhất thu nhập tính thuế với tiền thực nhận.

3. TIỀN LƯƠNG LÀM THÊM GIỜ VÀ LÀM VIỆC BAN ĐÊM (OT):
- Bắt buộc xác định quy định miễn thuế áp dụng cho đúng kỳ tính thuế trước khi tính toán.
- Không mặc định chỉ phần tiền lương trả cao hơn giờ làm việc tiêu chuẩn mới được miễn thuế nếu văn bản mới có quy định khác.
- Tách riêng: Tổng tiền OT, Phần OT miễn thuế và Phần OT chịu thuế.
- Công thức: Thu nhập chịu thuế từ tiền lương = Tổng thu nhập từ tiền lương, tiền công thuộc diện chịu thuế sau khi loại các khoản miễn thuế theo đúng quy định.

4. BẢO HIỂM BẮT BUỘC:
- Không mặc định mức đóng bảo hiểm luôn bằng 10.5% toàn bộ lương nếu chưa xác minh căn cứ đóng.
- Phân biệt phần bảo hiểm người lao động đóng và phần người sử dụng lao động đóng.
- Chỉ trừ khoản bảo hiểm bắt buộc thuộc trách nhiệm người lao động khi tính thu nhập tính thuế TNCN.

5. GIẢM TRỪ GIA CẢNH:
- Xác định mức giảm trừ bản thân và mức giảm trừ cho mỗi người phụ thuộc theo đúng kỳ tính thuế ({tax_year_label}).
- Không hardcode mức giảm trừ của một năm cho tất cả các năm.

6. CÔNG THỨC VÀ NGUYÊN TẮC TÍNH TOÁN:
- Thu nhập tính thuế = Thu nhập chịu thuế - Các khoản bảo hiểm được trừ - Giảm trừ gia cảnh - Các khoản đóng góp từ thiện, nhân đạo hợp lệ.
- Khi tính thuế lũy tiến từng phần, chỉ áp dụng thuế suất của mỗi bậc cho phần thu nhập nằm trong bậc đó.
- Không áp dụng thuế suất của bậc cao nhất lên toàn bộ thu nhập tính thuế.

7. CÁCH TRÌNH BÀY CÂU TRẢ LỜI:
- Trả lời bằng tiếng Việt, rõ ràng, dễ hiểu và theo từng bước.
- Nêu kỳ tính thuế, căn cứ pháp lý và giả định sử dụng.
- Nếu tính thuế lũy tiến, lập bảng gồm: bậc thuế, khoảng thu nhập, phần thu nhập thuộc bậc, thuế suất, số thuế của bậc và tổng thuế phải nộp.
- Tiền thực nhận (Net) = Tổng thu nhập thực tế - Bảo hiểm NLĐ đóng - Thuế TNCN phải nộp - Các khoản khấu trừ khác (nếu có)."""

INCOME_OCR_SYSTEM_PROMPT = """Bạn là Chuyên gia AI OCR cao cấp chuyên bóc tách Phiếu lương (Payslip), Bảng thanh toán tiền lương, Thư xác nhận thu nhập và Chứng từ khấu trừ thuế TNCN tại Việt Nam.

MỤC TIÊU:
Phân tích kỹ lưỡng tài liệu và bóc tách các trường tài chính chính xác tuyệt đối phục vụ kê khai thuế TNCN vào bảng 'incomes'.

QUY TẮC NHẬN DIỆN VÀ BÓC TÁCH:
1. KIỂM TRA TÍNH HỢP LỆ (isIncomeDocument):
   - True: Phiếu lương, Bảng kê lương hàng tháng, Sao kê lương, Xác nhận thu nhập năm, Chứng từ khấu trừ thuế TNCN.
   - False: Hóa đơn bán lẻ, vé xe, ảnh cá nhân không liên quan tiền lương.

2. CÁC TRƯỜNG DỮ LIỆU CỐT LÕI:
   - organizationName: Tên công ty hoặc tổ chức chi trả thu nhập.
   - taxIdNumber: Mã số thuế công ty hoặc Mã số thuế cá nhân.
   - month: Tháng tính lương (1 - 12).
   - year: Năm tính lương (ví dụ: {target_year_instruction}).
   - totalTaxableIncome (Tổng thu nhập chịu thuế): Ưu tiên thu nhập chịu thuế hoặc Tổng thu nhập Gross sau khi trừ các khoản phụ cấp miễn thuế.
   - insuranceDeducted (Bảo hiểm khấu trừ): Tổng BHXH (8%) + BHYT (1.5%) + BHTN (1%) do người lao động đóng.
   - taxAlreadyDeducted (Thuế đã khấu trừ): Số thuế TNCN tạm nộp/khấu trừ trong kỳ.

3. KIỂM TRA CHÉO TÀI CHÍNH:
   - Net Salary xấp xỉ = Tổng thu nhập - Bảo hiểm - Thuế TNCN - Giảm trừ khác.
   - Các giá trị tiền phải là số thực (float), không chứa ký tự 'VNĐ' hay dấu chấm phẩy ngăn cách."""

CERTIFICATE_OCR_SYSTEM_PROMPT = """Bạn là chuyên gia thẩm định văn bằng, chứng chỉ chuyên môn tài chính - kế toán - thuế tại Việt Nam.
Nhiệm vụ của bạn là kiểm tra xem tài liệu được gửi lên CÓ PHẢI LÀ CHỨNG CHỈ HÀNH NGHỀ / BẰNG CẤP HỢP LỆ HAY KHÔNG, và trích xuất thông tin pháp lý.

DANH MỤC MÃ LOẠI CHỨNG CHỈ:
{allowed_types_guide}

QUY TẮC PHÂN LOẠI:
- TAX_AGENT: Chứng chỉ hành nghề dịch vụ làm thủ tục về thuế (Đại lý thuế) do Tổng cục Thuế / Bộ Tài chính cấp.
- CPA: Chứng chỉ Kiểm toán viên do Bộ Tài chính cấp.
- ACCOUNTANT: Chứng chỉ hành nghề Kế toán do Bộ Tài chính cấp.
- CHIEF_ACCOUNTANT: Chứng chỉ bồi dưỡng Kế toán trưởng.
- OTHER: Bằng tốt nghiệp đại học chuyên ngành Kinh tế/Thuế/Luật, hoặc chứng chỉ chuyên môn liên quan khác.

QUY TẮC LOẠI TRỪ (is_certificate = false):
- Giấy tờ tùy thân (CCCD, CMND, Hộ chiếu) -> KHÔNG PHẢI chứng chỉ hành nghề.
- Hóa đơn, sao kê ngân hàng, hợp đồng lao động, CV, sách vở, ảnh selfie -> KHÔNG PHẢI chứng chỉ.
- Khi is_certificate = false: Ghi rõ rejection_reason, tất cả các trường thông tin còn lại đặt null.

KHI LÀ CHỨNG CHỈ HỢP LỆ (is_certificate = true):
- Trích xuất: full_name, certificate_name, certificate_number, issuing_authority, issue_date, expiry_date."""

SEED_TEMPLATES = [
    {
        "prompt_key": "PROMPT_TAX_CHAT_ADVISORY",
        "system_prompt": TAX_CHAT_SYSTEM_PROMPT,
        "description": "System prompt cốt lõi tư vấn thuế TNCN và giải đáp thắc mắc lương / OT",
        "variables": ["tax_year_label", "knowledge_base"],
        "is_active": True,
        "version": 1
    },
    {
        "prompt_key": "PROMPT_EXPENSE_OCR",
        "system_prompt": EXPENSE_OCR_SYSTEM_PROMPT_TEMPLATE,
        "description": "System prompt bóc tách và phân loại hóa đơn chi phí hợp lệ giảm trừ thuế",
        "variables": ["categories_text", "medical_statement_rules"],
        "is_active": True,
        "version": 1
    },
    {
        "prompt_key": "PROMPT_MEDICAL_STATEMENT_RULES",
        "system_prompt": MEDICAL_STATEMENT_RULES,
        "description": "Quy tắc bóc tách bảng kê chi phí KCB (Mục 7a) chèn động vào hóa đơn chi phí",
        "variables": [],
        "is_active": True,
        "version": 1
    },
    {
        "prompt_key": "PROMPT_MEDICAL_STATEMENT_OCR",
        "system_prompt": MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
        "description": "System prompt chuyên biệt bóc tách Bảng kê chi phí khám bệnh, chữa bệnh (Mẫu số 01/BV, 02/BV)",
        "variables": ["medical_doc_type_code", "medical_categories_guide"],
        "is_active": True,
        "version": 1
    },
    {
        "prompt_key": "PROMPT_INCOME_OCR",
        "system_prompt": INCOME_OCR_SYSTEM_PROMPT,
        "description": "System prompt bóc tách phiếu lương và thu nhập chịu thuế",
        "variables": ["target_year_instruction"],
        "is_active": True,
        "version": 1
    },
    {
        "prompt_key": "PROMPT_DEPENDENT_OCR",
        "system_prompt": DEPENDENT_OCR_SYSTEM_PROMPT_TEMPLATE,
        "description": "System prompt bóc tách và thẩm định giấy tờ người phụ thuộc",
        "variables": ["dependent_rules_text"],
        "is_active": True,
        "version": 1
    },
    {
        "prompt_key": "PROMPT_CERTIFICATE_OCR",
        "system_prompt": CERTIFICATE_OCR_SYSTEM_PROMPT,
        "description": "System prompt thẩm định chứng chỉ hành nghề thuế / kế toán / kiểm toán",
        "variables": ["allowed_types_guide"],
        "is_active": True,
        "version": 1
    },
    {
        "prompt_key": "PROMPT_TAX_RULE_EXTRACTION",
        "system_prompt": TAX_RULE_EXTRACTION_SYSTEM_PROMPT_TEMPLATE,
        "description": "System prompt phân tích và bóc tách quy tắc thuế từ văn bản pháp luật PDF",
        "variables": TAX_RULE_EXTRACTION_PROMPT_VARIABLES,
        "is_active": True,
        "version": 1
    }
]


def seed_prompts():
    print("Bắt đầu nạp dữ liệu System Prompt Template vào Database...")
    with get_db_context() as db:
        repo = PromptTemplateRepository(db)
        created_count = 0
        updated_count = 0

        for item in SEED_TEMPLATES:
            existing = repo.get_by_key(item["prompt_key"], active_only=False)
            if existing:
                existing.system_prompt = item["system_prompt"]
                existing.description = item["description"]
                existing.variables = item["variables"]
                existing.is_active = item["is_active"]
                repo.save(existing)
                updated_count += 1
                print(f" -> Đã cập nhật prompt: {item['prompt_key']}")
            else:
                new_row = AiPromptTemplate(
                    prompt_key=item["prompt_key"],
                    system_prompt=item["system_prompt"],
                    description=item["description"],
                    variables=item["variables"],
                    is_active=item["is_active"],
                    version=1
                )
                repo.save(new_row)
                created_count += 1
                print(f" -> Đã tạo mới prompt: {item['prompt_key']}")

        print(f"\n[HOÀN TẤT] Tạo mới: {created_count}, Cập nhật: {updated_count} System Prompt Templates!")


def seed_expense_medical_prompt():
    prompt_key = "PROMPT_EXPENSE_OCR"
    with get_db_context() as db:
        service = PromptTemplateService(PromptTemplateRepository(db))
        existing = service.get_by_key(prompt_key)
        if existing is None:
            saved = service.create(PromptTemplateCreateRequest(
                prompt_key=prompt_key,
                system_prompt=EXPENSE_OCR_SYSTEM_PROMPT_TEMPLATE,
                description="System prompt bóc tách và phân loại hóa đơn chi phí hợp lệ giảm trừ thuế",
                variables=["categories_text", "medical_statement_rules"],
            ))
            print(f" -> Đã tạo mới prompt: {prompt_key}")
        else:
            saved = service.update(prompt_key, PromptTemplateUpdateRequest(
                system_prompt=EXPENSE_OCR_SYSTEM_PROMPT_TEMPLATE,
                description="System prompt bóc tách và phân loại hóa đơn chi phí hợp lệ giảm trừ thuế",
                variables=["categories_text", "medical_statement_rules"],
                is_active=existing.is_active,
            ))
            service.clear_cache(prompt_key)
            print(f" -> Đã cập nhật prompt: {prompt_key} (version {saved.version})")

        # Đồng bộ cấu hình động cho PROMPT_MEDICAL_STATEMENT_RULES
        rules_key = "PROMPT_MEDICAL_STATEMENT_RULES"
        existing_rules = service.get_by_key(rules_key)
        if existing_rules is None:
            saved_rules = service.create(PromptTemplateCreateRequest(
                prompt_key=rules_key,
                system_prompt=MEDICAL_STATEMENT_RULES,
                description="Quy tắc bóc tách bảng kê chi phí KCB (Mục 7a) chèn động vào hóa đơn chi phí",
                variables=[],
            ))
            print(f" -> Đã tạo mới prompt: {rules_key}")
        else:
            saved_rules = service.update(rules_key, PromptTemplateUpdateRequest(
                system_prompt=MEDICAL_STATEMENT_RULES,
                description="Quy tắc bóc tách bảng kê chi phí KCB (Mục 7a) chèn động vào hóa đơn chi phí",
                variables=[],
                is_active=existing_rules.is_active,
            ))
            service.clear_cache(rules_key)
            print(f" -> Đã cập nhật prompt: {rules_key} (version {saved_rules.version})")


def seed_medical_statement_prompt():
    prompt_key = "PROMPT_MEDICAL_STATEMENT_OCR"
    with get_db_context() as db:
        service = PromptTemplateService(PromptTemplateRepository(db))
        existing = service.get_by_key(prompt_key)
        if existing is None:
            saved = service.create(PromptTemplateCreateRequest(
                prompt_key=prompt_key,
                system_prompt=MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
                description="System prompt chuyên biệt bóc tách Bảng kê chi phí khám bệnh, chữa bệnh (Mẫu số 01/BV, 02/BV)",
                variables=["medical_doc_type_code", "medical_categories_guide"],
            ))
            print(f" -> Đã tạo mới prompt: {prompt_key}")
        else:
            saved = service.update(prompt_key, PromptTemplateUpdateRequest(
                system_prompt=MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
                description="System prompt chuyên biệt bóc tách Bảng kê chi phí khám bệnh, chữa bệnh (Mẫu số 01/BV, 02/BV)",
                variables=["medical_doc_type_code", "medical_categories_guide"],
                is_active=existing.is_active,
            ))
            service.clear_cache(prompt_key)
            print(f" -> Đã cập nhật prompt: {prompt_key} (version {saved.version})")


if __name__ == "__main__":
    if sys.argv[1:] == ["--expense-medical"]:
        seed_expense_medical_prompt()
    elif sys.argv[1:] == ["--medical-statement"]:
        seed_medical_statement_prompt()
    elif not sys.argv[1:]:
        seed_prompts()
    else:
        raise SystemExit("Usage: python -m app.scripts.seed_prompts [--expense-medical | --medical-statement]")
