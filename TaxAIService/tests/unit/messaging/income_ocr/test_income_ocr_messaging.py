import asyncio
import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from app.messaging.income_ocr.income_consumer import (
    _download_file_bytes,
    handle_income_ocr_job,
)
from app.messaging.income_ocr.producer import publish_income_ocr_response
from app.schemas.income_ocr.income_ocr_schema import (
    IncomeOcrResponse,
    IncomeExtractedData,
    IncomeThresholdValidationResult,
)


# ==============================================================================
# 1. Tests cho _download_file_bytes
# ==============================================================================

def test_download_file_bytes_from_base64():
    """Giải mã file bytes từ base64 string"""
    original = b"%PDF-1.4 test payslip"
    b64_str = base64.b64encode(original).decode("utf-8")

    async def _test():
        content, mime = await _download_file_bytes(file_base64=b64_str)
        assert content == original
        assert mime == "image/jpeg"

    asyncio.run(_test())


def test_download_file_bytes_from_url():
    """Tải file bytes từ URL qua HTTP client"""
    original = b"%PDF-1.4 url payslip"

    async def _test():
        mock_resp = MagicMock()
        mock_resp.content = original
        mock_resp.headers = {"content-type": "application/pdf; charset=utf-8"}
        mock_resp.raise_for_status = MagicMock()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_resp)
        mock_client.__aenter__.return_value = mock_client

        with patch("httpx.AsyncClient", return_value=mock_client):
            content, mime = await _download_file_bytes(file_url="https://s3.com/pay.pdf")
            assert content == original
            assert mime == "application/pdf"

    asyncio.run(_test())


# ==============================================================================
# 2. Tests cho publish_income_ocr_response
# ==============================================================================

def test_publish_income_ocr_response_success():
    """Publish kết quả bóc tách bảng lương lên hàng đợi RabbitMQ"""
    payload = {"taskId": "123", "statusCode": 200, "message": "OK"}

    async def _test():
        with patch("app.messaging.income_ocr.producer.rabbitmq_client") as mock_client:
            mock_channel = AsyncMock()
            mock_default_exchange = AsyncMock()
            mock_channel.default_exchange = mock_default_exchange
            mock_client.channel = mock_channel

            await publish_income_ocr_response(payload)
            mock_default_exchange.publish.assert_awaited_once()

    asyncio.run(_test())


def test_publish_income_ocr_response_error_handling():
    """publish_income_ocr_response bắt lỗi không làm crash"""
    payload = {"taskId": "123", "statusCode": 500}

    async def _test():
        with patch("app.messaging.income_ocr.producer.rabbitmq_client") as mock_client:
            mock_channel = AsyncMock()
            mock_channel.default_exchange.publish = AsyncMock(side_effect=Exception("RabbitMQ connection error"))
            mock_client.channel = mock_channel

            # Không quăng lỗi ra ngoài
            await publish_income_ocr_response(payload)

    asyncio.run(_test())


# ==============================================================================
# 3. Tests cho handle_income_ocr_job
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


def test_handle_income_ocr_job_success():
    """Xử lý thành công message bóc tách bảng lương"""
    task_id = str(uuid.uuid4())
    user_id = str(uuid.uuid4())
    b64_img = base64.b64encode(b"\xff\xd8\xff\xe0 payslip").decode("utf-8")

    body_dict = {
        "taskId": task_id,
        "userId": user_id,
        "targetMonth": 10,
        "targetYear": 2025,
        "fileBase64": b64_img,
    }
    message = _create_mock_message(body_dict)

    dummy_service_result = IncomeOcrResponse(
        success=True,
        statusCode=200,
        message="Bóc tách thành công.",
        data=IncomeExtractedData(
            organizationName="Công ty ABC",
            month=10,
            year=2025,
            totalTaxableIncome=20000000.0,
            insuranceDeducted=2100000.0,
            taxAlreadyDeducted=1000000.0,
            thresholdValidation=IncomeThresholdValidationResult(
                appliedThreshold=0.80,
                overallConfidence=0.92,
                isPassedThreshold=True,
                lowConfidenceFields=[],
            )
        )
    )

    async def _test():
        with patch("app.messaging.income_ocr.income_consumer.get_db_context"):
            with patch("app.messaging.income_ocr.income_consumer.IncomeOcrService") as mock_service_cls:
                mock_svc = MagicMock()
                mock_svc.extract_payslip.return_value = dummy_service_result
                mock_service_cls.return_value = mock_svc

                with patch("app.messaging.income_ocr.income_consumer.publish_income_ocr_response", new=AsyncMock()) as mock_pub:
                    await handle_income_ocr_job(message)

                    mock_svc.extract_payslip.assert_called_once()
                    mock_pub.assert_awaited_once()

                    published = mock_pub.call_args[0][0]
                    assert published["taskId"] == task_id
                    assert published["statusCode"] == 200
                    assert published["data"]["organizationName"] == "Công ty ABC"

    asyncio.run(_test())


def test_handle_income_ocr_job_exception():
    """Khi có exception trong quá trình bóc tách -> publish response failure 500"""
    task_id = str(uuid.uuid4())
    body_dict = {
        "taskId": task_id,
        "fileBase64": "INVALID_B64_!!!",
    }
    message = _create_mock_message(body_dict)

    async def _test():
        with patch("app.messaging.income_ocr.income_consumer.publish_income_ocr_response", new=AsyncMock()) as mock_pub:
            await handle_income_ocr_job(message)

            mock_pub.assert_awaited_once()
            published = mock_pub.call_args[0][0]
            assert published["taskId"] == task_id
            assert published["statusCode"] == 500
            assert "Processing failed" in published["message"]

    asyncio.run(_test())
