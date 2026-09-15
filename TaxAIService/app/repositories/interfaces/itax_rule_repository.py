import uuid
from abc import abstractmethod
from typing import Optional, List, Tuple
from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.repositories.interfaces.irepository import IRepository


class ITaxRuleRepository(IRepository[TaxRuleSet]):
    """Interface định nghĩa các thao tác dữ liệu riêng cho Tax Rule, kế thừa IRepository."""

    @abstractmethod
    def get_rule_set_by_year(self, tax_year: int) -> Optional[TaxRuleSet]:
        """Truy vấn TaxRuleSet theo năm tính thuế."""
        pass

    @abstractmethod
    def get_all_rule_sets(self) -> List[TaxRuleSet]:
        """Truy xuất danh sách tất cả các bộ quy tắc thuế đã tạo."""
        pass

    @abstractmethod
    def get_tax_rule_set_detail_by_year(
        self,
        tax_year: int
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]:
        """Truy xuất chi tiết bộ quy tắc thuế theo năm tính thuế."""
        pass

    @abstractmethod
    def get_rule_set_by_id(self, rule_set_id: uuid.UUID) -> Optional[TaxRuleSet]:
        """Truy vấn TaxRuleSet theo ID (UUID)."""
        pass

    @abstractmethod
    def check_existing_rule_codes(self, rule_codes: List[str]) -> bool:
        """Kiểm tra có bất kỳ ruleCode nào đã tồn tại trong database hay chưa."""
        pass

    @abstractmethod
    def create_tax_rule_set(
        self,
        rule_set: TaxRuleSet,
        rules: List[TaxRule],
        dependent_rules: List[DependentRule]
    ) -> Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]:
        """Lưu TaxRuleSet cùng danh sách TaxRule và DependentRule trong Transaction."""
        pass
        
    @abstractmethod
    def approve_tax_rule_set(
        self,
        rule_set_id: uuid.UUID,
        admin_id: Optional[uuid.UUID] = None
    ) -> Optional[TaxRuleSet]:
        """Kích hoạt trạng thái Active cho TaxRuleSet và các quy tắc liên kết, đồng thời ghi nhận admin phê duyệt."""
        pass

    @abstractmethod
    def get_tax_rule_set_detail(
        self,
        rule_set_id: uuid.UUID
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]:
        """Truy xuất chi tiết bộ quy tắc thuế bao gồm TaxRuleSet, TaxRules và DependentRules."""
        pass
    
    @abstractmethod
    def update_tax_rule_set(
        self,
        rule_set_id: uuid.UUID,
        name: Optional[str] = None,
        tax_year: Optional[int] = None,
        effective_from: Optional[str] = None,
        effective_to: Optional[str] = None,
        status: Optional[str] = None,
        tax_rules: Optional[List[dict]] = None,
        dependent_rules: Optional[List[dict]] = None
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]:
        """Chỉnh sửa thông tin TaxRuleSet, TaxRules và DependentRules."""
        pass
