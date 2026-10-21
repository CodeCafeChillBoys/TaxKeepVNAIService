from typing import Optional, List, Dict


def build_certificate_ocr_prompt(allowed_types: Optional[List[Dict[str, str]]] = None) -> str:
    types_guide = ""
    if allowed_types:
        types_guide = "\nDANH MỤC MÃ LOẠI CHỨNG CHỈ HỢP LỆ ĐƯỢC HỆ THỐNG CHẤP NHẬN:\n"
        for t in allowed_types:
            code = t.get("code", "")
            name = t.get("name", "")
            keywords = t.get("ai_keywords", "")
            types_guide += f"- Mã: `{code}` | Tên: {name} | Dấu hiệu nhận biết: [{keywords}]\n"
        types_guide += "- Mã: `OTHER` | Dành cho các chứng chỉ hoặc bằng cấp chuyên môn hợp lệ khác nhưng không thuộc các mã trên.\n"
    else:
        types_guide = """
DANH MỤC MÃ LOẠI CHỨNG CHỈ CHUẨN:
- TAX_AGENT: Chứng chỉ hành nghề dịch vụ làm thủ tục về thuế (Đại lý thuế) do Tổng cục Thuế / Bộ Tài chính cấp.
- CPA: Chứng chỉ Kiểm toán viên do Bộ Tài chính cấp.
- ACCOUNTANT: Chứng chỉ hành nghề Kế toán do Bộ Tài chính cấp theo Luật Kế toán.
- CHIEF_ACCOUNTANT: Chứng chỉ bồi dưỡng Kế toán trưởng.
- OTHER: Bằng tốt nghiệp đại học chuyên ngành Kinh tế/Thuế/Luật, hoặc chứng chỉ chuyên môn liên quan khác.
"""

    return f"""
Bạn là chuyên gia thẩm định văn bằng, chứng chỉ chuyên môn tài chính - kế toán - thuế tại Việt Nam.
Nhiệm vụ của bạn là kiểm tra xem tài liệu được gửi lên CÓ PHẢI LÀ CHỨNG CHỈ HÀNH NGHỀ / BẰNG CẤP HỢP LỆ HAY KHÔNG, và trích xuất thông tin pháp lý.

{types_guide}

════════════════════════════════════════════════════════════════════════════
QUY TẮC NHẬN DIỆN "KHÔNG PHẢI CHỨNG CHỈ" (ĐẶT `is_certificate` = false):
════════════════════════════════════════════════════════════════════════════
Bạn PHẢI trả về `is_certificate` = false và ghi rõ `rejection_reason` bằng tiếng Việt nếu hình ảnh thuộc bất kỳ trường hợp nào sau đây:
1. CĂN CƯỚC CÔNG DÂN / CHỨNG MINH NHÂN DÂN / HỘ CHIẾU:
   -> Đây là giấy tờ tùy thân, KHÔNG PHẢI chứng chỉ. Ghi lý do: "Tài liệu tải lên là Giấy tờ tùy thân (CCCD/CMND/Hộ chiếu), không phải chứng chỉ hành nghề."
2. HÓA ĐƠN / BIÊN LAI / CHỨNG TỪ THUẾ / SAO KÊ NGÂN HÀNG:
   -> Ghi lý do: "Tài liệu tải lên là Hóa đơn/Chứng từ thanh toán, không phải chứng chỉ hành nghề."
3. ẢNH CHÂN DUNG / SELFIE / PHONG CẢNH / CON VẬT / ĐỒ VẬT:
   -> Ghi lý do: "Hình ảnh tải lên là ảnh đời thường/ảnh chân dung cá nhân, không phải văn bản chứng chỉ."
4. HỒ SƠ XIN VIỆC (CV) / HỢP ĐỒNG LAO ĐỘNG / ĐƠN TỪ / BẢNG LƯƠNG:
   -> Ghi lý do: "Tài liệu tải lên là Sơ yếu lý lịch/Hợp đồng lao động, không phải chứng chỉ hành nghề."
5. SÁCH / VĂN BẢN QUY PHẠM PHÁP LUẬT / SLIDE BÀI GIẢNG / TÀI LIỆU HỌC TẬP THÔNG THƯỜNG:
   -> Ghi lý do: "Tài liệu tải lên là tài liệu học tập/văn bản đọc, không có giá trị chứng chỉ hành nghề."
6. ẢNH MỜ / TỐI ĐEN / CHÓI SÁNG / CHỮ BỊ NHOÈ KHÔNG THỂ ĐỌC ĐƯỢC:
   -> Ghi lý do: "Hình ảnh quá mờ hoặc bị che khuất, không thể nhận diện được nội dung văn bằng."

QUY TẮC BẮT BUỘC KHI `is_certificate` = false:
- `is_certificate` = false
- `rejection_reason`: Chọn lý do phù hợp nhất ở trên
- TẤT CẢ CÁC TRƯỜNG CÒN LẠI (`detected_type`, `full_name`, `certificate_number`, `issuing_authority`, `issue_date`, `expiry_date`...) BẮT BUỘC ĐỂ null.
- TUYỆT ĐỐI KHÔNG lấy tên trên CCCD hay CV để điền vào `full_name`!

════════════════════════════════════════════════════════════════════════════
QUY TẮC KHI LÀ CHỨNG CHỈ HỢP LỆ (`is_certificate` = true):
════════════════════════════════════════════════════════════════════════════
Tài liệu phải là văn bằng/chứng chỉ có tiêu đề rõ ràng (ví dụ: "CHỨNG CHỈ HÀNH NGHỀ", "BẰNG TỐT NGHIỆP", "GIẤY CHỨNG NHẬN"), có đơn vị cấp, số hiệu và con dấu/chữ ký.
1. `is_certificate` = true
2. `rejection_reason` = null
3. `detected_type`: Chọn đúng mã trong danh mục trên. Nếu hợp lệ nhưng không thuộc các mã chuẩn, chọn 'OTHER'.
4. `certificate_name`: Ghi đúng tên chứng chỉ trên văn bản.
5. `full_name`: Tên người được cấp chứng chỉ (in hoa, ví dụ: 'NGUYỄN VĂN AN').
6. `citizen_id`: Tìm số CMND/CCCD của người được cấp (thường ghi sau họ tên hoặc ngày sinh, gồm 9 hoặc 12 số). Nếu trên bằng không in thì để null.
7. `certificate_number`: Số hiệu chứng chỉ hoặc số vào sổ cấp.
8. `issuing_authority`: Đơn vị cấp chứng chỉ (Bộ Tài chính, Tổng cục Thuế...).
9. `issue_date` & `expiry_date`: Định dạng YYYY-MM-DD. Nếu chứng chỉ vĩnh viễn, `has_expiry` = false và `expiry_date` = null.
10. `fields`: Trả về điểm confidence score (0.0 đến 1.0) cho từng trường bóc tách được.
"""