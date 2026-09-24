from __future__ import annotations
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class GCitation(BaseModel):
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    page: Optional[int] = None


class GBracket(BaseModel):
    toAnnual: Optional[float] = None   # null cho bậc cuối
    rate: float                        # 0..1


class GDependentGroup(BaseModel):
    group: Literal["CHILD", "ADULT_CHILD", "SPOUSE", "PARENT", "OTHER"]
    name: str
    maxAge: Optional[int] = None
    requiresStudying: bool = False
    requiresDisability: bool = False
    incomeLimitApplies: bool = False
    conditions: List[str] = Field(default_factory=list)


class GConditionItem(BaseModel):
    key: str
    value: str                          # mapper đổi "true"/"false"/số sang kiểu tương ứng


class GValue(BaseModel):
    valueNumber: Optional[float] = None
    valueText: Optional[str] = None
    unit: Optional[Literal["VND/month", "VND/year", "VND/person/month", "VND/payment"]] = None
    schedule: Optional[List[GBracket]] = None
    dependentGroups: Optional[List[GDependentGroup]] = None
    conditionItems: Optional[List[GConditionItem]] = None
    conditionText: Optional[str] = None


class GOperation(BaseModel):
    op: Literal["ADD", "UPDATE", "END", "RECITE"]
    ruleCode: str
    newCode: bool = False
    proposedRuleGroup: Optional[str] = None
    proposedValueKind: Optional[str] = None
    proposedDefaultUnit: Optional[str] = None
    proposedDisplayName: Optional[str] = None
    proposedDescription: Optional[str] = None
    after: Optional[GValue] = None
    applyFrom: Optional[str] = None      # YYYY-MM-DD
    applyTo: Optional[str] = None
    applyBasis: Optional[GCitation] = None
    citation: GCitation
    evidence: str
    confidence: float
    rationale: Optional[str] = None


class GRelation(BaseModel):
    type: Literal["REPLACES", "AMENDS", "REPEALS", "BASED_ON", "CONSOLIDATES"]
    targetDocumentNumber: str
    targetArticle: Optional[str] = None
    targetClause: Optional[str] = None
    targetPoint: Optional[str] = None
    effectiveDate: Optional[str] = None
    citation: GCitation
    evidence: str
    note: Optional[str] = None


class GDocument(BaseModel):
    documentNumber: Optional[str] = None
    documentType: Optional[Literal["LUAT", "NGHI_QUYET", "NGHI_DINH", "THONG_TU", "VBHN", "QUYET_DINH", "KHAC"]] = None
    issuer: Optional[str] = None
    title: Optional[str] = None
    issuedDate: Optional[str] = None
    effectiveDate: Optional[str] = None
    evidencePage: Optional[int] = None


class GReference(BaseModel):
    text: str
    targetDocumentNumber: Optional[str] = None
    article: Optional[str] = None
    clause: Optional[str] = None
    point: Optional[str] = None
    page: Optional[int] = None


class GeminiChangesetOutput(BaseModel):
    document: GDocument
    relations: List[GRelation] = Field(default_factory=list)
    operations: List[GOperation] = Field(default_factory=list)
    references: List[GReference] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
