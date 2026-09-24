from __future__ import annotations
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.schemas.law_changeset.contract import (
    CurrentRuleItem,
    KnownDocumentItem,
    LawChangesetExtractResponse,
    RuleCatalogItem,
)
from app.services.law_changeset.law_changeset_service import law_changeset_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/law-changesets", tags=["Law Changeset Extraction"])


@router.post(
    "/extract",
    response_model=LawChangesetExtractResponse,
    response_model_by_alias=True,
    summary="Đồng bộ trích xuất thay đổi luật từ file PDF (Dành cho test/dev)",
)
async def extract_law_changeset_sync(
    file: UploadFile = File(..., description="File PDF văn bản pháp luật"),
    context: str = Form(..., description="Chuỗi JSON context chứa baseRevision, currentRules, ruleCatalog..."),
) -> LawChangesetExtractResponse:
    if not settings.LAW_CHANGESET_SYNC_ENDPOINT_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Law changeset sync endpoint is disabled by configuration.",
        )

    task_id = uuid.uuid4()
    changeset_id = uuid.uuid4()
    base_revision = 0

    try:
        context_dict = json.loads(context)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Context is not valid JSON: {e}",
        )

    base_revision = context_dict.get("baseRevision", 0)
    current_rules_raw = context_dict.get("currentRules", [])
    rule_catalog_raw = context_dict.get("ruleCatalog", [])
    known_documents_raw = context_dict.get("knownDocuments", [])
    document_number_hint = context_dict.get("documentNumberHint")
    source_url = context_dict.get("sourceUrl")

    current_rules = [CurrentRuleItem.model_validate(r) for r in current_rules_raw]
    rule_catalog = [RuleCatalogItem.model_validate(r) for r in rule_catalog_raw]
    known_documents = [KnownDocumentItem.model_validate(r) for r in known_documents_raw]

    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File content is empty.",
        )

    try:
        changeset_result = await law_changeset_service.extract_law_changeset(
            file_bytes=file_bytes,
            file_name=file.filename or "uploaded.pdf",
            current_rules=current_rules,
            rule_catalog=rule_catalog,
            known_documents=known_documents,
            document_number_hint=document_number_hint,
            source_url=source_url,
        )

        return LawChangesetExtractResponse(
            schema_version=1,
            task_id=task_id,
            changeset_id=changeset_id,
            base_revision=base_revision,
            status="SUCCESS",
            error_code=None,
            error_message=None,
            model=settings.LAW_CHANGESET_MODEL or settings.GEMINI_MODEL,
            processed_at=datetime.now(timezone.utc).isoformat(),
            result=changeset_result,
        )
    except Exception as ex:
        logger.error(f"Error during sync law changeset extraction: {ex}", exc_info=True)
        return LawChangesetExtractResponse(
            schema_version=1,
            task_id=task_id,
            changeset_id=changeset_id,
            base_revision=base_revision,
            status="FAILED",
            error_code="E-AI_INTERNAL",
            error_message=str(ex),
            model=settings.LAW_CHANGESET_MODEL or settings.GEMINI_MODEL,
            processed_at=datetime.now(timezone.utc).isoformat(),
            result=None,
        )
