import asyncio
import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.messaging.dependent_ocr.schemas import (
    OcrExtractRequestMessage,
    OcrExtractResponseMessage,
)
from app.messaging.dependent_ocr.consumer import (
    _download_or_decode_bytes,
    handle_ocr_extract_message,
)
from app.messaging.dependent_ocr.producer import publish_ocr_response
from app.schemas.ocr.ocr_document_schema import (
    OcrExtractionResponse,
    ExtractedDependentData,
)


# ==============================================================================
# 1. Tests cho _download_or_decode_bytes
# ==============================================================================

def test_download_or_decode_bytes_from_base64():
    """Giải mã file bytes từ base64 string"""
    original = b"\xff\xd8\xff\xe0 fake jpeg"
    b64_str = base64.b64encode(original).decode("utf-8")

    async def _test():
        result = await _download_or_decode_bytes(b64_str, None, None)
        assert result == original

    asyncio.run(_test())


def test_download_or_decode_bytes_from_url():
    """Tải file bytes từ URL"""
    original = b"\xff\xd8\xff\xe0 fake jpeg url"

    async def _test():
        mock_resp = MagicMock()
        mock_resp.content = original
        mock_resp.raise_for_status = MagicMock()

        mock_http_client = AsyncMock()
        mock_http_client.get = AsyncMock(return_value=mock_resp)
        mock_http_client.__aenter__.return_value = mock_http_client

        with patch("httpx.AsyncClient", return_value=mock_http_client):
            result = await _download_or_decode_bytes(None, "https://example.com/cccd.jpg", None)
            assert result == original

    asyncio.run(_test())


def test_download_or_decode_bytes_from_path(tmp_path):
    """Đọc file bytes từ đường dẫn đĩa"""
    original = b"\xff\xd8\xff\xe0 local jpeg"
    f = tmp_path / "img.jpg"
    f.write_bytes(original)

    async def _test():
        result = await _download_or_decode_bytes(None, None, str(f))
        assert result == original

    asyncio.run(_test())


def test_download_or_decode_bytes_not_found():
    """Đường dẫn file không tồn tại ném FileNotFoundError"""
    async def _test():
        with pytest.raises(FileNotFoundError):
            await _download_or_decode_bytes(None, None, "missing.jpg")

    asyncio.run(_test())


def test_download_or_decode_bytes_no_source():
    """Không có nguồn nào được cung cấp ném ValueError"""
    async def _test():
        with pytest.raises(ValueError, match="Cần cung cấp ít nhất một trong ba"):
            await _download_or_decode_bytes(None, None, None)

    asyncio.run(_test())


# ==============================================================================
# 2. Tests cho publish_ocr_response
# ==============================================================================

def test_publish_ocr_response():
    """Publish kết quả OCR lên RabbitMQ"""
    resp_msg = OcrExtractResponseMessage(
        task_id=uuid.uuid4(),
        success=True,
        status_code=200,
        message="OK",
    )

    async def _test():
        with patch("app.messaging.dependent_ocr.producer.rabbitmq_client.publish_json", new=AsyncMock()) as mock_pub:
            await publish_ocr_response(resp_msg)
            mock_pub.assert_awaited_once()

    asyncio.run(_test())


def test_publish_ocr_response_error_handling():
    """publish_ocr_response bắt lỗi không làm crash"""
    resp_msg = OcrExtractResponseMessage(
        task_id=uuid.uuid4(),
        success=False,
        status_code=500,
        message="Lỗi",
    )

    async def _test():
        with patch("app.messaging.dependent_ocr.producer.rabbitmq_client.publish_json", new=AsyncMock(side_effect=Exception("RabbitMQ error"))):
            await publish_ocr_response(resp_msg)

    asyncio.run(_test())


# ==============================================================================
# 3. Tests cho handle_ocr_extract_message
# ==============================================================================

def _create_mock_message(body_dict: dict) -> MagicMock:
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


