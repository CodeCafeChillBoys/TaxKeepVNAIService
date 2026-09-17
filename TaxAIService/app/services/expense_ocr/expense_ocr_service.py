import json
import logging
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from app.core.config import settings
from app.repositories.interfaces.isystem_config_repository import ISystemConfigRepository
from app.schemas.expense_ocr.expense_ocr_schema import GeminiOcrOutput, AdminCategoryItem
from app.prompts.expense_ocr.expense_orc_promt import _build_prompt

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

        prompt = _build_prompt(categories)

        # 1. Gọi Gemini Multimodal Vision
        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=GeminiOcrOutput,
                temperature=0.1  # Giữ tính chính xác cao nhất
            )
        )

        raw_json = response.text
        doc_data = GeminiOcrOutput.model_validate_json(raw_json)

        # 2. Logic kiểm tra nghiệp vụ (Validation)
        validation_errors = []

        # Kiểm tra loại tài liệu có hợp lệ không
        valid_codes = [c.code for c in categories]
        is_doc_type_valid = doc_data.docTypeCode in valid_codes
        if not is_doc_type_valid:
            validation_errors.append(
                f"Chứng từ không hợp lệ: {doc_data.classificationReason or 'Không thuộc danh mục nào của Admin quy định'}"
            )

        # Kiểm tra Năm: Hóa đơn có thuộc năm kê khai target_year không?
        is_year_valid = True
        if doc_data.extractedYear and doc_data.extractedYear != target_year:
            is_year_valid = False
            validation_errors.append(
                f"Năm trên hóa đơn ({doc_data.extractedYear}) không khớp với năm kê khai ({target_year})."
            )

        # 3. Lấy cấu hình ngưỡng (threshold) và danh sách trường cốt lõi qua self.repo
        doc_type = doc_data.docTypeCode if doc_data else None
        if self.repo:
            if applied_threshold is None:
                applied_threshold = self.repo.get_system_threshold(category_code=doc_type)
            crucial_fields = self.repo.get_crucial_fields(category_code=doc_type)
        else:
            if applied_threshold is None:
                applied_threshold = 0.80
            crucial_fields = {"total_amount", "seller_tax_code", "buyer_id_card", "invoice_number"}

        # 4. Tính điểm tin cậy tổng thể (overall_confidence)
        if doc_data.fields:
            scores = [f.confidenceScore for f in doc_data.fields]
            overall_confidence = round(sum(scores) / len(scores), 2)
        else:
            overall_confidence = 0.95

        # 5. Tiến hành so sánh với ngưỡng và lọc các trường độ tin cậy thấp
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
                if f.fieldName in crucial_fields:
                    has_crucial_low_confidence = True

        # Nếu trường cốt lõi bị mờ, lập tức đánh dấu không đạt ngưỡng để bắt người dùng review
        if has_crucial_low_confidence:
            is_passed_threshold = False

        if not is_passed_threshold:
            validation_errors.append(
                f"Độ tin cậy tổng thể ({overall_confidence}) hoặc trường thông tin cốt lõi thấp hơn ngưỡng quy định ({applied_threshold}). Cần xác nhận thủ công."
            )

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
