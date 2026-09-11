from fastapi import HTTPException, status


class TaxRuleErrorMessages:
    """Bảng thông báo lỗi chuẩn cho tính năng Quy Tắc Thuế (Tax Rules & Extraction)."""
    NO_TAX_RULE_EXTRACTED = "No tax rule information could be extracted from the document."
    REQUIRED_FIELDS_MISSING = "Some required tax rule fields could not be extracted."
    TAX_RULE_SET_EXISTS = "A tax rule set for this tax year already exists."
    TAX_RULE_SET_NAME_EXISTS = "A tax rule set with this name already exists."
    DUPLICATE_RULE_CODE_IN_EXTRACT = "Duplicate ruleCode detected in extracted rules."
    FAILED_TO_PROCESS_DOCUMENT = "Failed to process tax rule document."
    RULE_SET_NOT_FOUND = "Tax rule set not found."
    RULE_SET_ALREADY_ACTIVE = "Tax rule set is already active."

    @staticmethod
    def duplicate_db_rule_code(code: str) -> str:
        return f"Duplicate ruleCode in database: {code}."


class TaxRuleServiceError(Exception):
    """Exception nghiệp vụ riêng cho TaxRuleService."""
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(message)


class TaxRuleExtractionError(HTTPException):
    """Exception khi LLM không thể trích xuất quy tắc thuế hợp lệ."""
    def __init__(self, detail: str = TaxRuleErrorMessages.NO_TAX_RULE_EXTRACTED):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
