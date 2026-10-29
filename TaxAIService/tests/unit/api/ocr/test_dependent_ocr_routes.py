import io
import json
from unittest.mock import MagicMock, patch
import pytest
from app.infrastructure.database import get_db
from app.main import app
from app.schemas.ocr.ocr_document_schema import OcrExtractionResponse, ExtractedDependentData, RequiredDocument


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    app.dependency_overrides[get_db] = lambda: db
    return db


def test_extract_unsupported_mime_type(client):
    """Gửi file với mime type không hỗ trợ (vd: text/plain) trả về 400 Bad Request"""
    response = client.post(
        "/api/ocr/extract",
        files={"file": ("test.txt", io.BytesIO(b"hello world"), "text/plain")}
    )
    assert response.status_code == 400
    assert "không được hỗ trợ" in response.json()["detail"]


@patch("app.api.routes.ocr.dependent_ocr_routes.DependentOcrService")
def test_extract_single_file_success(mock_service_cls, client, mock_db):
    """Gửi 1 file ảnh hợp lệ bóc tách thành công trả về 200 OK"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_document.return_value = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="Trích xuất thành công",
        data=ExtractedDependentData(
            fullName="NGUYỄN VĂN A",
            citizenId="012345678901",
            required_documents=[]
        )
    )

    image_content = b"\xff\xd8\xff\xe0"  # fake JPEG header
    response = client.post(
        "/api/ocr/extract",
        files={"file": ("cccd.jpg", io.BytesIO(image_content), "image/jpeg")},
        data={"target_group": "CHILD", "applied_threshold": "0.85"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["data"]["fullName"] == "NGUYỄN VĂN A"
    mock_instance.extract_document.assert_called_once()


@patch("app.api.routes.ocr.dependent_ocr_routes.DependentOcrService")
def test_extract_with_back_file(mock_service_cls, client, mock_db):
    """Gửi cả mặt trước và mặt sau CCCD"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_document.return_value = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="OK",
        data=ExtractedDependentData(fullName="TRẦN THỊ B", required_documents=[])
    )

    front = b"\xff\xd8\xff\xe0 front"
    back = b"\xff\xd8\xff\xe0 back"
    response = client.post(
        "/api/ocr/extract",
        files={
            "file": ("front.jpg", io.BytesIO(front), "image/jpeg"),
            "back_file": ("back.jpg", io.BytesIO(back), "image/jpeg"),
        }
    )
    assert response.status_code == 200
    args, kwargs = mock_instance.extract_document.call_args
    files_arg = kwargs["files"]
    assert len(files_arg) == 2
    assert files_arg[0][0] == front
    assert files_arg[1][0] == back


@patch("app.api.routes.ocr.dependent_ocr_routes.DependentOcrService")
def test_extract_with_rules_json_list(mock_service_cls, client, mock_db):
    """Gửi rules_json dạng danh sách JSON"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_document.return_value = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="OK",
        data=ExtractedDependentData(
            fullName="LÊ VĂN C",
            required_documents=[RequiredDocument(doc_type="CITIZEN_ID", is_mandatory=True)]
        )
    )

    rules_list = [{"docType": "CITIZEN_ID", "isMandatory": True}]
    response = client.post(
        "/api/ocr/extract",
        files={"file": ("cccd.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
        data={"rules_json": json.dumps(rules_list)}
    )
    assert response.status_code == 200
    args, kwargs = mock_instance.extract_document.call_args
    assert kwargs["rules"] == rules_list


@patch("app.api.routes.ocr.dependent_ocr_routes.DependentOcrService")
def test_extract_with_rules_json_dict(mock_service_cls, client, mock_db):
    """Gửi rules_json dạng object có key 'rules'"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_document.return_value = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="OK",
        data=ExtractedDependentData(
            required_documents=[RequiredDocument(doc_type="BIRTH_CERTIFICATE")]
        )
    )

    rules_dict = {"rules": [{"docType": "BIRTH_CERTIFICATE"}]}
    response = client.post(
        "/api/ocr/extract",
        files={"file": ("cccd.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
        data={"rules_json": json.dumps(rules_dict)}
    )
    assert response.status_code == 200
    args, kwargs = mock_instance.extract_document.call_args
    assert kwargs["rules"] == [{"docType": "BIRTH_CERTIFICATE"}]


@patch("app.api.routes.ocr.dependent_ocr_routes.DependentOcrService")
def test_extract_with_invalid_rules_json(mock_service_cls, client, mock_db):
    """Gửi rules_json bị sai định dạng JSON -> không crash, fallback bình thường"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_document.return_value = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="OK",
        data=ExtractedDependentData(required_documents=[])
    )

    response = client.post(
        "/api/ocr/extract",
        files={"file": ("cccd.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
        data={"rules_json": "INVALID_NOT_JSON"}
    )
    assert response.status_code == 200
    args, kwargs = mock_instance.extract_document.call_args
    assert kwargs["rules"] is None


@patch("app.api.routes.ocr.dependent_ocr_routes.DependentOcrService")
def test_extract_negative_threshold_resets_to_none(mock_service_cls, client, mock_db):
    """Gửi applied_threshold <= 0 được reset về None"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_document.return_value = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="OK",
        data=ExtractedDependentData(required_documents=[])
    )

    response = client.post(
        "/api/ocr/extract",
        files={"file": ("cccd.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
        data={"applied_threshold": "-0.5"}
    )
    assert response.status_code == 200
    args, kwargs = mock_instance.extract_document.call_args
    assert kwargs["applied_threshold"] is None


@patch("app.api.routes.ocr.dependent_ocr_routes.DependentOcrService")
def test_extract_fallback_db_rules_by_target_group(mock_service_cls, client, mock_db):
    """Không có rules_json nhưng có target_group -> truy vấn DB tìm required_documents"""
    mock_instance = MagicMock()
    mock_service_cls.return_value = mock_instance
    mock_instance.extract_document.return_value = OcrExtractionResponse(
        success=True,
        statusCode=200,
        message="OK",
        data=ExtractedDependentData(
            required_documents=[RequiredDocument(doc_type="BIRTH_CERTIFICATE", is_mandatory=True)]
        )
    )

    dummy_dep_rule = MagicMock()
    dummy_dep_rule.required_documents = [RequiredDocument(doc_type="BIRTH_CERTIFICATE", is_mandatory=True)]
    mock_db.query.return_value.filter.return_value.first.return_value = dummy_dep_rule

    response = client.post(
        "/api/ocr/extract",
        files={"file": ("cccd.png", io.BytesIO(b"\x89PNG\r\n\x1a\n"), "image/png")},
        data={"target_group": "CHILD"}
    )
    assert response.status_code == 200
    args, kwargs = mock_instance.extract_document.call_args
    assert len(kwargs["rules"]) == 1

