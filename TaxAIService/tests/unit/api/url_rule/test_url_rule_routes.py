import uuid
from datetime import datetime
from unittest.mock import MagicMock
import pytest
from app.api.routes.url_rule.url_rule_routes import get_url_validation_service
from app.main import app


@pytest.fixture
def mock_url_service():
    service = MagicMock()
    app.dependency_overrides[get_url_validation_service] = lambda: service
    return service


def test_get_rules_default(client, mock_url_service):
    """GET /api/url-rules trả về danh sách quy tắc với active_only=False mặc định"""
    rule_id = uuid.uuid4()
    mock_url_service.get_all_rules.return_value = [
        {
            "id": rule_id,
            "name": "Chính phủ",
            "domain": "chinhphu.vn",
            "description": "Cổng thông tin CP",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }
    ]

    response = client.get("/api/url-rules")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["domain"] == "chinhphu.vn"
    mock_url_service.get_all_rules.assert_called_once_with(active_only=False)


def test_get_rules_active_only(client, mock_url_service):
    """GET /api/url-rules?active_only=true gọi service với active_only=True"""
    mock_url_service.get_all_rules.return_value = []

    response = client.get("/api/url-rules?active_only=true")
    assert response.status_code == 200
    mock_url_service.get_all_rules.assert_called_once_with(active_only=True)


def test_create_rule_success(client, mock_url_service):
    """POST /api/url-rules tạo mới thành công trả về 201 Created"""
    rule_id = uuid.uuid4()
    mock_url_service.create_rule.return_value = {
        "id": rule_id,
        "name": "Tổng cục thuế",
        "domain": "gdt.gov.vn",
        "description": "Trang thuế",
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    payload = {
        "name": "Tổng cục thuế",
        "domain": "gdt.gov.vn",
        "description": "Trang thuế",
        "is_active": True,
    }
    response = client.post("/api/url-rules", json=payload)
    assert response.status_code == 201
    assert response.json()["domain"] == "gdt.gov.vn"
    mock_url_service.create_rule.assert_called_once()


def test_create_rule_validation_error(client, mock_url_service):
    """POST /api/url-rules thiếu trường bắt buộc trả về 422 Unprocessable Entity"""
    response = client.post("/api/url-rules", json={})
    assert response.status_code == 422
    mock_url_service.create_rule.assert_not_called()


def test_get_rule_by_id_found(client, mock_url_service):
    """GET /api/url-rules/{id} tìm thấy quy tắc trả về 200 OK"""
    rule_id = uuid.uuid4()
    mock_url_service.repo.get_by_id.return_value = {
        "id": rule_id,
        "name": "Thư viện pháp luật",
        "domain": "thuvienphapluat.vn",
        "description": "TVPL",
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    response = client.get(f"/api/url-rules/{rule_id}")
    assert response.status_code == 200
    assert response.json()["id"] == str(rule_id)
    mock_url_service.repo.get_by_id.assert_called_once_with(rule_id)


def test_get_rule_by_id_not_found(client, mock_url_service):
    """GET /api/url-rules/{id} không tìm thấy trả về 404 NOT FOUND"""
    rule_id = uuid.uuid4()
    mock_url_service.repo.get_by_id.return_value = None

    response = client.get(f"/api/url-rules/{rule_id}")
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_update_rule_success(client, mock_url_service):
    """PUT /api/url-rules/{id} cập nhật thành công trả về 200 OK"""
    rule_id = uuid.uuid4()
    mock_url_service.update_rule.return_value = {
        "id": rule_id,
        "name": "Cập nhật domain",
        "domain": "mof.gov.vn",
        "description": "Bộ tài chính",
        "is_active": True,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
    }

    payload = {"name": "Cập nhật domain", "domain": "mof.gov.vn"}
    response = client.put(f"/api/url-rules/{rule_id}", json=payload)
    assert response.status_code == 200
    assert response.json()["domain"] == "mof.gov.vn"
    mock_url_service.update_rule.assert_called_once()


def test_update_rule_not_found(client, mock_url_service):
    """PUT /api/url-rules/{id} không tồn tại trả về 404 NOT FOUND"""
    rule_id = uuid.uuid4()
    mock_url_service.update_rule.return_value = None

    payload = {"name": "Test"}
    response = client.put(f"/api/url-rules/{rule_id}", json=payload)
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_delete_rule_success(client, mock_url_service):
    """DELETE /api/url-rules/{id} xóa thành công trả về 200 OK message"""
    rule_id = uuid.uuid4()
    mock_url_service.delete_rule.return_value = True

    response = client.delete(f"/api/url-rules/{rule_id}")
    assert response.status_code == 200
    assert "thành công" in response.json()["message"]
    mock_url_service.delete_rule.assert_called_once_with(rule_id=rule_id)


def test_delete_rule_not_found(client, mock_url_service):
    """DELETE /api/url-rules/{id} không tìm thấy trả về 404 NOT FOUND"""
    rule_id = uuid.uuid4()
    mock_url_service.delete_rule.return_value = False

    response = client.delete(f"/api/url-rules/{rule_id}")
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_get_url_validation_service_factory():
    """Kiểm tra dependency provider get_url_validation_service()"""
    mock_db = MagicMock()
    service = get_url_validation_service(db=mock_db)
    assert service is not None
    assert service.repo.db == mock_db

