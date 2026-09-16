# app/services/url_validation_service.py
import uuid
from typing import List, Optional, Tuple
from urllib.parse import urlparse
from app.models.url_validation_rule import UrlValidationRule
from app.repositories.interfaces.iurl_rule_repository import IUrlRuleRepository
from app.schemas.url_rule import UrlRuleCreateRequest, UrlRuleUpdateRequest

class UrlValidationService:
    def __init__(self, repo: IUrlRuleRepository):
        self.repo = repo

    def _clean_domain(self, domain_str: str) -> str:
        """Hàm chuẩn hóa domain: bỏ http, https, www, và path đằng sau."""
        clean = domain_str.strip().lower()
        clean = clean.replace("https://", "").replace("http://", "").split("/")[0].split(":")[0]
        if clean.startswith("www."):
            clean = clean[4:]
        return clean

    def validate_url(self, url: str) -> Tuple[bool, Optional[str], Optional[UrlValidationRule]]:
        """
        Kiểm tra URL có thuộc danh sách tên miền cho phép trong CSDL không.
        Trả về: (is_valid, error_message, matched_rule)
        """
        if not url or not url.strip():
            return False, "URL không được để trống.", None

        clean_url = url.strip()

        # 1. Kiểm tra cú pháp cơ bản
        try:
            # urlparse thư viên dùng để bóc tách từng phần trong URL
            # Ví du: ParseResult(scheme='https', netloc='thuvienphapluat.vn', path='/lao-dong-tien-luong/tinh-thue.html',params='',query='',fragment='')
            parsed = urlparse(clean_url)
            if parsed.scheme not in ("http", "https") or not parsed.netloc:
                return False, "URL không đúng định dạng (phải bắt đầu bằng http:// hoặc https://).", None
            hostname = parsed.netloc.split(":")[0].lower()
            if hostname.startswith("www."):
                hostname = hostname[4:]
        except Exception:
            return False, "Không thể phân tích cú pháp URL.", None

        # 2. Lấy danh sách rule đang active
        active_rules = self.repo.get_active_rules()
        if not active_rules:
            # Nếu chưa có rule nào trong DB, mặc định cho qua cú pháp hợp lệ
            return True, None, None

        # 3. So khớp tên miền/đuôi tên miền
        for rule in active_rules:
            target_domain = self._clean_domain(rule.domain)
            if not target_domain:
                continue

            # Khớp chính xác tên miền hoặc là subdomain (vd: vanban.chinhphu.vn khớp chinhphu.vn)
            if hostname == target_domain or hostname.endswith("." + target_domain):
                return True, None, rule

        return False, "URL nguồn không thuộc danh sách tên miền/nguồn được phê duyệt trong hệ thống.", None

    # Các hàm CRUD cho Admin:
    def get_all_rules(self, active_only: bool = False) -> List[UrlValidationRule]:
        return self.repo.get_all(active_only=active_only)

    def create_rule(self, dto: UrlRuleCreateRequest) -> UrlValidationRule:
        rule = UrlValidationRule(
            name=dto.name,
            domain=self._clean_domain(dto.domain),
            description=dto.description,
            is_active=dto.is_active,
            created_by=dto.created_by,
            updated_by=dto.created_by,
        )
        return self.repo.create(rule)

    def update_rule(self, rule_id: uuid.UUID, dto: UrlRuleUpdateRequest) -> Optional[UrlValidationRule]:
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            return None
        if dto.name is not None: rule.name = dto.name
        if dto.domain is not None: rule.domain = self._clean_domain(dto.domain)
        if dto.description is not None: rule.description = dto.description
        if dto.is_active is not None: rule.is_active = dto.is_active
        if dto.updated_by is not None: rule.updated_by = dto.updated_by
        return self.repo.update(rule)

    def delete_rule(self, rule_id: uuid.UUID) -> bool:
        rule = self.repo.get_by_id(rule_id)
        if not rule:
            return False
        self.repo.delete(rule)
        return True
