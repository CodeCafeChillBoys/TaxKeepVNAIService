import logging
from typing import Optional
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings
from app.repositories.interfaces.isystem_config_repository import ISystemConfigRepository
from app.schemas.income_ocr.income_ocr_schema import (
    GeminiIncomeOcrOutput,
    IncomeOcrResponse,
    IncomeExtractedData,
    IncomeThresholdValidationResult
)
from app.prompts.income_ocr.income_ocr_prompt import build_income_ocr_prompt

logger = logging.getLogger(__name__)


def evaluate_income_threshold(
    doc: GeminiIncomeOcrOutput,
    applied_threshold: float
) -> IncomeThresholdValidationResult:
    """Tính trung bình cộng confidence các trường và kiểm tra ngưỡng động"""
    if doc.fields:
        scores = [f.confidence_score for f in doc.fields]
        overall_conf = round(sum(scores) / len(scores), 2)
    else:
        overall_conf = 0.90 if doc.is_income_document else 0.0

    # Lọc các trường có điểm thấp hơn ngưỡng
    low_fields = [
        f.field_name for f in doc.fields 
        if f.confidence_score < applied_threshold
    ]

    # Các trường cốt lõi của bảng incomes bắt buộc phải rõ nét
    crucial_fields = {"organization_name", "month", "year", "total_taxable_income"}
    has_crucial_low = any(f in crucial_fields for f in low_fields)

    is_passed = (overall_conf >= applied_threshold) and not has_crucial_low

    warning_msg = None
    if not is_passed:
        if has_crucial_low:
            warning_msg = "Các trường cốt lõi của phiếu lương bị mờ hoặc không nhận diện được rõ ràng. Vui lòng tải ảnh rõ nét hơn."
        else:
            warning_msg = f"Độ tin cậy tổng thể ({overall_conf}) thấp hơn ngưỡng quy định ({applied_threshold})."

    return IncomeThresholdValidationResult(
        appliedThreshold=applied_threshold,
        overallConfidence=overall_conf,
        isPassedThreshold=is_passed,
        lowConfidenceFields=low_fields,
        warningMessage=warning_msg
    )


