import json
import logging
from typing import List, Optional
from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.ocr import (
    OcrExtractionResponse, 
    ExtractedDependentData, 
    ConfidenceScores, 
    ThresholdValidationResult
)
from app.prompts.ocr import build_dependent_ocr_prompt, OCR_DEPENDENT_DOCUMENT_SYSTEM_PROMPT
from app.repositories.interfaces.isystem_config_repository import ISystemConfigRepository

logger = logging.getLogger(__name__)


def evaluate_dynamic_threshold(
    confidence_scores: ConfidenceScores, 
    applied_threshold: float
) -> ThresholdValidationResult:
    """
    Tính trung bình cộng tự động trên TẤT CẢ các trường hiện diện (khác None).
    Công thức: Tổng điểm các cột chia cho số lượng cột hiện có (tổng / độ dài).

    """
    scores_dict = confidence_scores.model_dump(exclude_none=True, by_alias=True)
    # Loại bỏ trường overall để không bị tính trùng vào mẫu số
    scores_dict.pop("overall", None)

    score_values = list(scores_dict.values())
    if len(score_values) > 0:
        overall_confidence = round(sum(score_values) / len(score_values), 2)
    else:
        overall_confidence = 0.0

    confidence_scores.overall = overall_confidence
    is_passed = overall_confidence >= applied_threshold

    # Lọc tự động các trường có điểm thấp hơn ngưỡng
    low_fields = [
        field_name for field_name, score in scores_dict.items() 
        if score < applied_threshold
    ]

    warning_msg = None
    if not is_passed:
        fields_str = ", ".join(low_fields) if low_fields else "tổng thể"
        warning_msg = (
            f"Độ tin cậy trích xuất ({overall_confidence}) thấp hơn ngưỡng quy định ({applied_threshold}). "
            f"Các trường không đạt yêu cầu: [{fields_str}]. Vui lòng kiểm tra lại hoặc chụp ảnh rõ nét hơn."
        )

    return ThresholdValidationResult(
        appliedThreshold=applied_threshold,
        overallConfidence=overall_confidence,
        isPassedThreshold=is_passed,
        lowConfidenceFields=low_fields,
        warningMessage=warning_msg
    )


class DependentOcrService:
    def __init__(self, repo: Optional[ISystemConfigRepository] = None):
        # Khởi tạo GenAI client với API Key từ config
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Sử dụng gemini-2.5-flash hoặc gemini-2.0-flash để tốc độ nhanh và chi phí rẻ nhất
        self.model = settings.GEMINI_MODEL 
        self.repo = repo

    def extract_document(
        self, 
        files: List[tuple[bytes, str]], # Danh sách các cặp (file_bytes, mime_type)
        target_group: Optional[str] = None,
        rules: Optional[List[dict]] = None,
        applied_threshold: Optional[float] = None
    ) -> OcrExtractionResponse:
        """
        Bóc tách thông tin từ 1 hoặc 2 ảnh (ví dụ: mặt trước + mặt sau CCCD).
        Hỗ trợ nhận diện & đối chiếu động theo danh mục quy tắc (rules) từ bảng dependent_document_rules của .NET.
        Kiểm tra ngưỡng tin cậy động (tổng cột / độ dài) lấy từ bảng system_configs trong DB.
        """
        try:
            # 1. Chuẩn bị các Part hình ảnh gửi lên Gemini
            contents = []
            for file_bytes, mime_type in files:
                contents.append(
                    types.Part.from_bytes(
                        data=file_bytes,
                        mime_type=mime_type
                    )
                )

            # 2. Xây dựng prompt động dựa trên rules của Admin truyền vào (nếu có)
            prompt = build_dependent_ocr_prompt(target_group=target_group, rules=rules)
            contents.append(prompt)

            # 3. Gọi Gemini API với Structured JSON Output
            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=OcrExtractionResponse,
                    temperature=0.0 # Bắt buộc để 0.0 để loại bỏ sáng tạo/ảo giác
                )
            )

            raw_text = (response.text or "").strip()
            
            # 4. Parse JSON sang Pydantic Model
            result = OcrExtractionResponse.model_validate_json(raw_text)
            result.success = True
            result.status_code = 200

            # 5. XÁC ĐỊNH NGƯỠNG ĐỘNG TỪ DATABASE VÀ ĐỐI SOÁT (TỔNG CỘT / ĐỘ DÀI)
            if result.data:
                # Nếu không truyền trực tiếp hoặc truyền <= 0 (do Swagger UI điền 0), tự động lấy từ DB system_configs
                if applied_threshold is None or applied_threshold <= 0:
                    if self.repo:
                        applied_threshold = self.repo.get_system_threshold()
                    else:
                        applied_threshold = 0.80
                # Tính trung bình cộng và thẩm định ngưỡng
                if result.data.confidence_scores:
                    threshold_res = evaluate_dynamic_threshold(
                        confidence_scores=result.data.confidence_scores,
                        applied_threshold=applied_threshold
                    )
                    result.data.threshold_validation = threshold_res

                    # Cảnh báo nếu không đạt ngưỡng
                    if not threshold_res.is_passed_threshold:
                        result.message = threshold_res.warning_message or "Độ tin cậy trích xuất không đạt ngưỡng quy định."

            return result

        except Exception as ex:
            logger.error(f"Lỗi khi OCR tài liệu qua Gemini: {ex}", exc_info=True)
            return OcrExtractionResponse(
                success=False,
                status_code=500,
                message="Trích xuất thông tin thất bại.",
                data=None,
                errors=str(ex)
            )