from typing import Optional, List, Dict, Any
from app.mappers.tax_rule.tax_rule_mapper import normalize_dependent_type


def build_dependent_rules_text(
    target_group: Optional[str] = None, 
    rules: Optional[List[Dict[str, Any]]] = None
) -> str:
    rules_text = ""
    if target_group:
        # Tự động chuẩn hóa nếu FE gửi tiếng Việt (ví dụ: 'Người phụ thuộc khác' -> 'OTHER_HELPLESS')
        normalized_group = normalize_dependent_type(target_group)
        group_desc_map = {
            "PARENT_RETIRED": "Cha/Mẹ ngoài độ tuổi lao động (Nam >= 60/62 tuổi, Nữ >= 55/60 tuổi, không có thu nhập hoặc thu nhập bình quân <= mức quy định; gồm cha đẻ, mẹ đẻ, cha mẹ vợ/chồng, cha mẹ nuôi). Giấy tờ cần thiết: CCCD chứng minh độ tuổi (CITIZEN_ID), Khai sinh hoặc CT07 chứng minh quan hệ (BIRTH_CERTIFICATE / RESIDENCE_CT07 / RELATIONSHIP_CERTIFICATE).",
            "PARENT_DISABLED": "Cha/Mẹ trong độ tuổi lao động nhưng bị khuyết tật, mất khả năng lao động từ 61% trở lên (gồm cha đẻ, mẹ đẻ, cha mẹ vợ/chồng, cha mẹ nuôi). Giấy tờ cần thiết: Giấy xác nhận khuyết tật / hồ sơ bệnh án (DISABILITY_CERTIFICATE), CCCD (CITIZEN_ID), Khai sinh hoặc CT07 (BIRTH_CERTIFICATE / RESIDENCE_CT07 / RELATIONSHIP_CERTIFICATE).",
            "CHILD_UNDER_18": "Con chưa thành niên dưới 18 tuổi (gồm con đẻ, con nuôi hợp pháp, con riêng của vợ/chồng, con ngoài giá thú). Giấy tờ cần thiết: Giấy khai sinh (BIRTH_CERTIFICATE), CCCD nếu có (CITIZEN_ID); đối với con nuôi cần thêm Quyết định công nhận việc nuôi con nuôi (RELATIONSHIP_CERTIFICATE); đối với con riêng cần thêm Giấy đăng ký kết hôn của cha mẹ (MARRIAGE_CERTIFICATE).",
            "CHILD_OVER_18_STUDYING": "Con từ 18 tuổi trở lên đang theo học ĐH, CĐ, THCN, dạy nghề... (gồm con đẻ, con nuôi hợp pháp, con riêng của vợ/chồng). Giấy tờ cần thiết: Thẻ HSSV hoặc Giấy xác nhận đang theo học (STUDENT_CARD), Giấy khai sinh (BIRTH_CERTIFICATE), CCCD (CITIZEN_ID); đối với con nuôi cần thêm Quyết định công nhận việc nuôi con nuôi (RELATIONSHIP_CERTIFICATE); đối với con riêng cần thêm Giấy đăng ký kết hôn của cha mẹ (MARRIAGE_CERTIFICATE).",
            "CHILD_OVER_18_DISABLED": "Con từ 18 tuổi trở lên bị khuyết tật, mất khả năng lao động (gồm con đẻ, con nuôi hợp pháp, con riêng của vợ/chồng). Giấy tờ cần thiết: Giấy xác nhận khuyết tật / hồ sơ bệnh án kết luận mất KNLĐ (DISABILITY_CERTIFICATE), Giấy khai sinh (BIRTH_CERTIFICATE), CCCD (CITIZEN_ID); đối với con nuôi cần thêm Quyết định công nhận việc nuôi con nuôi (RELATIONSHIP_CERTIFICATE); đối với con riêng cần thêm Giấy đăng ký kết hôn của cha mẹ (MARRIAGE_CERTIFICATE).",
            "SPOUSE_RETIRED": "Vợ hoặc chồng ngoài độ tuổi lao động. Giấy tờ cần thiết: Giấy chứng nhận kết hôn (MARRIAGE_CERTIFICATE), CCCD (CITIZEN_ID).",
            "SPOUSE_DISABLED": "Vợ hoặc chồng trong độ tuổi lao động bị khuyết tật, mất khả năng lao động. Giấy tờ cần thiết: Giấy chứng nhận kết hôn (MARRIAGE_CERTIFICATE), CCCD (CITIZEN_ID), Giấy xác nhận khuyết tật (DISABILITY_CERTIFICATE).",
            "OTHER_HELPLESS": "Người phụ thuộc khác không nơi nương tựa đang trực tiếp nuôi dưỡng. Giấy tờ cần thiết: Bản cam kết nuôi dưỡng Mẫu 07/XN-NPT (SUPPORT_COMMITMENT_FORM), CCCD (CITIZEN_ID), Xác nhận cư trú CT07 (RESIDENCE_CT07), Giấy tờ khuyết tật nếu trong độ tuổi LĐ (DISABILITY_CERTIFICATE).",
        }
        if normalized_group in group_desc_map:
            rules_text += f"\n- Nhóm đối tượng đang thẩm định: [{normalized_group}] - {group_desc_map[normalized_group]}\n"
        else:
            rules_text += f"\n- Nhóm đối tượng đang thẩm định: [{normalized_group}]\n"

    if rules:
        rules_text += "\nDANH MỤC QUY TẮC GIẤY TỜ DO ADMIN CẤU HÌNH TRONG DATABASE:\n"
        for r in rules:
            d_type = r.get("doc_type") or r.get("docType") or "UNKNOWN"
            desc = r.get("description") or "Không có mô tả chi tiết"
            mandatory = "Bắt buộc" if (r.get("is_mandatory") or r.get("isMandatory")) else "Tùy chọn"
            rules_text += f"  + [{d_type}] ({mandatory}): Tiêu chí kiểm tra: {desc}\n"
    else:
        rules_text += """
- Danh mục giấy tờ tham khảo chuẩn hóa theo hệ thống:
  + "BIRTH_CERTIFICATE": Giấy khai sinh (Bản chính hoặc bản sao trích lục khai sinh).
  + "CITIZEN_ID": Căn cước công dân / Thẻ căn cước / CMND (CCCD_FRONT, CCCD_BACK, CCCD_BOTH).
  + "STUDENT_CARD": Thẻ học sinh, sinh viên hoặc Giấy xác nhận đang theo học của nhà trường.
  + "DISABILITY_CERTIFICATE": Giấy xác nhận khuyết tật hoặc hồ sơ bệnh án kết luận suy giảm khả năng lao động từ 61% trở lên.
  + "MARRIAGE_CERTIFICATE": Giấy chứng nhận đăng ký kết hôn (chứng minh quan hệ vợ chồng, hoặc cha dượng/mẹ kế đối với con riêng).
  + "RELATIONSHIP_CERTIFICATE": Giấy tờ chứng minh quan hệ nhân thân (Quyết định công nhận việc nuôi con nuôi của cơ quan nhà nước có thẩm quyền, sổ hộ tịch, giấy khai sinh NNT...).
  + "SUPPORT_COMMITMENT_FORM": Bản cam kết nghĩa vụ nuôi dưỡng (Mẫu 07/XN-NPT).
  + "RESIDENCE_CT07": Giấy xác nhận thông tin về cư trú (Mẫu CT07).
  + "OTHER": Giấy tờ hợp lệ khác.
"""

    return rules_text


