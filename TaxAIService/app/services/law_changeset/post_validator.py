from __future__ import annotations
import json
import logging
import re
import unicodedata
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from app.schemas.law_changeset.contract import (
    CurrentRuleItem,
    LawChangesetResult,
    OperationModel,
    RuleCatalogItem,
)

logger = logging.getLogger(__name__)

ALLOWED_UNITS = {"VND/month", "VND/year", "VND/person/month", "VND/payment"}


def normalize_doc_number(doc_str: Optional[str]) -> str:
    """
    Chuẩn hoá số hiệu văn bản: bỏ khoảng trắng, viết hoa, bỏ dấu, Đ thành D.
    Ví dụ: '253/2026/NĐ-CP' -> '253/2026/ND-CP'
    """
    if not doc_str:
        return ""
    s = doc_str.replace(" ", "").upper()
    s = s.replace("Đ", "D")
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def clean_citation_part(val: Optional[str]) -> Optional[str]:
    """
    Chỉ giữ số hoặc chữ cái, loại bỏ chữ 'Điều', 'khoản', 'điểm'.
    Ví dụ: 'Điều 49' -> '49', 'Khoản 2' -> '2', 'Điểm a' -> 'a'.
    """
    if not val:
        return None
    s = val.strip()
    for prefix in ["điều", "khoản", "điểm", "dieu", "khoan", "diem"]:
        if s.lower().startswith(prefix):
            s = s[len(prefix):].strip()
            break
    return s if s else None


def is_valid_date(date_str: Optional[str]) -> bool:
    if not date_str:
        return False
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def is_value_identical(kind: str, after_val: Any, curr: CurrentRuleItem) -> bool:
    if kind in ("AMOUNT", "RATE"):
        if after_val.value_number != curr.value_number:
            return False
        if (after_val.unit or None) != (curr.unit or None):
            return False
        return True

    elif kind == "SCHEDULE":
        after_sched = after_val.value_json or []
        curr_sched = curr.value_json or []
        if len(after_sched) != len(curr_sched):
            return False
        for a_br, c_br in zip(after_sched, curr_sched):
            if a_br.get("toAnnual") != c_br.get("toAnnual"):
                return False
            if a_br.get("rate") != c_br.get("rate"):
                return False
        return True

    elif kind == "JSON":
        try:
            j1 = json.dumps(after_val.value_json or {}, sort_keys=True)
            j2 = json.dumps(curr.value_json or {}, sort_keys=True)
            return j1 == j2
        except Exception:
            return False

    elif kind in ("FLAG", "TEXT"):
        t1 = re.sub(r"\s+", " ", (after_val.value_text or "").strip())
        t2 = re.sub(r"\s+", " ", (curr.value_text or "").strip())
        return t1 == t2

    return False


