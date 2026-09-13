"""
Tax Rule Schemas Module
Định nghĩa và re-export các Request DTO và Response DTO phục vụ Tax Rules Extraction & Approval.
"""

from app.schemas.tax_rule_request import TaxRuleUploadRequest, TaxRuleApproveRequest
from app.schemas.tax_rule_response import (
    TaxRuleItemResponse,
    TaxRuleSetResponse,
    TaxRuleExtractionDataResponse,
    TaxRuleUploadResponse,
    TaxRuleApproveResponse,
    DependentRuleResponse,
)

# Alias backward compatibility cho code cũ
TaxRuleItemSchema = TaxRuleItemResponse
TaxRuleSetSchema = TaxRuleSetResponse
TaxRuleExtractionData = TaxRuleExtractionDataResponse

__all__ = [
    # Requests
    "TaxRuleUploadRequest",
    "TaxRuleApproveRequest",
    # Responses
    "TaxRuleItemResponse",
    "TaxRuleSetResponse",
    "TaxRuleExtractionDataResponse",
    "TaxRuleUploadResponse",
    "TaxRuleApproveResponse",
    "DependentRuleResponse",
    # Aliases
    "TaxRuleItemSchema",
    "TaxRuleSetSchema",
    "TaxRuleExtractionData",
]
