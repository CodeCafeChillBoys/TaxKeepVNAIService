import json
from unittest.mock import MagicMock, patch
import pytest
from app.services.certificate_ocr.certificate_ocr_service import CertificateOcrService
from app.schemas.certificate_ocr.certificate_ocr_schema import (
    GeminiCertificateOcrOutput,
    ExtractedCertificateFieldDetail,
)


@pytest.fixture
def service():
    with patch("app.services.certificate_ocr.certificate_ocr_service.genai.Client"):
        svc = CertificateOcrService()
        svc.client = MagicMock()
        return svc


def test_extract_certificate_file_too_small(service):
    result = service.extract_certificate(b"short", mime_type="image/jpeg")
    assert result.success is False
    assert result.status_code == 400
    assert result.errors[0]["code"] == "ERR_INVALID_FILE"


def test_extract_certificate_empty_ai_response(service):
    mock_resp = MagicMock()
    mock_resp.text = ""
    service.client.models.generate_content.return_value = mock_resp

    result = service.extract_certificate(b"x" * 200, mime_type="image/jpeg")
    assert result.success is False
    assert result.status_code == 422
    assert result.errors[0]["code"] == "ERR_UNREADABLE"


def test_extract_certificate_not_a_certificate(service):
    output = GeminiCertificateOcrOutput(
        is_certificate=False,
        rejection_reason="Ảnh chụp hóa đơn, không phải chứng chỉ",
        detected_type="OTHER"
    )
    mock_resp = MagicMock()
    mock_resp.text = output.model_dump_json()
    service.client.models.generate_content.return_value = mock_resp

    result = service.extract_certificate(b"x" * 200, mime_type="image/jpeg")
    assert result.success is False
    assert result.status_code == 400
    assert result.errors[0]["code"] == "ERR_NOT_A_CERTIFICATE"
    assert "Ảnh chụp hóa đơn" in result.message


def test_extract_certificate_missing_name(service):
    output = GeminiCertificateOcrOutput(
        is_certificate=True,
        full_name="",
        detected_type="CPA"
    )
    mock_resp = MagicMock()
    mock_resp.text = output.model_dump_json()
    service.client.models.generate_content.return_value = mock_resp

    result = service.extract_certificate(b"x" * 200, mime_type="image/jpeg")
    assert result.success is False
    assert result.status_code == 422
    assert result.errors[0]["code"] == "ERR_MISSING_NAME"


def test_extract_certificate_success_with_allowed_types(service):
    field1 = ExtractedCertificateFieldDetail(fieldName="fullName", extractedValue="NGUYỄN VĂN A", confidenceScore=0.98)
    field2 = ExtractedCertificateFieldDetail(fieldName="certificateNumber", extractedValue="CPA-12345", confidenceScore=0.92)
    output = GeminiCertificateOcrOutput(
        is_certificate=True,
        full_name="NGUYỄN VĂN A",
        certificate_name="Chứng chỉ kiểm toán viên",
        certificate_number="CPA-12345",
        citizen_id="001200001234",
        date_of_birth="1985-05-15",
        issuing_authority="Bộ Tài chính",
        issue_date="2020-01-01",
        has_expiry=False,
        detected_type="CPA",
        fields=[field1, field2]
    )
    mock_resp = MagicMock()
    mock_resp.text = output.model_dump_json()
    service.client.models.generate_content.return_value = mock_resp

    allowed = [{"code": "CPA", "name": "Chứng chỉ kiểm toán viên"}]
    result = service.extract_certificate(b"x" * 200, mime_type="image/jpeg", allowed_types=allowed)

    assert result.success is True
    assert result.status_code == 200
    assert result.data.full_name == "NGUYỄN VĂN A"
    assert result.data.is_valid_type is True
    assert result.data.overall_confidence == 0.95


def test_extract_certificate_success_without_fields(service):
    output = GeminiCertificateOcrOutput(
        is_certificate=True,
        full_name="Trần Thị B",
        certificate_name="Chứng chỉ đại lý thuế",
        certificate_number="TAX-999",
        detected_type="TAX_AGENT",
        fields=[]
    )
    mock_resp = MagicMock()
    mock_resp.text = output.model_dump_json()
    service.client.models.generate_content.return_value = mock_resp

    result = service.extract_certificate(b"x" * 200, mime_type="image/png", allowed_types=None)
    assert result.success is True
    assert result.status_code == 200
    assert result.data.full_name == "TRẦN THỊ B"
    assert result.data.is_valid_type is True
    assert result.data.overall_confidence == 0.92


def test_extract_certificate_exception(service):
    service.client.models.generate_content.side_effect = RuntimeError("AI quota exceeded")

    result = service.extract_certificate(b"x" * 200, mime_type="image/jpeg")
    assert result.success is False
    assert result.status_code == 500
    assert result.errors[0]["code"] == "ERR_INTERNAL_AI"
