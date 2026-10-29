from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from app.models.tax_rule import TaxRule
from app.models.tax_rule_set import TaxRuleSet
from app.models.dependent_rule import DependentRule
from app.enum import TaxRuleStatus

class TaxChatRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_active_rules(self, tax_year: Optional[int] = None) -> List[TaxRule]:
        """
        Lấy tất cả các quy tắc thuế đang Active trong DB.
        Nếu truyền tax_year thì lọc theo năm tính thuế đó.
        Sắp xếp theo tax_year giảm dần (năm mới nhất lên trước).
        """
        query = (
            self.db.query(TaxRule)
            .join(TaxRuleSet, TaxRule.rule_set_id == TaxRuleSet.rule_set_id)
            .options(joinedload(TaxRule.rule_set))
            .filter(TaxRule.status == TaxRuleStatus.ACTIVE.value)
        )

        if tax_year:
            query = query.filter(TaxRuleSet.tax_year == tax_year)

        return query.order_by(TaxRuleSet.tax_year.desc(), TaxRule.rule_type, TaxRule.rule_code).all()

    def get_dependent_rules(self) -> List[DependentRule]:
        """Lấy các điều kiện quy định về người phụ thuộc."""
        return self.db.query(DependentRule).filter(DependentRule.status == TaxRuleStatus.ACTIVE.value).all()