import pytest
import time
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient

from backend.app.auth.password import hash_password, verify_password
from backend.app.auth.jwt import create_access_token, create_refresh_token, decode_token
from backend.app.auth.rate_limiter import LoginRateLimiter
from backend.app.auth.roles import UserRole, ROLE_PERMISSIONS, has_permission
from backend.app.services.auth_service import auth_service
from backend.app.models.user import UserDocument


def test_password_hashing_and_verification():
    raw_pw = "SuperSecurePassword123!"
    hashed = hash_password(raw_pw)
    assert hashed != raw_pw
    assert hashed.startswith("$2b$") or hashed.startswith("$2a$")
    assert verify_password(raw_pw, hashed) is True
    assert verify_password("WrongPassword123!", hashed) is False
    assert verify_password("", hashed) is False


def test_jwt_access_and_refresh_tokens():
    user_id = "usr-test-12345"
    claims = {"username": "sec_analyst", "role": "analyst"}

    # Access Token
    access_tok = create_access_token(user_id, claims, expires_delta=timedelta(minutes=15))
    decoded_access = decode_token(access_tok, expected_type="access")
    assert decoded_access["sub"] == user_id
    assert decoded_access["type"] == "access"
    assert decoded_access["username"] == "sec_analyst"
    assert decoded_access["role"] == "analyst"

    # Refresh Token
    refresh_tok = create_refresh_token(user_id, claims, expires_delta=timedelta(days=7))
    decoded_refresh = decode_token(refresh_tok, expected_type="refresh")
    assert decoded_refresh["sub"] == user_id
    assert decoded_refresh["type"] == "refresh"

    # Type mismatch rejection
    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(access_tok, expected_type="refresh")

    with pytest.raises(ValueError, match="Invalid token type"):
        decode_token(refresh_tok, expected_type="access")


def test_jwt_expired_token():
    user_id = "usr-expired-01"
    expired_tok = create_access_token(user_id, expires_delta=timedelta(seconds=-10))
    import jwt
    with pytest.raises(jwt.ExpiredSignatureError):
        decode_token(expired_tok, expected_type="access")


def test_role_hierarchy():
    assert has_permission(UserRole.ADMIN, "users:manage") is True
    assert has_permission(UserRole.ADMIN, "alerts:triage") is True
    assert has_permission(UserRole.ADMIN, "dashboard:read") is True

    assert has_permission(UserRole.ANALYST, "users:manage") is False
    assert has_permission(UserRole.ANALYST, "alerts:triage") is True
    assert has_permission(UserRole.ANALYST, "dashboard:read") is True

    assert has_permission(UserRole.VIEWER, "users:manage") is False
    assert has_permission(UserRole.VIEWER, "alerts:triage") is False
    assert has_permission(UserRole.VIEWER, "dashboard:read") is True


def test_login_rate_limiter():
    limiter = LoginRateLimiter(max_attempts=3, window_seconds=2)
    key = "192.168.1.100:test_user"

    # Initial state
    blocked, remaining = limiter.is_rate_limited(key)
    assert blocked is False
    assert remaining == 0

    # 1st attempt
    limiter.record_failure(key)
    blocked, _ = limiter.is_rate_limited(key)
    assert blocked is False

    # 2nd attempt
    limiter.record_failure(key)
    blocked, _ = limiter.is_rate_limited(key)
    assert blocked is False

    # 3rd attempt -> reaches threshold
    limiter.record_failure(key)
    blocked, remaining = limiter.is_rate_limited(key)
    assert blocked is True
    assert remaining > 0

    # Reset on successful login
    limiter.record_success(key)
    blocked, _ = limiter.is_rate_limited(key)
    assert blocked is False


@pytest.mark.asyncio
async def test_auth_service_authenticate_success():
    hashed = hash_password("ValidPassword123!")
    user_data = {
        "_id": "usr-auth-001",
        "user_id": "usr-auth-001",
        "username": "valid_user",
        "email": "valid@test.ai",
        "hashed_password": hashed,
        "full_name": "Valid User",
        "role": "analyst",
        "is_active": True,
    }

    with patch("backend.app.services.auth_service.UserRepository.get_user_by_identifier", new_callable=AsyncMock) as mock_get, \
         patch("backend.app.services.auth_service.UserRepository.update_last_login", new_callable=AsyncMock) as mock_last_login, \
         patch("backend.app.services.auth_service.audit_service.log_event", new_callable=AsyncMock) as mock_audit:
        
        mock_get.return_value = user_data
        
        res = await auth_service.authenticate_user(
            identifier="valid_user",
            password="ValidPassword123!",
            client_ip="127.0.0.1",
        )

        assert res.access_token is not None
        assert res.refresh_token is not None
        assert res.token_type == "bearer"
        assert res.user.username == "valid_user"
        assert res.user.role == "analyst"
        mock_last_login.assert_called_once()
        mock_audit.assert_called_once()