def post_validate_changeset_result(
    result: LawChangesetResult,
    rule_catalog: List[RuleCatalogItem],
    current_rules: List[CurrentRuleItem],
    current_doc_number: Optional[str] = None,
) -> LawChangesetResult:
    """
    Bộ lọc và làm sạch dữ liệu theo đặc tả §9:
    - Chuẩn hóa ngày tháng, tỷ lệ thuế, độ dài evidence.
    - Loại bỏ mã không thuộc danh mục (nếu newCode=false).
    - Khử trùng lặp khóa (ruleCode, applyFrom / applyTo).
    - So sánh với currentRules để bỏ dòng giống hệt phiên bản hiện tại.
    """
    warnings: List[str] = list(result.warnings)
    valid_catalog_codes: Set[str] = {c.rule_code for c in rule_catalog}

    # 1. Làm sạch văn bản và ngày tháng document
    if result.document:
        if result.document.effective_date and not is_valid_date(result.document.effective_date):
            warnings.append(f"Ngày hiệu lực văn bản '{result.document.effective_date}' sai định dạng YYYY-MM-DD.")
            result.document.effective_date = None
        if result.document.issued_date and not is_valid_date(result.document.issued_date):
            warnings.append(f"Ngày ban hành văn bản '{result.document.issued_date}' sai định dạng YYYY-MM-DD.")
            result.document.issued_date = None

    # 2. Làm sạch relations
    for r in result.relations:
        if r.effective_date and not is_valid_date(r.effective_date):
            warnings.append(f"Ngày hiệu lực quan hệ '{r.effective_date}' sai định dạng YYYY-MM-DD.")
            r.effective_date = None
        if r.citation:
            r.citation.article = clean_citation_part(r.citation.article)
            r.citation.clause = clean_citation_part(r.citation.clause)
            r.citation.point = clean_citation_part(r.citation.point)
        if r.target_scope:
            r.target_scope.article = clean_citation_part(r.target_scope.article)
            r.target_scope.clause = clean_citation_part(r.target_scope.clause)
            r.target_scope.point = clean_citation_part(r.target_scope.point)
        if len(r.evidence) > 300:
            r.evidence = r.evidence[:299] + "…"

    # 3. Làm sạch operations
    processed_ops: List[OperationModel] = []

    for op in result.operations:
        # a. Kiểm tra ruleCode thuộc danh mục
        if not op.new_code and op.rule_code not in valid_catalog_codes:
            warnings.append(f"Bỏ dòng thay đổi mã '{op.rule_code}' vì không nằm trong ruleCatalog và newCode=false.")
            continue

        # b. Làm sạch ngày applyFrom / applyTo
        if op.apply_from and not is_valid_date(op.apply_from):
            warnings.append(f"Mã '{op.rule_code}' có applyFrom='{op.apply_from}' sai định dạng YYYY-MM-DD, đặt về null.")
            op.apply_from = None
        if op.apply_to and not is_valid_date(op.apply_to):
            warnings.append(f"Mã '{op.rule_code}' có applyTo='{op.apply_to}' sai định dạng YYYY-MM-DD, đặt về null.")
            op.apply_to = None

        # c. Làm sạch citation và applyBasis
        if op.citation:
            op.citation.article = clean_citation_part(op.citation.article)
            op.citation.clause = clean_citation_part(op.citation.clause)
            op.citation.point = clean_citation_part(op.citation.point)
        if op.apply_basis:
            op.apply_basis.article = clean_citation_part(op.apply_basis.article)
            op.apply_basis.clause = clean_citation_part(op.apply_basis.clause)
            op.apply_basis.point = clean_citation_part(op.apply_basis.point)

        # d. Cắt evidence nếu dài hơn 300 ký tự
        if len(op.evidence) > 300:
            op.evidence = op.evidence[:299] + "…"

        # e. Kiểm tra và chuẩn hóa giá trị trong after
        if op.after:
            # Kiểm tra unit
            if op.after.unit and op.after.unit not in ALLOWED_UNITS:
                warnings.append(f"Mã '{op.rule_code}' có unit '{op.after.unit}' không thuộc danh mục, đặt về null.")
                op.after.unit = None

            # Kiểm tra RATE cho valueNumber
            v_kind = "AMOUNT"
            for c_item in rule_catalog:
                if c_item.rule_code == op.rule_code:
                    v_kind = c_item.value_kind
                    break
            if op.new_code and op.proposed_definition:
                v_kind = op.proposed_definition.value_kind

            if v_kind == "RATE" and op.after.value_number is not None:
                rate = op.after.value_number
                if 1.0 < rate <= 100.0:
                    op.after.value_number = round(rate / 100.0, 4)
                    warnings.append(f"Mã '{op.rule_code}' có thuế suất {rate}%, tự động đổi thành {op.after.value_number}.")
                elif rate < 0.0 or rate > 1.0:
                    warnings.append(f"Bỏ dòng '{op.rule_code}' do thuế suất {rate} không hợp lệ.")
                    continue

            # Kiểm tra biểu thuế SCHEDULE
            if op.after.value_json and isinstance(op.after.value_json, list):
                sched = op.after.value_json
                is_sched = True
                prev_to_annual = -1.0
                for br_idx, br in enumerate(sched):
                    if not isinstance(br, dict) or "rate" not in br:
                        is_sched = False
                        break
                    br_rate = br.get("rate")
                    if br_rate is not None and 1.0 < br_rate <= 100.0:
                        br["rate"] = round(br_rate / 100.0, 4)
                        warnings.append(f"Bậc {br_idx + 1} của '{op.rule_code}' có thuế suất {br_rate}%, đổi thành {br['rate']}.")

                    to_ann = br.get("toAnnual")
                    if to_ann is not None:
                        if to_ann <= prev_to_annual:
                            warnings.append(f"Biểu thuế '{op.rule_code}' có toAnnual không tăng dần tại bậc {br_idx + 1}.")
                        prev_to_annual = to_ann
                    elif br_idx != len(sched) - 1:
                        warnings.append(f"Biểu thuế '{op.rule_code}' có toAnnual là null không nằm ở bậc cuối.")

        processed_ops.append(op)

    # 4. Khử trùng lặp khóa (ruleCode, ngày của dòng)
    ops_by_key: Dict[str, OperationModel] = {}
    for op in processed_ops:
        key_date = op.apply_to if op.op == "END" else op.apply_from
        key = f"{op.rule_code}::{key_date}"
        if key in ops_by_key:
            existing = ops_by_key[key]
            if op.confidence > existing.confidence:
                ops_by_key[key] = op
        else:
            ops_by_key[key] = op

    deduped_ops = list(ops_by_key.values())

    # 5. So sánh với currentRules để bỏ dòng giống hệt phiên bản hiện tại
    final_ops: List[OperationModel] = []
    norm_current_doc = normalize_doc_number(current_doc_number)

    for op in deduped_ops:
        if op.op in ("ADD", "UPDATE", "RECITE") and op.after:
            op_from = op.apply_from or "9999-12-31"
            is_duplicate_of_current = False

            v_kind = "AMOUNT"
            for c_item in rule_catalog:
                if c_item.rule_code == op.rule_code:
                    v_kind = c_item.value_kind
                    break

            for curr in current_rules:
                if curr.rule_code != op.rule_code:
                    continue
                c_from = curr.apply_from or "0000-01-01"
                c_to = curr.apply_to or "9999-12-31"

                if c_from <= op_from < c_to:
                    val_same = is_value_identical(v_kind, op.after, curr)
                    cond_same = True
                    if op.after.condition is not None and curr.condition is not None:
                        cond_same = (op.after.condition == curr.condition)

                    curr_doc_norm = ""
                    if curr.citation and curr.citation.document_number:
                        curr_doc_norm = normalize_doc_number(curr.citation.document_number)

                    doc_same = bool(norm_current_doc and curr_doc_norm and norm_current_doc == curr_doc_norm)

                    if val_same and cond_same and doc_same:
                        is_duplicate_of_current = True
                        break

            if is_duplicate_of_current:
                warnings.append(
                    f"Bỏ dòng '{op.rule_code}' vì giá trị và văn bản căn cứ giống hệt phiên bản hiện tại đang áp dụng."
                )
                continue

        final_ops.append(op)

    for idx, op in enumerate(final_ops):
        op.op_key = f"op-{idx + 1}"

    result.operations = final_ops
    result.warnings = warnings
    return result
