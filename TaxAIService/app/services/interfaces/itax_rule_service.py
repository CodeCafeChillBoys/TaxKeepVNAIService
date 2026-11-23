import uuid
from abc import abstractmethod
from app.services.interfaces.iservice import IService
from typing import Optional, Dict, Any, List


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
    def get_all_rule_sets(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tóm tắt tất cả các bộ quy tắc thuế đã bóc tách."""
        pass

    @abstractmethod
    def get_tax_rule_set_detail_by_year(
        self,
        tax_year: int
    ) -> Dict[str, Any]:
        """Review toàn bộ nội dung chi tiết của TaxRuleSet theo năm tính thuế."""
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

    @abstractmethod
    def create_dependent_rule(
        self,
        rule_id: uuid.UUID,
        payload: Any
    ) -> Dict[str, Any]:
        """Thêm mới một DependentRule."""
        pass

    @abstractmethod
    def update_dependent_rule(
        self,
        dep_id: uuid.UUID,
        payload: Any
    ) -> Dict[str, Any]:
        """Cập nhật một DependentRule."""
        pass

    @abstractmethod
    def delete_dependent_rule(
        self,
        dep_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Xóa một DependentRule."""
        pass

    @abstractmethod
    def add_required_document(
        self,
        dependent_rule_id: uuid.UUID,
        payload: Any
    ) -> Dict[str, Any]:
        """Thêm mới giấy tờ cho một DependentRule."""
        pass

    @abstractmethod
    def update_required_document(
        self,
        doc_id: uuid.UUID,
        payload: Any
    ) -> Dict[str, Any]:
        """Cập nhật thông tin giấy tờ của DependentRule."""
        pass

    @abstractmethod
    def delete_required_document(
        self,
        doc_id: uuid.UUID
    ) -> Dict[str, Any]:
        """Xóa một giấy tờ của DependentRule."""
        pass