@pytest.mark.asyncio
async def test_auth_service_authenticate_invalid_password():
    from fastapi import HTTPException
    hashed = hash_password("CorrectPassword123!")
    user_data = {
        "_id": "usr-auth-002",
        "user_id": "usr-auth-002",
        "username": "auth_user_2",
        "email": "user2@test.ai",
        "hashed_password": hashed,
        "role": "analyst",
        "is_active": True,
    }

    with patch("backend.app.services.auth_service.UserRepository.get_user_by_identifier", new_callable=AsyncMock) as mock_get, \
         patch("backend.app.services.auth_service.audit_service.log_event", new_callable=AsyncMock):
        
        mock_get.return_value = user_data

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user(
                identifier="auth_user_2",
                password="WrongPassword123!",
                client_ip="127.0.0.1",
            )
        assert exc_info.value.status_code == 401
        assert "Invalid username or password" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_service_authenticate_deactivated_user():
    from fastapi import HTTPException
    hashed = hash_password("ValidPassword123!")
    user_data = {
        "_id": "usr-auth-003",
        "user_id": "usr-auth-003",
        "username": "deactivated_user",
        "email": "deactivated@test.ai",
        "hashed_password": hashed,
        "role": "analyst",
        "is_active": False,
    }

    with patch("backend.app.services.auth_service.UserRepository.get_user_by_identifier", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = user_data

        with pytest.raises(HTTPException) as exc_info:
            await auth_service.authenticate_user(
                identifier="deactivated_user",
                password="ValidPassword123!",
                client_ip="127.0.0.1",
            )
        assert exc_info.value.status_code == 401
        assert "deactivated" in exc_info.value.detail


@pytest.mark.asyncio
async def test_auth_service_refresh_token_flow():
    user_data = {
        "_id": "usr-auth-004",
        "user_id": "usr-auth-004",
        "username": "refresh_user",
        "email": "refresh@test.ai",
        "role": "admin",
        "is_active": True,
    }

    refresh_tok = create_refresh_token(user_data["user_id"], {"username": user_data["username"], "role": user_data["role"]})

    with patch("backend.app.services.auth_service.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_get:
        mock_get.return_value = user_data

        res = await auth_service.refresh_access_token(
            refresh_token=refresh_tok,
            client_ip="127.0.0.1",
        )

        assert res.access_token is not None
        assert res.token_type == "bearer"
        assert res.user.username == "refresh_user"
        assert res.user.role == "admin"


def test_api_login_and_me_flow(client: TestClient):
    """Test full HTTP login and /me endpoint flow."""
    hashed = hash_password("ValidPass12345!")
    mock_db_user = {
        "_id": "usr-e2e-001",
        "user_id": "usr-e2e-001",
        "username": "test_e2e_analyst",
        "email": "e2e@zeroday.ai",
        "hashed_password": hashed,
        "full_name": "E2E Analyst",
        "role": "analyst",
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
    }

    with patch("backend.app.services.auth_service.UserRepository.get_user_by_identifier", new_callable=AsyncMock) as mock_ident, \
         patch("backend.app.services.auth_service.UserRepository.update_last_login", new_callable=AsyncMock), \
         patch("backend.app.services.auth_service.audit_service.log_event", new_callable=AsyncMock), \
         patch("backend.app.auth.dependencies.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_by_id:

        mock_ident.return_value = mock_db_user
        mock_by_id.return_value = mock_db_user

        # 1. Login
        login_res = client.post(
            "/api/v1/auth/login",
            json={"username": "test_e2e_analyst", "password": "ValidPass12345!"},
        )
        assert login_res.status_code == 200
        data = login_res.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["username"] == "test_e2e_analyst"
        assert data["user"]["role"] == "analyst"

        access_token = data["access_token"]
        refresh_token = data["refresh_token"]

        # 2. Get /me with valid Bearer token
        me_res = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert me_res.status_code == 200
        me_data = me_res.json()
        assert me_data["username"] == "test_e2e_analyst"
        assert me_data["email"] == "e2e@zeroday.ai"

        # 3. Refresh token
        refresh_res = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert refresh_res.status_code == 200
        refreshed_data = refresh_res.json()
        assert "access_token" in refreshed_data

        # 4. Logout
        logout_res = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_res.status_code == 200


def test_api_unauthenticated_me_rejected(client: TestClient):
    """Test GET /api/v1/auth/me without token returns 401."""
    res = client.get("/api/v1/auth/me")
    assert res.status_code == 401