def test_handle_ocr_extract_message_parse_error():
    """Body không phải JSON -> ack và return"""
    message = MagicMock()
    message.body = b"INVALID_BODY"
    message.ack = AsyncMock()

    class FakeProcessContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    message.process.return_value = FakeProcessContext()

    async def _test():
        await handle_ocr_extract_message(message)
        message.ack.assert_awaited_once()

    asyncio.run(_test())


def test_handle_ocr_extract_message_front_only_success():
    """Xử lý thành công message chỉ có ảnh mặt trước"""
    task_id = str(uuid.uuid4())
    b64_img = base64.b64encode(b"\xff\xd8\xff\xe0 front").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "fileName": "cccd_front.jpg",
        "fileBase64": b64_img,
        "targetGroup": "CHILD",
    }
    message = _create_mock_message(body_dict)

    dummy_ocr_result = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="Trích xuất thành công",
        data=ExtractedDependentData(fullName="NGUYỄN VĂN A")
    )

    async def _test():
        with patch("app.messaging.dependent_ocr.consumer.get_db_context"):
            with patch("app.messaging.dependent_ocr.consumer.DependentOcrService") as mock_service_cls:
                mock_svc = MagicMock()
                mock_svc.extract_document.return_value = dummy_ocr_result
                mock_service_cls.return_value = mock_svc

                with patch("app.messaging.dependent_ocr.consumer.publish_ocr_response", new=AsyncMock()) as mock_pub:
                    await handle_ocr_extract_message(message)

                    mock_svc.extract_document.assert_called_once()
                    mock_pub.assert_awaited_once()
                    published: OcrExtractResponseMessage = mock_pub.call_args[0][0]
                    assert str(published.task_id) == task_id
                    assert published.success is True
                    assert published.data.full_name == "NGUYỄN VĂN A"

    asyncio.run(_test())


def test_handle_ocr_extract_message_with_back_file():
    """Xử lý thành công message có cả ảnh mặt trước và mặt sau"""
    task_id = str(uuid.uuid4())
    b64_front = base64.b64encode(b"\xff\xd8\xff\xe0 front").decode("utf-8")
    b64_back = base64.b64encode(b"\xff\xd8\xff\xe0 back").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "fileName": "cccd.jpg",
        "fileBase64": b64_front,
        "backFileBase64": b64_back,
    }
    message = _create_mock_message(body_dict)

    dummy_ocr_result = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="Trích xuất 2 mặt thành công",
        data=ExtractedDependentData(fullName="TRẦN VĂN B")
    )

    async def _test():
        with patch("app.messaging.dependent_ocr.consumer.get_db_context"):
            with patch("app.messaging.dependent_ocr.consumer.DependentOcrService") as mock_service_cls:
                mock_svc = MagicMock()
                mock_svc.extract_document.return_value = dummy_ocr_result
                mock_service_cls.return_value = mock_svc

                with patch("app.messaging.dependent_ocr.consumer.publish_ocr_response", new=AsyncMock()) as mock_pub:
                    await handle_ocr_extract_message(message)

                    args, kwargs = mock_svc.extract_document.call_args
                    assert len(kwargs["files"]) == 2
                    mock_pub.assert_awaited_once()

    asyncio.run(_test())


def test_handle_ocr_extract_message_exception():
    """Khi có exception trong quá trình bóc tách -> publish response failure 500"""
    task_id = str(uuid.uuid4())
    b64_img = base64.b64encode(b"\xff\xd8\xff\xe0").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "fileName": "cccd.jpg",
        "fileBase64": b64_img,
    }
    message = _create_mock_message(body_dict)

    async def _test():
        with patch("app.messaging.dependent_ocr.consumer.get_db_context"):
            with patch("app.messaging.dependent_ocr.consumer.DependentOcrService", side_effect=RuntimeError("AI Vision error")):
                with patch("app.messaging.dependent_ocr.consumer.publish_ocr_response", new=AsyncMock()) as mock_pub:
                    await handle_ocr_extract_message(message)

                    mock_pub.assert_awaited_once()
                    published: OcrExtractResponseMessage = mock_pub.call_args[0][0]
                    assert published.success is False
                    assert published.status_code == 500
                    assert "AI Vision error" in str(published.errors)

    asyncio.run(_test())
