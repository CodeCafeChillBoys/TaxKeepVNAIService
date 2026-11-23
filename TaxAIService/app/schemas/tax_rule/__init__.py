from app.schemas.tax_rule.tax_rule_request import (
    TaxRuleUploadRequest,
    TaxRuleApproveRequest,
    TaxRuleUpdateRequest,
    TaxRuleItemUpdateRequest,
    DependentRuleUpdateRequest,
    DependentRuleCreateRequest,
    RequiredDocumentItemRequest,
    RequiredDocumentCreateRequest,
    RequiredDocumentUpdateRequest,
)
from app.schemas.tax_rule.tax_rule_response import (
    TaxRuleItemResponse,
    TaxRuleSetResponse,
    TaxRuleExtractionDataResponse,
    TaxRuleUploadResponse,
    TaxRuleApproveResponse,
    TaxRuleDetailResponse,
    DependentRuleResponse,
    RequiredDocumentResponse,
)
from app.enum.tax_rule_enum import RequiredDocumentType
from app.schemas.tax_rule.tax_rule_schema import (
    TaxRuleItemSchema,
    TaxRuleSetSchema,
    TaxRuleExtractionData,
)

__all__ = [
    # Requests
    "TaxRuleUploadRequest",
    "TaxRuleApproveRequest",
    "TaxRuleUpdateRequest",
    "TaxRuleItemUpdateRequest",
    "DependentRuleUpdateRequest",
    "DependentRuleCreateRequest",
    "RequiredDocumentItemRequest",
    "RequiredDocumentCreateRequest",
    "RequiredDocumentUpdateRequest",
    # Responses
    "TaxRuleItemResponse",
    "TaxRuleSetResponse",
    "TaxRuleExtractionDataResponse",
    "TaxRuleUploadResponse",
    "TaxRuleApproveResponse",
    "TaxRuleDetailResponse",
    "DependentRuleResponse",
    "RequiredDocumentResponse",
    # Enums
    "RequiredDocumentType",
    # Aliases
    "TaxRuleItemSchema",
    "TaxRuleSetSchema",
    "TaxRuleExtractionData",
]
