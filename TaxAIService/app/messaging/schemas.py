# Re-export để tương thích ngược
from app.messaging.tax_rule.schemas import (
    TaxRuleExtractRequestMessage,
    TaxRuleExtractResponseMessage,
)

__all__ = [
    "TaxRuleExtractRequestMessage",
    "TaxRuleExtractResponseMessage",
]
