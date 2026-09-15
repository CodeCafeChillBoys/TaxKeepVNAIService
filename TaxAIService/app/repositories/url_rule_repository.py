import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from app.models.url_validation_rule import UrlValidationRule
from app.repositories.interfaces.iurl_rule_repository import IUrlRuleRepository

class UrlRuleRepository(IUrlRuleRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_all(self, active_only: bool = False) -> List[UrlValidationRule]:
        query = self.db.query(UrlValidationRule)
        if active_only:
            query = query.filter(UrlValidationRule.is_active.is_(True))
        return query.order_by(UrlValidationRule.created_at.desc()).all()

    def get_by_id(self, rule_id: uuid.UUID) -> Optional[UrlValidationRule]:
        return self.db.query(UrlValidationRule).filter(
            UrlValidationRule.id == rule_id,
            UrlValidationRule.is_deleted.is_(False)
        ).first()

    def get_active_rules(self) -> List[UrlValidationRule]:
        return self.db.query(UrlValidationRule).filter(
            UrlValidationRule.is_active.is_(True),
            UrlValidationRule.is_deleted.is_(False)
        ).all()

    def create(self, rule: UrlValidationRule) -> UrlValidationRule:
        self.db.add(rule)
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def update(self, rule: UrlValidationRule) -> UrlValidationRule:
        self.db.commit()
        self.db.refresh(rule)
        return rule

    def delete(self, rule: UrlValidationRule) -> None:
        rule.is_active = False
        rule.is_deleted = True
        rule.deleted_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(rule)