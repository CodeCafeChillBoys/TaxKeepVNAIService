# app/services/url_validation_service.py
import re
import uuid
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from app.models.url_validation_rule import UrlValidationRule
from app.repositories.interfaces.iurl_rule_repository import IUrlRuleRepository
from app.schemas.url_rule_schema import UrlRuleCreateRequest, UrlRuleUpdateRequest

class UrlValidationService:
    def __init__(self, repo: IUrlRuleRepository):
        self.repo = repo

    def validate_url(self, url: str) -> Tuple[bool, Optional[str], Optional[UrlValidationRule]]:
        """
        Kiểm tra URL dựa trên danh sách quy tắc active trong CSDL.
        Trả về: (is_valid, error_message, matched_rule)
        """
        if not url or not url.strip():
            return False, "URL không được để trống.", None

        clean_url = url.strip()

        # 1. Kiểm tra cú pháp cơ bản
        try:
            parsed = urlparse(clean_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return False, "URL không đúng định dạng (phải bắt đầu bằng http:// hoặc https://).", None
            hostname = parsed.netloc.split(":")[0].lower() # Bỏ port nếu có
        except Exception:
            return False, "Không thể phân tích cú pháp URL.", None

        # 2. Lấy danh sách rule đang active
        active_rules = self.repo.get_active_rules()
        if not active_rules:
            # Nếu chưa có rule nào trong DB, mặc định cho qua cú pháp hợp lệ
            return True, None, None

        # 3. So khớp với từng rule
        for rule in active_rules:
            rule_type = rule.rule_type.upper()
            pattern = rule.pattern.strip()

            if rule_type == "DOMAIN":
                pat_domain = pattern.lower()
                if hostname == pat_domain or hostname.endswith("." + pat_domain):
                    return True, None, rule

            elif rule_type == "PREFIX":
                if clean_url.startswith(pattern):
                    return True, None, rule

            elif rule_type == "REGEX":
                try:
                    if re.search(pattern, clean_url):
                        return True, None, rule
                except re.error:
                    continue  # Bỏ qua nếu regex của rule bị lỗi cú pháp

            elif rule_type == "EXACT":
                if clean_url == pattern:
                    return True, None, rule

        return False, "URL nguồn không thuộc danh sách tên miền/nguồn được phê duyệt trong hệ thống.", None

    # Các hàm CRUD cho Admin:
    def get_all_rules(self, active_only: bool = False) -> List[UrlValidationRule]:
        return self.repo.get_all(active_only=active_only)

    def create_rule(self, dto: UrlRuleCreateRequest) -> UrlValidationRule:
        rule = UrlValidationRule(
            name=dto.name,
            rule_type=dto.rule_type.upper(),
            pattern=dto.pattern,
            description=dto.description,
            is_active=dto.is_active,
        )
        return self.repo.create(rule)

    def update_rule(self, rule_id: uuid.UUID, dto: UrlRuleUpdateRequest) -> Optional[UrlValidationRule]:
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            return None
        if dto.name is not None: rule.name = dto.name
        if dto.rule_type is not None: rule.rule_type = dto.rule_type.upper()
        if dto.pattern is not None: rule.pattern = dto.pattern
        if dto.description is not None: rule.description = dto.description
        if dto.is_active is not None: rule.is_active = dto.is_active
        return self.repo.update(rule)

    def delete_rule(self, rule_id: uuid.UUID) -> bool:
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            return False
        self.repo.delete(rule)
        return True