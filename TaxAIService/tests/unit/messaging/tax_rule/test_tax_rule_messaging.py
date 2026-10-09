import asyncio
import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.errors.tax_rule_errors import TaxRuleServiceError
from app.messaging.tax_rule.schemas import (
    TaxRuleExtractRequestMessage,
    TaxRuleExtractResponseMessage,
)
from app.messaging.tax_rule.consumer import (
    _resolve_file_bytes,
    handle_tax_extract_message,
)
from app.messaging.tax_rule.producer import publish_extraction_response


# ==============================================================================
# 1. Tests cho _resolve_file_bytes
# ==============================================================================

def test_resolve_file_bytes_from_base64():
    """Giải mã file bytes từ base64 string"""
    original = b"%PDF-1.4 sample content"
    b64_str = base64.b64encode(original).decode("utf-8")
    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="luat.pdf",
        tax_year=2026,
        file_base64=b64_str,
    )

    async def _test():
        result = await _resolve_file_bytes(req)
        assert result == original

    asyncio.run(_test())


def test_resolve_file_bytes_from_url():
    """Tải file bytes qua HTTP/HTTPS URL"""
    original = b"%PDF-1.4 downloaded content"
    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="luat.pdf",
        tax_year=2026,
        file_url="https://example.com/law.pdf",
    )

    async def _test():
        mock_resp = MagicMock()
        mock_resp.content = original
        mock_resp.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_resp)
        mock_http_client.__aenter__.return_value = mock_http_client

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await _resolve_file_bytes(req)
            assert result == original

    asyncio.run(_test())


def test_resolve_file_bytes_from_path(tmp_path):
    """Đọc file bytes từ đường dẫn local"""
    file_content = b"%PDF-1.4 local file"
    temp_file = tmp_path / "law.pdf"
    temp_file.write_bytes(file_content)

    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="luat.pdf",
        tax_year=2026,
        file_path=str(temp_file),
    )

    async def _test():
        result = await _resolve_file_bytes(req)
        assert result == file_content

    asyncio.run(_test())


def test_resolve_file_bytes_path_not_found():
    """Đường dẫn file local không tồn tại ném FileNotFoundError"""
    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="luat.pdf",
        tax_year=2026,
        file_path="non_existent_file.pdf",
    )

    async def _test():
        with pytest.raises(FileNotFoundError):
            await _resolve_file_bytes(req)

    asyncio.run(_test())


def test_resolve_file_bytes_no_source():
    """Không có URL, Base64 hay Path nào được truyền ném ValueError"""
    req = TaxRuleExtractRequestMessage(
        task_id=uuid.uuid4(),
        file_name="luat.pdf",
        tax_year=2026,
    )

    async def _test():
        with pytest.raises(ValueError, match="at least one of"):
            await _resolve_file_bytes(req)

    asyncio.run(_test())


# ==============================================================================
# 2. Tests cho publish_extraction_response
# ==============================================================================

def test_publish_extraction_response():
    """Publish kết quả xử lý bóc tách lên rabbitmq_client"""
    resp_msg = TaxRuleExtractResponseMessage(
        task_id=uuid.uuid4(),
        status="SUCCESS",
        rule_set_id=uuid.uuid4(),
    )

    async def _test():
        with patch("app.messaging.tax_rule.producer.rabbitmq_client.publish_json", new=AsyncMock()) as mock_pub:
            await publish_extraction_response(resp_msg)
            mock_pub.assert_awaited_once()

    asyncio.run(_test())


def test_publish_extraction_response_error_handling():
    """publish_extraction_response bắt lỗi và không làm crash ứng dụng"""
    resp_msg = TaxRuleExtractResponseMessage(
        task_id=uuid.uuid4(),
        status="FAILED",
    )

    async def _test():
        with patch("app.messaging.tax_rule.producer.rabbitmq_client.publish_json", new=AsyncMock(side_effect=Exception("RabbitMQ Down"))):
            # Không được throw exception ra ngoài
            await publish_extraction_response(resp_msg)

    asyncio.run(_test())


# ==============================================================================
# 3. Tests cho handle_tax_extract_message
# ==============================================================================

def _create_mock_message(body_dict: dict) -> MagicMock:
    """Helper tạo mock aio_pika.IncomingMessage"""
    message = MagicMock()
    message.body = json.dumps(body_dict).encode("utf-8")
    message.ack = AsyncMock()

    class FakeProcessContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    message.process.return_value = FakeProcessContext()
    return message


