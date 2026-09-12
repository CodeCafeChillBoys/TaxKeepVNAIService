import uuid
from abc import abstractmethod
from typing import Optional, Dict, Any
from app.services.interfaces.iservice import IService


class ITaxRuleService(IService):
    """Interface định nghĩa Business Logic cho Tax Rule Service, kế thừa IService."""

    @abstractmethod
    async def process_tax_rule_document(
        self,
        filename: str,
        file_bytes: bytes,
        tax_year: int,
        name: Optional[str] = None,
        source_url: Optional[str] = None,
        admin_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Quy trình tiếp nhận, trích xuất AI và lưu trữ Tax Rules từ file PDF."""
        pass

    @abstractmethod
    def approve_tax_rule_set(self, rule_set_id: uuid.UUID) -> Dict[str, Any]:
        """Phê duyệt TaxRuleSet sang Active."""
        pass
