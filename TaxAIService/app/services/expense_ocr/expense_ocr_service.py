# app/services/expense_ocr/expense_ocr_service.py
import json
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pydantic import ValidationError
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings
from app.services.apiKey.ai_key_manager import AiKeyManager
from app.repositories.interfaces.isystem_config_repository import ISystemConfigRepository
from app.schemas.expense_ocr.expense_ocr_schema import GeminiOcrOutput, AdminCategoryItem
from app.prompts.expense_ocr import (
    EXPENSE_OCR_SYSTEM_PROMPT,
    MEDICAL_STATEMENT_RULES,
    MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
    format_expense_categories,
    replace_medical_statement_rules,
    build_medical_categories_guide,
    build_medical_statement_prompt,
    build_expense_ocr_prompt,
)
from app.errors.expense_ocr_errors import CorruptedFileError, UnreadableDocumentError
from app.services.prompt_template.prompt_template_service import PromptTemplateService

logger = logging.getLogger(__name__)

def check_medical_statement_amounts(doc: GeminiOcrOutput, tolerance: float) -> List[str]:
    issues = dict.fromkeys(doc.crossCheckIssues)
    lines = [line for line in doc.medicalLines if not line.isPackageSubLine]
    section_cards = {
        section.sectionIndex: section.hasInsuranceCard for section in doc.medicalSections
    }

    def differs(expected: Optional[float], *parts: Optional[float]) -> bool:
        return (
            expected is not None
            and all(part is not None for part in parts)
            and abs(expected - sum(part for part in parts if part is not None)) > tolerance
        )

    for line in lines:
        has_card = section_cards.get(line.sectionIndex)
        if line.sectionIndex not in section_cards:
            issues["UNKNOWN_SECTION"] = None

        if has_card is False:
            mismatch = differs(line.hospitalAmount, line.patientSelfPay)
        else:
            mismatch = differs(line.hospitalAmount, line.insuranceAmount, line.patientSelfPay)
            if has_card is True:
                mismatch |= differs(
                    line.insuranceAmount, line.insuranceFundPaid, line.patientCoPay, line.otherSourcePaid
                )
        if mismatch:
            issues["LINE_SUM_MISMATCH"] = None

    if doc.medicalSummary and lines:
        summary_columns = {
            "totalHospitalAmount": "hospitalAmount",
            "coPayWithinInsurance": "patientCoPay",
            "otherPatientPayments": "patientSelfPay",
            "insuranceFundPaid": "insuranceFundPaid",
            "otherSourcePaid": "otherSourcePaid",
        }
        for summary_field, line_field in summary_columns.items():
            if differs(getattr(doc.medicalSummary, summary_field), *(getattr(line, line_field) for line in lines)):
                issues["SUMMARY_MISMATCH"] = None
                break
        if differs(
            doc.medicalSummary.patientPaid,
            doc.medicalSummary.coPayWithinInsurance,
            doc.medicalSummary.otherPatientPayments,
        ):
            issues["SUMMARY_MISMATCH"] = None

    return list(issues)


