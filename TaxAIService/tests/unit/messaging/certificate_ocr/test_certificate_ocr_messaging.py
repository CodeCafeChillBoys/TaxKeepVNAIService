import asyncio
import base64
import json
import uuid
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.messaging.certificate_ocr.consumer import (
    _download_or_decode_bytes,
    handle_certificate_ocr_job,
)
from app.messaging.certificate_ocr.producer import publish_certificate_ocr_response
from app.messaging.certificate_ocr.schemas import (
    CertificateOcrRequestMessage,
    CertificateOcrResponseMessage,
)
from app.schemas.certificate_ocr.certificate_ocr_schema import (
    CertificateOcrResponse,
    CertificateExtractedData,
)


def test_download_or_decode_base64():
    async def _test():
        raw_data = b"sample_certificate_bytes"
        b64_data = base64.b64encode(raw_data).decode("utf-8")
        result = await _download_or_decode_bytes(file_base64=b64_data, file_url=None, file_path=None)
        assert result == raw_data

    asyncio.run(_test())


def test_download_or_decode_url():
    async def _test():
        raw_data = b"downloaded_bytes"
        mock_client = AsyncMock()
        mock_resp = MagicMock()
        mock_resp.content = raw_data
        mock_resp.raise_for_status = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None

        with patch("httpx.AsyncClient", return_value=mock_client):
            result = await _download_or_decode_bytes(file_base64=None, file_url="https://example.com/cert.jpg", file_path=None)
            assert result == raw_data

    asyncio.run(_test())


def test_download_or_decode_file_path(tmp_path):
    async def _test():
        temp_file = tmp_path / "cert.jpg"
        temp_file.write_bytes(b"local_file_bytes")

        result = await _download_or_decode_bytes(file_base64=None, file_url=None, file_path=str(temp_file))
        assert result == b"local_file_bytes"

    asyncio.run(_test())


def test_download_or_decode_file_path_not_found():
    async def _test():
        with pytest.raises(FileNotFoundError):
            await _download_or_decode_bytes(file_base64=None, file_url=None, file_path="/nonexistent/file.jpg")

    asyncio.run(_test())


def test_download_or_decode_none_provided():
    async def _test():
        with pytest.raises(ValueError):
            await _download_or_decode_bytes(file_base64=None, file_url=None, file_path=None)

    asyncio.run(_test())


def test_handle_certificate_ocr_job_invalid_json():
    async def _test():
        mock_message = MagicMock()
        mock_message.body = b"NOT_JSON"
        mock_message.process.return_value.__aenter__ = AsyncMock()
        mock_message.process.return_value.__aexit__ = AsyncMock()
        mock_message.ack = AsyncMock()

        await handle_certificate_ocr_job(mock_message)
        mock_message.ack.assert_awaited_once()

    asyncio.run(_test())


def test_handle_certificate_ocr_job_success():
    async def _test():
        req = {
            "taskId": str(uuid.uuid4()),
            "userId": str(uuid.uuid4()),
            "fileName": "cert.jpg",
            "fileBase64": base64.b64encode(b"dummy_cert_content_long_enough").decode("utf-8"),
            "allowedTypes": [{"code": "CPA", "name": "Kiem toan"}]
        }

        mock_message = MagicMock()
        mock_message.body = json.dumps(req).encode("utf-8")
        mock_message.process.return_value.__aenter__ = AsyncMock()
        mock_message.process.return_value.__aexit__ = AsyncMock()

        mock_ocr_result = CertificateOcrResponse(
            success=True,
            status_code=200,
            message="Thành công",
            data=CertificateExtractedData(
                detected_type="CPA",
                is_valid_type=True,
                certificate_name="CPA",
                full_name="NGUYỄN VĂN A"
            )
        )

        with patch("app.messaging.certificate_ocr.consumer.CertificateOcrService") as mock_svc_cls, \
             patch("app.messaging.certificate_ocr.consumer.publish_certificate_ocr_response", new=AsyncMock()) as mock_publish:
            mock_svc = MagicMock()
            mock_svc.extract_certificate.return_value = mock_ocr_result
            mock_svc_cls.return_value = mock_svc

            await handle_certificate_ocr_job(mock_message)

            mock_svc.extract_certificate.assert_called_once()
            mock_publish.assert_awaited_once()
            sent_response = mock_publish.call_args[0][0]
            assert sent_response.success is True
            assert sent_response.data.full_name == "NGUYỄN VĂN A"

    asyncio.run(_test())


def test_handle_certificate_ocr_job_exception():
    async def _test():
        req = {
            "taskId": str(uuid.uuid4()),
            "fileName": "cert.jpg",
            "fileBase64": base64.b64encode(b"some_bytes").decode("utf-8"),
        }

        mock_message = MagicMock()
        mock_message.body = json.dumps(req).encode("utf-8")
        mock_message.process.return_value.__aenter__ = AsyncMock()
        mock_message.process.return_value.__aexit__ = AsyncMock()

        with patch("app.messaging.certificate_ocr.consumer.CertificateOcrService", side_effect=Exception("Unexpected crash")), \
             patch("app.messaging.certificate_ocr.consumer.publish_certificate_ocr_response", new=AsyncMock()) as mock_publish:
            await handle_certificate_ocr_job(mock_message)

            mock_publish.assert_awaited_once()
            sent_response = mock_publish.call_args[0][0]
            assert sent_response.success is False
            assert sent_response.status_code == 500

    asyncio.run(_test())


def test_publish_certificate_ocr_response_success():
    async def _test():
        resp_msg = CertificateOcrResponseMessage(
            task_id=uuid.uuid4(),
            success=True,
            status_code=200,
            message="OK"
        )
        with patch("app.messaging.certificate_ocr.producer.rabbitmq_client.publish_json", new=AsyncMock()) as mock_pub:
            await publish_certificate_ocr_response(resp_msg)
            mock_pub.assert_awaited_once()

    asyncio.run(_test())


def test_publish_certificate_ocr_response_error():
    async def _test():
        resp_msg = CertificateOcrResponseMessage(
            task_id=uuid.uuid4(),
            success=False,
            status_code=500,
            message="Fail"
        )
        with patch("app.messaging.certificate_ocr.producer.rabbitmq_client.publish_json", side_effect=Exception("RabbitMQ down")):
            # Should catch exception without crashing
            await publish_certificate_ocr_response(resp_msg)

    asyncio.run(_test())