class IncomeOcrService:
    def __init__(self, repo: Optional[ISystemConfigRepository] = None):
        self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.model = settings.GEMINI_MODEL  # gemini-2.5-flash
        self.repo = repo

    def extract_payslip(
        self,
        file_bytes: bytes,
        mime_type: str,
        target_month: Optional[int] = None,
        target_year: Optional[int] = None,
        applied_threshold: Optional[float] = None
    ) -> IncomeOcrResponse:
        """
        Bóc tách thông tin tờ báo cáo/phiếu lương bằng Gemini Vision Multimodal.
        Khớp chuẩn với các trường của bảng incomes.
        """
        # 1. Kiểm tra kích thước file cơ bản
        if not file_bytes or len(file_bytes) < 100:
            return IncomeOcrResponse(
                success=False,
                status_code=400,
                message="Tệp tin rỗng hoặc bị hỏng trong quá trình tải lên.",
                errors=[{"code": "ERR_CORRUPTED_FILE", "message": "File bytes empty or too small"}]
            )

        try:
            # 2. Xây dựng prompt & gọi Gemini API
            prompt = build_income_ocr_prompt(target_month=target_month, target_year=target_year)
            contents = [
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                prompt
            ]

            response = self.client.models.generate_content(
                model=self.model,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiIncomeOcrOutput,
                    temperature=0.0  # Loại trừ sáng tạo ảo giác
                )
            )

            raw_json = (response.text or "").strip()
            if not raw_json:
                return IncomeOcrResponse(
                    success=False,
                    status_code=422,
                    message="AI không thể đọc được nội dung từ tài liệu. Ảnh có thể bị nhòe hoặc quá mờ.",
                    errors=[{"code": "ERR_UNREADABLE", "message": "Empty model output"}]
                )

            # 3. Parse JSON sang Schema Pydantic
            doc: GeminiIncomeOcrOutput = GeminiIncomeOcrOutput.model_validate_json(raw_json)

            # 4. Kiểm tra nghiệp vụ (Business Rules Validation)
            validation_errors = []

            # 4.1. Không phải phiếu lương
            if not doc.is_income_document:
                validation_errors.append({
                    "code": "ERR_NOT_INCOME_DOCUMENT",
                    "field": "file",
                    "message": "Hình ảnh tải lên không được nhận diện là Phiếu lương hoặc Báo cáo thu nhập hợp lệ."
                })

            # 4.2. Kiểm tra tính hợp lệ của tháng và năm
            if doc.month is not None and not (1 <= doc.month <= 12):
                validation_errors.append({
                    "code": "ERR_INVALID_MONTH",
                    "field": "month",
                    "message": f"Tháng lương trích xuất không hợp lệ ({doc.month}). Tháng phải từ 1 đến 12."
                })

            if target_year and doc.year and doc.year != target_year:
                validation_errors.append({
                    "code": "ERR_YEAR_MISMATCH",
                    "field": "year",
                    "message": f"Năm trên phiếu lương ({doc.year}) không khớp với năm kê khai ({target_year})."
                })

            # 5. Phân giải ngưỡng động từ Database
            if applied_threshold is None or applied_threshold <= 0:
                if self.repo:
                    applied_threshold = self.repo.get_system_threshold(category_code="INCOME_PAYSLIP")
                else:
                    applied_threshold = 0.80

            # 6. Thẩm định ngưỡng tin cậy
            threshold_res = evaluate_income_threshold(doc, applied_threshold)
            if not threshold_res.is_passed_threshold:
                validation_errors.append({
                    "code": "ERR_IMAGE_QUALITY_LOW",
                    "field": "file",
                    "message": threshold_res.warning_message or "Độ tin cậy trích xuất không đạt ngưỡng quy định."
                })

            # 7. Nếu có lỗi nghiệp vụ -> trả về trạng thái thất bại
            if validation_errors:
                return IncomeOcrResponse(
                    success=False,
                    status_code=422,
                    message=validation_errors[0]["message"],
                    errors=validation_errors
                )

            # 8. Đóng gói dữ liệu đầu ra chuẩn theo bảng incomes
            extracted_data = IncomeExtractedData(
                organizationName=doc.organization_name or "Không xác định",
                taxIdNumber=doc.tax_id_number,
                month=doc.month or 1,
                year=doc.year or 2026,
                totalTaxableIncome=doc.total_taxable_income,
                insuranceDeducted=doc.insurance_deducted,
                taxAlreadyDeducted=doc.tax_already_deducted,
                payslipFileUrl=None,
                employeeName=doc.employee_name,
                grossSalary=doc.gross_salary,
                netSalary=doc.net_salary,
                thresholdValidation=threshold_res
            )

            return IncomeOcrResponse(
                success=True,
                status_code=200,
                message="Bóc tách thông tin phiếu lương thành công.",
                data=extracted_data
            )

        except APIError as api_err:
            logger.error(f"Google GenAI API Error khi OCR phiếu lương: {api_err}", exc_info=True)
            return IncomeOcrResponse(
                success=False,
                status_code=502,
                message="Lỗi kết nối tới AI Engine. Vui lòng thử lại sau.",
                errors=[{"code": "ERR_AI_API", "message": str(api_err)}]
            )
        except Exception as e:
            logger.error(f"Lỗi không xác định khi OCR phiếu lương: {e}", exc_info=True)
            return IncomeOcrResponse(
                success=False,
                status_code=500,
                message="Xảy ra lỗi hệ thống khi bóc tách phiếu lương.",
                errors=[{"code": "ERR_INTERNAL_SERVER", "message": str(e)}]
            )
            
