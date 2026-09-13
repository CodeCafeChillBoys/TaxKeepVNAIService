from typing import Optional


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
    prompt = f"""
Bạn là một Chuyên gia Pháp chế cao cấp và Chuyên gia Phân tích Dữ liệu Thuế Thu Nhập Cá Nhân (PIT Legal & Tax Engine Specialist).
Nhiệm vụ của bạn là đọc sâu, rà soát toàn diện từng điều, khoản, điểm và bảng phụ lục trong văn bản pháp luật được cung cấp, sau đó phân tích và trích xuất ĐẦY ĐỦ, CHÍNH XÁC, CHI TIẾT TỪNG QUY TẮC THUẾ (Tax Rules) phục vụ cho Công cụ Tính Thuế (Tax Calculation Engine) cho năm tính thuế {tax_year}.

THÔNG TIN ĐẦU VÀO:
- Năm tính thuế (taxYear): {tax_year}
- Tên Rule Set: {default_set_name}
- Nguồn tài liệu (sourceUrl): {source_url or ""}
- Văn bản căn cứ (legalDocument): {legal_doc_name or "Luật Thuế Thu Nhập Cá Nhân"}

════════════════════════════════════════════════════════════════════════════════
QUY TRÌNH PHÂN TÍCH VĂN BẢN PHÁP LUẬT BẮT BUỘC (DEEP ANALYSIS PROTOCOL):
════════════════════════════════════════════════════════════════════════════════
Trước khi xuất JSON, bạn phải thực hiện tuần tự 4 bước phân tích trong tư duy:
1. RÀ SOÁT CẤU TRÚC VĂN BẢN: Đọc kỹ từ đầu đến cuối, xác định rõ:
   - Các điều khoản quy định đối tượng nộp thuế (cá nhân cư trú, không cư trú).
   - Các điều khoản quy định thu nhập chịu thuế, thu nhập tính thuế.
   - Các điều khoản và phụ lục biểu thuế (biểu lũy tiến từng phần, biểu thuế toàn phần).
   - Các quy định về giảm trừ gia cảnh, bảo hiểm, đóng góp từ thiện nhân đạo.
   - Các quy định về miễn thuế, giảm thuế.
2. ĐỐI SOÁT CHÍNH XÁC PHÁP LÝ (Không suy diễn, không bịa đặt số liệu):
   - Mọi quy tắc trích xuất BẮT BUỘC phải ghi rõ căn cứ: Số Điều (article), Số Khoản (clause), Điểm (point) nếu có trong văn bản.
   - Trích xuất đúng số tiền (VND) hoặc thuế suất dạng số thập phân (ví dụ: 5% -> 0.05, 10% -> 0.1, 20% -> 0.2, 35% -> 0.35).
3. ĐẢM BẢO TÍNH TOÀN VẸN (COMPLETENESS):
   - Không được bỏ sót bất kỳ Bậc thuế nào trong Biểu thuế lũy tiến từng phần.
   - Phải có đầy đủ 2 mức giảm trừ gia cảnh cốt lõi: Bản thân và Người phụ thuộc.
4. CHUẨN HÓA MÃ QUY TẮC (RULE CODE):
   - Dùng tiền tố PIT_ kèm loại quy tắc viết HOA chuẩn SNAKE_CASE.

════════════════════════════════════════════════════════════════════════════════
DANH MỤC QUY TẮC THUẾ BẮT BUỘC TRÍCH XUẤT CHI TIẾT:
════════════════════════════════════════════════════════════════════════════════

1. NHÓM GIẢM TRỪ (ruleType: "DEDUCTION"):
   a. PIT_DEDUCTION_PERSONAL: Mức giảm trừ cho bản thân người nộp thuế.
      - Giá trị (value): Số tiền VND/tháng theo luật (ví dụ: 11000000 hoặc mức cập nhật mới như 15500000).
      - Đơn vị (unit): "VND/month".
      - Điều kiện (condition): "Áp dụng cho bản thân người nộp thuế cư trú có thu nhập từ tiền lương, tiền công".
   b. PIT_DEDUCTION_DEPENDENT: Mức giảm trừ cho mỗi người phụ thuộc.
      - Giá trị (value): Số tiền VND/người/tháng theo luật (ví dụ: 4400000 hoặc mức mới như 6200000).
      - Đơn vị (unit): "VND/person/month".
      - Điều kiện (condition): BẮT BUỘC định dạng chuỗi JSON chi tiết tiêu chí xét duyệt người phụ thuộc theo luật:
        {{"subject": "DEPENDENT", "eligibility": [{{"type": "CHILD", "name": "Con chưa thành niên", "maxAge": 18, "conditions": ["Con đẻ, con nuôi, con ngoài giá thú hợp pháp", "Dưới 18 tuổi"]}}, {{"type": "ADULT_CHILD", "name": "Con thành niên đang học hoặc khuyết tật", "maxAge": 24, "isStudying": true, "maxMonthlyIncome": 1000000, "conditions": ["Bị tàn tật/khuyết tật không có khả năng lao động HOẶC đang học ĐH, CĐ, THCN, học nghề có thu nhập <= 1 triệu đồng/tháng"]}}, {{"type": "SPOUSE", "name": "Vợ hoặc chồng", "maxMonthlyIncome": 1000000, "conditions": ["Trong độ tuổi lao động bị khuyết tật mất khả năng lao động HOẶC ngoài độ tuổi lao động không có thu nhập hoặc thu nhập bình quân <= 1 triệu đồng/tháng"]}}, {{"type": "PARENT", "name": "Cha đẻ, mẹ đẻ, cha mẹ vợ/chồng", "maxMonthlyIncome": 1000000, "conditions": ["Hết tuổi lao động HOẶC trong độ tuổi lao động bị khuyết tật không có khả năng lao động, có thu nhập bình quân <= 1 triệu đồng/tháng"]}}, {{"type": "OTHER", "name": "Cá nhân khác không nơi nương tựa", "maxMonthlyIncome": 1000000, "conditions": ["Người nộp thuế trực tiếp nuôi dưỡng, đáp ứng điều kiện mất sức lao động hoặc hết tuổi lao động và thu nhập <= 1 triệu đồng/tháng"]}}]}}
   c. PIT_DEDUCTION_INSURANCE: Các khoản đóng bảo hiểm bắt buộc được trừ.
      - Trích xuất quy tắc trừ các khoản bảo hiểm bắt buộc: BHXH, BHYT, BHTN, bảo hiểm trách nhiệm nghề nghiệp.
   d. PIT_DEDUCTION_CHARITY: Các khoản đóng góp từ thiện, nhân đạo, khuyến học.
      - Điều kiện: Đóng góp vào các tổ chức, cơ sở được cơ quan nhà nước có thẩm quyền công nhận.

2. NHÓM BIỂU THUẾ LŨY TIẾN TỪNG PHẦN (ruleType: "BRACKET"):
   Áp dụng đối với thu nhập tính thuế từ tiền lương, tiền công của cá nhân cư trú. BẮT BUỘC TRÍCH XUẤT ĐẦY ĐỦ TỪNG BẬC:
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

3. NHÓM THUẾ SUẤT TOÀN PHẦN VÀ CÁC THU NHẬP KHÁC (ruleType: "RATE"):
   Trích xuất chi tiết thuế suất từng nguồn thu nhập:
   - PIT_RATE_NON_RESIDENT_SALARY: Thuế suất đối với tiền lương, tiền công của cá nhân KHÔNG cư trú (thường 20% -> value: 0.2).
   - PIT_RATE_REAL_ESTATE: Chuyển nhượng bất động sản (thường 2% trên giá chuyển nhượng -> value: 0.02).
   - PIT_RATE_CAPITAL_TRANSFER: Chuyển nhượng vốn, chuyển nhượng chứng khoán (ví dụ chứng khoán 0.1% giá chuyển nhượng -> value: 0.001).
   - PIT_RATE_CAPITAL_INVESTMENT: Đầu tư vốn (cổ tức, lợi tức cổ phần, lãi tiền gửi phi ngân hàng -> value: 0.05).
   - PIT_RATE_PRIZE: Trúng thưởng xổ số, khuyến mại, cá cược (thường 10% phần vượt trên 10 triệu đồng -> value: 0.1).
   - PIT_RATE_ROYALTY: Bản quyền, nhượng quyền thương mại (thường 5% phần vượt trên 10 triệu đồng -> value: 0.05).
   - PIT_RATE_INHERITANCE_GIFT: Thừa kế, quà tặng (chứng khoán, vốn, BĐS) (thường 10% phần vượt trên 10 triệu đồng -> value: 0.1).
   - PIT_RATE_BUSINESS: Thu nhập từ kinh doanh của cá nhân (ghi rõ ngành nghề và tỷ lệ % thuế tính trên doanh thu nếu văn bản có nêu).

4. NHÓM MIỄN THUẾ TIÊU BIỂU (ruleType: "EXEMPTION"):
   Trích xuất 4-6 khoản miễn thuế quan trọng, có ảnh hưởng trực tiếp đến người nộp thuế:
   - PIT_EXEMPTION_OVERTIME: Thu nhập từ phần tiền lương, tiền công làm việc ban đêm, làm thêm giờ được trả cao hơn so với bình thường.
   - PIT_EXEMPTION_REAL_ESTATE_FAMILY: Thu nhập từ chuyển nhượng, thừa kế, quà tặng bất động sản giữa những người thân (vợ với chồng, cha mẹ với con, anh chị em ruột, ông bà với cháu...).
   - PIT_EXEMPTION_INSURANCE_COMPENSATION: Tiền bồi thường bảo hiểm nhân thọ, phi nhân thọ, tai nạn lao động.
   - PIT_EXEMPTION_SCHOLARSHIP: Học bổng nhận được từ ngân sách nhà nước hoặc tổ chức trong/ngoài nước.
   - PIT_EXEMPTION_RETIREMENT_PENSION: Tiền lương hưu do Quỹ bảo hiểm xã hội chi trả.

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
File PDF đính kèm chứa toàn văn bản pháp luật (bao gồm các trang in điện tử, scan ảnh và bảng biểu). Hãy rà soát kỹ từng trang để tìm các điều khoản về Biểu thuế lũy tiến từng phần, Mức giảm trừ gia cảnh, các khoản giảm trừ khác, biểu thuế toàn phần và các khoản miễn thuế.
"""

    prompt += f"""
════════════════════════════════════════════════════════════════════════════════
YÊU CẦU ĐẦU RA (CHỈ XUẤT DUY NHẤT 1 ĐỐI TƯỢNG JSON HỢP LỆ, KHÔNG KÈM TEXT GIẢI THÍCH):
════════════════════════════════════════════════════════════════════════════════
{{
  "taxRuleSet": {{
    "name": "{default_set_name}",
    "taxYear": {tax_year},
    "effectiveFrom": "YYYY-MM-DD hoặc null (lấy từ ngày hiệu lực thi hành của văn bản)",
    "effectiveTo": "YYYY-MM-DD hoặc null",
    "status": "Draft"
  }},
  "taxRules": [
    {{
      "ruleCode": "Mã chuẩn SNAKE_CASE in hoa (ví dụ: PIT_DEDUCTION_PERSONAL, PIT_BRACKET_1, PIT_RATE_REAL_ESTATE)",
      "ruleName": "Tên quy tắc ngắn gọn, rõ nghĩa bằng tiếng Việt hoặc tiếng Anh",
      "ruleType": "Bắt buộc thuộc một trong 4 loại: DEDUCTION, BRACKET, RATE, EXEMPTION",
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
      "status": "Draft",
      "version": 1
    }}
  ]
}}
"""
    return prompt
