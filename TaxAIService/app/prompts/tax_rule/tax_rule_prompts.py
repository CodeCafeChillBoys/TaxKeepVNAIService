from typing import Optional
from app.enum import DependentType, TaxRuleType, TaxRuleStatus


def build_tax_rule_extraction_prompt(
    tax_year: int,
    default_set_name: str,
    source_url: Optional[str] = None,
    legal_doc_name: Optional[str] = None,
    document_text: Optional[str] = None,
) -> str:
    """
    Xây dựng prompt chuyên sâu hướng dẫn Gemini LLM đọc, phân tích và trích xuất
    đầy đủ, chi tiết các quy tắc Luật Thuế Thu Nhập Cá Nhân theo chuẩn JSON Output.
    """
    valid_dependent_types = ", ".join([dt.value for dt in DependentType])
    valid_rule_types = ", ".join([rt.value for rt in TaxRuleType])
    default_status = TaxRuleStatus.DRAFT.value

    prompt = f"""
Bạn là một Chuyên gia Pháp chế cao cấp và Chuyên gia Phân tích Dữ liệu Thuế Thu Nhập Cá Nhân (PIT Legal & Tax Engine Specialist).
Nhiệm vụ của bạn là đọc sâu, rà soát toàn diện từng điều, khoản, điểm và bảng phụ lục trong văn bản pháp luật được cung cấp, sau đó phân tích và trích xuất CHUYÊN BIỆT CÁC QUY TẮC THUẾ THU NHẬP CÁ NHÂN TỪ TIỀN LƯƠNG, TIỀN CÔNG (Personal Income Tax on Salary & Wages / Employment Income) có trong văn bản này phục vụ cho Công cụ Tính Thuế (Tax Calculation Engine).

QUY TẮC RÀNG BUỘC PHẠM VI BẮT BUỘC (SCOPE CONSTRAINTS - CHỈ LẤY TIỀN LƯƠNG, TIỀN CÔNG - TUYỆT ĐỐI KHÔNG LẤY KINH DOANH):
- CHỈ trích xuất các quy tắc thuế trực tiếp áp dụng cho thu nhập từ TIỀN LƯƠNG, TIỀN CÔNG (Employment Income / Salary & Wages của người lao động làm công ăn lương).
- TUYỆT ĐỐI KHÔNG trích xuất bất kỳ quy tắc thuế nào liên quan đến THU NHẬP TỪ KINH DOANH (Business Income / hộ kinh doanh / cá nhân kinh doanh / doanh thu kinh doanh). Mọi điều khoản về cá nhân kinh doanh trong văn bản BẮT BUỘC PHẢI BỎ QUA HOÀN TOÀN.
- TUYỆT ĐỐI KHÔNG trích xuất các nguồn thu nhập khác: chuyển nhượng bất động sản, chuyển nhượng vốn, chứng khoán, đầu tư vốn (cổ tức, lợi tức), trúng thưởng, bản quyền, nhượng quyền thương mại, thừa kế, quà tặng.

THÔNG TIN ĐẦU VÀO:
- Năm tính thuế người dùng nhập (taxYear): {tax_year}
- Tên Rule Set: {default_set_name}
- Nguồn tài liệu (sourceUrl): {source_url or ""}
- Văn bản căn cứ (legalDocument): {legal_doc_name or "Luật Thuế Thu Nhập Cá Nhân"}

════════════════════════════════════════════════════════════════════════════════
QUY TRÌNH PHÂN TÍCH VĂN BẢN PHÁP LUẬT BẮT BUỘC (DEEP ANALYSIS PROTOCOL):
════════════════════════════════════════════════════════════════════════════════
Trước khi xuất JSON, bạn phải thực hiện tuần tự 5 bước phân tích trong tư duy:
1. BẮT BUỘC ĐỐI SOÁT NĂM ÁP DỤNG (TAX YEAR VERIFICATION):
   - Đọc kỹ tiêu đề, căn cứ pháp lý, ngày ký ban hành và điều khoản về hiệu lực thi hành để xác định năm áp dụng thuế của văn bản (extractedTaxYear dạng số nguyên, ví dụ: 2026 hoặc 2020).
   - So sánh extractedTaxYear với năm người dùng đã nhập ({tax_year}):
     + isTaxYearMatched = true: nếu văn bản pháp luật này quy định áp dụng hoặc có hiệu lực điều chỉnh cho năm tính thuế {tax_year}.
     + isTaxYearMatched = false: nếu văn bản này thuộc về năm khác và KHÔNG áp dụng cho năm tính thuế {tax_year}.
     + mismatchReason: Nếu không khớp, giải thích rõ lý do ngắn gọn bằng tiếng Việt (ví dụ: "Văn bản này ban hành và áp dụng cho năm 2020, không phải năm {tax_year}"). Nếu khớp thì ghi null.

   ⚠️ CHỈ THỊ BẮT BUỘC KHI NĂM KHÔNG KHỚP (CRITICAL RULE FOR YEAR MISMATCH):
   - DÙ NĂM CỦA VĂN BẢN (extractedTaxYear) CÓ KHỚP VỚI NĂM NGƯỜI DÙNG NHẬP ({tax_year}) HAY KHÔNG (kể cả khi isTaxYearMatched = false, ví dụ: văn bản thuộc năm 2020 trong khi người dùng nhập {tax_year}), BẠN VẪN BẮT BUỘC 100% PHẢI TRÍCH XUẤT ĐẦY ĐỦ CÁC QUY TẮC THUẾ (DEDUCTIONS, BRACKETS, RATES, EXEMPTIONS) CÓ TRONG VĂN BẢN NÀY VÀO MẢNG "taxRules".
   - TUYỆT ĐỐI KHÔNG ĐƯỢC trả về "taxRules": [] rỗng chỉ vì lý do lệch năm! Hệ thống sẽ lưu các quy tắc này kèm cảnh báo lệch năm để Admin có thể đối soát và chỉnh sửa lại năm áp dụng.
   - Nếu văn bản là văn bản sửa đổi, bổ sung (ví dụ: chỉ quy định về mức giảm trừ gia cảnh): Hãy trích xuất tất cả các quy tắc xuất hiện trong văn bản đó.
2. RÀ SOÁT CẤU TRÚC VĂN BẢN (CHUYÊN BIỆT TIỀN LƯƠNG, TIỀN CÔNG): Đọc kỹ từ đầu đến cuối, chỉ tập trung vào:
   - Các điều khoản quy định đối tượng nộp thuế có thu nhập từ tiền lương, tiền công (cá nhân cư trú, không cư trú).
   - Biểu thuế lũy tiến từng phần áp dụng cho thu nhập từ tiền lương, tiền công.
   - Các quy định về giảm trừ gia cảnh (bản thân, người phụ thuộc), bảo hiểm bắt buộc trừ vào lương, đóng góp từ thiện nhân đạo.
   - Thuế suất áp dụng cho tiền lương cá nhân không cư trú hoặc hợp đồng vãng lai/ngắn hạn.
   - Các khoản miễn thuế gắn liền trực tiếp với tiền lương, tiền công (làm đêm, thêm giờ, lương hưu, trợ cấp bồi thường tai nạn lao động).
3. ĐỐI SOÁT CHÍNH XÁC PHÁP LÝ (Không suy diễn, không bịa đặt số liệu):
   - Mọi quy tắc trích xuất BẮT BUỘC phải ghi rõ căn cứ: Số Điều (article), Số Khoản (clause), Điểm (point) nếu có trong văn bản.
   - Trích xuất đúng số tiền (VND) hoặc thuế suất dạng số thập phân (ví dụ: 5% -> 0.05, 10% -> 0.1, 20% -> 0.2, 35% -> 0.35).
4. ĐẢM BẢO TÍNH TOÀN VẸN (COMPLETENESS):
   - Không được bỏ sót bất kỳ Bậc thuế nào trong Biểu thuế lũy tiến từng phần.
   - Phải có đầy đủ 2 mức giảm trừ gia cảnh cốt lõi: Bản thân và Người phụ thuộc.
5. CHUẨN HÓA MÃ QUY TẮC (RULE CODE):
   - Dùng tiền tố PIT_ kèm loại quy tắc viết HOA chuẩn SNAKE_CASE.

════════════════════════════════════════════════════════════════════════════════
DANH MỤC QUY TẮC THUẾ BẮT BUỘC TRÍCH XUẤT CHI TIẾT (CHỈ THUỘC TIỀN LƯƠNG, TIỀN CÔNG):
════════════════════════════════════════════════════════════════════════════════

1. NHÓM GIẢM TRỪ (ruleType: "DEDUCTION"):
   a. PIT_DEDUCTION_PERSONAL: Mức giảm trừ cho bản thân người nộp thuế cư trú có thu nhập từ tiền lương, tiền công.
      - Giá trị (value): Số tiền VND/tháng theo luật (ví dụ: 11000000 hoặc mức cập nhật mới như 15500000).
      - Đơn vị (unit): "VND/month".
      - Điều kiện (condition): "Áp dụng cho bản thân người nộp thuế cư trú có thu nhập từ tiền lương, tiền công".
   b. PIT_DEDUCTION_DEPENDENT: Mức giảm trừ cho mỗi người phụ thuộc.
      - Giá trị (value): Số tiền VND/người/tháng theo luật quy định (ví dụ: 4400000 hoặc mức cập nhật mới như 6200000).
      - Đơn vị (unit): "VND/person/month".
      - Điều kiện (condition): Phân tích chi tiết các điều kiện xét duyệt giảm trừ người phụ thuộc và xuất chuỗi JSON theo cấu trúc chuẩn.
        * Xác định đầy đủ các nhóm đối tượng người phụ thuộc theo quy định pháp luật (ví dụ: Con chưa thành niên [CHILD], Con thành niên đang học/khuyết tật [ADULT_CHILD], Vợ/chồng [SPOUSE], Cha mẹ [PARENT], Người phụ thuộc khác [OTHER]).
        * Đối với danh mục giấy tờ cần nộp (requiredDocuments):
          - Nếu văn bản có quy định cụ thể hồ sơ chứng minh: Trích xuất chính xác theo điều khoản của văn bản đó.
          - Nếu văn bản là Luật khung (chưa quy định chi tiết hồ sơ chứng minh mà dẫn chiếu văn bản hướng dẫn): Hãy dựa trên kiến thức pháp luật quản lý thuế TNCN hiện hành của Việt Nam để đề xuất danh mục giấy tờ pháp lý cần thiết tương ứng với từng nhóm (giấy tờ chứng minh nhân thân, quan hệ huyết thống/hôn nhân/nuôi dưỡng, nghĩa vụ phụng dưỡng, xác nhận đang theo học hoặc mất khả năng lao động/khuyết tật).
        * Cấu trúc JSON bắt buộc:
        {{"subject": "DEPENDENT", "eligibility": [{{"type": "Mã nhóm chuẩn SNAKE_CASE in hoa ({valid_dependent_types})", "name": "Tên nhóm đối tượng theo đúng văn bản luật", "maxAge": "Số tuổi tối đa (số nguyên hoặc null)", "maxMonthlyIncome": "Mức thu nhập tối đa (số thực hoặc null)", "isStudying": "true nếu yêu cầu đang đi học, ngược lại false", "isDisabled": "true nếu yêu cầu khuyết tật/mất KNLĐ, ngược lại false", "conditions": ["Mô tả tóm tắt các điều kiện đủ tư cách hưởng giảm trừ"], "requiredDocuments": [{{"docType": "Mã loại giấy tờ chuẩn hóa in hoa (BIRTH_CERTIFICATE, CITIZEN_ID, STUDENT_CARD, DISABILITY_CERTIFICATE, MARRIAGE_CERTIFICATE, RELATIONSHIP_CERTIFICATE, SUPPORT_COMMITMENT_FORM, RESIDENCE_CT07, OTHER)", "name": "Tên loại giấy tờ", "isMandatory": "true nếu bắt buộc nộp, false nếu là giấy tờ theo điều kiện/tùy chọn", "description": "Trích dẫn hoặc mô tả cụ thể yêu cầu/hướng dẫn của giấy tờ đó"}}]}}]}}
   c. PIT_DEDUCTION_INSURANCE: Các khoản đóng bảo hiểm bắt buộc trừ vào thu nhập tiền lương (BHXH, BHYT, BHTN, bảo hiểm trách nhiệm nghề nghiệp).
      - Đơn vị (unit): "VND/month" hoặc "%" hoặc "actual".
   d. PIT_DEDUCTION_CHARITY: Các khoản đóng góp từ thiện, nhân đạo, khuyến học trừ vào thu nhập tiền lương, tiền công.
      - Điều kiện (condition): Đóng góp vào các tổ chức, quỹ từ thiện được Nhà nước cấp phép.

2. NHÓM BIỂU THUẾ LŨY TIẾN TỪNG PHẦN (ruleType: "BRACKET"):
   Áp dụng đối với thu nhập tính thuế từ tiền lương, tiền công của cá nhân cư trú ký hợp đồng lao động từ 3 tháng trở lên. BẮT BUỘC TRÍCH XUẤT ĐẦY ĐỦ TỪNG BẬC:
   - PIT_BRACKET_1: Bậc 1 (ví dụ: Thu nhập tính thuế đến 5 hoặc 10 triệu đồng/tháng, thuế suất ví dụ 0.05).
   - PIT_BRACKET_2: Bậc 2.
   - PIT_BRACKET_3: Bậc 3.
   - PIT_BRACKET_4: Bậc 4.
   - PIT_BRACKET_5: Bậc 5.
   - PIT_BRACKET_6, PIT_BRACKET_7 (nếu văn bản áp dụng biểu 7 bậc).
   Yêu cầu với mỗi bậc:
   - "condition": Mô tả rõ ràng khoảng thu nhập tính thuế cả theo tháng (VND/tháng) và theo năm (VND/năm), ví dụ: "Thu nhập tính thuế đến 60 triệu đồng/năm (đến 5 triệu đồng/tháng)" hoặc "Trên 60 triệu đến 120 triệu đồng/năm (trên 5 triệu đến 10 triệu đồng/tháng)".
   - "value": Thuế suất dạng thập phân (0.05, 0.1, 0.15, 0.2, 0.25, 0.3, 0.35...).
   - "unit": "%".

3. NHÓM THUẾ SUẤT TIỀN LƯƠNG, TIỀN CÔNG ĐẶC THÙ (ruleType: "RATE"):
   CHỈ trích xuất các thuế suất liên quan đến tiền lương, tiền công:
   - PIT_RATE_NON_RESIDENT_SALARY: Thuế suất đối với thu nhập từ tiền lương, tiền công của cá nhân KHÔNG cư trú (20% -> value: 0.2).
   - PIT_RATE_CASUAL_SALARY: Thuế suất khấu trừ tại nguồn đối với cá nhân cư trú không ký hợp đồng lao động hoặc ký hợp đồng dưới 3 tháng có mức chi trả thu nhập từ 2 triệu đồng/lần trở lên (10% -> value: 0.1).
   *(CHÚ Ý: TUYỆT ĐỐI BỎ QUA các loại thuế suất Bất động sản, Chứng khoán, Đầu tư vốn, Trúng thưởng, Bản quyền, Thừa kế, Quà tặng, Kinh doanh).*

4. NHÓM MIỄN THUẾ GẮN LIỀN VỚI TIỀN LƯƠNG, TIỀN CÔNG (ruleType: "EXEMPTION"):
   CHỈ trích xuất các khoản miễn thuế trực tiếp thuộc thu nhập từ tiền lương, tiền công:
   - PIT_EXEMPTION_OVERTIME: Thu nhập từ phần tiền lương, tiền công làm việc ban đêm, làm thêm giờ được trả cao hơn so với tiền lương làm việc ban ngày, làm việc trong giờ tiêu chuẩn.
   - PIT_EXEMPTION_RETIREMENT_PENSION: Tiền lương hưu do Quỹ bảo hiểm xã hội chi trả.
   - PIT_EXEMPTION_INSURANCE_COMPENSATION: Tiền bồi thường bảo hiểm nhân thọ, phi nhân thọ, tiền trợ cấp tai nạn lao động hoặc bệnh nghề nghiệp.
   *(CHÚ Ý: TUYỆT ĐỐI BỎ QUA miễn thuế chuyển nhượng BĐS, quà tặng BĐS gia đình, học bổng ngoại giao...)*

════════════════════════════════════════════════════════════════════════════════
VĂN BẢN PHÁP LUẬT CẦN PHÂN TÍCH:
════════════════════════════════════════════════════════════════════════════════
"""
    if document_text:
        prompt += f"""
NỘI DUNG VĂN BẢN PHÁP LUẬT:
---
{document_text[:45000]}
---
"""
    else:
        prompt += """
TÀI LIỆU PHÁP LUẬT ĐÍNH KÈM:
File PDF đính kèm chứa toàn văn bản pháp luật (bao gồm các trang in điện tử, scan ảnh và bảng biểu). Hãy rà soát kỹ từng trang để tìm các điều khoản quy định về thuế thu nhập từ tiền lương, tiền công: Biểu thuế lũy tiến từng phần, Mức giảm trừ gia cảnh (bản thân, người phụ thuộc), các khoản giảm trừ bảo hiểm/từ thiện, thuế suất tiền lương đặc thù và các khoản miễn thuế gắn liền với tiền lương.
"""

    prompt += f"""
════════════════════════════════════════════════════════════════════════════════
YÊU CẦU ĐẦU RA (CHỈ XUẤT DUY NHẤT 1 ĐỐI TƯỢNG JSON HỢP LỆ, KHÔNG KÈM TEXT GIẢI THÍCH):
════════════════════════════════════════════════════════════════════════════════
{{
  "verification": {{
    "inputTaxYear": {tax_year},
    "extractedTaxYear": {tax_year},
    "isTaxYearMatched": true,
    "mismatchReason": null
  }},
  "taxRuleSet": {{
    "name": "{default_set_name}",
    "taxYear": {tax_year},
    "effectiveFrom": "YYYY-MM-DD hoặc null (lấy từ ngày hiệu lực thi hành của văn bản)",
    "effectiveTo": "YYYY-MM-DD hoặc null",
    "status": "{default_status}"
  }},
  "taxRules": [
    {{
      "ruleCode": "Mã chuẩn SNAKE_CASE in hoa (ví dụ: PIT_DEDUCTION_PERSONAL, PIT_BRACKET_1, PIT_RATE_NON_RESIDENT_SALARY)",
      "ruleName": "Tên quy tắc ngắn gọn, rõ nghĩa bằng tiếng Việt hoặc tiếng Anh",
      "ruleType": "Bắt buộc thuộc một trong các loại: {valid_rule_types}",
      "condition": "Mo ta chi tiet dieu kien ap dung hoac nguong thu nhap tinh thue. Voi PIT_DEDUCTION_DEPENDENT thi bat buoc xuat JSON eligibility nhu mau o tren, khong kem chu ben ngoai JSON.",
      "value": số thực đại diện cho giá trị tiền hoặc tỷ lệ thuế suất (ví dụ: 11000000, 15500000, 0.05, 0.1, 0.2) hoặc null nếu là quy tắc miễn thuế không có tỷ lệ cố định,
      "unit": "VND/month hoặc VND/person/month hoặc % hoặc null",
      "effectiveFrom": "YYYY-MM-DD hoặc null",
      "effectiveTo": "YYYY-MM-DD hoặc null",
      "legalDocument": "{legal_doc_name or 'Luật Thuế Thu Nhập Cá Nhân'}",
      "article": "Số điều (ví dụ: 'Điều 19' hoặc '19')",
      "clause": "Số khoản (ví dụ: 'Khoản 1' hoặc '1')",
      "point": "Điểm (ví dụ: 'Điểm a' hoặc 'a') hoặc null",
      "sourceUrl": "{source_url or ''}",
      "status": "{default_status}"
    }}
  ]
}}
"""
    return prompt
