import os
import uuid
import re
from urllib.parse import urlparse
from typing import Optional
from fastapi import APIRouter, UploadFile, File, Form, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from app.infrastructure.database import get_db
from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.services.pdf_service import pdf_service, PDFProcessingError
from app.services.tax_rule_extraction_service import tax_rule_extraction_service
from app.core.config import settings
from app.schemas import TaxRuleUploadResponse, TaxRuleApproveResponse

router = APIRouter(prefix="/api/tax-rules", tags=["Tax Rules Extraction"])


def is_valid_url(url: str) -> bool:
    try:
        result = urlparse(url)
        return all([result.scheme in ("http", "https"), result.netloc])
    except Exception:
        return False


@router.post(
    "/documents/upload",
    response_model=TaxRuleUploadResponse,
    summary="Upload văn bản PDF luật thuế và AI trích xuất Tax Rules"
)
async def upload_and_extract_tax_rules(
    file: Optional[UploadFile] = File(None),
    taxYear: Optional[str] = Form(None),
    name: Optional[str] = Form(None),
    sourceUrl: Optional[str] = Form(None),
    db: Session = Depends(get_db)
):
    # 1. Kiểm tra trường file bắt buộc
    if file is None or not file.filename:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "The file field is required."}
        )

    # 2. Kiểm tra định dạng PDF
    if not file.filename.lower().endswith(".pdf"):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "The file must be a PDF."}
        )

    # 3. Kiểm tra trường taxYear bắt buộc
    if taxYear is None or str(taxYear).strip() == "":
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"TaxYear": "The TaxYear field is required."}
        )

    # 4. Kiểm tra taxYear hợp lệ (phải là số nguyên, 4 chữ số)
    try:
        tax_year_int = int(str(taxYear).strip())
        if tax_year_int < 1900 or tax_year_int > 2100:
            raise ValueError()
    except (ValueError, TypeError):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": "Tax year must be a valid year."}
        )

    # 5. Kiểm tra SourceUrl nếu có truyền vào
    if sourceUrl and sourceUrl.strip():
        if not is_valid_url(sourceUrl.strip()):
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"SourceUrl": "The SourceUrl must be a valid URL."}
            )

    # 6. Kiểm tra kích thước file (tối đa 20 MB)
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    file_bytes = await file.read()
    if len(file_bytes) > max_bytes:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"message": f"The file size must not exceed {settings.MAX_FILE_SIZE_MB} MB."}
        )

    # 7. Kiểm tra trùng lặp taxYear trước khi xử lý AI để tiết kiệm tài nguyên
    existing_rule_set = db.query(TaxRuleSet).filter(TaxRuleSet.tax_year == tax_year_int).first()
    if existing_rule_set:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"message": "A tax rule set for this tax year already exists."}
        )

    # 8. Lưu file tạm thời vào thư mục uploads
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    temp_file_name = f"{uuid.uuid4()}_{file.filename}"
    temp_file_path = os.path.join(settings.UPLOAD_DIR, temp_file_name)

    with open(temp_file_path, "wb") as f:
        f.write(file_bytes)

    try:
        # 9. Bóc tách text bằng PyMuPDF (Nếu là ảnh scan thì lấy dữ liệu nhị phân gửi Gemini Vision)
        try:
            is_scanned, pdf_text, scan_bytes = pdf_service.prepare_pdf_for_ai(temp_file_path, max_scan_pages=30)
        except PDFProcessingError as pe:
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={"message": "No tax rule information could be extracted from the document."}
            )

        # 10. Gọi AI Engine (Gemini) để bóc tách các trường tax_rule_sets & tax_rules
        try:
            extracted_data = tax_rule_extraction_service.extract_tax_rules(
                document_text=pdf_text if not is_scanned else None,
                pdf_bytes=scan_bytes if is_scanned else None,
                tax_year=tax_year_int,
                rule_set_name=name,
                source_url=sourceUrl,
                legal_doc_name=file.filename
            )
        except HTTPException as he:
            return JSONResponse(
                status_code=he.status_code,
                content={"message": he.detail}
            )


        # 11. Kiểm tra trùng lặp ruleCode trong database
        rule_codes = [r["ruleCode"] for r in extracted_data.get("taxRules", []) if "ruleCode" in r]
        if rule_codes:
            existing_rule = db.query(TaxRule).filter(TaxRule.rule_code.in_(rule_codes)).first()
            if existing_rule:
                return JSONResponse(
                    status_code=status.HTTP_409_CONFLICT,
                    content={"message": "The rule code already exists."}
                )

        # 12. Lưu bản nháp (Draft) vào database trong một Transaction
        rule_set_dict = extracted_data["taxRuleSet"]
        new_rule_set = TaxRuleSet(
            name=rule_set_dict["name"],
            tax_year=tax_year_int,
            effective_from=rule_set_dict.get("effectiveFrom"),
            effective_to=rule_set_dict.get("effectiveTo"),
            status="Draft"
        )
        db.add(new_rule_set)
        db.flush()  # Lấy rule_set_id vừa sinh

        new_rules = []
        for item in extracted_data["taxRules"]:
            val = item.get("value")
            numeric_val = float(val) if val is not None else None
            
            rule_obj = TaxRule(
                rule_set_id=new_rule_set.rule_set_id,
                rule_code=item["ruleCode"],
                rule_name=item["ruleName"],
                rule_type=item["ruleType"],
                condition=item.get("condition"),
                value=numeric_val,
                unit=item.get("unit"),
                effective_from=item.get("effectiveFrom") or rule_set_dict.get("effectiveFrom"),
                effective_to=item.get("effectiveTo") or rule_set_dict.get("effectiveTo"),
                legal_document=item.get("legalDocument") or file.filename,
                article=str(item.get("article")) if item.get("article") is not None else None,
                clause=str(item.get("clause")) if item.get("clause") is not None else None,
                point=str(item.get("point")) if item.get("point") is not None else None,
                source_url=item.get("sourceUrl") or sourceUrl,
                status="Draft",
                version=int(item.get("version", 1))
            )
            new_rules.append(rule_obj)

        db.add_all(new_rules)
        db.commit()

        # 13. Chuẩn bị response trả về cho Admin theo đúng Response sample
        response_payload = {
            "message": "Tax document processed successfully.",
            "data": {
                "taxRuleSet": {
                    "name": new_rule_set.name,
                    "taxYear": new_rule_set.tax_year,
                    "effectiveFrom": new_rule_set.effective_from,
                    "effectiveTo": new_rule_set.effective_to,
                    "status": new_rule_set.status
                },
                "taxRules": [
                    {
                        "ruleCode": r.rule_code,
                        "ruleName": r.rule_name,
                        "ruleType": r.rule_type,
                        "condition": r.condition,
                        "value": r.value,
                        "unit": r.unit,
                        "effectiveFrom": r.effective_from,
                        "effectiveTo": r.effective_to,
                        "legalDocument": r.legal_document,
                        "article": r.article,
                        "clause": r.clause,
                        "point": r.point,
                        "sourceUrl": r.source_url,
                        "status": r.status,
                        "version": r.version
                    }
                    for r in new_rules
                ]
            }
        }

        return JSONResponse(status_code=status.HTTP_200_OK, content=response_payload)

    except Exception as e:
        db.rollback()
        raise e


@router.post(
    "/{id}/approve",
    response_model=TaxRuleApproveResponse,
    summary="Phê duyệt Tax Rule Set sang Active"
)
def approve_tax_rule_set(
    id: uuid.UUID,
    db: Session = Depends(get_db)
):
    rule_set = db.query(TaxRuleSet).filter(TaxRuleSet.rule_set_id == id).first()
    if not rule_set:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tax rule set not found."
        )

    # Chuyển trạng thái TaxRuleSet sang Active
    rule_set.status = "Active"

    # Chuyển trạng thái toàn bộ TaxRule liên kết sang Active
    db.query(TaxRule).filter(TaxRule.rule_set_id == id).update({"status": "Active"})
    db.commit()

    return {
        "message": "Tax rule set approved successfully.",
        "ruleSetId": str(rule_set.rule_set_id),
        "status": "Active"
    }
