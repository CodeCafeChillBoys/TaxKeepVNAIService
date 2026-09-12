import os
import uuid
import json
from typing import Optional, Dict, Any
from fastapi import status, HTTPException
from app.core.config import settings
from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.repositories.interfaces.tax_rule_repository_interface import ITaxRuleRepository
from app.services.interfaces.tax_rule_service_interface import ITaxRuleService
from app.services.pdf_service import pdf_service
from app.services.tax_rule_extraction_service import tax_rule_extraction_service
from app.errors.tax_rule_errors import TaxRuleErrorMessages, TaxRuleServiceError
from app.errors.pdf_errors import PDFProcessingError, PDFErrorMessages


def _parse_condition(cond_val: Any) -> Any:
    """Helper chuyển chuỗi JSON condition thành Dict/List nếu có."""
    if not cond_val:
        return None
    if isinstance(cond_val, str) and (cond_val.startswith("{") or cond_val.startswith("[")):
        try:
            return json.loads(cond_val)
        except Exception:
            return cond_val
    return cond_val


class TaxRuleService(ITaxRuleService):
    """Triển khai cụ thể ITaxRuleService."""

    def __init__(self, repository: ITaxRuleRepository):
        self.repository = repository

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
        1. Kiểm tra trùng lặp taxYear trong database.
        2. Lưu file tạm thời và xử lý PDF (PyMuPDF / Scan bytes).
        3. Gọi AI trích xuất thông tin quy tắc thuế.
        4. Kiểm tra trùng lặp ruleCode trong database.
        5. Tạo và lưu bản ghi TaxRuleSet, TaxRule, DependentRule qua Repository.
        6. Dọn dẹp file tạm và chuẩn bị dữ liệu phản hồi.
        """
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

            # 6. Chuẩn bị các thực thể ORM
            rule_set_dict = extracted_data["taxRuleSet"]
            new_rule_set = TaxRuleSet(
                admin_id=admin_id,
                name=rule_set_dict["name"],
                tax_year=tax_year,
                effective_from=rule_set_dict.get("effectiveFrom"),
                effective_to=rule_set_dict.get("effectiveTo"),
                status="Draft"
            )

            new_rules = []
            dependent_rules_to_create = []

            for item in extracted_data.get("taxRules", []):
                val = item.get("value")
                numeric_val = float(val) if val is not None else None

                raw_cond = item.get("condition")
                if isinstance(raw_cond, (dict, list)):
                    cond_str = json.dumps(raw_cond, ensure_ascii=False)
                else:
                    cond_str = str(raw_cond) if raw_cond is not None else None

                rule_id = uuid.uuid4()
                rule_obj = TaxRule(
                    rule_id=rule_id,
                    rule_code=item["ruleCode"],
                    rule_name=item["ruleName"],
                    rule_type=item["ruleType"],
                    condition=cond_str,
                    value=numeric_val,
                    unit=item.get("unit"),
                    effective_from=item.get("effectiveFrom") or rule_set_dict.get("effectiveFrom"),
                    effective_to=item.get("effectiveTo") or rule_set_dict.get("effectiveTo"),
                    legal_document=item.get("legalDocument") or filename,
                    article=str(item.get("article")) if item.get("article") is not None else None,
                    clause=str(item.get("clause")) if item.get("clause") is not None else None,
                    point=str(item.get("point")) if item.get("point") is not None else None,
                    source_url=item.get("sourceUrl") or source_url,
                    status="Draft",
                    version=int(item.get("version", 1))
                )
                new_rules.append(rule_obj)

                # Nếu condition có chứa eligibility của người phụ thuộc
                cond_data = None
                if isinstance(raw_cond, dict):
                    cond_data = raw_cond
                elif isinstance(raw_cond, str):
                    try:
                        cond_data = json.loads(raw_cond)
                    except Exception:
                        start_idx = raw_cond.find("{")
                        end_idx = raw_cond.rfind("}")
                        if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                            try:
                                cond_data = json.loads(raw_cond[start_idx:end_idx + 1])
                            except Exception:
                                cond_data = None

                if isinstance(cond_data, dict) and "eligibility" in cond_data:
                    for elig in cond_data.get("eligibility", []):
                        dep_type = elig.get("type", "OTHER")
                        dep_name = elig.get("name") or elig.get("type", "Người phụ thuộc")
                        max_age = elig.get("maxAge")
                        max_inc = elig.get("maxMonthlyIncome")
                        is_stud = bool(elig.get("isStudying", False))
                        is_dis = bool(elig.get("isDisabled", False))
                        conds = elig.get("conditions", [])
                        conds_str = json.dumps(conds, ensure_ascii=False) if isinstance(conds, (dict, list)) else str(conds)

                        dep_rule = DependentRule(
                            rule_id=rule_obj.rule_id,
                            dependent_type=dep_type,
                            name=dep_name,
                            max_age=int(max_age) if max_age is not None else None,
                            max_monthly_income=float(max_inc) if max_inc is not None else None,
                            is_studying=is_stud,
                            is_disabled=is_dis,
                            conditions=conds_str,
                            status="Draft"
                        )
                        rule_obj.dependent_rules.append(dep_rule)
                        dependent_rules_to_create.append(dep_rule)

            # 7. Lưu vào DB thông qua Repository
            saved_rule_set, saved_rules, saved_dep_rules = self.repository.create_tax_rule_set(
                rule_set=new_rule_set,
                rules=new_rules,
                dependent_rules=dependent_rules_to_create
            )

            # 8. Định dạng cấu trúc trả về
            return {
                "message": "Tax document processed successfully.",
                "data": {
                    "taxRuleSet": {
                        "ruleSetId": saved_rule_set.rule_set_id,
                        "adminId": saved_rule_set.admin_id,
                        "name": saved_rule_set.name,
                        "taxYear": saved_rule_set.tax_year,
                        "effectiveFrom": saved_rule_set.effective_from,
                        "effectiveTo": saved_rule_set.effective_to,
                        "status": saved_rule_set.status
                    },
                    "taxRules": [
                        {
                            "ruleCode": r.rule_code,
                            "ruleName": r.rule_name,
                            "ruleType": r.rule_type,
                            "condition": _parse_condition(r.condition),
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
                        for r in saved_rules
                    ],
                    "dependentRules": [
                        {
                            "id": str(dep.id),
                            "ruleId": str(dep.rule_id) if dep.rule_id else None,
                            "ruleSetId": str(dep.rule_set_id or saved_rule_set.rule_set_id),
                            "dependentType": dep.dependent_type,
                            "name": dep.name,
                            "maxAge": dep.max_age,
                            "maxMonthlyIncome": dep.max_monthly_income,
                            "isStudying": dep.is_studying,
                            "isDisabled": dep.is_disabled,
                            "conditions": _parse_condition(dep.conditions),
                            "status": dep.status
                        }
                        for dep in saved_dep_rules
                    ]
                }
            }
        finally:
            # Luôn dọn dẹp file tạm sau khi xử lý xong
            if os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                except OSError:
                    pass

    def approve_tax_rule_set(self, rule_set_id: uuid.UUID) -> Dict[str, Any]:
        """Phê duyệt TaxRuleSet sang Active thông qua Repository."""
        approved_rule_set = self.repository.approve_tax_rule_set(rule_set_id)
        if not approved_rule_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TaxRuleErrorMessages.RULE_SET_NOT_FOUND
            )

        return {
            "message": "Tax rule set approved successfully.",
            "ruleSetId": str(approved_rule_set.rule_set_id),
            "status": "Active"
        }
