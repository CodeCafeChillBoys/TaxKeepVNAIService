from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional
from app.schemas.law_changeset.contract import (
    CoverageModel,
    DocumentModel,
    TargetScopeModel,
    RelationCitationModel,
    RelationModel,
    ProposedDefinitionModel,
    AfterValueModel,
    OperationModel,
    ReferenceModel,
    LawChangesetResult,
)
from app.schemas.law_changeset.gemini_output import (
    GeminiChangesetOutput,
    GCitation,
    GOperation,
    GRelation,
    GDocument,
    GReference,
)

logger = logging.getLogger(__name__)


def _adjust_page(page: Optional[int], page_offset: int) -> Optional[int]:
    if page is None:
        return None
    return page + page_offset


def _map_citation(c: Optional[GCitation], page_offset: int) -> Optional[RelationCitationModel]:
    if not c:
        return None
    return RelationCitationModel(
        article=c.article,
        clause=c.clause,
        point=c.point,
        page=_adjust_page(c.page, page_offset),
    )


def _map_condition_items(items: Optional[List[Any]]) -> Optional[Dict[str, Any]]:
    if not items:
        return None
    res: Dict[str, Any] = {}
    for item in items:
        k = item.key
        v_str = str(item.value).strip()
        v_lower = v_str.lower()
        if v_lower == "true":
            res[k] = True
        elif v_lower == "false":
            res[k] = False
        else:
            try:
                if "." in v_str:
                    res[k] = float(v_str)
                else:
                    res[k] = int(v_str)
            except ValueError:
                res[k] = v_str
    return res


def map_gemini_output_to_result(
    output: GeminiChangesetOutput,
    total_pages: int,
    pages_read: int,
    mode: str,
    chunks_count: int = 1,
    page_offset: int = 0,
) -> LawChangesetResult:
    """
    Chuyển đổi Structured Output từ Gemini sang cấu trúc LawChangesetResult hợp đồng.
    """
    # 1. Coverage
    coverage = CoverageModel(
        total_pages=total_pages,
        pages_read=pages_read,
        mode=mode,  # type: ignore
        chunks=chunks_count,
    )

    # 2. Document
    doc = output.document
    document = DocumentModel(
        document_number=doc.documentNumber,
        document_type=doc.documentType,  # type: ignore
        issuer=doc.issuer,
        title=doc.title,
        issued_date=doc.issuedDate,
        effective_date=doc.effectiveDate,
        evidence_page=_adjust_page(doc.evidencePage, page_offset),
    )

    # 3. Relations
    relations: List[RelationModel] = []
    for idx, r in enumerate(output.relations):
        target_scope = None
        if r.targetArticle or r.targetClause or r.targetPoint:
            target_scope = TargetScopeModel(
                article=r.targetArticle,
                clause=r.targetClause,
                point=r.targetPoint,
            )

        citation = _map_citation(r.citation, page_offset) or RelationCitationModel()
        relations.append(
            RelationModel(
                relation_key=f"rel-{idx + 1}",
                type=r.type,  # type: ignore
                target_document_number=r.targetDocumentNumber,
                target_scope=target_scope,
                effective_date=r.effectiveDate,
                citation=citation,
                evidence=r.evidence,
                note=r.note,
            )
        )

    # 4. Operations
    operations: List[OperationModel] = []
    for idx, op in enumerate(output.operations):
        after_model = None
        if op.after:
            value_json = None
            if op.after.schedule is not None:
                value_json = [
                    {"toAnnual": b.toAnnual, "rate": b.rate}
                    for b in op.after.schedule
                ]
            elif op.after.dependentGroups is not None:
                value_json = [
                    g.model_dump(by_alias=True)
                    for g in op.after.dependentGroups
                ]

            cond_dict = _map_condition_items(op.after.conditionItems)

            after_model = AfterValueModel(
                value_number=op.after.valueNumber,
                value_json=value_json,
                value_text=op.after.valueText,
                unit=op.after.unit,  # type: ignore
                condition=cond_dict,
                condition_text=op.after.conditionText,
            )

        proposed_def = None
        if op.newCode:
            proposed_def = ProposedDefinitionModel(
                rule_code=op.ruleCode,
                rule_group=op.proposedRuleGroup or "EXEMPTION",  # type: ignore
                value_kind=op.proposedValueKind or "TEXT",  # type: ignore
                default_unit=op.proposedDefaultUnit,  # type: ignore
                display_name=op.proposedDisplayName or op.ruleCode,
                description=op.proposedDescription,
            )

        citation = _map_citation(op.citation, page_offset) or RelationCitationModel()
        apply_basis = _map_citation(op.applyBasis, page_offset)

        operations.append(
            OperationModel(
                op_key=f"op-{idx + 1}",
                op=op.op,  # type: ignore
                rule_code=op.ruleCode,
                new_code=op.newCode,
                proposed_definition=proposed_def,
                after=after_model,
                apply_from=op.applyFrom,
                apply_to=op.applyTo,
                apply_basis=apply_basis,
                citation=citation,
                evidence=op.evidence,
                confidence=round(op.confidence, 4) if op.confidence is not None else 0.8,
                rationale=op.rationale,
            )
        )

    # 5. References
    references: List[ReferenceModel] = []
    for ref in output.references:
        references.append(
            ReferenceModel(
                text=ref.text,
                target_document_number=ref.targetDocumentNumber,
                article=ref.article,
                clause=ref.clause,
                point=ref.point,
                page=_adjust_page(ref.page, page_offset),
            )
        )

    return LawChangesetResult(
        coverage=coverage,
        document=document,
        relations=relations,
        operations=operations,
        references=references,
        warnings=list(output.warnings),
    )
