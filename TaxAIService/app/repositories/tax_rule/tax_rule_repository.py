from app.core import exclude_from_coverage
import uuid
import json
from datetime import datetime
from typing import Optional, List, Tuple, Any
from sqlalchemy.orm import Session
from app.models.tax_rule_set import TaxRuleSet
from app.models.tax_rule import TaxRule
from app.models.dependent_rule import DependentRule
from app.models.dependent_rule_document import DependentRuleDocument
from app.enum import TaxRuleStatus
from app.repositories.interfaces.tax_rule_repository_interface import ITaxRuleRepository


@exclude_from_coverage
class TaxRuleRepository(ITaxRuleRepository):
    """Triển khai cụ thể ITaxRuleRepository sử dụng SQLAlchemy Session."""

    def __init__(self, db: Session):
        self.db = db
    # check id của taxRuleSetBy ID đã tồn tại chưa
    def get_by_id(self, id: Any) -> Optional[TaxRuleSet]:
        """Triển khai IRepository.get_by_id."""
        if isinstance(id, str):
            try:
                id = uuid.UUID(id)
            except ValueError:
                return None
        return self.get_rule_set_by_id(id)

    # check year của rule_set đã tồn tại chưa
    def get_rule_set_by_year(self, tax_year: int) -> Optional[TaxRuleSet]:
        return self.db.query(TaxRuleSet).filter(TaxRuleSet.tax_year == tax_year).first()

    # lấy lên hết rule set 
    def get_all_rule_sets(self) -> List[TaxRuleSet]:
        return self.db.query(TaxRuleSet).order_by(TaxRuleSet.tax_year.desc()).all()

    # lấy lên ruleSet chi tiết theo year 
    def get_tax_rule_set_detail_by_year(
        self,
        tax_year: int
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]:
        rule_set = self.get_rule_set_by_year(tax_year)
        if not rule_set:
            return None
        return self.get_tax_rule_set_detail(rule_set.rule_set_id)
    # check id rule set 
    def get_rule_set_by_id(self, rule_set_id: uuid.UUID) -> Optional[TaxRuleSet]:
        return self.db.query(TaxRuleSet).filter(TaxRuleSet.rule_set_id == rule_set_id).first()  

    # check ruleCode tồn tài chưa 
    def check_existing_rule_codes(self, rule_codes: List[str]) -> bool:
        if not rule_codes:
            return False
        return self.db.query(TaxRule).filter(TaxRule.rule_code.in_(rule_codes)).first() is not None

    # Tạo taxRuleSet bên trong sẽ tạo taxRule và dependent_rule
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
    
    # phê duyệt bởi admin 
    def approve_tax_rule_set(
        self,
        rule_set_id: uuid.UUID,
        admin_id: Optional[uuid.UUID] = None
    ) -> Optional[TaxRuleSet]:
        try:
            #  Check RuleSet tồn tại thì update nếu ko có none
            rule_set = self.get_rule_set_by_id(rule_set_id)
            if not rule_set:
                return None

            rule_set.status = TaxRuleStatus.ACTIVE.value
            rule_set.approved_by = admin_id
            rule_set.approved_at = datetime.now()
            # query những dữ liệu trong taxRule có id = TaxRuleSetID update  Active
            self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).update({"status": TaxRuleStatus.ACTIVE.value})
            # lọc lên những taxRule có id = TaxRuleSetID
            rule_ids = [
                r[0] for r in self.db.query(TaxRule.rule_id).filter(TaxRule.rule_set_id == rule_set_id).all()
            ]
            # nếu ruleiD tồn tại thì lọc ruleID ben trong DependentRule update status Active
            if rule_ids:
                self.db.query(DependentRule).filter(DependentRule.rule_id.in_(rule_ids)).update(
                    {"status": TaxRuleStatus.ACTIVE.value}, synchronize_session=False
                )

            self.db.commit()
            self.db.refresh(rule_set)
            return rule_set
        except Exception:
            self.db.rollback()
            raise

    # lấy chi tiết taxRuleSet
    def get_tax_rule_set_detail(
        self,
        rule_set_id: uuid.UUID
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]:
        # lấy lên ruleSetID 
        rule_set = self.get_rule_set_by_id(rule_set_id)
        if not rule_set:
            return None
        # lấy tất cả rule và lọc với ruleSetId
        rules = self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).all()
        # lấy ra tất cả RuleID
        rule_ids = [r.rule_id for r in rules]
        dep_rules = []
        # check vs ruleId của DependentRule và lấy lên hết DependentRule
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
    ) -> Optional[Tuple[TaxRuleSet, List[TaxRule], List[DependentRule]]]: #Tuple: Tuple trong Python là một kiểu dữ liệu dùng để chứa nhiều giá trị, khá giống list, nhưng không thể thay đổi sau khi tạo. 
        try:
            #lấy lên ruleSetId kiểm tra
            rule_set = self.get_rule_set_by_id(rule_set_id)
            if not rule_set:
                return None
            # nếu tồn tại Update
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
                # Check rule vs ruleSetId lấy lên hết
                current_rules = self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).all()
                # Lọc ruleCode lấy lên
                existing_rules_by_code = {r.rule_code: r for r in current_rules if r.rule_code}
                # lọc RuleId lấy lên
                existing_rules_by_id = {str(r.rule_id): r for r in current_rules}

                for r_data in tax_rules:
                    rule_id_str = str(r_data.get("rule_id")) if r_data.get("rule_id") else None
                    code = r_data.get("rule_code")
                    cond = r_data.get("condition")
                    # parse từ dic sang json
                    # ensure_ascii=False : giữ nguyên ký tự Unicode như tiếng Việt thay vì chuyển chúng thành dạng \uXXXX.
                    cond_str = json.dumps(cond, ensure_ascii=False) if isinstance(cond, (dict, list)) else (str(cond) if cond is not None else None)

                    r = None
                    # check ruleId và ruleID lấy bên trong exits có tồn tại ko
                    if rule_id_str and rule_id_str in existing_rules_by_id:
                        r = existing_rules_by_id[rule_id_str]
                    # nếu ruleID ko tồn tại thì qua check code
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
                            status=r_data.get("status", TaxRuleStatus.DRAFT.value)
                        )
                        self.db.add(new_r)
                        # nếu ruleCode true
                        if new_r.rule_code:
                            existing_rules_by_code[new_r.rule_code] = new_r
                        existing_rules_by_id[str(new_r.rule_id)] = new_r

            if dependent_rules is not None:
                # lấy lên Rule có ruleSetId = TaxSetRule
                all_rules = self.db.query(TaxRule).filter(TaxRule.rule_set_id == rule_set_id).all()
                # lọc tất id vào mảng
                all_rule_ids = [r.rule_id for r in all_rules]
                # tìm ruleCode có người phụ thuộc  sau đó bỏ vào mảng
                dep_parent_rule = next((r for r in all_rules if r.rule_code == "PIT_DEDUCTION_DEPENDENT"), None)
                # dep_parent_rule nếu có lấy lên RuleID nếu ko có lấy lên hết all_rules
                default_parent_rule_id = dep_parent_rule.rule_id if dep_parent_rule else (all_rules[0].rule_id if all_rules else None)
                # if all_rule_ids lấy lên DependentRule có ruleID bằng rule nếu ko trả về {}
                existing_dep_rules = {str(d.id): d for d in self.db.query(DependentRule).filter(DependentRule.rule_id.in_(all_rule_ids)).all()} if all_rule_ids else {}

                for d_data in dependent_rules:
                    d_id_str = str(d_data.get("id")) if d_data.get("id") else None
                    cond = d_data.get("conditions")
                    cond_str = json.dumps(cond, ensure_ascii=False) if isinstance(cond, (dict, list)) else (str(cond) if cond is not None else None)
                    parent_rule_id = d_data.get("rule_id") or default_parent_rule_id
                    req_docs_data = d_data.get("required_documents") if "required_documents" in d_data else d_data.get("requiredDocuments")

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

                        # Cập nhật required_documents nếu được truyền vào
                        if req_docs_data is not None:
                            existing_docs_map = {str(doc.id): doc for doc in d.required_documents}
                            kept_doc_ids = set()
                            for doc_item in req_docs_data:
                                doc_dict = doc_item if isinstance(doc_item, dict) else (doc_item.model_dump(by_alias=False) if hasattr(doc_item, "model_dump") else {})
                                doc_id_str = str(doc_dict.get("id")) if doc_dict.get("id") else None
                                if doc_id_str and doc_id_str in existing_docs_map:
                                    target_doc = existing_docs_map[doc_id_str]
                                    if doc_dict.get("doc_type") or doc_dict.get("docType"):
                                        target_doc.doc_type = doc_dict.get("doc_type") or doc_dict.get("docType")
                                    if doc_dict.get("name"):
                                        target_doc.name = doc_dict.get("name")
                                    if "is_mandatory" in doc_dict or "isMandatory" in doc_dict:
                                        target_doc.is_mandatory = bool(doc_dict.get("is_mandatory", doc_dict.get("isMandatory")))
                                    if "description" in doc_dict:
                                        target_doc.description = doc_dict.get("description")
                                    kept_doc_ids.add(doc_id_str)
                                else:
                                    new_doc = DependentRuleDocument(
                                        id=uuid.UUID(str(doc_dict["id"])) if doc_dict.get("id") else uuid.uuid4(),
                                        dependent_rule_id=d.id,
                                        doc_type=doc_dict.get("doc_type") or doc_dict.get("docType") or "OTHER",
                                        name=doc_dict.get("name") or "Giấy tờ",
                                        is_mandatory=bool(doc_dict.get("is_mandatory", doc_dict.get("isMandatory", True))),
                                        description=doc_dict.get("description")
                                    )
                                    d.required_documents.append(new_doc)
                                    kept_doc_ids.add(str(new_doc.id))

                            for old_id, old_doc in list(existing_docs_map.items()):
                                if old_id not in kept_doc_ids:
                                    d.required_documents.remove(old_doc)
                                    self.db.delete(old_doc)

                    elif parent_rule_id:
                        new_dep_id = d_data.get("id") or uuid.uuid4()
                        if isinstance(new_dep_id, str):
                            new_dep_id = uuid.UUID(new_dep_id)
                        new_dep = DependentRule(
                            id=new_dep_id,
                            rule_id=parent_rule_id,
                            dependent_type=d_data.get("dependent_type", "OTHER"),
                            name=d_data.get("name", ""),
                            max_age=d_data.get("max_age"),
                            max_monthly_income=d_data.get("max_monthly_income"),
                            is_studying=d_data.get("is_studying", False),
                            is_disabled=d_data.get("is_disabled", False),
                            conditions=cond_str,
                            status=d_data.get("status", TaxRuleStatus.DRAFT.value)
                        )
                        if req_docs_data:
                            for doc_item in req_docs_data:
                                doc_dict = doc_item if isinstance(doc_item, dict) else (doc_item.model_dump(by_alias=False) if hasattr(doc_item, "model_dump") else {})
                                new_doc = DependentRuleDocument(
                                    id=uuid.UUID(str(doc_dict["id"])) if doc_dict.get("id") else uuid.uuid4(),
                                    dependent_rule_id=new_dep_id,
                                    doc_type=doc_dict.get("doc_type") or doc_dict.get("docType") or "OTHER",
                                    name=doc_dict.get("name") or "Giấy tờ",
                                    is_mandatory=bool(doc_dict.get("is_mandatory", doc_dict.get("isMandatory", True))),
                                    description=doc_dict.get("description")
                                )
                                new_dep.required_documents.append(new_doc)

                        self.db.add(new_dep)
                        existing_dep_rules[str(new_dep.id)] = new_dep

            self.db.commit()
            self.db.refresh(rule_set)
            return self.get_tax_rule_set_detail(rule_set_id)
        except Exception:
            self.db.rollback()
            raise

    def create_dependent_rule(
        self,
        rule_id: uuid.UUID,
        dep_data: dict
    ) -> DependentRule:
        try:
            cond = dep_data.get("conditions")
            cond_str = json.dumps(cond, ensure_ascii=False) if isinstance(cond, (dict, list)) else (str(cond) if cond is not None else None)
            dep_id = dep_data.get("id") or uuid.uuid4()
            if isinstance(dep_id, str):
                dep_id = uuid.UUID(dep_id)

            dep = DependentRule(
                id=dep_id,
                rule_id=rule_id,
                dependent_type=dep_data.get("dependent_type") or dep_data.get("dependentType", "OTHER"),
                name=dep_data.get("name", ""),
                max_age=dep_data.get("max_age") if "max_age" in dep_data else dep_data.get("maxAge"),
                max_monthly_income=dep_data.get("max_monthly_income") if "max_monthly_income" in dep_data else dep_data.get("maxMonthlyIncome"),
                is_studying=bool(dep_data.get("is_studying", dep_data.get("isStudying", False))),
                is_disabled=bool(dep_data.get("is_disabled", dep_data.get("isDisabled", False))),
                conditions=cond_str,
                status=dep_data.get("status", TaxRuleStatus.DRAFT.value)
            )

            req_docs = dep_data.get("required_documents") if "required_documents" in dep_data else dep_data.get("requiredDocuments", [])
            if req_docs:
                for doc in req_docs:
                    doc_dict = doc if isinstance(doc, dict) else (doc.model_dump(by_alias=False) if hasattr(doc, "model_dump") else {})
                    new_doc = DependentRuleDocument(
                        id=uuid.UUID(str(doc_dict["id"])) if doc_dict.get("id") else uuid.uuid4(),
                        dependent_rule_id=dep.id,
                        doc_type=doc_dict.get("doc_type") or doc_dict.get("docType", "OTHER"),
                        name=doc_dict.get("name", "Giấy tờ"),
                        is_mandatory=bool(doc_dict.get("is_mandatory", doc_dict.get("isMandatory", True))),
                        description=doc_dict.get("description")
                    )
                    dep.required_documents.append(new_doc)

            self.db.add(dep)
            self.db.commit()
            self.db.refresh(dep)
            return dep
        except Exception:
            self.db.rollback()
            raise

    def update_dependent_rule(
        self,
        dep_id: uuid.UUID,
        dep_data: dict
    ) -> Optional[DependentRule]:
        try:
            dep = self.db.query(DependentRule).filter(DependentRule.id == dep_id).first()
            if not dep:
                return None

            if "dependent_type" in dep_data or "dependentType" in dep_data:
                dep.dependent_type = dep_data.get("dependent_type") or dep_data.get("dependentType")
            if "name" in dep_data and dep_data["name"]:
                dep.name = dep_data["name"]
            if "max_age" in dep_data or "maxAge" in dep_data:
                dep.max_age = dep_data.get("max_age") if "max_age" in dep_data else dep_data.get("maxAge")
            if "max_monthly_income" in dep_data or "maxMonthlyIncome" in dep_data:
                dep.max_monthly_income = dep_data.get("max_monthly_income") if "max_monthly_income" in dep_data else dep_data.get("maxMonthlyIncome")
            if "is_studying" in dep_data or "isStudying" in dep_data:
                val = dep_data.get("is_studying") if "is_studying" in dep_data else dep_data.get("isStudying")
                if val is not None:
                    dep.is_studying = bool(val)
            if "is_disabled" in dep_data or "isDisabled" in dep_data:
                val = dep_data.get("is_disabled") if "is_disabled" in dep_data else dep_data.get("isDisabled")
                if val is not None:
                    dep.is_disabled = bool(val)
            if "conditions" in dep_data and dep_data["conditions"] is not None:
                cond = dep_data["conditions"]
                dep.conditions = json.dumps(cond, ensure_ascii=False) if isinstance(cond, (dict, list)) else str(cond)
            if "status" in dep_data and dep_data["status"]:
                dep.status = dep_data["status"]

            req_docs = dep_data.get("required_documents") if "required_documents" in dep_data else dep_data.get("requiredDocuments")
            if req_docs is not None:
                existing_docs_map = {str(doc.id): doc for doc in dep.required_documents}
                kept_doc_ids = set()
                for doc in req_docs:
                    doc_dict = doc if isinstance(doc, dict) else (doc.model_dump(by_alias=False) if hasattr(doc, "model_dump") else {})
                    doc_id_str = str(doc_dict.get("id")) if doc_dict.get("id") else None
                    if doc_id_str and doc_id_str in existing_docs_map:
                        target_doc = existing_docs_map[doc_id_str]
                        if doc_dict.get("doc_type") or doc_dict.get("docType"):
                            target_doc.doc_type = doc_dict.get("doc_type") or doc_dict.get("docType")
                        if doc_dict.get("name"):
                            target_doc.name = doc_dict.get("name")
                        if "is_mandatory" in doc_dict or "isMandatory" in doc_dict:
                            target_doc.is_mandatory = bool(doc_dict.get("is_mandatory", doc_dict.get("isMandatory")))
                        if "description" in doc_dict:
                            target_doc.description = doc_dict.get("description")
                        kept_doc_ids.add(doc_id_str)
                    else:
                        new_doc = DependentRuleDocument(
                            id=uuid.UUID(str(doc_dict["id"])) if doc_dict.get("id") else uuid.uuid4(),
                            dependent_rule_id=dep.id,
                            doc_type=doc_dict.get("doc_type") or doc_dict.get("docType", "OTHER"),
                            name=doc_dict.get("name", "Giấy tờ"),
                            is_mandatory=bool(doc_dict.get("is_mandatory", doc_dict.get("isMandatory", True))),
                            description=doc_dict.get("description")
                        )
                        dep.required_documents.append(new_doc)
                        kept_doc_ids.add(str(new_doc.id))

                for old_id, old_doc in list(existing_docs_map.items()):
                    if old_id not in kept_doc_ids:
                        dep.required_documents.remove(old_doc)
                        self.db.delete(old_doc)

            self.db.commit()
            self.db.refresh(dep)
            return dep
        except Exception:
            self.db.rollback()
            raise

    def delete_dependent_rule(self, dep_id: uuid.UUID) -> bool:
        try:
            dep = self.db.query(DependentRule).filter(DependentRule.id == dep_id).first()
            if not dep:
                return False
            self.db.delete(dep)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise

    def add_required_document(
        self,
        dependent_rule_id: uuid.UUID,
        doc_data: dict
    ) -> DependentRuleDocument:
        try:
            dep = self.db.query(DependentRule).filter(DependentRule.id == dependent_rule_id).first()
            if not dep:
                raise ValueError(f"DependentRule {dependent_rule_id} not found")

            doc_id = doc_data.get("id") or uuid.uuid4()
            if isinstance(doc_id, str):
                doc_id = uuid.UUID(doc_id)

            new_doc = DependentRuleDocument(
                id=doc_id,
                dependent_rule_id=dependent_rule_id,
                doc_type=doc_data.get("doc_type") or doc_data.get("docType", "OTHER"),
                name=doc_data.get("name", "Giấy tờ"),
                is_mandatory=bool(doc_data.get("is_mandatory", doc_data.get("isMandatory", True))),
                description=doc_data.get("description")
            )
            self.db.add(new_doc)
            self.db.commit()
            self.db.refresh(new_doc)
            return new_doc
        except Exception:
            self.db.rollback()
            raise

    def update_required_document(
        self,
        doc_id: uuid.UUID,
        doc_data: dict
    ) -> Optional[DependentRuleDocument]:
        try:
            doc = self.db.query(DependentRuleDocument).filter(DependentRuleDocument.id == doc_id).first()
            if not doc:
                return None

            if "doc_type" in doc_data or "docType" in doc_data:
                doc.doc_type = doc_data.get("doc_type") or doc_data.get("docType")
            if "name" in doc_data and doc_data["name"]:
                doc.name = doc_data["name"]
            if "is_mandatory" in doc_data or "isMandatory" in doc_data:
                val = doc_data.get("is_mandatory") if "is_mandatory" in doc_data else doc_data.get("isMandatory")
                if val is not None:
                    doc.is_mandatory = bool(val)
            if "description" in doc_data:
                doc.description = doc_data["description"]

            self.db.commit()
            self.db.refresh(doc)
            return doc
        except Exception:
            self.db.rollback()
            raise

    def delete_required_document(self, doc_id: uuid.UUID) -> bool:
        try:
            doc = self.db.query(DependentRuleDocument).filter(DependentRuleDocument.id == doc_id).first()
            if not doc:
                return False
            self.db.delete(doc)
            self.db.commit()
            return True
        except Exception:
            self.db.rollback()
            raise
