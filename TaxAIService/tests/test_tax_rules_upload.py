import io
import fitz
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_upload_missing_file():
    response = client.post("/api/tax-rules/documents/upload")
    assert response.status_code == 400
    assert response.json() == {"message": "The file field is required."}


def test_upload_invalid_file_extension():
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("test.txt", b"dummy content", "text/plain")}
    )
    assert response.status_code == 400
    assert response.json() == {"message": "The file must be a PDF."}


def test_upload_missing_tax_year():
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 dummy", "application/pdf")}
    )
    assert response.status_code == 400
    assert response.json() == {"TaxYear": "The TaxYear field is required."}


def test_upload_invalid_tax_year():
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 dummy", "application/pdf")},
        data={"taxYear": "invalid_year"}
    )
    assert response.status_code == 400
    assert response.json() == {"message": "Tax year must be a valid year."}


def test_upload_invalid_source_url():
    response = client.post(
        "/api/tax-rules/documents/upload",
        files={"file": ("test.pdf", b"%PDF-1.4 dummy", "application/pdf")},
        data={"taxYear": "2030", "sourceUrl": "invalid_url_without_http"}
    )
    assert response.status_code == 400
    assert response.json() == {"SourceUrl": "URL không đúng định dạng (phải bắt đầu bằng http:// hoặc https://)."}
