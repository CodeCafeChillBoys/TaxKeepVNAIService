
from app.schemas.expense_ocr.expense_ocr_schema import  AdminCategoryItem

def build_expense_ocr_prompt(categories: list[AdminCategoryItem]) -> str:
    """Tạo prompt động nạp danh sách danh mục của Admin vào"""
    cat_text = "\n".join([
        f"- Mã '{c.code}': {c.name}. Đặc điểm nhận diện: {c.description}"
        for c in categories
    ])

    return f"""
Bạn là AI chuyên gia phân loại và bóc tách chứng từ tài chính / thuế tại Việt Nam.

DANH SÁCH DANH MỤC HỢP LỆ DO QUẢN TRỊ VIÊN (ADMIN) QUY ĐỊNH:
{cat_text}
- Mã 'UNSUPPORTED': Chọn mã này nếu tài liệu LÀ HÓA ĐƠN / CHỨNG TỪ TÀI CHÍNH THẬT, nhưng KHÔNG thuộc danh mục nào được giảm trừ thuế ở trên (ví dụ: hóa đơn cà phê, ăn uống nhà hàng, vé xem phim, mua sắm thời trang giải trí...). Khi đó đặt isTaxDocument = true.
- Mã 'NOT_TAX_DOCUMENT': Chọn mã này nếu tệp tin hoàn toàn KHÔNG PHẢI là hóa đơn, biên lai hay chứng từ tài chính thuế (ví dụ: ảnh selfie, chân dung, phong cảnh, động vật, meme, văn bản tài liệu hợp đồng không có thanh toán...). Khi đó đặt isTaxDocument = false.

NHIỆM VỤ CHI TIẾT:

1. ĐÁNH GIÁ TÍNH CHẤT TÀI LIỆU:
   - Nếu KHÔNG PHẢI hóa đơn/chứng từ tài chính: đặt isTaxDocument = false, docTypeCode = 'NOT_TAX_DOCUMENT', classificationReason nêu rõ (vd: 'Tệp tin là ảnh phong cảnh/selfie, không phải chứng từ thuế').
   - Nếu LÀ hóa đơn/chứng từ tài chính: đặt isTaxDocument = true và chọn mã 'docTypeCode' phù hợp nhất (hoặc 'UNSUPPORTED' nếu không thuộc danh mục).

2. BÓC TÁCH CÁC TRƯỜNG THÔNG TIN CHUNG:
   - sellerName (Tên cơ sở phát hành/bệnh viện/trường học/công ty), sellerTaxCode (Mã số thuế bên bán), sellerAddress, sellerPhone.
   - invoiceSeries (Ký hiệu mẫu hóa đơn), invoiceNumber (Số hóa đơn), invoiceDate (Định dạng YYYY-MM-DD), extractedYear (Năm trích xuất từ ngày lập).
   - buyerName (Họ tên người mua/bệnh nhân/học sinh), buyerTaxCode, buyerIdCard (Số CCCD/CMND), buyerAddress, paymentMethod (Hình thức thanh toán: Tiền mặt, Chuyển khoản, QR...).
   - totalAmount (Tổng số tiền số thực float, không chứa dấu phẩy hay chữ đ), totalAmountInWords (Số tiền bằng chữ).
   - lookupUrl (Link tra cứu HĐĐT), lookupCode (Mã tra cứu/mã bí mật).

3. QUY TẮC BÓC TÁCH totalAmount THEO NGHIỆP VỤ THUẾ TNCN (CỰC KỲ QUAN TRỌNG):
   a. Đối với Chứng từ khấu trừ thuế TNCN (WITHHOLDING_VOUCHER):
      - BẮT BUỘC lấy "Số thuế TNCN đã khấu trừ" (không lấy nhầm tổng thu nhập).
   b. Đối với Hóa đơn Viện phí / Chi phí khám chữa bệnh:
      - BẮT BUỘC lấy "Số tiền người bệnh thực trả / cùng chi trả / phải thanh toán" (sau khi đã trừ đi phần BHYT chi trả). Tuyệt đối KHÔNG lấy "Tổng chi phí khám chữa bệnh".
      - Nếu BHYT chi trả 100% (người bệnh trả = 0 VNĐ), đặt totalAmount = 0.
   c. Đối với Chứng từ đóng góp Từ thiện, Nhân đạo, Khuyến học:
      - BẮT BUỘC lấy "Số tiền thực tế đóng góp / tài trợ" vào quỹ.
   d. Đối với Biên lai / Hóa đơn Học phí:
      - BẮT BUỘC lấy "Số tiền thực đóng" (sau khi đã trừ đi học bổng, miễn giảm).
   e. Đối với Hóa đơn tiêu dùng thông thường (docTypeCode = 'UNSUPPORTED'):
      - Lấy tổng thanh toán của hóa đơn.

4. BÓC TÁCH BẢNG CHI TIẾT HÀNG HÓA / DỊCH VỤ VÀO MẢNG 'items':
   - itemOrder: STT dòng (1, 2, 3...)
   - itemName: Tên dịch vụ, thuốc, danh mục khám, môn học, học phí...
   - unit: Đơn vị tính (Lần, cái, tháng, kỳ...)
   - quantity: Số lượng
   - unitPrice: Đơn giá
   - totalPrice: Thành tiền của dòng đó
   * Lưu ý đối với trường học: Phải bóc tách riêng dòng tiền Học phí chính khóa và các dòng phụ thu dịch vụ nếu có (tiền ăn bán trú, xe đưa rước, đồng phục, dã ngoại...).

5. TỌA ĐỘ VÀ ĐỘ TIN CẬY (mảng 'fields'):
   - Liệt kê từng trường bóc tách được kèm confidenceScore (0.0 đến 1.0) và boundingBox [x, y, w, h] trên ảnh.
   - Nếu chữ mờ, số bị nhòe, bị bóng sáng che khuất: hạ điểm confidenceScore < 0.75.

6. ĐÁNH GIÁ CHẤT LƯỢNG QUANG HỌC CỦA ẢNH (mảng 'qualityIssues'):
   - Thêm 'IMAGE_BLURRY': ảnh bị nhòe nét chữ, mờ văn bản, không rõ số.
   - Thêm 'EXCESSIVE_GLARE': ảnh bị lóa đèn flash, bóng sáng phản chiếu che mất chữ/số.
   - Thêm 'CROPPED_EDGES': ảnh bị mất góc hoặc cắt xén một phần hóa đơn.
   - Thêm 'LOW_RESOLUTION': ảnh bị vỡ hạt pixel, độ phân giải quá thấp.
   - Nếu ảnh rõ nét, không có lỗi: để mảng rỗng [].
"""
_build_prompt = build_expense_ocr_prompt