def test_handle_tax_extract_message_parse_error():
    """Message body không đúng định dạng JSON -> ack và return"""
    message = MagicMock()
    message.body = b"NOT_A_VALID_JSON"
    message.ack = AsyncMock()

    class FakeProcessContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    message.process.return_value = FakeProcessContext()

    async def _test():
        await handle_tax_extract_message(message)
        message.ack.assert_awaited_once()

    asyncio.run(_test())


def test_handle_tax_extract_message_success():
    """Message hợp lệ xử lý bóc tách thành công và publish response SUCCESS"""
    task_id = str(uuid.uuid4())
    rule_set_id = str(uuid.uuid4())
    b64_pdf = base64.b64encode(b"%PDF-1.4 content").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "taxYear": 2026,
        "fileName": "luat_2026.pdf",
        "fileBase64": b64_pdf,
    }
    message = _create_mock_message(body_dict)

    dummy_result = {
        "data": {
            "taxRuleSet": {"ruleSetId": rule_set_id},
            "taxRules": [],
        }
    }

    async def _test():
        with patch("app.messaging.tax_rule.consumer.get_db_context"):
            with patch("app.messaging.tax_rule.consumer.TaxRuleService") as mock_service_cls:
                mock_svc = MagicMock()
                mock_svc.process_tax_rule_document = AsyncMock(return_value=dummy_result)
                mock_service_cls.return_value = mock_svc

                with patch("app.messaging.tax_rule.consumer.publish_extraction_response", new=AsyncMock()) as mock_pub:
                    await handle_tax_extract_message(message)

                    mock_svc.process_tax_rule_document.assert_awaited_once()
                    mock_pub.assert_awaited_once()
                    published_msg: TaxRuleExtractResponseMessage = mock_pub.call_args[0][0]
                    assert str(published_msg.task_id) == task_id
                    assert published_msg.status == "SUCCESS"
                    assert str(published_msg.rule_set_id) == rule_set_id

    asyncio.run(_test())


def test_handle_tax_extract_message_business_error():
    """Khi TaxRuleService ném TaxRuleServiceError -> publish response FAILED kèm thông điệp lỗi"""
    task_id = str(uuid.uuid4())
    b64_pdf = base64.b64encode(b"%PDF-1.4 content").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "taxYear": 2026,
        "fileName": "luat_2026.pdf",
        "fileBase64": b64_pdf,
    }
    message = _create_mock_message(body_dict)

    async def _test():
        with patch("app.messaging.tax_rule.consumer.get_db_context"):
            with patch("app.messaging.tax_rule.consumer.TaxRuleService") as mock_service_cls:
                mock_svc = MagicMock()
                mock_svc.process_tax_rule_document = AsyncMock(
                    side_effect=TaxRuleServiceError(status_code=400, message="Văn bản không hợp lệ")
                )
                mock_service_cls.return_value = mock_svc

                with patch("app.messaging.tax_rule.consumer.publish_extraction_response", new=AsyncMock()) as mock_pub:
                    await handle_tax_extract_message(message)

                    mock_pub.assert_awaited_once()
                    published_msg: TaxRuleExtractResponseMessage = mock_pub.call_args[0][0]
                    assert published_msg.status == "FAILED"
                    assert published_msg.error_message == "Văn bản không hợp lệ"

    asyncio.run(_test())


def test_handle_tax_extract_message_unexpected_error():
    """Khi có lỗi bất ngờ -> publish response FAILED kèm Internal error"""
    task_id = str(uuid.uuid4())
    b64_pdf = base64.b64encode(b"%PDF-1.4 content").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "taxYear": 2026,
        "fileName": "luat_2026.pdf",
        "fileBase64": b64_pdf,
    }
    message = _create_mock_message(body_dict)

    async def _test():
        with patch("app.messaging.tax_rule.consumer._resolve_file_bytes", side_effect=RuntimeError("Disk read failure")):
            with patch("app.messaging.tax_rule.consumer.publish_extraction_response", new=AsyncMock()) as mock_pub:
                await handle_tax_extract_message(message)

                mock_pub.assert_awaited_once()
                published_msg: TaxRuleExtractResponseMessage = mock_pub.call_args[0][0]
                assert published_msg.status == "FAILED"
                assert "Disk read failure" in published_msg.error_message

    asyncio.run(_test())
