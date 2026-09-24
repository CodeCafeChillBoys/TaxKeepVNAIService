import json
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app as main_app
from app.api.routes.law_changeset.law_changeset_routes import router as law_router
from app.schemas.law_changeset.contract import (
    CoverageModel,
    DocumentModel,
    LawChangesetResult,
)


@pytest.fixture
def sync_client():
    test_app = FastAPI()
    test_app.include_router(law_router)
    return TestClient(test_app)


def test_main_app_endpoint_disabled_by_default():
    # settings.LAW_CHANGESET_SYNC_ENDPOINT_ENABLED is False by default
    client = TestClient(main_app)
    response = client.post(
        "/api/law-changesets/extract",
        files={"file": ("test.pdf", b"%PDF-1.4 sample", "application/pdf")},
        data={"context": json.dumps({"baseRevision": 1})},
    )
    assert response.status_code == 404


def test_sync_endpoint_disabled_returns_404(sync_client):
    with patch.object(settings, "LAW_CHANGESET_SYNC_ENDPOINT_ENABLED", False):
        response = sync_client.post(
            "/api/law-changesets/extract",
            files={"file": ("test.pdf", b"%PDF-1.4 sample", "application/pdf")},
            data={"context": json.dumps({"baseRevision": 1})},
        )
        assert response.status_code == 404


def test_sync_endpoint_invalid_context_returns_400(sync_client):
    with patch.object(settings, "LAW_CHANGESET_SYNC_ENDPOINT_ENABLED", True):
        response = sync_client.post(
            "/api/law-changesets/extract",
            files={"file": ("test.pdf", b"%PDF-1.4 sample", "application/pdf")},
            data={"context": "invalid-json{{{"},
        )
        assert response.status_code == 400
        assert "Context is not valid JSON" in response.text


def test_sync_endpoint_empty_file_returns_400(sync_client):
    with patch.object(settings, "LAW_CHANGESET_SYNC_ENDPOINT_ENABLED", True):
        response = sync_client.post(
            "/api/law-changesets/extract",
            files={"file": ("test.pdf", b"", "application/pdf")},
            data={"context": json.dumps({"baseRevision": 1})},
        )
        assert response.status_code == 400
        assert "File content is empty" in response.text


def test_sync_endpoint_success(sync_client):
    fake_result = LawChangesetResult(
        coverage=CoverageModel(total_pages=1, pages_read=1, mode="TEXT", chunks=1),
        document=DocumentModel(
            document_number="253/2026/NĐ-CP",
            document_type="NGHI_DINH",
            issued_date="2026-06-30",
            effective_date="2026-07-01",
        ),
        operations=[],
        relations=[],
    )

    with patch.object(settings, "LAW_CHANGESET_SYNC_ENDPOINT_ENABLED", True), \
         patch("app.api.routes.law_changeset.law_changeset_routes.law_changeset_service.extract_law_changeset", new_callable=AsyncMock, return_value=fake_result):
        response = sync_client.post(
            "/api/law-changesets/extract",
            files={"file": ("test.pdf", b"%PDF-1.4 sample content", "application/pdf")},
            data={"context": json.dumps({
                "baseRevision": 4,
                "currentRules": [],
                "ruleCatalog": [],
                "knownDocuments": [],
            })},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "SUCCESS"
        assert data["baseRevision"] == 4
        assert data["taskId"] is not None
        assert data["changesetId"] is not None
        assert data["result"]["document"]["documentNumber"] == "253/2026/NĐ-CP"


def test_sync_endpoint_service_error_returns_failed_response(sync_client):
    with patch.object(settings, "LAW_CHANGESET_SYNC_ENDPOINT_ENABLED", True), \
         patch("app.api.routes.law_changeset.law_changeset_routes.law_changeset_service.extract_law_changeset", side_effect=RuntimeError("AI model crashed")):
        response = sync_client.post(
            "/api/law-changesets/extract",
            files={"file": ("test.pdf", b"%PDF-1.4 sample content", "application/pdf")},
            data={"context": json.dumps({"baseRevision": 2})},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "FAILED"
        assert data["errorCode"] == "E-AI_INTERNAL"
        assert "AI model crashed" in data["errorMessage"]
