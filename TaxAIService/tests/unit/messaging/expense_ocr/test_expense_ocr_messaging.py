import asyncio
import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
import httpx
from app.errors.expense_ocr_errors import CorruptedFileError, ExpenseOcrError
from app.enum.expense_document_enum import DocumentExtractionStatus
from app.schemas.expense_ocr.expense_ocr_schema import GeminiOcrOutput, ProcessDocumentResponse
from app.messaging.expense_ocr.expense_consumer import (
    _get_file_bytes_and_mime,
    handle_expense_ocr_job,
)
from app.messaging.expense_ocr.producer import publish_expense_ocr_response


# ==============================================================================
# 1. Tests cho _get_file_bytes_and_mime
# ==============================================================================

def test_get_file_bytes_valid_base64():
    """Giải mã file bytes từ chuỗi Base64 hợp lệ"""
    original = b"\xff\xd8\xff\xe0 fake jpeg"
    b64_str = base64.b64encode(original).decode("utf-8")

    async def _test():
        bytes_out, mime = await _get_file_bytes_and_mime(file_base64=b64_str, filename="invoice.jpg")
        assert bytes_out == original
        assert mime == "image/jpeg"

    asyncio.run(_test())


def test_get_file_bytes_invalid_base64():
    """Chuỗi Base64 bị hỏng quăng CorruptedFileError"""
    async def _test():
        with pytest.raises(CorruptedFileError, match="Base64 không hợp lệ"):
            await _get_file_bytes_and_mime(file_base64="INVALID_BASE64_!!!")

    asyncio.run(_test())


def test_get_file_bytes_valid_url():
    """Tải file từ URL qua HTTP Client"""
    original = b"%PDF-1.4 test invoice"

    async def _test():
        mock_resp = MagicMock()
        mock_resp.content = original
        mock_resp.headers = {"content-type": "application/pdf"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__.return_value = mock_client

        with patch("httpx.AsyncClient", return_value=mock_client):
            bytes_out, mime = await _get_file_bytes_and_mime(file_url="https://s3.aws.com/inv.pdf")
            assert bytes_out == original
            assert mime == "application/pdf"

    asyncio.run(_test())


def test_get_file_bytes_url_http_error():
    """URL trả về lỗi HTTP quăng CorruptedFileError"""
    async def _test():
        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.HTTPError("404 Not Found"))
        mock_client.__aenter__.return_value = mock_client

        with patch("httpx.AsyncClient", return_value=mock_client):
            with pytest.raises(CorruptedFileError, match="Không thể tải tệp"):
                await _get_file_bytes_and_mime(file_url="https://s3.aws.com/missing.pdf")

    asyncio.run(_test())


def test_get_file_bytes_empty_content():
    """File rỗng quăng CorruptedFileError"""
    async def _test():
        with pytest.raises(CorruptedFileError, match="tệp rỗng"):
            await _get_file_bytes_and_mime(file_base64="")

    asyncio.run(_test())


# ==============================================================================
# 2. Tests cho publish_expense_ocr_response
# ==============================================================================

