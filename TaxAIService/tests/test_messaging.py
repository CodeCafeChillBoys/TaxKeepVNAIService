import uuid
import base64
import json
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.messaging.tax_rule.schemas import (
    TaxRuleExtractRequestMessage,
    TaxRuleExtractResponseMessage,
)
from app.messaging.tax_rule.consumer import (
    _resolve_file_bytes,
    handle_tax_extract_message,
)


def test_request_message_schema_aliases():
    task_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    raw = {
        "taskId": str(task_id),
        "adminId": str(admin_id),
        "fileName": "thue_2026.pdf",
        "taxYear": 2026,
        "fileBase64": base64.b64encode(b"dummy pdf bytes").decode("utf-8")
    }

    req = TaxRuleExtractRequestMessage.model_validate(raw)
    assert req.task_id == task_id
    assert req.admin_id == admin_id
    assert req.file_name == "thue_2026.pdf"
    assert req.tax_year == 2026


def test_response_message_serialization():
    task_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    rule_set_id = uuid.uuid4()

    res = TaxRuleExtractResponseMessage(
        task_id=task_id,
        admin_id=admin_id,
        status="SUCCESS",
        rule_set_id=rule_set_id,
        data={"rulesCount": 5}
    )

    dumped = res.model_dump(by_alias=True)
    assert dumped["taskId"] == task_id
    assert dumped["adminId"] == admin_id
    assert dumped["status"] == "SUCCESS"
    assert dumped["ruleSetId"] == rule_set_id
    assert dumped["data"] == {"rulesCount": 5}
    assert "processedAt" in dumped


@pytest.mark.anyio
async def test_resolve_file_bytes_base64():
    content = b"%PDF-test-content"
    b64_str = base64.b64encode(content).decode("utf-8")

    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="test.pdf",
        file_base64=b64_str,
        tax_year=2026
    )

    resolved = await _resolve_file_bytes(req)
    assert resolved == content


@pytest.mark.anyio
async def test_resolve_file_bytes_file_url():
    content = b"%PDF-supabase-downloaded"
    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="test.pdf",
        file_url="https://fake-supabase.co/storage/v1/object/public/taxkeep-documents/tax-rules/test.pdf",
        tax_year=2026
    )

    mock_resp = MagicMock()
    mock_resp.content = content
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = mock_resp
        resolved = await _resolve_file_bytes(req)
        assert resolved == content
        mock_get.assert_called_once()



@pytest.mark.anyio
async def test_resolve_file_bytes_missing_sources():
    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="test.pdf",
        tax_year=2026
    )

    with pytest.raises(ValueError, match="at least one of"):
        await _resolve_file_bytes(req)


@pytest.mark.anyio
async def test_handle_tax_extract_message_success():
    task_id = uuid.uuid4()
    admin_id = uuid.uuid4()
    rule_set_id = uuid.uuid4()

    payload = {
        "taskId": str(task_id),
        "adminId": str(admin_id),
        "fileName": "luat_thue.pdf",
        "fileBase64": base64.b64encode(b"%PDF-1.4 dummy").decode("utf-8"),
        "taxYear": 2026
    }

    mock_msg = MagicMock()
    mock_msg.body = json.dumps(payload).encode("utf-8")

    # Mock async context manager for message.process()
    async def async_cm():
        yield mock_msg
    mock_msg.process = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(), __aexit__=AsyncMock()))

    with patch("app.messaging.tax_rule.consumer.get_db_context") as mock_db_ctx, \
         patch("app.messaging.tax_rule.consumer.TaxRuleService.process_tax_rule_document", new_callable=AsyncMock) as mock_service_call, \
         patch("app.messaging.tax_rule.consumer.publish_extraction_response", new_callable=AsyncMock) as mock_publish:

        mock_service_call.return_value = {
            "message": "Success",
            "data": {
                "taxRuleSet": {
                    "ruleSetId": rule_set_id,
                    "adminId": admin_id,
                    "taxYear": 2026
                }
            }
        }

        await handle_tax_extract_message(mock_msg)

        assert mock_service_call.called
        assert mock_publish.called
        response_sent: TaxRuleExtractResponseMessage = mock_publish.call_args[0][0]
        assert response_sent.status == "SUCCESS"
        assert response_sent.task_id == task_id
        assert response_sent.admin_id == admin_id
        assert response_sent.rule_set_id == rule_set_id
