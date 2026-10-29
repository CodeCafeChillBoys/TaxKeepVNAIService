import uuid
from datetime import datetime
from unittest.mock import MagicMock
import pytest
from app.api.routes.system_config.system_config_routes import get_config_service
from app.main import app


@pytest.fixture
def mock_config_service():
    service = MagicMock()
    app.dependency_overrides[get_config_service] = lambda: service
    return service


def test_get_all_configs(client, mock_config_service):
    """GET /api/system-configs trả về danh sách cấu hình"""
    config_id = uuid.uuid4()
    mock_config_service.get_all_configs.return_value = [
        {
            "config_key": "AI_CONFIDENCE_THRESHOLD",
            "config_value": "0.85",
            "data_type": "FLOAT",
            "description": "Ngưỡng tin cậy",
            "is_active": True,
            "is_deleted": False,
            "admin_id": None,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
            "deleted_at": None,
        }
    ]

    response = client.get("/api/system-configs")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["config_key"] == "AI_CONFIDENCE_THRESHOLD"
    mock_config_service.get_all_configs.assert_called_once_with(active_only=False)


def test_get_all_configs_active_only(client, mock_config_service):
    """GET /api/system-configs?active_only=true lọc chỉ cấu hình active"""
    mock_config_service.get_all_configs.return_value = []
    response = client.get("/api/system-configs?active_only=true")
    assert response.status_code == 200
    mock_config_service.get_all_configs.assert_called_once_with(active_only=True)


def test_create_config_success(client, mock_config_service):
    """POST /api/system-configs tạo mới cấu hình thành công trả về 201 Created"""
    admin_id = uuid.uuid4()
    mock_config_service.create_config.return_value = {
        "config_key": "MAX_TOKENS",
        "config_value": "4096",
        "data_type": "INTEGER",
        "description": "Token tối đa",
        "is_active": True,
        "is_deleted": False,
        "admin_id": admin_id,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "deleted_at": None,
    }

    payload = {
        "config_key": "MAX_TOKENS",
        "config_value": "4096",
        "description": "Token tối đa",
        "admin_id": str(admin_id),
    }
    response = client.post("/api/system-configs", json=payload)
    assert response.status_code == 201
    assert response.json()["config_key"] == "MAX_TOKENS"
    mock_config_service.create_config.assert_called_once()


def test_create_config_value_error(client, mock_config_service):
    """POST /api/system-configs bị trùng lặp key (ValueError) trả về 400 Bad Request"""
    mock_config_service.create_config.side_effect = ValueError("Cấu hình với key 'EXISTING_KEY' đã tồn tại.")

    payload = {
        "config_key": "EXISTING_KEY",
        "config_value": "123",
    }
    response = client.post("/api/system-configs", json=payload)
    assert response.status_code == 400
    assert "đã tồn tại" in response.json()["detail"]


def test_test_threshold_resolve(client, mock_config_service):
    """GET /api/system-configs/threshold/test-resolve trả về thông tin resolve threshold"""
    mock_config_service.test_resolve_threshold.return_value = {
        "category_code": "MEDICAL",
        "applied_threshold": 0.90,
        "source": "category_specific",
    }

    response = client.get("/api/system-configs/threshold/test-resolve?category_code=MEDICAL")
    assert response.status_code == 200
    data = response.json()
    assert data["applied_threshold"] == 0.90
    mock_config_service.test_resolve_threshold.assert_called_once_with(category_code="MEDICAL")


def test_get_config_by_key_found(client, mock_config_service):
    """GET /api/system-configs/{key} tìm thấy cấu hình trả về 200 OK"""
    mock_config_service.get_config_by_key.return_value = {
        "config_key": "AI_CONFIDENCE_THRESHOLD",
        "config_value": "0.80",
        "data_type": "FLOAT",
        "description": "Ngưỡng",
        "is_active": True,
        "is_deleted": False,
        "admin_id": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "deleted_at": None,
    }

    response = client.get("/api/system-configs/AI_CONFIDENCE_THRESHOLD")
    assert response.status_code == 200
    assert response.json()["config_key"] == "AI_CONFIDENCE_THRESHOLD"
    mock_config_service.get_config_by_key.assert_called_once_with("AI_CONFIDENCE_THRESHOLD")


