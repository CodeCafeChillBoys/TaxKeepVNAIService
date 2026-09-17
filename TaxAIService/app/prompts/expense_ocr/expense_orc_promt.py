
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
- Mã 'UNSUPPORTED': Chọn mã này nếu tài liệu KHÔNG thuộc bất kỳ danh mục nào ở trên (ví dụ hóa đơn cafe, ăn uống, vé xem phim, ảnh rác, giấy tờ cá nhân không liên quan...).

NHIỆM VỤ:
1. Đọc ảnh/tài liệu, phân tích nội dung và chọn ra 1 mã 'docTypeCode' phù hợp nhất.
2. Bóc tách các trường: sellerName, sellerTaxCode, sellerAddress, sellerPhone, invoiceSeries, invoiceNumber, invoiceDate (YYYY-MM-DD), extractedYear, buyerName, buyerIdCard, buyerAddress, paymentMethod, totalAmount, totalAmountInWords, lookupUrl, lookupCode.
3. Trong mảng 'fields', liệt kê từng trường bóc tách được, chấm điểm confidenceScore (0.0 đến 1.0) và boundingBox [x, y, w, h] trên ảnh. Chữ bị mờ hoặc số bị nhòe thì hạ điểm confidenceScore < 0.75.
"""

_build_prompt = build_expense_ocr_prompt