class ExpenseOcrService:
    def __init__(
        self, 
        repo: Optional[ISystemConfigRepository] = None,
        prompt_service: Optional[PromptTemplateService] = None
    ):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY) if settings.GEMINI_API_KEY else None
        self.model = settings.GEMINI_MODEL  # gemini-2.5-flash
        self.repo = repo
        self.prompt_service = prompt_service

    async def extract_and_classify(
        self,
        file_bytes: bytes,
        mime_type: str,
        target_year: int,
        categories: List[AdminCategoryItem],
        applied_threshold: Optional[float] = None,
        is_medical_statement_request: bool = False,
        expected_doc_type: Optional[str] = None
    ) -> Dict[str, Any]:

        # 1. Kiểm tra tệp tin rỗng hoặc hỏng trước khi gửi sang AI
        if not file_bytes or len(file_bytes) < 100:
            raise CorruptedFileError("Dữ liệu tệp tin rỗng hoặc quá nhỏ, tệp có thể bị hỏng trong quá trình tải.")

        medical_statement_codes = {c.code for c in categories if c.isMedicalStatement}

        # CHỌN SYSTEM PROMPT RIÊNG BIỆT DỰA VÀO LOẠI TÀI LIỆU
        if is_medical_statement_request:
            medical_doc_type = expected_doc_type or "MEDICAL_COST_STATEMENT"
            for c in categories:
                if c.isMedicalStatement:
                    medical_doc_type = c.code
                    break

            cat_text = format_expense_categories(categories)
            system_instruction = build_medical_statement_prompt(
                medical_doc_type=medical_doc_type,
                categories_text=cat_text,
                prompt_service=self.prompt_service,
            )
        else:
            system_instruction = build_expense_ocr_prompt(
                categories=categories,
                prompt_service=self.prompt_service,
            )

        # 2. Gọi Gemini Multimodal Vision và bắt tách bạch lỗi
        try:
            def _call_gemini(client, model):
                return client.models.generate_content(
                    model=model,
                    contents=[
                        types.Part.from_bytes(data=file_bytes, mime_type=mime_type)
                    ],
                    config=types.GenerateContentConfig(
                        http_options=types.HttpOptions(api_version="v1beta"),
                        system_instruction=system_instruction,
                        response_mime_type="application/json",
                        response_schema=GeminiOcrOutput,
                        temperature=0.1
                    )
                )

            db_session = self.repo.db if self.repo and hasattr(self.repo, "db") else None
            response = AiKeyManager.execute_with_failover(db_session, _call_gemini, default_client=self.client)
            raw_json = response.text
            if not raw_json or not raw_json.strip():
                raise UnreadableDocumentError("AI Engine không nhận diện được bất kỳ nội dung nào từ tài liệu.")

        except APIError as api_err:
            logger.error(f"Google GenAI APIError khi phân tích tài liệu: {api_err}", exc_info=True)
            # Lỗi do định dạng tệp ảnh bị hỏng khiến Vision Engine không mở được
            raise CorruptedFileError(f"AI Engine không thể mở tệp tin do lỗi định dạng hoặc tệp bị hỏng: {str(api_err)}")

        except Exception as gen_err:
            logger.error(f"Lỗi không xác định khi gọi Gemini API: {gen_err}", exc_info=True)
            raise UnreadableDocumentError()

        # 3. Parse JSON sang Pydantic Model
        try:
            doc_data = GeminiOcrOutput.model_validate_json(raw_json)
        except ValidationError as val_err:
            logger.error(f"Lỗi validate schema JSON từ kết quả Gemini: {val_err}\nRaw: {raw_json}", exc_info=True)
            raise UnreadableDocumentError(
                message="AI Engine could not parse the document. The image quality may be too blurry or illegible."
            )

        if is_medical_statement_request:
            doc_data.docTypeCode = medical_doc_type
            doc_data.isTaxDocument = True
            doc_data.invoiceSeries = None
            doc_data.sellerTaxCode = None
            doc_data.sellerPhone = None
            doc_data.buyerTaxCode = None
            doc_data.lookupUrl = None
            doc_data.lookupCode = None
            doc_data.items = []
            if doc_data.medicalHeader:
                doc_data.sellerName = doc_data.medicalHeader.facilityName or doc_data.sellerName
                doc_data.buyerName = doc_data.medicalHeader.patientName or doc_data.buyerName
                doc_data.invoiceDate = doc_data.medicalHeader.visitDate or doc_data.invoiceDate
            if doc_data.medicalSummary:
                doc_data.totalAmount = (
                    doc_data.medicalSummary.patientPaid
                    if doc_data.medicalSummary.patientPaid is not None
                    else doc_data.medicalSummary.totalHospitalAmount
                )

        # 4. Kiểm tra nghiệp vụ (Business Rules Validation)
        validation_errors = []

        # 4.0. CASE 10: Kiểm tra tệp tin có phải chứng từ thuế / hóa đơn hợp lệ không
        is_tax_document = getattr(doc_data, "isTaxDocument", True)
        if not is_tax_document or doc_data.docTypeCode == "NOT_TAX_DOCUMENT":
            validation_errors.append({
                "code": "ERR_NOT_TAX_DOCUMENT",
                "field": "file",
                "message": "Uploaded file is not recognized as a valid tax document."
            })
            is_doc_type_valid = False
        else:
            # 4.1. CASE 6: Kiểm tra loại tài liệu có hợp lệ trong danh mục giảm trừ không
            valid_codes = [c.code for c in categories]
            is_doc_type_valid = doc_data.docTypeCode in valid_codes
            if not is_doc_type_valid:
                validation_errors.append({
                    "code": "ERR_INVALID_DOC_TYPE",
                    "field": "docTypeCode",
                    "message": doc_data.classificationReason or "This document category does not qualify for tax relief or deductions."
                })


        # 4.2. Kiểm tra năm tính thuế
        is_year_valid = True
        # Chứng từ khấu trừ có thể được lập vào năm sau năm phát sinh thu nhập.
        # Vì vậy kỳ tính thuế phải đối chiếu với incomeYear, không phải ngày lập chứng từ.
        year_to_validate = (
            doc_data.incomeYear
            if doc_data.docTypeCode == "WITHHOLDING_VOUCHER"
            else doc_data.extractedYear
        )
        year_field = (
            "incomeYear"
            if doc_data.docTypeCode == "WITHHOLDING_VOUCHER"
            else "extractedYear"
        )
        if year_to_validate and year_to_validate != target_year:
            is_year_valid = False
            validation_errors.append({
                "code": "ERR_YEAR_MISMATCH",
                "field": year_field,
                "message": f"Document income year is {year_to_validate} but filing year is {target_year}."
            })

        # 4.3. Kiểm tra ngày hóa đơn không được ở tương lai (ERR_FUTURE_DATE)
        if doc_data.invoiceDate:
            try:
                # Chuẩn hóa định dạng YYYY-MM-DD
                inv_date = datetime.strptime(doc_data.invoiceDate.strip(), "%Y-%m-%d").date()
                today_utc = datetime.now(timezone.utc).date()
                if inv_date > today_utc:
                    validation_errors.append({
                        "code": "ERR_FUTURE_DATE",
                        "field": "invoiceDate",
                        "message": "Invoice date cannot be greater than the current date."
                    })
            except ValueError:
                pass

        # 5. Phân giải Ngưỡng động 3 tầng từ Database
        doc_type = doc_data.docTypeCode if doc_data else None
        is_medical_statement = is_medical_statement_request or (doc_type in medical_statement_codes)
        if self.repo:
            if applied_threshold is None:
                applied_threshold = self.repo.get_system_threshold(category_code=doc_type)
            crucial_fields = self.repo.get_crucial_fields(category_code=doc_type) if not is_medical_statement else set()
        else:
            if applied_threshold is None:
                applied_threshold = 0.80
            crucial_fields = set() if is_medical_statement else {"total_amount", "seller_tax_code", "buyer_id_card", "invoice_number"}

        # 6. Tính điểm tin cậy tổng thể (overall_confidence)
        scores = [f.confidenceScore for f in doc_data.fields]
        if is_medical_statement:
            tolerance = (
                self.repo.get_float_value("MEDICAL_STATEMENT_AMOUNT_TOLERANCE", 1000.0)
                if self.repo else 1000.0
            )
            doc_data.crossCheckIssues = check_medical_statement_amounts(doc_data, tolerance)
            scores.extend(line.confidenceScore for line in doc_data.medicalLines if not line.isPackageSubLine)
        if scores:
            overall_confidence = round(sum(scores) / len(scores), 2)
        else:
            overall_confidence = 0.0
            validation_errors.append({
                "code": "ERR_NO_FIELDS_EXTRACTED",
                "field": "fields",
                "message": "Không trích xuất được trường thông tin nào từ tài liệu."
            })

        # 7. Kiểm tra ngưỡng và bảo vệ trường cốt lõi (Crucial Fields)
        # Check ngưỡng từng trường vừa tính lại bên trên công lại chia độ dài
        # Nếu mà lớn hơn thì return data
        # Nhỏ hơn tiến hành quăng lỗi
        is_passed_threshold = overall_confidence >= applied_threshold
        low_confidence_fields = []
        has_crucial_low_confidence = False

        for f in doc_data.fields:
            if f.confidenceScore < applied_threshold:
                low_confidence_fields.append({
                    "fieldName": f.fieldName,
                    "extractedValue": f.extractedValue,
                    "confidenceScore": f.confidenceScore,
                    "threshold": applied_threshold
                })
                # nếu nhỏ hơn đánh dấu trường trường lạị
                if f.fieldName in crucial_fields:
                    has_crucial_low_confidence = True

        # Nếu trường cốt lõi bị mờ, lập tức từ chối đạt ngưỡng
        if has_crucial_low_confidence:
            is_passed_threshold = False

        if not is_passed_threshold:
            # Ưu tiên lấy trực tiếp các lý do quang học do AI quan sát được từ ảnh
            ai_reasons = getattr(doc_data, "qualityIssues", []) or []
            if not ai_reasons:
                if has_crucial_low_confidence:
                    ai_reasons = ["IMAGE_BLURRY", "EXCESSIVE_GLARE"]
                else:
                    ai_reasons = ["IMAGE_BLURRY"]

            validation_errors.append({
                "code": "ERR_IMAGE_QUALITY_TOO_LOW",
                "field": "file",
                "qualityScore": overall_confidence,
                "requiredThreshold": applied_threshold,
                "reasons": ai_reasons,
                "message": "Image quality is too low for accurate tax document extraction. Please capture or upload a clearer document."
            })

        return {
            "data": doc_data,
            "overall_confidence": overall_confidence,
            "applied_threshold": applied_threshold,
            "is_passed_threshold": is_passed_threshold,
            "low_confidence_fields": low_confidence_fields,
            "is_year_valid": is_year_valid,
            "is_doc_type_valid": is_doc_type_valid,
            "is_medical_statement": is_medical_statement,
            "validation_errors": validation_errors,
            "raw_payload": doc_data.model_dump(mode="json") if is_medical_statement else json.loads(raw_json)
        }
