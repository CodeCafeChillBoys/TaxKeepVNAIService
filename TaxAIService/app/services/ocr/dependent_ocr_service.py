import json
import logging
from typing import List, Optional
from google import genai
from google.genai import types

from app.core.config import settings
from app.schemas.ocr import OcrExtractionResponse, ExtractedDependentData
from app.prompts.ocr import build_dependent_ocr_prompt, OCR_DEPENDENT_DOCUMENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)


class DependentOcrService:
    def __init__(self):
        # Khởi tạo GenAI client với API Key từ config
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        # Sử dụng gemini-2.5-flash hoặc gemini-2.0-flash để tốc độ nhanh và chi phí rẻ nhất
        self.model = settings.GEMINI_MODEL 

    def extract_document(
        self, 
        files: List[tuple[bytes, str]], # Danh sách các cặp (file_bytes, mime_type)
        target_group: Optional[str] = None,
        rules: Optional[List[dict]] = None
    ) -> OcrExtractionResponse:
        """
        Bóc tách thông tin từ 1 hoặc 2 ảnh (ví dụ: mặt trước + mặt sau CCCD).
        Hỗ trợ nhận diện & đối chiếu động theo danh mục quy tắc (rules) từ bảng dependent_document_rules của .NET.
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