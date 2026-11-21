# app/prompts/expense_ocr/expense_orc_promt.py
# Proxy for backward-compatibility with legacy imports and typos
from app.prompts.expense_ocr import (
    EXPENSE_OCR_SYSTEM_PROMPT,
    MEDICAL_STATEMENT_RULES,
    MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT,
    format_expense_categories,
    replace_medical_statement_rules,
    build_medical_categories_guide,
    build_medical_statement_prompt,
    build_expense_ocr_prompt,
    _build_prompt,
)

__all__ = [
    "EXPENSE_OCR_SYSTEM_PROMPT",
    "MEDICAL_STATEMENT_RULES",
    "MEDICAL_STATEMENT_ONLY_SYSTEM_PROMPT",
    "format_expense_categories",
    "replace_medical_statement_rules",
    "build_medical_categories_guide",
    "build_medical_statement_prompt",
    "build_expense_ocr_prompt",
    "_build_prompt",
]
