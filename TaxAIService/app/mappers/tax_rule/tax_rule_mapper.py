import json
import re
import unicodedata
import uuid
from typing import Any, Dict, List, Optional, Tuple
from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.models.dependent_rule_document import DependentRuleDocument
from app.enum import TaxRuleStatus, RequiredDocumentType


def to_snake_case_code(text: Any) -> str:
    """
    Chuyển chuỗi bất kỳ thành mã định danh chuẩn UPPER_SNAKE_CASE.
    Ví dụ: 'BIRTH CERTIFICATE' -> 'BIRTH_CERTIFICATE'
    """
    if not text:
        return ""
    raw = str(text).strip()
    # Loại bỏ dấu tiếng Việt (nếu có)
    norm = unicodedata.normalize("NFD", raw)
    norm = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    norm = norm.replace("đ", "d").replace("Đ", "D")
    # Thay thế khoảng trắng và ký tự đặc biệt bằng dấu gạch dưới
    snake = re.sub(r"[^a-zA-Z0-9]+", "_", norm).strip("_").upper()
    return snake


def normalize_document_type(raw_type: Any) -> str:
    """
    Chuẩn hóa mã định danh loại giấy tờ:
    - Nếu khớp với Enum RequiredDocumentType thì lấy giá trị Enum.
    - Hỗ trợ các viết tắt CCCD/CMND thông dụng.
    - Nếu là mã mới do Admin cấu hình trên UI/DB hoặc AI sinh từ luật mới: giữ nguyên mã UPPER_SNAKE_CASE.
    """
    if not raw_type:
        return RequiredDocumentType.OTHER.value
    cleaned = to_snake_case_code(raw_type)
    if not cleaned:
        return RequiredDocumentType.OTHER.value
    if cleaned in ("CCCD", "CMND", "CCCD_FRONT", "CCCD_BACK", "CCCD_BOTH"):
        return RequiredDocumentType.CITIZEN_ID.value
    if cleaned == "DISABILITY_CERT":
        return RequiredDocumentType.DISABILITY_CERTIFICATE.value
    try:
        return RequiredDocumentType(cleaned).value
    except ValueError:
        return cleaned


def normalize_dependent_type(raw_type: Any) -> str:
    """Chuẩn hóa mã nhóm người phụ thuộc về dạng UPPER_SNAKE_CASE chuẩn."""
    if not raw_type:
        return "OTHER_HELPLESS"
    cleaned = to_snake_case_code(raw_type)
    return cleaned if cleaned else "OTHER_HELPLESS"


def parse_condition(cond_val: Any) -> Any:
    """Helper chuyển chuỗi JSON condition thành Dict/List nếu có."""
    if not cond_val:
        return None
    if isinstance(cond_val, str) and (cond_val.startswith("{") or cond_val.startswith("[")):
        try:
            return json.loads(cond_val)
        except Exception:
            return cond_val
    return cond_val


