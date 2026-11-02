from typing import Optional, List
from sqlalchemy.orm import Session
from app.models.ai_prompt_template import AiPromptTemplate
from app.repositories.interfaces.iprompt_template_repository import IPromptTemplateRepository

class PromptTemplateRepository(IPromptTemplateRepository):
    def __init__(self, db: Session):
        self.db = db

    def get_by_key(self, prompt_key: str, active_only: bool = True) -> Optional[AiPromptTemplate]:
        query = self.db.query(AiPromptTemplate).filter(AiPromptTemplate.prompt_key == prompt_key)
        if active_only:
            query = query.filter(AiPromptTemplate.is_active.is_(True))
        return query.first()

    def get_all(self, active_only: bool = False) -> List[AiPromptTemplate]:
        query = self.db.query(AiPromptTemplate)
        if active_only:
            query = query.filter(AiPromptTemplate.is_active.is_(True))
        return query.order_by(AiPromptTemplate.prompt_key.asc()).all()

    def save(self, template: AiPromptTemplate) -> AiPromptTemplate:
        self.db.add(template)
        self.db.commit()
        self.db.refresh(template)
        return template

    def delete(self, template: AiPromptTemplate) -> None:
        self.db.delete(template)
        self.db.commit()