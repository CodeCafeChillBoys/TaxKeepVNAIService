from typing import Optional, List, Dict, Any


def build_dependent_ocr_prompt(
    target_group: Optional[str] = None, 
    rules: Optional[List[Dict[str, Any]]] = None
) -> str:
    rules_text = ""
    if rules:
        rules_text += "\nDANH MỤC QUY TẮC GIẤY TỜ DO ADMIN CẤU HÌNH TRONG DATABASE:\n"
        if target_group:
            rules_text += f"- Nhóm đối tượng đang thẩm định: {target_group}\n"
        for r in rules:
            d_type = r.get("doc_type") or r.get("docType") or "UNKNOWN"
            desc = r.get("description") or "Không có mô tả chi tiết"
            mandatory = "Bắt buộc" if (r.get("is_mandatory") or r.get("isMandatory")) else "Tùy chọn"
            rules_text += f"  + [{d_type}] ({mandatory}): Tiêu chí kiểm tra: {desc}\n"
    else:
        rules_text = """
- Danh mục giấy tờ tham khảo chuẩn:
  + "CITIZEN_ID": Căn cước công dân / Thẻ căn cước / CMND (CCCD_FRONT, CCCD_BACK, CCCD_BOTH).
  + "BIRTH_CERTIFICATE": Giấy khai sinh (Bản chính hoặc bản sao trích lục).
  + "STUDENT_CARD": Thẻ học sinh, sinh viên hoặc giấy xác nhận đang theo học của trường.
  + "DISABILITY_CERTIFICATE": Giấy xác nhận khuyết tật hoặc giấy chứng nhận suy giảm khả năng lao động.
  + "MARRIAGE_CERTIFICATE": Giấy chứng nhận kết hôn.
  + "RELATIONSHIP_CERTIFICATE": Giấy tờ chứng minh quan hệ cha mẹ/con cái hợp pháp (Khai sinh NNT, sổ hộ tịch...).
  + "SUPPORT_COMMITMENT_FORM": Bản cam kết nghĩa vụ nuôi dưỡng (Mẫu 07/XN-NPT).
  + "RESIDENCE_CT07": Giấy xác nhận thông tin về cư trú (Mẫu CT07).
  + "OTHER": Giấy tờ hợp lệ khác.
"""

    return f"""
Bạn là hệ thống AI OCR chuyên gia pháp lý và nhận diện giấy tờ chứng minh người phụ thuộc phục vụ đăng ký Thuế Thu nhập cá nhân (TNCN) tại Việt Nam.

Nhiệm vụ của bạn:
1. Nhận diện loại giấy tờ (documentType):
{rules_text}
   - Ưu tiên gán `documentType` bằng chính xác mã `doc_type` trong danh mục quy tắc của hệ thống nếu ảnh khớp.
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


# Prompt mặc định khi không truyền dynamic rules
OCR_DEPENDENT_DOCUMENT_SYSTEM_PROMPT = build_dependent_ocr_prompt()