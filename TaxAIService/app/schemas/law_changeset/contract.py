from __future__ import annotations
import uuid
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseContractModel(BaseModel):
    model_config = ConfigDict(
        populate_by_name=True,
        alias_generator=to_camel,
    )


class MinimalRequestHeader(BaseContractModel):
    task_id: Optional[Union[uuid.UUID, str]] = None
    changeset_id: Optional[Union[uuid.UUID, str]] = None
    base_revision: Optional[int] = None
    schema_version: Optional[int] = None



class CitationModel(BaseContractModel):
    document_number: Optional[str] = None
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    page: Optional[int] = None


class CurrentRuleItem(BaseContractModel):
    version_id: Optional[str] = None
    rule_code: str
    value_kind: Literal["AMOUNT", "RATE", "SCHEDULE", "JSON", "FLAG", "TEXT"]
    value_number: Optional[float] = None
    value_json: Optional[Any] = None
    value_text: Optional[str] = None
    unit: Optional[Literal["VND/month", "VND/year", "VND/person/month", "VND/payment"]] = None
    condition: Optional[Dict[str, Any]] = None
    condition_text: Optional[str] = None
    apply_from: Optional[str] = None
    apply_to: Optional[str] = None
    citation: Optional[CitationModel] = None


class RuleCatalogItem(BaseContractModel):
    rule_code: str
    rule_group: Literal["SCHEDULE", "DEDUCTION", "DEPENDENT", "SETTLEMENT", "WITHHOLDING", "RATE", "EXEMPTION"]
    value_kind: Literal["AMOUNT", "RATE", "SCHEDULE", "JSON", "FLAG", "TEXT"]
    default_unit: Optional[Literal["VND/month", "VND/year", "VND/person/month", "VND/payment"]] = None
    display_name: str
    description: Optional[str] = None


class KnownDocumentItem(BaseContractModel):
    document_number: str
    document_type: Optional[Literal["LUAT", "NGHI_QUYET", "NGHI_DINH", "THONG_TU", "VBHN", "QUYET_DINH", "KHAC"]] = None
    title: Optional[str] = None
    legal_status: Optional[Literal["CON_HIEU_LUC", "HET_HIEU_LUC_MOT_PHAN", "HET_HIEU_LUC", "CHUA_RO"]] = None


class LawChangesetExtractRequest(BaseContractModel):
    schema_version: int
    task_id: Union[uuid.UUID, str]
    changeset_id: Union[uuid.UUID, str]
    file_url: str

    file_name: str
    source_url: Optional[str] = None
    document_number_hint: Optional[str] = None
    base_revision: int
    current_rules: List[CurrentRuleItem] = Field(default_factory=list)
    rule_catalog: List[RuleCatalogItem] = Field(default_factory=list)
    known_documents: List[KnownDocumentItem] = Field(default_factory=list)


# --- Response Models ---

class CoverageModel(BaseContractModel):
    total_pages: int
    pages_read: int
    mode: Literal["TEXT", "PDF"]
    chunks: int = 1


class DocumentModel(BaseContractModel):
    document_number: Optional[str] = None
    document_type: Optional[Literal["LUAT", "NGHI_QUYET", "NGHI_DINH", "THONG_TU", "VBHN", "QUYET_DINH", "KHAC"]] = None
    issuer: Optional[str] = None
    title: Optional[str] = None
    issued_date: Optional[str] = None
    effective_date: Optional[str] = None
    evidence_page: Optional[int] = None


class TargetScopeModel(BaseContractModel):
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None


class RelationCitationModel(BaseContractModel):
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    page: Optional[int] = None


class RelationModel(BaseContractModel):
    relation_key: str
    type: Literal["REPLACES", "AMENDS", "REPEALS", "BASED_ON", "CONSOLIDATES"]
    target_document_number: str
    target_scope: Optional[TargetScopeModel] = None
    effective_date: Optional[str] = None
    citation: RelationCitationModel
    evidence: str
    note: Optional[str] = None


class ProposedDefinitionModel(BaseContractModel):
    rule_code: str
    rule_group: Literal["SCHEDULE", "DEDUCTION", "DEPENDENT", "SETTLEMENT", "WITHHOLDING", "RATE", "EXEMPTION"]
    value_kind: Literal["AMOUNT", "RATE", "SCHEDULE", "JSON", "FLAG", "TEXT"]
    default_unit: Optional[Literal["VND/month", "VND/year", "VND/person/month", "VND/payment"]] = None
    display_name: str
    description: Optional[str] = None


class AfterValueModel(BaseContractModel):
    value_number: Optional[float] = None
    value_json: Optional[Any] = None
    value_text: Optional[str] = None
    unit: Optional[Literal["VND/month", "VND/year", "VND/person/month", "VND/payment"]] = None
    condition: Optional[Dict[str, Any]] = None
    condition_text: Optional[str] = None


class OperationModel(BaseContractModel):
    op_key: str
    op: Literal["ADD", "UPDATE", "END", "RECITE"]
    rule_code: str
    new_code: bool = False
    proposed_definition: Optional[ProposedDefinitionModel] = None
    after: Optional[AfterValueModel] = None
    apply_from: Optional[str] = None
    apply_to: Optional[str] = None
    apply_basis: Optional[RelationCitationModel] = None
    citation: RelationCitationModel
    evidence: str
    confidence: float
    rationale: Optional[str] = None


class ReferenceModel(BaseContractModel):
    text: str
    target_document_number: Optional[str] = None
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    page: Optional[int] = None


class LawChangesetResult(BaseContractModel):
    coverage: CoverageModel
    document: DocumentModel
    relations: List[RelationModel] = Field(default_factory=list)
    operations: List[OperationModel] = Field(default_factory=list)
    references: List[ReferenceModel] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class LawChangesetExtractResponse(BaseContractModel):
    schema_version: int = 1
    task_id: Union[uuid.UUID, str]
    changeset_id: Union[uuid.UUID, str]
    base_revision: int

    status: Literal["SUCCESS", "FAILED"]
    error_code: Optional[Literal[
        "E-AI_BAD_REQUEST",
        "E-AI_FILE_DOWNLOAD",
        "E-AI_PDF_UNREADABLE",
        "E-AI_TOO_LARGE",
        "E-AI_MODEL_ERROR",
        "E-AI_SCHEMA_INVALID",
        "E-AI_INTERNAL"
    ]] = None
    error_message: Optional[str] = None
    model: Optional[str] = None
    processed_at: str
    result: Optional[LawChangesetResult] = None
