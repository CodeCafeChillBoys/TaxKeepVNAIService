import json
from typing import Dict, Any, Optional
from google import genai
from google.genai import types
from fastapi import HTTPException, status
from app.core.config import settings


class TaxRuleExtractionService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL

    def extract_tax_rules(
        self,
        document_text: Optional[str] = None,
        pdf_bytes: Optional[bytes] = None,
        tax_year: int = 2026,
        rule_set_name: Optional[str] = None,
        source_url: Optional[str] = None,
        legal_doc_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sử dụng Gemini LLM với Structured JSON Output để trích xuất các quy tắc thuế
        (TaxRuleSet và danh sách TaxRule).
        """
        if not document_text and not pdf_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tax rule information could be extracted from the document."
            )

        default_set_name = rule_set_name or f"Personal Income Tax Rules {tax_year}"

        prompt = f"""
Bạn là chuyên gia trích xuất dữ liệu luật thuế chuyên nghiệp phục vụ Tax Calculation Engine.
Nhiệm vụ của bạn là đọc kỹ toàn bộ văn bản pháp luật sau (chú ý đọc kỹ tất cả các trang, bảng biểu, điều khoản)
và trích xuất danh sách các Quy Tắc Thuế (Tax Rules) quan trọng nhất cho năm tính thuế {tax_year}.

THÔNG TIN ĐẦU VÀO:
- Năm tính thuế (taxYear): {tax_year}
- Tên Rule Set mặc định: {default_set_name}
- Nguồn tài liệu (sourceUrl): {source_url or ""}
- Tên văn bản luật (legalDocument): {legal_doc_name or "Luật Thuế Thu Nhập Cá Nhân"}

HƯỚNG DẪN ƯU TIÊN TRÍCH XUẤT CỐT LÕI (BẮT BUỘC PHẢI TÌM VÀ CÓ ĐẦY ĐỦ):
1. DEDUCTION (Mức giảm trừ gia cảnh):
   - Bắt buộc tìm và trích xuất Mức giảm trừ gia cảnh cho bản thân người nộp thuế (ruleCode: PIT_DEDUCTION_PERSONAL) và Mức giảm trừ cho mỗi người phụ thuộc (ruleCode: PIT_DEDUCTION_DEPENDENT).
   - Lấy đúng giá trị số (ví dụ: 15500000 hoặc 11000000) và đơn vị "VND/month".
2. BRACKET (Biểu thuế lũy tiến từng phần đối với tiền lương, tiền công):
   - Bắt buộc trích xuất ĐẦY ĐỦ TẤT CẢ CÁC BẬC THUẾ (ví dụ: Bậc 1, Bậc 2, Bậc 3, Bậc 4, Bậc 5... với ruleCode tương ứng: PIT_BRACKET_1, PIT_BRACKET_2,...).
   - Ghi rõ điều kiện ngưỡng thu nhập tính thuế trong trường "condition" (ví dụ: "Thu nhập tính thuế đến 10 triệu đồng/tháng").
   - Ghi rõ thuế suất dạng số thực trong trường "value" (ví dụ: 0.05, 0.1, 0.2, 0.3, 0.35) và đơn vị "%".
3. RATE (Thuế suất các khoản thu nhập khác):
   - Trích xuất thuế suất áp dụng cho: Thu nhập kinh doanh, chuyển nhượng bất động sản, chuyển nhượng vốn/chứng khoán, đầu tư vốn, trúng thưởng, bản quyền...
4. EXEMPTION (Các khoản miễn thuế):
   - Chỉ trích xuất tối đa 3-5 khoản miễn thuế lớn, tiêu biểu. TUYỆT ĐỐI KHÔNG liệt kê tràn lan hàng chục khoản trợ cấp xã hội nhỏ lẻ làm tràn danh sách và che lấp các quy tắc tính thuế cốt lõi.
"""

        if document_text:
            prompt += f"""
NỘI DUNG VĂN BẢN PHÁP LUẬT:
---
{document_text[:35000]}
---
"""
        else:
            prompt += """
VĂN BẢN PHÁP LUẬT ĐÍNH KÈM:
File PDF đính kèm chứa các trang văn bản (gồm cả trang in điện tử lẫn các trang scan ảnh chụp và bảng biểu). Hãy quét kỹ từng trang để tìm các điều khoản về Biểu thuế lũy tiến (thường ở Điều 9 hoặc Điều 22) và Mức giảm trừ gia cảnh (thường ở Điều 10 hoặc Điều 19).
"""

        prompt += f"""
YÊU CẦU ĐẦU RA (JSON FORMAT DUY NHẤT):
{{
  "taxRuleSet": {{
    "name": "{default_set_name}",
    "taxYear": {tax_year},
    "effectiveFrom": "YYYY-MM-DD hoặc null",
    "effectiveTo": "YYYY-MM-DD hoặc null",
    "status": "Draft"
  }},
  "taxRules": [
    {{
      "ruleCode": "Mã quy tắc SNAKE_CASE in hoa (ví dụ: PIT_DEDUCTION_PERSONAL, PIT_BRACKET_1, PIT_RATE_REAL_ESTATE)",
      "ruleName": "Tên tiếng Anh hoặc tiếng Việt rõ ràng",
      "ruleType": "Phải là một trong [DEDUCTION, BRACKET, RATE, EXEMPTION]",
      "condition": "Mô tả điều kiện áp dụng dưới dạng text hoặc JSON object. Riêng với PIT_DEDUCTION_DEPENDENT hãy xuất định dạng JSON: {{\"subject\": \"DEPENDENT\", \"eligibility\": [{{\"type\": \"CHILD\", \"name\": \"Con chưa thành niên\", \"maxAge\": 18, \"conditions\": [\"Chưa thành niên\"]}}, {{\"type\": \"ADULT_CHILD\", \"name\": \"Con thành niên khuyết tật hoặc đang đi học\", \"maxAge\": 24, \"isStudying\": true, \"maxMonthlyIncome\": 1000000, \"conditions\": [\"Bị khuyết tật\", \"Không có khả năng lao động\", \"Đang theo học ĐH/CĐ\"]}}, {{\"type\": \"SPOUSE\", \"name\": \"Vợ/chồng\", \"maxMonthlyIncome\": 1000000, \"conditions\": [\"Đáp ứng điều kiện theo luật\"]}}, {{\"type\": \"PARENT\", \"name\": \"Cha/Mẹ\", \"maxMonthlyIncome\": 1000000, \"conditions\": [\"Hết tuổi lao động\", \"Mất sức lao động\"]}}, {{\"type\": \"OTHER\", \"name\": \"Cá nhân khác\", \"maxMonthlyIncome\": 1000000, \"conditions\": [\"Đáp ứng điều kiện theo luật\"]}}]}}",
      "value": số thực đại diện cho mức tiền hoặc thuế suất (ví dụ: 15500000, 0.05, 0.1) hoặc null,
      "unit": "VND/month hoặc % hoặc null",
      "effectiveFrom": "YYYY-MM-DD hoặc null",
      "effectiveTo": "YYYY-MM-DD hoặc null",
      "legalDocument": "{legal_doc_name or 'Luật Thuế'}",
      "article": "Số điều (ví dụ: 9 hoặc 10)",
      "clause": "Số khoản (ví dụ: 1 hoặc 2)",
      "point": "Điểm (ví dụ: a hoặc b) hoặc null",
      "sourceUrl": "{source_url or ''}",
      "status": "Draft",
      "version": 1
    }}
  ]
}}
"""

        contents = []
        if pdf_bytes:
            pdf_part = types.Part.from_bytes(data=pdf_bytes, mime_type="application/pdf")
            contents.append(pdf_part)
        contents.append(prompt)

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.1
                )
            )
            raw_text = response.text or "{}"
            data = json.loads(raw_text)
        except Exception:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tax rule information could be extracted from the document."
            )
        
        if not isinstance(data, dict) or "taxRules" not in data or not data["taxRules"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tax rule information could be extracted from the document."
            )

        tax_rules = data.get("taxRules", [])
        if not isinstance(tax_rules, list) or len(tax_rules) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No tax rule information could be extracted from the document."
            )

        for rule in tax_rules:
            if not rule.get("ruleCode") or not rule.get("ruleName") or not rule.get("ruleType"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Some required tax rule fields could not be extracted."
                )

        rule_set = data.get("taxRuleSet", {})
        if not rule_set.get("name"):
            rule_set["name"] = default_set_name
        rule_set["taxYear"] = tax_year
        rule_set["status"] = "Draft"
        data["taxRuleSet"] = rule_set

        return data


tax_rule_extraction_service = TaxRuleExtractionService()
