import io
from unittest.mock import MagicMock, patch
import pytest
from app.infrastructure.database import get_db
from app.main import app
from app.schemas.income_ocr.income_ocr_schema import (
    IncomeOcrResponse,
    IncomeExtractedData,
    IncomeThresholdValidationResult,
)


@pytest.fixture
def mock_db():
    db = MagicMock()
    app.dependency_overrides[get_db] = lambda: db
    return db


def test_extract_income_unsupported_mime_type(client):
    """Gửi file với mime type không hỗ trợ (vd: text/csv) trả về 400 Bad Request"""
    response = client.post(
        "/api/incomes/ocr/extract",
        files={"file": ("salary.csv", io.BytesIO(b"a,b,c"), "text/csv")}
    )
    assert response.status_code == 400
    assert "không được hỗ trợ" in response.json()["detail"]


@patch("app.api.routes.income_ocr.income_ocr_routes.IncomeOcrService")
def test_extract_income_success(mock_service_cls, client, mock_db):
    """Gửi file bảng lương hợp lệ trả về 200 OK cùng dữ liệu bóc tách"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_payslip.return_value = IncomeOcrResponse(
        success=True,
        statusCode=200,
        message="Bóc tách báo cáo lương thành công.",
        data=IncomeExtractedData(
            organizationName="Công ty Cổ phần TaxKeep",
            taxIdNumber="0101234567",
            month=10,
            year=2025,
            totalTaxableIncome=25000000.0,
            insuranceDeducted=2625000.0,
            taxAlreadyDeducted=1500000.0,
            thresholdValidation=IncomeThresholdValidationResult(
                appliedThreshold=0.80,
                overallConfidence=0.95,
                isPassedThreshold=True,
                lowConfidenceFields=[],
            )
        )
    )

    pdf_bytes = b"%PDF-1.4 test payslip"
    response = client.post(
        "/api/incomes/ocr/extract",
        files={"file": ("payslip.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        data={"target_month": "10", "target_year": "2025", "applied_threshold": "0.85"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["organizationName"] == "Công ty Cổ phần TaxKeep"
    assert data["data"]["totalTaxableIncome"] == 25000000.0

    mock_instance.extract_payslip.assert_called_once_with(
        file_bytes=pdf_bytes,
        mime_type="application/pdf",
        target_month=10,
        target_year=2025,
        applied_threshold=0.85,
    )


@patch("app.api.routes.income_ocr.income_ocr_routes.IncomeOcrService")
def test_extract_income_without_optional_params(mock_service_cls, client, mock_db):
    """Gửi file không kèm target_month/target_year/applied_threshold"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_payslip.return_value = IncomeOcrResponse(
        success=False,
        statusCode=422,
        message="Tài liệu không phải bảng lương.",
        data=None,
        errors=[{"error": "NOT_AN_INCOME_DOC"}]
    )

    png_bytes = b"\x89PNG\r\n\x1a\n"
    response = client.post(
        "/api/incomes/ocr/extract",
        files={"file": ("random.png", io.BytesIO(png_bytes), "image/png")}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is False
    assert data["statusCode"] == 422
    mock_instance.extract_payslip.assert_called_once_with(
        file_bytes=png_bytes,
        mime_type="image/png",
        target_month=None,
        target_year=None,
        applied_threshold=None,
    )
