import json
from typing import Any, Dict, List, Optional


def build_law_changeset_prompt(
    current_rules: List[Dict[str, Any]],
    rule_catalog: List[Dict[str, Any]],
    known_documents: List[Dict[str, Any]],
    document_number_hint: Optional[str] = None,
    source_url: Optional[str] = None,
) -> str:
    context_data = {
        "currentRules": current_rules,
        "ruleCatalog": rule_catalog,
        "knownDocuments": known_documents,
    }
    if document_number_hint:
        context_data["documentNumberHint"] = document_number_hint
    if source_url:
        context_data["sourceUrl"] = source_url

    context_json = json.dumps(context_data, ensure_ascii=False, indent=2)

    prompt = f"""Bạn là chuyên gia pháp chế thuế thu nhập cá nhân Việt Nam. Nhiệm vụ: đọc VĂN BẢN ĐÍNH KÈM và so với LUẬT HỆ THỐNG HIỆN TẠI để
lập BẢN ĐỀ XUẤT THAY ĐỔI. Chỉ trả JSON đúng schema được cấu hình, không kèm lời giải thích.

PHẠM VI: chỉ quy định về thu nhập từ tiền lương, tiền công (cá nhân cư trú và không cư trú). Bỏ qua kinh doanh, đầu tư vốn,
chuyển nhượng vốn, bất động sản, trúng thưởng, bản quyền, nhượng quyền thương mại, thừa kế, quà tặng.

DỮ LIỆU ĐẦU VÀO (JSON):
- currentRules: các phiên bản đang hiệu lực của luật hệ thống, mỗi phiên bản có khoảng áp dụng [applyFrom, applyTo).
- ruleCatalog: danh mục mã luật được phép dùng.
- knownDocuments: các văn bản hệ thống đã biết.
{context_json}

VIỆC PHẢI LÀM:
1. document: số hiệu, loại, cơ quan ban hành, ngày ký (trang đầu), ngày hiệu lực (điều hiệu lực thi hành). Không đọc được thì null.
2. relations: đọc kỹ các ĐIỀU CUỐI (hiệu lực thi hành, điều khoản chuyển tiếp) để lấy REPLACES, REPEALS (kèm phạm vi điều/khoản),
   AMENDS; phần đầu văn bản hợp nhất để lấy CONSOLIDATES (văn bản gốc được hợp nhất ghi note = "BASE");
   đoạn "Căn cứ" để lấy BASED_ON (chỉ văn bản về thuế TNCN).
3. operations: với mỗi quy định do CHÍNH văn bản này đặt ra (mức tiền, thuế suất, ngưỡng, biểu thuế, nhóm người phụ thuộc,
   nghĩa vụ quyết toán):
   a. Ghép vào một ruleCode trong ruleCatalog. Không có mã phù hợp thì newCode=true và điền các trường proposed*.
   b. Xác định applyFrom: văn bản ghi "áp dụng từ kỳ tính thuế năm Y" thì Y-01-01; không có thì ngày hiệu lực của văn bản.
      Luôn điền applyBasis là điều, khoản làm căn cứ cho ngày đó.
   c. So với phiên bản của mã đó đang phủ ngày applyFrom trong currentRules:
      - không có phiên bản: ADD
      - có, giá trị khác: UPDATE
      - giá trị giống, văn bản căn cứ khác, và văn bản này cùng cấp hoặc cao hơn: RECITE
      - các trường hợp còn lại: không sinh dòng.
      Thứ bậc: LUAT > NGHI_QUYET (UBTVQH) > NGHI_DINH > QUYET_DINH > THONG_TU > KHAC. VBHN lấy cấp của văn bản gốc mà nó
      hợp nhất.
   d. END chỉ khi văn bản VIẾT RÕ việc bãi bỏ hoặc chấm dứt một quy định đang có trong currentRules.
4. Số liệu mà văn bản chỉ dẫn chiếu văn bản khác ("theo Điều 9 của Luật …") thì ghi vào references, KHÔNG sinh dòng thay đổi.
   Quy định giao cho cơ quan khác ("do Bộ trưởng Bộ Tài chính quy định") thì ghi vào warnings.
5. Mỗi dòng phải có citation (article, clause, point, page, với page đánh số từ 1 theo file), evidence trích nguyên văn
   tối đa 300 ký tự, confidence từ 0 đến 1, rationale một câu.
6. Số tiền ghi bằng VND (số). Thuế suất ghi số thập phân từ 0 đến 1. Biểu thuế ghi ngưỡng THEO NĂM (toAnnual), bậc cuối null.
7. KHÔNG bịa số liệu, KHÔNG dùng kiến thức bên ngoài để bổ sung những gì văn bản không viết.
"""
    return prompt