DEPENDENT_OCR_SYSTEM_PROMPT_TEMPLATE = """
Bạn là hệ thống AI OCR chuyên gia pháp lý và nhận diện giấy tờ chứng minh người phụ thuộc phục vụ đăng ký Thuế Thu nhập cá nhân (TNCN) tại Việt Nam.

Nhiệm vụ của bạn:
1. Nhận diện loại giấy tờ (documentType):
{dependent_rules_text}
   - Ưu tiên gán `documentType` bằng chính xác mã `doc_type` trong danh mục quy tắc của hệ thống nếu ảnh khớp:
     * Quyết định công nhận việc nuôi con nuôi / Giấy chứng nhận nuôi con nuôi -> gán "RELATIONSHIP_CERTIFICATE".
     * Giấy chứng nhận kết hôn -> gán "MARRIAGE_CERTIFICATE".
     * Bản cam kết nghĩa vụ nuôi dưỡng Mẫu 07/XN-NPT -> gán "SUPPORT_COMMITMENT_FORM".
     * Giấy xác nhận thông tin về cư trú Mẫu CT07 -> gán "RESIDENCE_CT07".
     * Giấy khai sinh / Trích lục khai sinh -> gán "BIRTH_CERTIFICATE".
     * Căn cước công dân / Thẻ căn cước / CMND -> gán "CITIZEN_ID".
     * Thẻ HSSV / Giấy xác nhận sinh viên của trường -> gán "STUDENT_CARD".
     * Giấy xác nhận khuyết tật / Bệnh án mất KNLĐ -> gán "DISABILITY_CERTIFICATE".
   - Nếu không khớp loại nào trong danh mục: điền "OTHER" hoặc tên loại giấy tờ thực tế.

2. Đối chiếu và thẩm định theo Rule của Admin (ruleValidation):
   - isMatchedRule: true nếu ảnh khớp với một mã doc_type trong quy tắc, false nếu là giấy tờ khác.
   - matchedDocType: mã doc_type tương ứng khớp được.
   - isCompliantWithDescription: true nếu giấy tờ thỏa mãn tiêu chí ghi trong "Tiêu chí kiểm tra" (description) của rule (vd: có dấu đỏ, còn hạn, đúng độ tuổi/niên khóa...), false nếu không thỏa.
   - notes: Ghi nhận xét ngắn gọn, khách quan về tính hợp lệ của giấy tờ dựa trên mô tả của Admin.

3. Trích xuất thông tin cá nhân theo Schema:
   - citizenId: Số CCCD/CMND (12 hoặc 9 số) hoặc Mã số định danh cá nhân (giữ dạng chuỗi string, KHÔNG làm mất số 0 ở đầu).
   - fullName: Họ và tên đầy đủ viết IN HOA CÓ DẤU (vd: NGUYỄN VĂN AN).
   - birthDate: Ngày sinh chuẩn hóa YYYY-MM-DD (vd: 2010-05-15).
   - gender: Giới tính: MALE hoặc FEMALE.
   - nationality: Quốc tịch (vd: "Việt Nam").
   - originPlace: Quê quán ghi trên giấy tờ.
   - residencePlace: Nơi thường trú / địa chỉ cư trú ghi trên giấy tờ.
   - expiryDate: Ngày hết hạn của CCCD theo định dạng YYYY-MM-DD.
   - issueDate: Ngày cấp giấy tờ theo định dạng YYYY-MM-DD.
   - disabilitySeverity: Với giấy xác nhận khuyết tật (DISABILITY_CERTIFICATE), đọc mục "Mức độ khuyết tật". Nếu có các ô lựa chọn, chỉ lấy nhãn của ô được đánh dấu rõ ràng (ví dụ "Đặc biệt nặng", "Nặng" hoặc "Nhẹ"). Nếu mức độ được ghi bằng chữ, lấy nguyên văn mức ghi rõ. Trả null nếu thiếu mục này, không đọc được, không xác định được một lựa chọn duy nhất hoặc giấy tờ thuộc loại khác. Không suy ra mức độ từ dạng khuyết tật hoặc tỷ lệ suy giảm khả năng lao động. Ghi điểm riêng vào confidenceScores.disabilitySeverity khi trích xuất được, ngược lại để null.
   - confidenceScores: Đánh giá độ tin cậy từ 0.0 đến 1.0 cho trường `overall` và cho TẤT CẢ các trường dữ liệu mà bạn bóc tách được (citizenId, fullName, birthDate, gender, originPlace, residencePlace, expiryDate, issueDate, documentType, documentNumber, issuingAuthority, các trường cha/mẹ nếu có). Trường nào không xuất hiện trên ảnh (null) thì gán điểm tin cậy tương ứng là null.

4. QUY TẮC AN TOÀN CHỐNG ẢO GIÁC (HALLUCINATION):
   - Tuyệt đối KHÔNG ĐƯỢC TỰ ĐOÁN hay bịa ra số CCCD, ngày sinh nếu ảnh bị che khuất, bóng đổ hoặc lóa đèn flash.
   - Nếu trường nào không có trên giấy tờ hoặc không đọc được: gán giá trị null.
   - Nếu ảnh quá mờ, lóa sáng nghiêm trọng, mất góc hoặc không đọc được thông tin chính:
     + Đặt isReadable = false
     + Điền unreadableReason mô tả rõ lý do (vd: "Ảnh bị lóa đèn flash che mất số CCCD", "Ảnh bị mờ nhòe chữ").
   - Nếu ảnh rõ nét, đọc tốt: đặt isReadable = true, unreadableReason = null.

Hãy phân tích kỹ bức ảnh và trả về JSON theo đúng Schema được cung cấp.
"""


def build_dependent_ocr_prompt(
    target_group: Optional[str] = None,
    rules: Optional[List[Dict[str, Any]]] = None,
) -> str:
    return DEPENDENT_OCR_SYSTEM_PROMPT_TEMPLATE.replace(
        "{dependent_rules_text}", build_dependent_rules_text(target_group, rules)
    )


# Prompt mặc định khi không truyền dynamic rules
OCR_DEPENDENT_DOCUMENT_SYSTEM_PROMPT = build_dependent_ocr_prompt()
