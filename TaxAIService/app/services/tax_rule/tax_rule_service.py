import uuid
from typing import Optional, Dict, Any, List
from fastapi import status, HTTPException
from app.repositories.interfaces.tax_rule_repository_interface import ITaxRuleRepository
from app.services.interfaces.tax_rule_service_interface import ITaxRuleService
from app.services.tax_rule.tax_rule_document_service import TaxRuleDocumentService
from app.mappers.tax_rule import format_tax_rule_data
from app.enum import TaxRuleStatus
from app.errors.tax_rule_errors import TaxRuleErrorMessages, TaxRuleServiceError


class TaxRuleService(ITaxRuleService):
    """
    Core Domain Service quản lý Tax Rules.
    Chỉ tương tác trực tiếp với TaxRuleRepository và điều phối nghiệp vụ.
    """

    def __init__(
        self,
        repository: ITaxRuleRepository,
        url_validation_service: Optional[Any] = None,
        document_service: Optional[TaxRuleDocumentService] = None
    ):
        self.repository = repository
        self.url_validation_service = url_validation_service
        self.document_service = document_service or TaxRuleDocumentService(
            repository=repository,
            url_validation_service=url_validation_service
        )

    async def process_tax_rule_document(
        self,
        filename: str,
        file_bytes: bytes,
        tax_year: int,
        name: Optional[str] = None,
        source_url: Optional[str] = None,
        admin_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Ủy quyền (delegate) xử lý tài liệu sang TaxRuleDocumentService."""
        return await self.document_service.process_tax_rule_document(
            filename=filename,
            file_bytes=file_bytes,
            tax_year=tax_year,
            name=name,
            source_url=source_url,
            admin_id=admin_id
        )

    def get_all_rule_sets(self) -> List[Dict[str, Any]]:
        """Lấy danh sách tóm tắt tất cả các bộ quy tắc thuế từ Repository."""
        rule_sets = self.repository.get_all_rule_sets()
        return [
            {
                "ruleSetId": rs.rule_set_id,
                "adminId": rs.admin_id,
                "name": rs.name,
                "taxYear": rs.tax_year,
                "effectiveFrom": rs.effective_from,
                "effectiveTo": rs.effective_to,
                "status": rs.status,
                "approvedBy": rs.approved_by,
                "approvedAt": rs.approved_at,
                "createdAt": rs.created_at,
                "updatedAt": rs.updated_at,
            }
            for rs in rule_sets
        ]

    def get_tax_rule_set_detail_by_year(self, tax_year: int) -> Dict[str, Any]:
        """Review toàn bộ nội dung chi tiết của TaxRuleSet theo năm tính thuế từ Repository."""
        result = self.repository.get_tax_rule_set_detail_by_year(tax_year)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Không tìm thấy bộ quy tắc thuế cho năm tính thuế {tax_year}."
            )
        rule_set, rules, dep_rules = result
        return {
            "message": f"Tax rule set for year {tax_year} retrieved successfully.",
            "data": format_tax_rule_data(rule_set, rules, dep_rules)
        }

    def get_tax_rule_set_detail(self, rule_set_id: uuid.UUID) -> Dict[str, Any]:
        """Review toàn bộ nội dung chi tiết của TaxRuleSet từ Repository."""
        result = self.repository.get_tax_rule_set_detail(rule_set_id)
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TaxRuleErrorMessages.RULE_SET_NOT_FOUND
            )
        rule_set, rules, dep_rules = result
        return {
            "message": "Tax rule set retrieved successfully.",
            "data": format_tax_rule_data(rule_set, rules, dep_rules)
        }

    def update_tax_rule_set(self, rule_set_id: uuid.UUID, payload: Any) -> Dict[str, Any]:
        """Chỉnh sửa nội dung TaxRuleSet qua Repository (chỉ cho phép khi ở trạng thái Draft)."""
        existing_detail = self.repository.get_tax_rule_set_detail(rule_set_id)
        if not existing_detail:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TaxRuleErrorMessages.RULE_SET_NOT_FOUND
            )

        # chuyển dữ liệu sang dạng dic
        data_dict = payload.model_dump(exclude_unset=True) if hasattr(payload, "model_dump") else dict(payload)

        curr_rule_set = existing_detail[0]
        if curr_rule_set.status == TaxRuleStatus.ACTIVE.value:
            raise TaxRuleServiceError(
                status_code=status.HTTP_400_BAD_REQUEST,
                message=TaxRuleErrorMessages.CANNOT_UPDATE_ACTIVE_RULE_SET
            )

        # Kiểm tra trùng lặp tax_year nếu có thay đổi
        new_tax_year = data_dict.get("tax_year")
        # lấy new_tax_year check năm hiện tại AI đã trích xuất
        if new_tax_year is not None and new_tax_year != curr_rule_set.tax_year:
            # check DB
            conflict_set = self.repository.get_rule_set_by_year(new_tax_year)
            # nếu DB tồn tại khác taxRuleSet thì đã bị tồn tại trong cột khác
            if conflict_set and conflict_set.rule_set_id != rule_set_id:
                raise TaxRuleServiceError(
                    status_code=status.HTTP_409_CONFLICT,
                    message=TaxRuleErrorMessages.TAX_RULE_SET_EXISTS
                )

        updated_result = self.repository.update_tax_rule_set(
            rule_set_id=rule_set_id,
            name=data_dict.get("name"),
            tax_year=new_tax_year,
            effective_from=data_dict.get("effective_from"),
            effective_to=data_dict.get("effective_to"),
            status=data_dict.get("status"),
            tax_rules=data_dict.get("tax_rules"),
            dependent_rules=data_dict.get("dependent_rules")
        )
        if not updated_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TaxRuleErrorMessages.RULE_SET_NOT_FOUND
            )
        rule_set, rules, dep_rules = updated_result
        return {
            "message": "Tax rule set updated successfully.",
            "data": format_tax_rule_data(rule_set, rules, dep_rules)
        }

    def approve_tax_rule_set(
        self,
        rule_set_id: uuid.UUID,
        admin_id: Optional[uuid.UUID] = None
    ) -> Dict[str, Any]:
        """Phê duyệt TaxRuleSet sang Active thông qua Repository."""
        approved_rule_set = self.repository.approve_tax_rule_set(
            rule_set_id=rule_set_id,
            admin_id=admin_id
        )
        if not approved_rule_set:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=TaxRuleErrorMessages.RULE_SET_NOT_FOUND
            )

        return {
            "message": "Tax rule set approved successfully.",
            "ruleSetId": str(approved_rule_set.rule_set_id),
            "status": TaxRuleStatus.ACTIVE.value,
            "approvedBy": approved_rule_set.approved_by,
            "approvedAt": approved_rule_set.approved_at
        }
