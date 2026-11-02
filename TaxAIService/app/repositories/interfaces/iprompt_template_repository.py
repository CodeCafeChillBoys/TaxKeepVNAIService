from abc import ABC, abstractmethod
from typing import Optional, List
from app.models.ai_prompt_template import AiPromptTemplate

class IPromptTemplateRepository(ABC):
    @abstractmethod
    def get_by_key(self, prompt_key: str, active_only: bool = True) -> Optional[AiPromptTemplate]:
        pass

    @abstractmethod
    def get_all(self, active_only: bool = False) -> List[AiPromptTemplate]:
        pass

    @abstractmethod
    def save(self, template: AiPromptTemplate) -> AiPromptTemplate:
        pass

    @abstractmethod
    def delete(self, template: AiPromptTemplate) -> None:
        pass