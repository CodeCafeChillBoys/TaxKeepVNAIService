import uuid
import json
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

    def get_all_rule_sets(self) -> List[TaxRuleSet]:
        return self.db.query(TaxRuleSet).order_by(TaxRuleSet.tax_year.desc()).all()

    def get_tax_rule_set_detail_by_year(
        self,
        tax_year: int
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]:
        rule_set = self.get_rule_set_by_year(tax_year)
        if not rule_set:
            return None
        return self.get_tax_rule_set_detail(rule_set.rule_set_id)

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

    def get_tax_rule_set_detail(
        self,
        rule_set_id: uuid.UUID
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]:
        rule_set = self.get_rule_set_by_id(rule_set_id)
        if not rule_set:
            return None

        rules = self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).all()
        rule_ids = [r.rule_id for r in rules]
        dep_rules = []
        if rule_ids:
            dep_rules = self.db.query(DependentRule).filter(DependentRule.rule_id.in_(rule_ids)).all()
        return rule_set, rules, dep_rules

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
        try:
            rule_set = self.get_rule_set_by_id(rule_set_id)
            if not rule_set:
                return None

            if name is not None:
                rule_set.name = name
            if tax_year is not None:
                rule_set.tax_year = tax_year
            if effective_from is not None:
                rule_set.effective_from = effective_from
            if effective_to is not None:
                rule_set.effective_to = effective_to
            if status is not None:
                rule_set.status = status

            if tax_rules is not None:
                current_rules = self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).all()
                existing_rules_by_code = {r.rule_code: r for r in current_rules if r.rule_code}
                existing_rules_by_id = {str(r.rule_id): r for r in current_rules}

                for r_data in tax_rules:
                    rule_id_str = str(r_data.get("rule_id")) if r_data.get("rule_id") else None
                    code = r_data.get("rule_code")
                    cond = r_data.get("condition")
                    # parse từ dic sang json
                    # ensure_ascii=False : giữ nguyên ký tự Unicode như tiếng Việt thay vì chuyển chúng thành dạng \uXXXX.
                    cond_str = json.dumps(cond, ensure_ascii=False) if isinstance(cond, (dict, list)) else (str(cond) if cond is not None else None)

                    r = None
                    if rule_id_str and rule_id_str in existing_rules_by_id:
                        r = existing_rules_by_id[rule_id_str]
                    elif code and code in existing_rules_by_code:
                        r = existing_rules_by_code[code]

                    if r:
                        if code:
                            r.rule_code = code
                        if "rule_name" in r_data and r_data["rule_name"] is not None:
                            r.rule_name = r_data["rule_name"]
                        if "rule_type" in r_data and r_data["rule_type"] is not None:
                            r.rule_type = r_data["rule_type"]
                        if cond is not None:
                            r.condition = cond_str
                        if "value" in r_data:
                            r.value = r_data["value"]
                        if "unit" in r_data:
                            r.unit = r_data["unit"]
                        if "effective_from" in r_data:
                            r.effective_from = r_data["effective_from"]
                        if "effective_to" in r_data:
                            r.effective_to = r_data["effective_to"]
                        if "legal_document" in r_data:
                            r.legal_document = r_data["legal_document"]
                        if "article" in r_data:
                            r.article = r_data["article"]
                        if "clause" in r_data:
                            r.clause = r_data["clause"]
                        if "point" in r_data:
                            r.point = r_data["point"]
                        if "source_url" in r_data:
                            r.source_url = r_data["source_url"]
                        if "status" in r_data and r_data["status"]:
                            r.status = r_data["status"]
                    else:
                        new_r = TaxRule(
                            rule_id=r_data.get("rule_id") or uuid.uuid4(),
                            rule_set_id=rule_set.rule_set_id,
                            rule_code=code or f"RULE_{uuid.uuid4().hex[:8].upper()}",
                            rule_name=r_data.get("rule_name", ""),
                            rule_type=r_data.get("rule_type", "DEDUCTION"),
                            condition=cond_str,
                            value=r_data.get("value"),
                            unit=r_data.get("unit"),
                            effective_from=r_data.get("effective_from") or rule_set.effective_from,
                            effective_to=r_data.get("effective_to") or rule_set.effective_to,
                            legal_document=r_data.get("legal_document"),
                            article=r_data.get("article"),
                            clause=r_data.get("clause"),
                            point=r_data.get("point"),
                            source_url=r_data.get("source_url"),
                            status=r_data.get("status", "Draft")
                        )
                        self.db.add(new_r)
                        if new_r.rule_code:
                            existing_rules_by_code[new_r.rule_code] = new_r
                        existing_rules_by_id[str(new_r.rule_id)] = new_r

            if dependent_rules is not None:
                all_rules = self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).all()
                all_rule_ids = [r.rule_id for r in all_rules]
                dep_parent_rule = next((r for r in all_rules if r.rule_code == "PIT_DEDUCTION_DEPENDENT"), None)
                default_parent_rule_id = dep_parent_rule.rule_id if dep_parent_rule else (all_rules[0].rule_id if all_rules else None)

                existing_dep_rules = {str(d.id): d for d in self.db.query(DependentRule).filter(DependentRule.rule_id.in_(all_rule_ids)).all()} if all_rule_ids else {}

                for d_data in dependent_rules:
                    d_id_str = str(d_data.get("id")) if d_data.get("id") else None
                    cond = d_data.get("conditions")
                    cond_str = json.dumps(cond, ensure_ascii=False) if isinstance(cond, (dict, list)) else (str(cond) if cond is not None else None)
                    parent_rule_id = d_data.get("rule_id") or default_parent_rule_id

                    if d_id_str and d_id_str in existing_dep_rules:
                        d = existing_dep_rules[d_id_str]
                        if "dependent_type" in d_data and d_data["dependent_type"]:
                            d.dependent_type = d_data["dependent_type"]
                        if "name" in d_data and d_data["name"]:
                            d.name = d_data["name"]
                        if "max_age" in d_data:
                            d.max_age = d_data["max_age"]
                        if "max_monthly_income" in d_data:
                            d.max_monthly_income = d_data["max_monthly_income"]
                        if "is_studying" in d_data and d_data["is_studying"] is not None:
                            d.is_studying = d_data["is_studying"]
                        if "is_disabled" in d_data and d_data["is_disabled"] is not None:
                            d.is_disabled = d_data["is_disabled"]
                        if cond is not None:
                            d.conditions = cond_str
                        if "status" in d_data and d_data["status"]:
                            d.status = d_data["status"]
                    elif parent_rule_id:
                        new_dep = DependentRule(
                            id=d_data.get("id") or uuid.uuid4(),
                            rule_id=parent_rule_id,
                            dependent_type=d_data.get("dependent_type", "OTHER"),
                            name=d_data.get("name", ""),
                            max_age=d_data.get("max_age"),
                            max_monthly_income=d_data.get("max_monthly_income"),
                            is_studying=d_data.get("is_studying", False),
                            is_disabled=d_data.get("is_disabled", False),
                            conditions=cond_str,
                            status=d_data.get("status", "Draft")
                        )
                        self.db.add(new_dep)
                        existing_dep_rules[str(new_dep.id)] = new_dep

            self.db.commit()
            self.db.refresh(rule_set)
            return self.get_tax_rule_set_detail(rule_set_id)
        except Exception:
            self.db.rollback()
            raise
