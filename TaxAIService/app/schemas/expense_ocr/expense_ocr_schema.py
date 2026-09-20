from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.enum.expense_document_enum import DocumentExtractionStatus


# 1. Schema cho từng danh mục Admin gửi sang
class AdminCategoryItem(BaseModel):
    code: str = Field(..., description="Mã danh mục, VD: MEDICAL_EXPENSE_INVOICE")
    name: str = Field(..., description="Tên hiển thị, VD: Chi phí y tế")
    description: str = Field(..., description="Mô tả đặc điểm để AI nhận diện")


# 2. Chi tiết từng trường kèm Bounding Box
class BoundingBox(BaseModel):
    x: int = 0
    y: int = 0
    w: int = 0
    h: int = 0


# Dùng để ocr bóc tách ra từng field
class ExtractedFieldDetail(BaseModel):
    fieldName: str
    extractedValue: Optional[str] = None
    # Dùng Field(...) để đánh dấu là REQUIRED trong schema gửi cho Gemini
    confidenceScore: float = Field(
        ..., 
        ge=0.0, 
        le=1.0, 
        description="Độ tin cậy từ 0.0 đến 1.0 dựa trên độ rõ nét thực tế của chữ/số trên ảnh (chữ rõ nét 0.9-1.0; chữ mờ, nhòe, bị che khuất thì < 0.7)"
    )
    boundingBox: Optional[BoundingBox] = None


# Chi tiết từng dòng hàng hóa / dịch vụ trên hóa đơn
class InvoiceLineItem(BaseModel):
    itemOrder: int = Field(1, description="Số thứ tự mặt hàng (1, 2, 3...)")
    itemName: str = Field(..., description="Tên hàng hóa, dịch vụ, danh mục khám, thuốc, học phí...")
    unit: Optional[str] = Field(None, description="Đơn vị tính (Lần, cái, tháng...)")
    quantity: float = Field(1.0, description="Số lượng")
    unitPrice: float = Field(0.0, description="Đơn giá")
    totalPrice: float = Field(0.0, description="Thành tiền = số lượng x đơn giá")


# 3. Kết quả Gemini trả về
class GeminiOcrOutput(BaseModel):
    # Phân loại
    docTypeCode: str = Field(
        description="Mã code danh mục khớp nhất trong danh sách Admin cung cấp, hoặc 'UNSUPPORTED' nếu không thuộc danh mục nào"
    )
    classificationReason: Optional[str] = Field(
        None, description="Lý do AI chọn danh mục này hoặc lý do từ chối"
    )

    # Thông tin bên bán (Bệnh viện / Trường học / ...)
    sellerName: Optional[str] = Field(None, description="Tên đơn vị phát hành")
    sellerTaxCode: Optional[str] = Field(None, description="Mã số thuế bên bán")
    sellerAddress: Optional[str] = None
    sellerPhone: Optional[str] = None

    # Thông tin hóa đơn
    invoiceSeries: Optional[str] = Field(None, description="Ký hiệu mẫu hóa đơn (VD: 2C26TBH)")
    invoiceNumber: Optional[str] = Field(None, description="Số hóa đơn (VD: 82621)")
    invoiceDate: Optional[str] = Field(None, description="Ngày lập YYYY-MM-DD")
    extractedYear: Optional[int] = Field(None, description="Năm trích xuất từ invoiceDate")

    # Thông tin người mua / bệnh nhân / học sinh
    buyerName: Optional[str] = Field(None, description="Họ tên người mua/bệnh nhân")
    buyerTaxCode: Optional[str] = None
    buyerIdCard: Optional[str] = Field(None, description="Số CCCD/CMND (VD: 079304010828)")
    buyerAddress: Optional[str] = None
    paymentMethod: Optional[str] = Field(None, description="Hình thức thanh toán (QR, Chuyển khoản, Tiền mặt...)")

    # Tài chính
    totalAmount: float = Field(0.0, description="Tổng số tiền thanh toán")
    totalAmountInWords: Optional[str] = Field(None, description="Số tiền viết bằng chữ")

    # Tra cứu
    lookupUrl: Optional[str] = Field(None, description="Đường dẫn tra cứu hóa đơn")
    lookupCode: Optional[str] = Field(None, description="Mã tra cứu / Mã bí mật")

    # Danh sách chi tiết từng hàng hóa / dịch vụ trên hóa đơn
    items: List[InvoiceLineItem] = Field(default_factory=list, description="Bảng danh sách các mặt hàng, dịch vụ, viện phí, học phí trong hóa đơn")

    # Danh sách chi tiết từng trường để lưu AI_EXTRACTIONS_Value
    fields: List[ExtractedFieldDetail] = Field(default_factory=list)


# 4. Response Schemas trả về cho Backend .NET
class ValidationStatus(BaseModel):
    isYearValid: bool = True
    isDocTypeValid: bool = True
    isIdentityValid: bool = True


class ProcessDocumentResponseData(BaseModel):
    id: str
    periodId: str
    userId: str
    docTypeCode: str

    fileUrl: str
    originalFilename: str
    invoiceSeries: Optional[str] = None
    invoiceNumber: Optional[str] = None
    invoiceDate: Optional[str] = None
    extractedYear: Optional[int] = None
    sellerName: Optional[str] = None
    sellerTaxCode: Optional[str] = None
    sellerAddress: Optional[str] = None
    sellerPhone: Optional[str] = None
    buyerName: Optional[str] = None
    buyerTaxCode: Optional[str] = None
    buyerIdCard: Optional[str] = None
    buyerAddress: Optional[str] = None
    paymentMethod: Optional[str] = None
    totalAmount: float = 0.0
    totalAmountInWords: Optional[str] = None
    lookupUrl: Optional[str] = None
    lookupCode: Optional[str] = None
    items: List[InvoiceLineItem] = Field(default_factory=list)
    validationStatus: ValidationStatus = Field(default_factory=ValidationStatus)
    validationErrors: List[str] = Field(default_factory=list)
    status: DocumentExtractionStatus = DocumentExtractionStatus.EXTRACTED
    createdAt: str


class ProcessDocumentResponse(BaseModel):
    message: str = "Document processed and validated successfully."
    data: ProcessDocumentResponseData
