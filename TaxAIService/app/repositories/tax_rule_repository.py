import uuid
from datetime import datetime
from typing import Optional, List, Tuple, Any
from sqlalchemy.orm import Session
from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.repositories.interfaces.tax_rule_repository_interface import ITaxRuleRepository


class TaxRuleRepository(ITaxRuleRepository):
    """Triển khai cụ thể ITaxRuleRepository sử dụng SQLAlchemy Session."""

    def __init__(self, db: Session):
        self.db = db

    def get_by_id(self, id: Any) -> Optional[TaxRuleSet]:
        """Triển khai IRepository.get_by_id."""
        if isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except ValueError:
                return None
        return self.get_rule_set_by_id(id)

    def get_rule_set_by_year(self, tax_year: int) -> Optional[TaxRuleSet]:
        return self.db.query(TaxRuleSet).filter(TaxRuleSet.tax_year == tax_year).first()

    def get_rule_set_by_id(self, rule_set_id: uuid.UUID) -> Optional[TaxRuleSet]:
        return self.db.query(TaxRuleSet).filter(TaxRuleSet.rule_set_id == rule_set_id).first()

    def check_existing_rule_codes(self, rule_codes: List[str]) -> bool:
        if not rule_codes:
            return False
        return self.db.query(TaxRule).filter(TaxRule.rule_code.in_(rule_codes)).first() is not None

    def create_tax_rule_set(
        self,
        rule_set: TaxRuleSet,
        rules: List[TaxRule],
        dependent_rules: List[DependentRule]
    ) -> Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]:
        try:
            self.db.add(rule_set)
            self.db.flush()

            for rule in rules:
                rule.rule_set_id = rule_set.rule_set_id
            self.db.add_all(rules)
            self.db.flush()

            if dependent_rules:
                self.db.add_all(dependent_rules)

            self.db.commit()
            self.db.refresh(rule_set)
            return rule_set, rules, dependent_rules
        except Exception:
            self.db.rollback()
            raise

    def approve_tax_rule_set(
        self,
        rule_set_id: uuid.UUID,
        admin_id: Optional[uuid.UUID] = None
    ) -> Optional[TaxRuleSet]:
        try:
            rule_set = self.get_rule_set_by_id(rule_set_id)
            if not rule_set:
                return None

            rule_set.status = "Active"
            rule_set.approved_by = admin_id
            rule_set.approved_at = datetime.now()
            self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).update({"status": "Active"})

            rule_ids = [
                r[0] for r in self.db.query(TaxRule.rule_id).filter(TaxRule.rule_set_id == rule_set_id).all()
            ]
            if rule_ids:
                self.db.query(DependentRule).filter(DependentRule.rule_id.in_(rule_ids)).update(
                    {"status": "Active"}, synchronize_session=False
                )

            self.db.commit()
            self.db.refresh(rule_set)
            return rule_set
        except Exception:
            self.db.rollback()
            raise
