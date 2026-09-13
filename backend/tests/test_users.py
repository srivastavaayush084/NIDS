import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.database.repository import UserRepository
from backend.app.schemas.user import UserCreate, UserUpdate
from backend.app.auth.roles import UserRole
from backend.app.main import app
from backend.app.models.user import UserDocument


@pytest.mark.asyncio
async def test_user_repository_create_and_get():
    repo = UserRepository()
    fake_user_doc = {
        "_id": "usr-test-100",
        "user_id": "usr-test-100",
        "username": "new_soc_analyst",
        "email": "analyst100@zeroday.ai",
        "hashed_password": "hashed_secret_pw",
        "full_name": "New SOC Analyst",
        "role": "analyst",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    with patch.object(repo, "insert_one", new_callable=AsyncMock) as mock_ins, \
         patch.object(repo, "get_user_by_id", new_callable=AsyncMock) as mock_id:

        mock_ins.return_value = "usr-test-100"
        mock_id.return_value = fake_user_doc

        created_id = await repo.create_user(fake_user_doc)
        assert created_id == "usr-test-100"

        fetched = await repo.get_user_by_id("usr-test-100")
        assert fetched["username"] == "new_soc_analyst"
        assert fetched["role"] == "analyst"


@pytest.mark.asyncio
async def test_user_repository_deactivate():
    repo = UserRepository()
    with patch.object(repo, "update_user", new_callable=AsyncMock) as mock_update:
        mock_update.return_value = True
        result = await repo.deactivate_user("usr-test-100")
        assert result is True
        mock_update.assert_called_once_with("usr-test-100", {"is_active": False})


def test_users_api_admin_access_allowed(client: TestClient, admin_headers, mock_admin_user):
    """Admin can list users successfully."""
    user_list = [
        {
            "_id": "usr-1",
            "user_id": "usr-1",
            "username": "admin",
            "email": "admin@test.ai",
            "role": "admin",
            "is_active": True,
            "created_at": datetime.now(timezone.utc),
        }
    ]

    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_auth_user, \
         patch("backend.app.database.repository.UserRepository.list_users", new_callable=AsyncMock) as mock_list, \
         patch("backend.app.database.repository.UserRepository.count", new_callable=AsyncMock) as mock_count:
        
        mock_auth_user.return_value = mock_admin_user.model_dump()
        mock_list.return_value = user_list
        mock_count.return_value = 1

        res = client.get("/api/v1/users", headers=admin_headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total"] == 1
        assert data["users"][0]["username"] == "admin"


def test_users_api_analyst_access_denied(client: TestClient, analyst_headers, mock_analyst_user):
    """Analyst is forbidden (403) from accessing user management endpoints."""
    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_auth_user, \
         patch("backend.app.services.audit_service.audit_service.log_event", new_callable=AsyncMock):
        
        mock_auth_user.return_value = mock_analyst_user.model_dump()

        res = client.get("/api/v1/users", headers=analyst_headers)
        assert res.status_code == 403


def test_users_api_viewer_access_denied(client: TestClient, viewer_headers, mock_viewer_user):
    """Viewer is forbidden (403) from accessing user management endpoints."""
    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_auth_user, \
         patch("backend.app.services.audit_service.audit_service.log_event", new_callable=AsyncMock):
        
        mock_auth_user.return_value = mock_viewer_user.model_dump()

        res = client.get("/api/v1/users", headers=viewer_headers)
        assert res.status_code == 403


def test_users_api_create_user(client: TestClient, admin_headers, mock_admin_user):
    """Admin can provision a new user account."""
    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_auth_user, \
         patch("backend.app.database.repository.UserRepository.get_user_by_username", new_callable=AsyncMock) as mock_un, \
         patch("backend.app.database.repository.UserRepository.get_user_by_email", new_callable=AsyncMock) as mock_em, \
         patch("backend.app.database.repository.UserRepository.create_user", new_callable=AsyncMock) as mock_create, \
         patch("backend.app.services.audit_service.audit_service.log_event", new_callable=AsyncMock):

        mock_auth_user.return_value = mock_admin_user.model_dump()
        mock_un.return_value = None
        mock_em.return_value = None
        mock_create.return_value = "usr-created-001"

        res = client.post(
            "/api/v1/users",
            json={
                "username": "created_analyst",
                "email": "created@zeroday.ai",
                "password": "Password123!",
                "role": "analyst",
                "full_name": "Created Analyst",
            },
            headers=admin_headers,
        )

        assert res.status_code == 201
        data = res.json()
        assert data["username"] == "created_analyst"
        assert data["role"] == "analyst"


def test_users_api_deactivate_last_admin_rejected(client: TestClient, admin_headers, mock_admin_user):
    """Admin cannot deactivate the last active administrator account."""
    existing_admin = {
        "_id": "usr-test-admin-01",
        "user_id": "usr-test-admin-01",
        "username": "admin_test",
        "email": "admin@test.ai",
        "hashed_password": "$2b$12$mockhashedpasswordadmin123456789012345678901234567890",
        "role": "admin",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_get_user, \
         patch("backend.app.database.repository.UserRepository.count_active_admins", new_callable=AsyncMock) as mock_count:

        mock_get_user.return_value = existing_admin
        mock_count.return_value = 1

        res = client.delete(
            f"/api/v1/users/{mock_admin_user.user_id}",
            headers=admin_headers,
        )

        assert res.status_code == 400
        err_msg = str(res.json())
        assert "Cannot deactivate the last remaining active administrator" in err_msg
