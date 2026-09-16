# Re-export để tương thích ngược
from app.messaging.tax_rule.producer import publish_extraction_response

__all__ = [
    "publish_extraction_response",
]
