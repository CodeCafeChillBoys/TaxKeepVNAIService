import logging
from typing import Optional, List, Dict
from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.certificate_ocr.certificate_ocr_schema import (
    GeminiCertificateOcrOutput,
    CertificateOcrResponse,
    CertificateExtractedData
)
from app.prompts.certificate_ocr.certificate_ocr_prompt import build_certificate_ocr_prompt

logger = logging.getLogger(__name__)


class CertificateOcrService:
    def __init__(self):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL  # gemini-2.5-flash

    def extract_certificate(
        self,
        file_bytes: bytes,
        mime_type: str,
        allowed_types: Optional[List[Dict[str, str]]] = None
    ) -> CertificateOcrResponse:
        """
        Bóc tách thông tin chứng chỉ hành nghề của chuyên gia bằng Gemini Vision Multimodal.
        Tự động phân loại hợp lệ hoặc từ chối nếu không phải chứng chỉ.
        """
        if not file_bytes or len(file_bytes) < 100:
            return CertificateOcrResponse(
                success=False,
                status_code=400,
                message="Tệp tin rỗng hoặc bị lỗi trong quá trình tải lên.",
                errors=[{"code": "ERR_INVALID_FILE", "message": "File bytes empty or too small"}]
            )

        try:
            prompt = build_certificate_ocr_prompt(allowed_types=allowed_types)
            contents = [
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ]

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiCertificateOcrOutput,
                    temperature=0.0  # Loại trừ ảo giác
                )
            )

            raw_json = (response.text or "").strip()
            if not raw_json:
                return CertificateOcrResponse(
                    success=False,
                    status_code=422,
                    message="AI không thể đọc được nội dung từ tài liệu. Ảnh có thể bị nhòe hoặc quá mờ.",
                    errors=[{"code": "ERR_UNREADABLE", "message": "Empty model output"}]
                )

            doc: GeminiCertificateOcrOutput = GeminiCertificateOcrOutput.model_validate_json(raw_json)

            # Trường hợp 1: AI xác định hình ảnh KHÔNG PHẢI CHỨNG CHỈ HỢP LỆ
            if not doc.is_certificate:
                rejection_msg = doc.rejection_reason or "Hình ảnh tải lên không phải là chứng chỉ hoặc bằng cấp chuyên môn hợp lệ."
                return CertificateOcrResponse(
                    success=False,
                    status_code=400,
                    message=rejection_msg,
                    errors=[{
                        "code": "ERR_NOT_A_CERTIFICATE",
                        "field": "file",
                        "message": rejection_msg
                    }]
                )

            # Trường hợp 2: Thiếu trường bắt buộc họ tên trên chứng chỉ
            if not doc.full_name or len(doc.full_name.strip()) < 2:
                return CertificateOcrResponse(
                    success=False,
                    status_code=422,
                    message="Không thể nhận diện được họ và tên người được cấp trên chứng chỉ. Vui lòng chụp rõ nét hơn.",
                    errors=[{
                        "code": "ERR_MISSING_NAME",
                        "field": "fullName",
                        "message": "Không tìm thấy họ tên trên chứng chỉ"
                    }]
                )

            # Tính độ tin cậy trung bình
            if doc.fields:
                scores = [f.confidence_score for f in doc.fields]
                overall_conf = round(sum(scores) / len(scores), 2)
            else:
                overall_conf = 0.92

            # Kiểm tra xem mã loại chứng chỉ nhận diện được có nằm trong danh mục hệ thống cho phép không
            valid_codes = [t.get("code") for t in (allowed_types or []) if t.get("code")]
            if valid_codes:
                is_valid_type = doc.detected_type in valid_codes
            else:
                is_valid_type = doc.detected_type in {"TAX_AGENT", "CPA", "ACCOUNTANT", "CHIEF_ACCOUNTANT"}

            extracted_data = CertificateExtractedData(
                detected_type=doc.detected_type,
                is_valid_type=is_valid_type,
                certificate_name=doc.certificate_name,
                certificate_number=doc.certificate_number,
                full_name=doc.full_name.strip().upper() if doc.full_name else None,
                citizen_id=doc.citizen_id.strip() if doc.citizen_id else None,
                date_of_birth=doc.date_of_birth,
                issuing_authority=doc.issuing_authority,
                issue_date=doc.issue_date,
                has_expiry=doc.has_expiry,
                expiry_date=doc.expiry_date,
                overall_confidence=overall_conf
            )

            return CertificateOcrResponse(
                success=True,
                status_code=200,
                message="Bóc tách chứng chỉ hành nghề thành công.",
                data=extracted_data
            )

        except Exception as e:
            logger.error(f"Lỗi ngoại lệ khi gọi OCR chứng chỉ: {str(e)}", exc_info=True)
            return CertificateOcrResponse(
                success=False,
                status_code=500,
                message=f"Lỗi trong quá trình AI phân tích tài liệu: {str(e)}",
                errors=[{"code": "ERR_INTERNAL_AI", "message": str(e)}]
            )