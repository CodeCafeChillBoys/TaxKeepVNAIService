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
    def approve_tax_rule_set(
        self,
        rule_set_id: uuid.UUID,
        admin_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Phê duyệt TaxRuleSet sang Active và ghi nhận admin phê duyệt."""
        pass

    @abstractmethod
    def get_tax_rule_set_detail(
        self,
        rule_set_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Review toàn bộ nội dung chi tiết của TaxRuleSet, TaxRules và DependentRules."""
        pass

    @abstractmethod
    def update_tax_rule_set(
        self,
        rule_set_id: uuid.UUID,
        payload: Any
    ) -> Dict[str, Any]:
        """Chỉnh sửa toàn bộ nội dung TaxRuleSet, TaxRules, DependentRules và cập nhật taxYear."""
        pass