def test_publish_expense_ocr_response_when_disabled(monkeypatch):
    """Khi RABBITMQ_ENABLED=False -> không publish và return"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "RABBITMQ_ENABLED", False)

    async def _test():
        with patch("app.messaging.expense_ocr.producer.rabbitmq_client.publish_json", new=AsyncMock()) as mock_pub:
            await publish_expense_ocr_response({"data": {"id": "123"}})
            mock_pub.assert_not_called()

    asyncio.run(_test())


def test_publish_expense_ocr_response_dict_payload(monkeypatch):
    """Publish payload dạng dictionary khi RabbitMQ bật"""
    from app.core.config import settings
    monkeypatch.setattr(settings, "RABBITMQ_ENABLED", True)

    payload = {"data": {"id": "123", "status": "EXTRACTED"}}

    async def _test():
        with patch("app.messaging.expense_ocr.producer.rabbitmq_client.publish_json", new=AsyncMock()) as mock_pub:
            await publish_expense_ocr_response(payload)
            mock_pub.assert_awaited_once_with(
                routing_key=settings.RABBITMQ_EXPENSE_OCR_RESPONSE_QUEUE,
                message_data=payload
            )

    asyncio.run(_test())


def test_publish_expense_ocr_response_model(monkeypatch):
    """Publish payload dạng Pydantic ProcessDocumentResponse"""
    from app.core.config import settings
    from app.schemas.expense_ocr.expense_ocr_schema import (
        ProcessDocumentResponse,
        ProcessDocumentResponseData,
    )
    monkeypatch.setattr(settings, "RABBITMQ_ENABLED", True)

    doc_data = ProcessDocumentResponseData(
        id="task-123",
        periodId="p-1",
        userId="u-1",
        docTypeCode="MEDICAL",
        fileUrl="https://s3/inv.pdf",
        originalFilename="inv.pdf",
        createdAt="2026-01-01T00:00:00Z"
    )
    model = ProcessDocumentResponse(message="OK", data=doc_data)

    async def _test():
        with patch("app.messaging.expense_ocr.producer.rabbitmq_client.publish_json", new=AsyncMock()) as mock_pub:
            await publish_expense_ocr_response(model)
            mock_pub.assert_awaited_once()

    asyncio.run(_test())



# ==============================================================================
# 3. Tests cho handle_expense_ocr_job
# ==============================================================================

def _create_mock_message(body_dict: dict) -> MagicMock:
    message = MagicMock()
    message.body = json.dumps(body_dict).encode("utf-8")

    class FakeProcessContext:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            return None

    message.process.return_value = FakeProcessContext()
    return message


def test_handle_expense_ocr_job_success():
    """Xử lý thành công message bóc tách hóa đơn hợp lệ"""
    task_id = str(uuid.uuid4())
    b64_img = base64.b64encode(b"\xff\xd8\xff\xe0 invoice").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "targetYear": 2026,
        "fileBase64": b64_img,
        "originalFilename": "invoice.jpg",
        "categories": [
            {"code": "MEDICAL", "name": "Y tế", "description": "Hóa đơn viện phí"}
        ]
    }
    message = _create_mock_message(body_dict)

    dummy_doc = GeminiOcrOutput(
        docTypeCode="MEDICAL",
        sellerName="Bệnh viện Bạch Mai",
        totalAmount=500000.0,
        fields=[]
    )

    dummy_service_result = {
        "data": dummy_doc,
        "overall_confidence": 0.95,
        "applied_threshold": 0.80,
        "is_passed_threshold": True,
        "is_year_valid": True,
        "is_doc_type_valid": True,
        "validation_errors": [],
        "raw_payload": "{}"
    }

    async def _test():
        with patch("app.messaging.expense_ocr.expense_consumer.get_db_context"):
            with patch("app.messaging.expense_ocr.expense_consumer.ExpenseOcrService") as mock_service_cls:
                mock_svc = MagicMock()
                mock_svc.extract_and_classify = AsyncMock(return_value=dummy_service_result)
                mock_service_cls.return_value = mock_svc

                with patch("app.messaging.expense_ocr.expense_consumer.ExpenseOcrRepository") as mock_repo_cls:
                    mock_repo = MagicMock()
                    mock_repo_cls.return_value = mock_repo

                    with patch("app.messaging.expense_ocr.expense_consumer.publish_expense_ocr_response", new=AsyncMock()) as mock_pub:
                        await handle_expense_ocr_job(message)

                        mock_svc.extract_and_classify.assert_awaited_once()
                        mock_repo.save_extraction_result.assert_called_once()
                        mock_pub.assert_awaited_once()

                        published_payload = mock_pub.call_args[0][0]
                        assert published_payload["statusCode"] == 200
                        assert published_payload["data"]["status"] == DocumentExtractionStatus.EXTRACTED.value
                        assert published_payload["data"]["sellerName"] == "Bệnh viện Bạch Mai"

    asyncio.run(_test())


def test_handle_expense_ocr_job_validation_errors():
    """Xử lý hóa đơn có lỗi xác thực (lệch năm, không đúng loại) -> trả về 422 FAILED"""
    task_id = str(uuid.uuid4())
    b64_img = base64.b64encode(b"\xff\xd8\xff\xe0 invoice").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "targetYear": 2026,
        "fileBase64": b64_img,
    }
    message = _create_mock_message(body_dict)

    dummy_doc = GeminiOcrOutput(
        docTypeCode="UNKNOWN",
        fields=[]
    )

    dummy_service_result = {
        "data": dummy_doc,
        "overall_confidence": 0.50,
        "applied_threshold": 0.80,
        "is_passed_threshold": False,
        "is_year_valid": False,
        "is_doc_type_valid": False,
        "validation_errors": [{"code": "ERR_YEAR", "message": "Năm trên hóa đơn 2024 không khớp với năm 2026"}],
        "raw_payload": "{}"
    }

    async def _test():
        with patch("app.messaging.expense_ocr.expense_consumer.get_db_context"):
            with patch("app.messaging.expense_ocr.expense_consumer.ExpenseOcrService") as mock_service_cls:
                mock_svc = MagicMock()
                mock_svc.extract_and_classify = AsyncMock(return_value=dummy_service_result)
                mock_service_cls.return_value = mock_svc

                with patch("app.messaging.expense_ocr.expense_consumer.ExpenseOcrRepository") as mock_repo_cls:
                    mock_repo = MagicMock()
                    mock_repo_cls.return_value = mock_repo

                    with patch("app.messaging.expense_ocr.expense_consumer.publish_expense_ocr_response", new=AsyncMock()) as mock_pub:
                        await handle_expense_ocr_job(message)

                        mock_pub.assert_awaited_once()
                        published_payload = mock_pub.call_args[0][0]
                        assert published_payload["statusCode"] == 422
                        assert published_payload["data"]["status"] == DocumentExtractionStatus.FAILED.value
                        assert "không khớp" in published_payload["message"]

    asyncio.run(_test())


def test_handle_expense_ocr_job_ocr_error():
    """Khi xảy ra ExpenseOcrError (file lỗi, không đọc được) -> publish response FAILED"""
    task_id = str(uuid.uuid4())
    body_dict = {
        "taskId": task_id,
        "fileBase64": "NOT_A_VALID_BASE64_AT_ALL_!!!",
    }
    message = _create_mock_message(body_dict)

    async def _test():
        with patch("app.messaging.expense_ocr.expense_consumer.publish_expense_ocr_response", new=AsyncMock()) as mock_pub:
            await handle_expense_ocr_job(message)

            mock_pub.assert_awaited_once()
            published_payload = mock_pub.call_args[0][0]
            assert published_payload["data"]["status"] == DocumentExtractionStatus.FAILED.value
            assert published_payload["errors"][0]["code"] == "ERR_CORRUPTED_FILE"

    asyncio.run(_test())


def test_handle_expense_ocr_job_unexpected_error():
    """Khi xảy ra lỗi hệ thống bất ngờ -> publish response 500 FAILED"""
    task_id = str(uuid.uuid4())
    b64_img = base64.b64encode(b"\xff\xd8\xff\xe0 invoice").decode("utf-8")
    body_dict = {
        "taskId": task_id,
        "fileBase64": b64_img,
    }
    message = _create_mock_message(body_dict)

    async def _test():
        with patch("app.messaging.expense_ocr.expense_consumer.get_db_context", side_effect=RuntimeError("DB Pool Exhausted")):
            with patch("app.messaging.expense_ocr.expense_consumer.publish_expense_ocr_response", new=AsyncMock()) as mock_pub:
                await handle_expense_ocr_job(message)

                mock_pub.assert_awaited_once()
                published_payload = mock_pub.call_args[0][0]
                assert published_payload["statusCode"] == 500
                assert published_payload["data"]["status"] == DocumentExtractionStatus.FAILED.value
                assert "DB Pool Exhausted" in published_payload["message"]

    asyncio.run(_test())
