import io
from unittest.mock import MagicMock, patch
import pytest
from app.schemas.certificate_ocr.certificate_ocr_schema import (
    CertificateOcrResponse,
    CertificateExtractedData
)


def test_extract_certificate_unsupported_mime_type(client):
    response = client.post(
        "/api/certificates/ocr/extract",
        files={"file": ("cert.txt", io.BytesIO(b"abc" * 100), "text/plain")}
    )
    assert response.status_code == 400
    assert "không được hỗ trợ" in response.json()["detail"]


@patch("app.api.routes.certificate_ocr.certificate_ocr_routes.ocr_service.extract_certificate")
def test_extract_certificate_success(mock_extract, client):
    mock_extract.return_value = CertificateOcrResponse(
        success=True,
        status_code=200,
        message="Bóc tách chứng chỉ hành nghề thành công.",
        data=CertificateExtractedData(
            detected_type="CPA",
            is_valid_type=True,
            certificate_name="Chứng chỉ kiểm toán viên",
            full_name="NGUYỄN VĂN A"
        )
    )

    response = client.post(
        "/api/certificates/ocr/extract",
        files={"file": ("cert.jpg", io.BytesIO(b"fake_image_bytes" * 20), "image/jpeg")},
        data={"allowed_types_json": '[{"code": "CPA", "name": "Kiem toan"}]'}
    )
    assert response.status_code == 200
    json_data = response.json()
    assert json_data["success"] is True
    assert json_data["data"]["fullName"] == "NGUYỄN VĂN A"


@patch("app.api.routes.certificate_ocr.certificate_ocr_routes.ocr_service.extract_certificate")
def test_extract_certificate_invalid_json(mock_extract, client):
    mock_extract.return_value = CertificateOcrResponse(
        success=True,
        status_code=200,
        message="Bóc tách chứng chỉ hành nghề thành công.",
        data=CertificateExtractedData(
            detected_type="TAX_AGENT",
            is_valid_type=True,
            certificate_name="Chứng chỉ đại lý thuế",
            full_name="TRẦN VĂN B"
        )
    )

    response = client.post(
        "/api/certificates/ocr/extract",
        files={"file": ("cert.png", io.BytesIO(b"fake_image_bytes" * 20), "image/png")},
        data={"allowed_types_json": "INVALID_JSON"}
    )
    assert response.status_code == 200
    mock_extract.assert_called_once()
    assert mock_extract.call_args.kwargs["allowed_types"] is None
