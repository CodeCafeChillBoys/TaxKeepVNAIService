import logging
from typing import Optional, Dict, Any, List
from app.models.ai_prompt_template import AiPromptTemplate
from app.repositories.interfaces.iprompt_template_repository import IPromptTemplateRepository
from app.schemas.prompt_template.prompt_template_schema import (
    PromptTemplateCreateRequest,
    PromptTemplateUpdateRequest
)
from app.infrastructure.redis_client import get_redis_client

logger = logging.getLogger(__name__)


class PromptTemplateService:
    CACHE_TTL_SECONDS = 300  # Thời hạn sống của cache trên Redis (5 phút)
    REDIS_PREFIX = "ai:prompt:"  # Tiền tố key để phân biệt trên Upstash Redis

    def __init__(self, repository: IPromptTemplateRepository):
        self.repository = repository

    def get_rendered_prompt(
        self,
        prompt_key: str,
        default_template: str,
        params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Lấy System Prompt hoàn chỉnh để gửi sang Gemini.
        Ưu tiên: Redis Cache -> Nếu không có thì Query DB và lưu vào Redis.
        """
        params = params or {}
        cache_key = f"{self.REDIS_PREFIX}{prompt_key}"
        redis_cli = get_redis_client()
        template_str = None

        # 1. Thử đọc từ Redis trước
        if redis_cli:
            try:
                cached_val = redis_cli.get(cache_key)
                if cached_val:
                    template_str = cached_val
            except Exception as e:
                logger.warning(f"Lỗi đọc Redis: {e}")

        # 2. Nếu Redis chưa có -> Query Database
        if not template_str:
            try:
                db_record = self.repository.get_by_key(prompt_key, active_only=True)
                if db_record and db_record.system_prompt:
                    template_str = db_record.system_prompt
                    # Ghi ngược lại vào Redis với thời hạn 5 phút (300 giây)
                    if redis_cli:
                        try:
                            redis_cli.setex(cache_key, self.CACHE_TTL_SECONDS, template_str)
                        except Exception as e:
                            logger.warning(f"Lỗi ghi Redis: {e}")
                else:
                    template_str = default_template
            except Exception as e:
                logger.warning(f"Lỗi đọc DB: {e}. Dùng default_template.")
                template_str = default_template

        # 3. Lắp ghép biến an toàn
        return self._safe_format(template_str, params, default_template)

    def _safe_format(self, template: str, params: Dict[str, Any], fallback: str) -> str:
        """
        Format chuỗi an toàn bằng cách thay thế từng placeholder {key}.
        Khắc phục hoàn toàn lỗi khi prompt chứa ví dụ JSON { "field": "value" }.
        """
        try:
            rendered = template
            for k, v in params.items():
                rendered = rendered.replace(f"{{{k}}}", str(v) if v is not None else "")
            return rendered
        except Exception as e:
            logger.error(f"Lỗi khi thay thế biến vào prompt: {e}. Sử dụng template fallback.")
            fallback_rendered = fallback
            for k, v in params.items():
                fallback_rendered = fallback_rendered.replace(f"{{{k}}}", str(v) if v is not None else "")
            return fallback_rendered

    def get_all(self, active_only: bool = False) -> List[AiPromptTemplate]:
        return self.repository.get_all(active_only=active_only)

    def get_by_key(self, prompt_key: str) -> Optional[AiPromptTemplate]:
        return self.repository.get_by_key(prompt_key, active_only=False)

    def create(self, payload: PromptTemplateCreateRequest) -> AiPromptTemplate:
        existing = self.repository.get_by_key(payload.prompt_key, active_only=False)
        if existing:
            raise ValueError(f"Prompt key '{payload.prompt_key}' đã tồn tại trong hệ thống!")

        new_template = AiPromptTemplate(
            prompt_key=payload.prompt_key.strip().upper(),
            system_prompt=payload.system_prompt,
            description=payload.description,
            variables=payload.variables or [],
            is_active=payload.is_active,
            version=1
        )
        saved = self.repository.save(new_template)
        self.clear_cache(saved.prompt_key)
        return saved

    def update(self, prompt_key: str, payload: PromptTemplateUpdateRequest) -> AiPromptTemplate:
        record = self.repository.get_by_key(prompt_key, active_only=False)
        if not record:
            raise ValueError(f"Không tìm thấy prompt key: {prompt_key}")

        record.system_prompt = payload.system_prompt
        if payload.description is not None:
            record.description = payload.description
        if payload.variables is not None:
            record.variables = payload.variables
        if payload.is_active is not None:
            record.is_active = payload.is_active
        record.version += 1

        updated = self.repository.save(record)
        self.clear_cache(prompt_key)
        return updated

    def delete(self, prompt_key: str) -> bool:
        record = self.repository.get_by_key(prompt_key, active_only=False)
        if not record:
            return False
        self.repository.delete(record)
        self.clear_cache(prompt_key)
        return True

    def clear_cache(self, prompt_key: Optional[str] = None):
        """Xóa cache trên Redis khi Admin cập nhật."""
        redis_cli = get_redis_client()
        if redis_cli:
            try:
                if prompt_key:
                    redis_cli.delete(f"{self.REDIS_PREFIX}{prompt_key}")
                else:
                    keys = redis_cli.keys(f"{self.REDIS_PREFIX}*")
                    if keys:
                        redis_cli.delete(*keys)
            except Exception as e:
                logger.warning(f"Lỗi xóa cache Redis: {e}")