def format_tax_rule_data(
    rule_set: TaxRuleSet,
    rules: List[TaxRule],
    dep_rules: List[DependentRule]
) -> Dict[str, Any]:
    """Định dạng dữ liệu TaxRuleSet, TaxRules và DependentRules thành dict trả về cho API."""
    return {
        "taxRuleSet": {
            "ruleSetId": rule_set.rule_set_id,
            "adminId": rule_set.admin_id,
            "name": rule_set.name,
            "taxYear": rule_set.tax_year,
            "effectiveFrom": rule_set.effective_from,
            "effectiveTo": rule_set.effective_to,
            "status": rule_set.status,
            "approvedBy": rule_set.approved_by,
            "approvedAt": rule_set.approved_at
        },
        "taxRules": [
            {
                "ruleCode": r.rule_code,
                "ruleName": r.rule_name,
                "ruleType": r.rule_type,
                "condition": parse_condition(r.condition),
                "value": r.value,
                "unit": r.unit,
                "effectiveFrom": r.effective_from,
                "effectiveTo": r.effective_to,
                "legalDocument": r.legal_document,
                "article": r.article,
                "clause": r.clause,
                "point": r.point,
                "sourceUrl": r.source_url,
                "status": r.status
            }
            for r in rules
        ],
        "dependentRules": [
            {
                "id": str(dep.id),
                "ruleId": str(dep.rule_id) if dep.rule_id else None,
                "ruleSetId": str(dep.rule_set_id or rule_set.rule_set_id),
                "dependentType": dep.dependent_type,
                "name": dep.name,
                "maxAge": dep.max_age,
                "maxMonthlyIncome": dep.max_monthly_income,
                "isStudying": dep.is_studying,
                "isDisabled": dep.is_disabled,
                "conditions": parse_condition(dep.conditions),
                "requiredDocuments": [
                    {
                        "id": str(doc.id) if hasattr(doc, "id") and doc.id else None,
                        "dependentRuleId": str(doc.dependent_rule_id) if hasattr(doc, "dependent_rule_id") and doc.dependent_rule_id else str(dep.id),
                        "docType": doc.doc_type if hasattr(doc, "doc_type") else (doc.get("docType") or doc.get("doc_type")),
                        "name": doc.name if hasattr(doc, "name") else doc.get("name"),
                        "isMandatory": doc.is_mandatory if hasattr(doc, "is_mandatory") else doc.get("isMandatory", doc.get("is_mandatory", True)),
                        "description": doc.description if hasattr(doc, "description") else doc.get("description")
                    }
                    for doc in (dep.required_documents or [])
                ],
                "status": dep.status
            }
            for dep in dep_rules
        ]
    }


def build_tax_rule_models(
    extracted_data: Dict[str, Any],
    tax_year: int,
    filename: str,
    source_url: Optional[str] = None,
    admin_id: Optional[uuid.UUID] = None
) -> Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]:
    """
    Chuyển đổi dữ liệu trích xuất JSON từ Gemini AI thành các thực thể ORM:
    TaxRuleSet, TaxRule và DependentRule.
    """
    rule_set_dict = extracted_data["taxRuleSet"]
    new_rule_set = TaxRuleSet(
        admin_id=admin_id,
        name=rule_set_dict["name"],
        tax_year=tax_year,
        effective_from=rule_set_dict.get("effectiveFrom"),
        effective_to=rule_set_dict.get("effectiveTo"),
        status=TaxRuleStatus.DRAFT.value
    )

    new_rules: List[TaxRule] = []
    dependent_rules_to_create: List[DependentRule] = []

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
            status=TaxRuleStatus.DRAFT.value
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
                required_docs = elig.get("requiredDocuments") or elig.get("required_documents") or []

                dep_rule = DependentRule(
                    rule_id=rule_obj.rule_id,
                    dependent_type=dep_type,
                    name=dep_name,
                    max_age=int(max_age) if max_age is not None else None,
                    max_monthly_income=float(max_inc) if max_inc is not None else None,
                    is_studying=is_stud,
                    is_disabled=is_dis,
                    conditions=conds_str,
                    status=TaxRuleStatus.DRAFT.value
                )
                if required_docs:
                    for rdoc in required_docs:
                        doc_dict = rdoc if isinstance(rdoc, dict) else (rdoc.model_dump() if hasattr(rdoc, "model_dump") else {})
                        doc_type = normalize_document_type(doc_dict.get("docType") or doc_dict.get("doc_type"))
                        doc_name = doc_dict.get("name") or doc_type
                        is_mand = bool(doc_dict.get("isMandatory", doc_dict.get("is_mandatory", True)))
                        doc_desc = doc_dict.get("description")
                        doc_obj = DependentRuleDocument(
                            dependent_rule_id=dep_rule.id,
                            doc_type=doc_type,
                            name=doc_name,
                            is_mandatory=is_mand,
                            description=doc_desc
                        )
                        dep_rule.required_documents.append(doc_obj)

                rule_obj.dependent_rules.append(dep_rule)
                dependent_rules_to_create.append(dep_rule)

    return new_rule_set, new_rules, dependent_rules_to_create
