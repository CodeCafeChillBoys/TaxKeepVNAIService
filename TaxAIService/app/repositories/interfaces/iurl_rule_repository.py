from abc import ABC, abstractmethod
from typing import List, Optional
import uuid
from app.models.url_validation_rule import UrlValidationRule

class IUrlRuleRepository(ABC):
    @abstractmethod
    def get_all(self, active_only: bool = False) -> List[UrlValidationRule]:
        pass

    @abstractmethod
    def get_by_id(self, rule_id: uuid.UUID) -> Optional[UrlValidationRule]:
        pass

    @abstractmethod
    def get_active_rules(self) -> List[UrlValidationRule]:
        pass

    @abstractmethod
    def create(self, rule: UrlValidationRule) -> UrlValidationRule:
        pass

    @abstractmethod
    def update(self, rule: UrlValidationRule) -> UrlValidationRule:
        pass

    @abstractmethod
    def delete(self, rule: UrlValidationRule) -> None:
        pass