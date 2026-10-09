import os
import uuid
from typing import Optional, Dict, Any
from fastapi import status, HTTPException
from app.core.config import settings
from app.repositories.interfaces.tax_rule_repository_interface import ITaxRuleRepository
from app.services.tax_rule.pdf_service import pdf_service
from app.services.tax_rule.tax_rule_extraction_service import tax_rule_extraction_service
from app.mappers.tax_rule import build_tax_rule_models, format_tax_rule_data
from app.errors.tax_rule_errors import TaxRuleErrorMessages, TaxRuleServiceError
from app.errors.pdf_errors import PDFProcessingError


class TaxRuleDocumentService:
    """
    Service chuyên trách pipeline xử lý văn bản quy tắc thuế:
    Tiếp nhận file PDF -> Trích xuất nội dung -> Phân tích với AI -> Lưu nháp vào DB.
    """

    def __init__(
        self,
        repository: ITaxRuleRepository,
        url_validation_service: Optional[Any] = None
    ):
        self.repository = repository
        self.url_validation_service = url_validation_service
        # check url_validation_service có true and có connect DB nếu chưa truyền UrlRuleRepository vào
        if not self.url_validation_service and hasattr(repository, "db"):
            from app.repositories.url_rule import UrlRuleRepository
            from app.services.url_rule import UrlValidationService
            self.url_validation_service = UrlValidationService(UrlRuleRepository(repository.db))

    async def process_tax_rule_document(
        self,
        filename: str,
        file_bytes: bytes,
        tax_year: int,
        name: Optional[str] = None,
        source_url: Optional[str] = None,
        admin_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """
        Quy trình xử lý văn bản luật thuế:
        0. Kiểm tra tính hợp lệ của source_url theo quy tắc cấu hình của Admin.
        1. Kiểm tra trùng lặp taxYear trong database.
        2. Lưu file tạm thời và xử lý PDF (PyMuPDF / Scan bytes).
        3. Gọi AI trích xuất thông tin quy tắc thuế.
        4. Kiểm tra trùng lặp ruleCode trong database.
        5. Tạo và lưu bản ghi TaxRuleSet, TaxRule, DependentRule qua Repository.
        6. Dọn dẹp file tạm và chuẩn bị dữ liệu phản hồi.
        """
        # 0. Kiểm tra tính hợp lệ của source_url nếu có truyền vào
        if source_url and source_url.strip():
            if self.url_validation_service:
                is_valid, err_msg, _ = self.url_validation_service.validate_url(source_url.strip())
                if not is_valid:
                    raise TaxRuleServiceError(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        message=err_msg or f"URL nguồn '{source_url}' không thuộc danh sách được phê duyệt bởi Admin."
                    )

        # 1. Kiểm tra trùng lặp taxYear trước khi xử lý AI
        existing_rule_set = self.repository.get_rule_set_by_year(tax_year)
        if existing_rule_set:
            raise TaxRuleServiceError(
                status_code=status.HTTP_409_CONFLICT,
                message=TaxRuleErrorMessages.TAX_RULE_SET_EXISTS
            )

        # 2. Lưu file tạm thời vào thư mục uploads
        os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
        temp_file_name = f"{uuid.uuid4()}_{filename}"
        temp_file_path = os.path.join(settings.UPLOAD_DIR, temp_file_name)

        with open(temp_file_path, "wb") as f:
            f.write(file_bytes)

        try:
            # 3. Bóc tách text bằng PyMuPDF
            try:
                is_scanned, pdf_text, scan_bytes = pdf_service.prepare_pdf_for_ai(
                    temp_file_path, max_scan_pages=30
                )
            except PDFProcessingError:
                raise TaxRuleServiceError(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    message=TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED
                )

            # 4. Gọi Gemini AI để trích xuất tax_rule_sets & tax_rules
            try:
                extracted_data = tax_rule_extraction_service.extract_tax_rules(
                    document_text=pdf_text if not is_scanned else None,
                    pdf_bytes=scan_bytes if is_scanned else None,
                    tax_year=tax_year,
                    rule_set_name=name,
                    source_url=source_url,
                    legal_doc_name=filename
                )
            except HTTPException as he:
                raise TaxRuleServiceError(
                    status_code=he.status_code,
                    message=he.detail
                )

            # 5. Kiểm tra trùng lặp ruleCode trong database
            rule_codes = [r["ruleCode"] for r in extracted_data.get("taxRules", []) if "ruleCode" in r]
            if rule_codes and self.repository.check_existing_rule_codes(rule_codes):
                raise TaxRuleServiceError(
                    status_code=status.HTTP_409_CONFLICT,
                    message="The rule code already exists."
                )

            # 6. Chuyển đổi JSON sang các thực thể ORM
            new_rule_set, new_rules, dependent_rules_to_create = build_tax_rule_models(
                extracted_data=extracted_data,
                tax_year=tax_year,
                filename=filename,
                source_url=source_url,
                admin_id=admin_id
            )

            # 7. Lưu vào DB thông qua Repository
            saved_rule_set, saved_rules, saved_dep_rules = self.repository.create_tax_rule_set(
                rule_set=new_rule_set,
                rules=new_rules,
                dependent_rules=dependent_rules_to_create
            )

            # 8. Định dạng cấu trúc trả về
            verification_data = extracted_data.get("verification")
            warning_msg = extracted_data.get("warning")

            res_data = format_tax_rule_data(saved_rule_set, saved_rules, saved_dep_rules)

            if verification_data:
                res_data["verification"] = verification_data
            if warning_msg:
                res_data["warning"] = warning_msg

            return {
                "message": "Tax document processed successfully." if not warning_msg else f"Tax document processed with warning: {warning_msg}",
                "warning": warning_msg,
                "data": res_data
            }
        finally:
            # Luôn dọn dẹp file tạm sau khi xử lý xong
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass
