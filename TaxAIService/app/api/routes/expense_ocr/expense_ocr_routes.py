import json
import uuid
from datetime import datetime, timezone
from typing import Optional, List
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, status, Depends
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.repositories.system_config import SystemConfigRepository
from app.schemas.expense_ocr.expense_ocr_schema import (
    AdminCategoryItem,
    ProcessDocumentResponse,
    ProcessDocumentResponseData,
    ValidationStatus
)
from app.enum.expense_document_enum import (
    DocumentExtractionStatus,
    DefaultExpenseDocTypeCode
)
from app.services.expense_ocr.expense_ocr_service import ExpenseOcrService


router = APIRouter(prefix="/api/ocr/expense", tags=["Expense Document OCR"])


ALLOWED_MIME_TYPES = {
    "image/jpeg", "image/png", "image/webp", "image/heic", "application/pdf"
}

DEFAULT_CATEGORIES = [
    AdminCategoryItem(
        code=DefaultExpenseDocTypeCode.MEDICAL_EXPENSE_INVOICE.value,
        name="Chi phí y tế & Khám chữa bệnh",
        description="Hóa đơn viện phí, bảng kê chi phí điều trị, phiếu thu tiền thuốc, khám bệnh tại bệnh viện, phòng khám"
    ),
    AdminCategoryItem(
        code=DefaultExpenseDocTypeCode.TUITION_FEE_INVOICE.value,
        name="Chi phí học phí & Giáo dục",
        description="Hóa đơn, biên lai thu học phí chính quy, học phí bán trú của học sinh, sinh viên tại trường học hoặc trung tâm"
    ),
    AdminCategoryItem(
        code=DefaultExpenseDocTypeCode.CHARITY_DONATION_RECEIPT.value,
        name="Đóng góp từ thiện nhân đạo",
        description="Biên nhận đóng góp cho các quỹ từ thiện, tổ chức nhân đạo, cứu trợ thiên tai hợp pháp"
    )
]



@router.post(
    "/extract",
    response_model=ProcessDocumentResponse,
    summary="[TEST] Bóc tách và phân loại hóa đơn y tế, giáo dục bằng Gemini Vision"
)
async def extract_expense_document(
    file: UploadFile = File(..., description="Ảnh chụp hóa đơn (JPG, PNG) hoặc file PDF"),
    target_year: int = Form(2026, description="Năm kỳ tính thuế cần đối soát (mặc định 2026)"),
    period_id: str = Form("c1a9f0e2-3a81-4bc9-9238-ec4f67d2681a", description="Mã kỳ tính thuế"),
    user_id: str = Form("u123-uuid", description="Mã người dùng"),
    categories_json: Optional[str] = Form(
        None, 
        description="JSON danh mục của Admin. Nếu để trống sẽ tự động dùng 3 danh mục mặc định (Y tế, Học phí, Từ thiện)"
    ),
    applied_threshold: Optional[float] = Form(
        None,
        description="Ngưỡng tin cậy áp dụng (nếu để trống, service sẽ tự động lấy ngưỡng từ DB system_configs)"
    ),
    db: Session = Depends(get_db)
):


    """
    Endpoint cho phép test trực tiếp bằng Swagger UI / Postman:
    1. Upload ảnh chụp hóa đơn (ví dụ Hóa đơn BV Lê Văn Việt)
    2. AI tự động phân loại vào danh mục Admin
    3. Trích xuất đầy đủ thông tin: bên bán, bên mua, số tiền, ngày lập, tra cứu...
    4. Trả về JSON chuẩn hợp đồng cho Backend .NET
    """
    # 1. Kiểm tra định dạng file
    content_type = file.content_type or "image/jpeg"
    if content_type not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Định dạng {content_type} không được hỗ trợ. Vui lòng tải file JPEG, PNG, WEBP hoặc PDF."
        )

    # 2. Xử lý danh mục của Admin
    categories = DEFAULT_CATEGORIES
    if categories_json and categories_json.strip():
        try:
            parsed = json.loads(categories_json)
            if isinstance(parsed, list):
                categories = [AdminCategoryItem.model_validate(c) for c in parsed]
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"categories_json không đúng định dạng JSON danh sách: {str(e)}"
            )

    # 3. Đọc dữ liệu file
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File tải lên không có dữ liệu (file rỗng)."
        )

    # 4. Khởi tạo Service với SystemConfigRepository và gọi AI OCR
    try:
        config_repo = SystemConfigRepository(db)
        ocr_service = ExpenseOcrService(repo=config_repo)
        ocr_result = await ocr_service.extract_and_classify(
            file_bytes=file_bytes,
            mime_type=content_type,
            target_year=target_year,
            categories=categories,
            applied_threshold=applied_threshold
        )

    except Exception as err:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Lỗi khi xử lý AI OCR: {str(err)}"
        )

    doc = ocr_result["data"]
    doc_id = str(uuid.uuid4())

    # 5. Đóng gói kết quả trả về
    response_data = ProcessDocumentResponseData(
        id=doc_id,
        periodId=period_id,
        userId=user_id,
        docTypeCode=doc.docTypeCode,

        fileUrl=f"temp://uploads/{file.filename}",
        originalFilename=file.filename or "invoice.jpg",
        invoiceSeries=doc.invoiceSeries,
        invoiceNumber=doc.invoiceNumber,
        invoiceDate=doc.invoiceDate,
        extractedYear=doc.extractedYear,
        sellerName=doc.sellerName,
        sellerTaxCode=doc.sellerTaxCode,
        sellerAddress=doc.sellerAddress,
        sellerPhone=doc.sellerPhone,
        buyerName=doc.buyerName,
        buyerTaxCode=doc.buyerTaxCode,
        buyerIdCard=doc.buyerIdCard,
        buyerAddress=doc.buyerAddress,
        paymentMethod=doc.paymentMethod,
        totalAmount=doc.totalAmount,
        totalAmountInWords=doc.totalAmountInWords,
        lookupUrl=doc.lookupUrl,
        lookupCode=doc.lookupCode,
        validationStatus=ValidationStatus(
            isYearValid=ocr_result["is_year_valid"],
            isDocTypeValid=ocr_result["is_doc_type_valid"],
            isIdentityValid=True
        ),
        validationErrors=ocr_result["validation_errors"],
        status=DocumentExtractionStatus.EXTRACTED,
        createdAt=datetime.now(timezone.utc).isoformat()
    )


    return ProcessDocumentResponse(
        message="Document processed and validated successfully.",
        data=response_data
    )