def test_get_config_by_key_not_found(client, mock_config_service):
    """GET /api/system-configs/{key} không tìm thấy trả về 404 NOT FOUND"""
    mock_config_service.get_config_by_key.return_value = None

    response = client.get("/api/system-configs/NON_EXISTENT")
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_update_config_success(client, mock_config_service):
    """PUT /api/system-configs/{key} cập nhật thành công trả về 200 OK"""
    mock_config_service.update_config.return_value = {
        "config_key": "AI_CONFIDENCE_THRESHOLD",
        "config_value": "0.95",
        "data_type": "FLOAT",
        "description": "Cập nhật mới",
        "is_active": True,
        "is_deleted": False,
        "admin_id": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "deleted_at": None,
    }

    payload = {"config_value": "0.95", "description": "Cập nhật mới"}
    response = client.put("/api/system-configs/AI_CONFIDENCE_THRESHOLD", json=payload)
    assert response.status_code == 200
    assert response.json()["config_value"] == "0.95"
    mock_config_service.update_config.assert_called_once()


def test_update_config_not_found(client, mock_config_service):
    """PUT /api/system-configs/{key} cấu hình không tồn tại trả về 404 NOT FOUND"""
    mock_config_service.update_config.return_value = None

    payload = {"config_value": "0.95"}
    response = client.put("/api/system-configs/NON_EXISTENT", json=payload)
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_update_config_value_error(client, mock_config_service):
    """PUT /api/system-configs/{key} gặp lỗi validate giá trị trả về 400 Bad Request"""
    mock_config_service.update_config.side_effect = ValueError("Ngưỡng threshold phải từ 0.0 đến 1.0.")

    payload = {"config_value": "5.0"}
    response = client.put("/api/system-configs/AI_CONFIDENCE_THRESHOLD", json=payload)
    assert response.status_code == 400
    assert "từ 0.0 đến 1.0" in response.json()["detail"]


def test_delete_config_success(client, mock_config_service):
    """DELETE /api/system-configs/{key} xóa mềm thành công trả về 200 OK"""
    admin_id = uuid.uuid4()
    mock_config_service.delete_config.return_value = True

    response = client.delete(f"/api/system-configs/MY_KEY?admin_id={admin_id}")
    assert response.status_code == 200
    assert "thành công" in response.json()["message"]
    mock_config_service.delete_config.assert_called_once_with(key="MY_KEY", admin_id=admin_id)


def test_delete_config_not_found(client, mock_config_service):
    """DELETE /api/system-configs/{key} không tồn tại trả về 404 NOT FOUND"""
    mock_config_service.delete_config.return_value = False

    response = client.delete("/api/system-configs/NON_EXISTENT")
    assert response.status_code == 404
    assert "Không tìm thấy" in response.json()["detail"]


def test_restore_config_success(client, mock_config_service):
    """PATCH /api/system-configs/{key}/restore khôi phục thành công trả về 200 OK"""
    mock_config_service.restore_config.return_value = {
        "config_key": "MY_KEY",
        "config_value": "123",
        "data_type": "STRING",
        "description": "Đã khôi phục",
        "is_active": True,
        "is_deleted": False,
        "admin_id": None,
        "created_at": datetime.now(),
        "updated_at": datetime.now(),
        "deleted_at": None,
    }

    response = client.patch("/api/system-configs/MY_KEY/restore")
    assert response.status_code == 200
    assert response.json()["config_key"] == "MY_KEY"
    mock_config_service.restore_config.assert_called_once()



def test_restore_config_not_found(client, mock_config_service):
    """PATCH /api/system-configs/{key}/restore cấu hình không tồn tại trả về 404 NOT FOUND"""
    mock_config_service.restore_config.return_value = None

    response = client.patch("/api/system-configs/NON_EXISTENT/restore")
    assert response.status_code == 404
    assert "không tồn tại" in response.json()["detail"]


def test_restore_config_value_error(client, mock_config_service):
    """PATCH /api/system-configs/{key}/restore chưa bị xóa trả về 400 Bad Request"""
    mock_config_service.restore_config.side_effect = ValueError("Cấu hình đang hoạt động bình thường, không cần khôi phục.")

    response = client.patch("/api/system-configs/ACTIVE_KEY/restore")
    assert response.status_code == 400
    assert "không cần khôi phục" in response.json()["detail"]


def test_get_config_service_factory():
    """Kiểm tra dependency provider get_config_service()"""
    mock_db = MagicMock()
    service = get_config_service(db=mock_db)
    assert service is not None
    assert service.repo.db == mock_db

