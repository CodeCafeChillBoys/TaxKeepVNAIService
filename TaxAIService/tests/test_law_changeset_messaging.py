import asyncio
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from app.schemas.law_changeset.contract import (
    LawChangesetExtractRequest,
    LawChangesetExtractResponse,
    LawChangesetResult,
    DocumentModel,
    CoverageModel,
)
from app.errors.law_changeset_errors import (
    LawChangesetFileDownloadError,
    LawChangesetPdfUnreadableError,
)
from app.messaging.law_changeset.consumer import handle_law_changeset_message


class FakeIncomingMessage:
    def __init__(self, body_dict: dict | None, raw_body: str | None = None):
        if raw_body is not None:
            self.body = raw_body.encode("utf-8")
        else:
            self.body = json.dumps(body_dict).encode("utf-8")
        self.processed = False

    def process(self, requeue=False, ignore_processed=True):
        fake_self = self
        class Context:
            async def __aenter__(self):
                return fake_self
            async def __aexit__(self, exc_type, exc_val, exc_tb):
                fake_self.processed = True
        return Context()


def test_consumer_missing_ids_no_publish():
    # Message has no taskId
    msg = FakeIncomingMessage({"schemaVersion": 1, "changesetId": "cs-1"})
    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub:
        asyncio.run(handle_law_changeset_message(msg))
        assert msg.processed is True
        mock_pub.assert_not_called()


def test_consumer_malformed_json_no_publish():
    msg = FakeIncomingMessage(None, raw_body="invalid-json{{{")
    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub:
        asyncio.run(handle_law_changeset_message(msg))
        assert msg.processed is True
        mock_pub.assert_not_called()


def test_consumer_unsupported_schema_version():
    msg = FakeIncomingMessage({
        "schemaVersion": 99,
        "taskId": "task-1",
        "changesetId": "cs-1",
        "fileUrl": "http://example.com/test.pdf"
    })
    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub:
        asyncio.run(handle_law_changeset_message(msg))
        assert msg.processed is True
        mock_pub.assert_called_once()
        resp: LawChangesetExtractResponse = mock_pub.call_args[0][0]
        assert resp.status == "FAILED"
        assert resp.error_code == "E-AI_BAD_REQUEST"
        assert "schemaVersion" in resp.error_message


def test_consumer_bad_request_validation():
    # Missing fileUrl
    msg = FakeIncomingMessage({
        "schemaVersion": 1,
        "taskId": "task-2",
        "changesetId": "cs-2",
    })
    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub:
        asyncio.run(handle_law_changeset_message(msg))
        assert msg.processed is True
        mock_pub.assert_called_once()
        resp: LawChangesetExtractResponse = mock_pub.call_args[0][0]
        assert resp.status == "FAILED"
        assert resp.error_code == "E-AI_BAD_REQUEST"


def test_consumer_file_download_error():
    msg = FakeIncomingMessage({
        "schemaVersion": 1,
        "taskId": "task-3",
        "changesetId": "cs-3",
        "baseRevision": 1,
        "fileName": "404.pdf",
        "fileUrl": "http://example.com/404.pdf",
    })
    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub, \
         patch("app.messaging.law_changeset.consumer.law_changeset_service.download_file", side_effect=LawChangesetFileDownloadError("Download failed 404")):
        asyncio.run(handle_law_changeset_message(msg))
        mock_pub.assert_called_once()
        resp: LawChangesetExtractResponse = mock_pub.call_args[0][0]
        assert resp.status == "FAILED"
        assert resp.error_code == "E-AI_FILE_DOWNLOAD"
        assert "Download failed 404" in resp.error_message


def test_consumer_pdf_unreadable_error():
    msg = FakeIncomingMessage({
        "schemaVersion": 1,
        "taskId": "task-4",
        "changesetId": "cs-4",
        "baseRevision": 1,
        "fileName": "bad.pdf",
        "fileUrl": "http://example.com/bad.pdf",
    })
    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub, \
         patch("app.messaging.law_changeset.consumer.law_changeset_service.download_file", new_callable=AsyncMock, return_value=b"bad_bytes"), \
         patch("app.messaging.law_changeset.consumer.law_changeset_service.extract_law_changeset", side_effect=LawChangesetPdfUnreadableError("PDF corrupt")):
        asyncio.run(handle_law_changeset_message(msg))
        mock_pub.assert_called_once()
        resp: LawChangesetExtractResponse = mock_pub.call_args[0][0]
        assert resp.status == "FAILED"
        assert resp.error_code == "E-AI_PDF_UNREADABLE"


def test_consumer_timeout_error():
    msg = FakeIncomingMessage({
        "schemaVersion": 1,
        "taskId": "task-5",
        "changesetId": "cs-5",
        "baseRevision": 1,
        "fileName": "slow.pdf",
        "fileUrl": "http://example.com/slow.pdf",
    })
    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub, \
         patch("app.messaging.law_changeset.consumer.asyncio.wait_for", side_effect=asyncio.TimeoutError()):
        asyncio.run(handle_law_changeset_message(msg))
        mock_pub.assert_called_once()
        resp: LawChangesetExtractResponse = mock_pub.call_args[0][0]
        assert resp.status == "FAILED"
        assert resp.error_code == "E-AI_MODEL_ERROR"



def test_consumer_success():
    msg = FakeIncomingMessage({
        "schemaVersion": 1,
        "taskId": "task-6",
        "changesetId": "cs-6",
        "baseRevision": 10,
        "fileUrl": "http://example.com/good.pdf",
        "fileName": "test.pdf"
    })
    fake_result = LawChangesetResult(
        coverage=CoverageModel(total_pages=5, pages_read=5, mode="TEXT", chunks=1),
        document=DocumentModel(
            document_number="253/2025/NĐ-CP",
            effective_date="2026-01-01"
        ),
        operations=[],
        relations=[],
    )

    with patch("app.messaging.law_changeset.consumer.publish_law_changeset_response", new_callable=AsyncMock) as mock_pub, \
         patch("app.messaging.law_changeset.consumer.law_changeset_service.download_file", new_callable=AsyncMock, return_value=b"%PDF-1.4 test"), \
         patch("app.messaging.law_changeset.consumer.law_changeset_service.extract_law_changeset", new_callable=AsyncMock, return_value=fake_result):
        asyncio.run(handle_law_changeset_message(msg))
        mock_pub.assert_called_once()
        resp: LawChangesetExtractResponse = mock_pub.call_args[0][0]
        assert resp.status == "SUCCESS"
        assert str(resp.task_id) == "task-6"
        assert str(resp.changeset_id) == "cs-6"
        assert resp.base_revision == 10
        assert resp.result is not None
        assert resp.result.document.document_number == "253/2025/NĐ-CP"

