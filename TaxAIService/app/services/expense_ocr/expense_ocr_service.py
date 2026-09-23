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
from app.repositories.interfaces.isystem_config_repository import ISystemConfigRepository
from app.schemas.expense_ocr.expense_ocr_schema import GeminiOcrOutput, AdminCategoryItem
from app.prompts.expense_ocr.expense_orc_promt import _build_prompt
from app.errors.expense_ocr_errors import CorruptedFileError, UnreadableDocumentError

logger = logging.getLogger(__name__)


class ExpenseOcrService:
    def __init__(self, repo: Optional[ISystemConfigRepository] = None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL  # gemini-2.5-flash
        self.repo = repo

    async def extract_and_classify(
        self,
        file_bytes: bytes,
        mime_type: str,
        target_year: int,
        categories: List[AdminCategoryItem],
        applied_threshold: Optional[float] = None
    ) -> Dict[str, Any]:

        # 1. Kiểm tra tệp tin rỗng hoặc hỏng trước khi gửi sang AI
        if not file_bytes or len(file_bytes) < 100:
            raise CorruptedFileError("Dữ liệu tệp tin rỗng hoặc quá nhỏ, tệp có thể bị hỏng trong quá trình tải.")

        prompt = _build_prompt(categories)

        # 2. Gọi Gemini Multimodal Vision và bắt tách bạch lỗi
        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[
                    types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                    prompt
                ],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiOcrOutput,
                    temperature=0.1  # Giữ tính chính xác cao nhất, loại trừ ảo giác
                )
            )
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
        if doc_data.extractedYear and doc_data.extractedYear != target_year:
            is_year_valid = False
            validation_errors.append({
                "code": "ERR_YEAR_MISMATCH",
                "field": "extractedYear",
                "message": f"Document is dated in {doc_data.extractedYear} but filing year is {target_year}."
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
        if self.repo:
            if applied_threshold is None:
                applied_threshold = self.repo.get_system_threshold(category_code=doc_type)
            crucial_fields = self.repo.get_crucial_fields(category_code=doc_type)
        else:
            if applied_threshold is None:
                applied_threshold = 0.80
            crucial_fields = {"total_amount", "seller_tax_code", "buyer_id_card", "invoice_number"}

        # 6. Tính điểm tin cậy tổng thể (overall_confidence)
        if doc_data.fields:
            scores = [f.confidenceScore for f in doc_data.fields]
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
            "validation_errors": validation_errors,
            "raw_payload": json.loads(raw_json)
        }
        
        