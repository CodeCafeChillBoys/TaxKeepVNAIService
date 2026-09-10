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
    def approve_tax_rule_set(self, rule_set_id: uuid.UUID) -> Optional[TaxRuleSet]:
        """Kích hoạt trạng thái Active cho TaxRuleSet và các quy tắc liên kết."""
        pass
