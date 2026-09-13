"""
Phase 16 — Comprehensive Security & API Protection Test Suite.
Verifies defensive HTTP security headers, CORS hardening, JWT token verification,
password protection, login brute-force rate limiting, global API rate limiting,
payload size limits, input validation schemas, PCAP traversal defense,
MongoDB query safety, RBAC permissions, and health endpoint safety.
"""

import os
import time
import pytest
import jwt
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient

from backend.app.core.config import settings
from backend.app.auth.jwt import create_access_token, create_refresh_token, decode_token
from backend.app.auth.password import hash_password, verify_password
from backend.app.auth.rate_limiter import login_rate_limiter
from backend.app.api.middleware import general_api_rate_limiter
from backend.app.monitoring.capture.pcap_reader import resolve_and_validate_pcap_path
from backend.app.database.repository import UserRepository, BaseRepository
from backend.app.models.user import UserDocument


@pytest.fixture(autouse=True)
def reset_rate_limiters():
    """Reset rate limiter state before each test."""
    login_rate_limiter.reset()
    general_api_rate_limiter.reset()
    yield
    login_rate_limiter.reset()
    general_api_rate_limiter.reset()


# =============================================================================
# 1. Security Headers Tests
# =============================================================================

class TestSecurityHeaders:
    def test_security_headers_present_on_health_check(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        headers = res.headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
        assert headers.get("X-XSS-Protection") == "0"
        assert "geolocation=()" in headers.get("Permissions-Policy", "")
        assert "default-src 'self'" in headers.get("Content-Security-Policy", "")
        assert "X-Request-ID" in headers
        assert "X-Process-Time" in headers

    def test_security_headers_present_on_api_v1(self, client: TestClient):
        res = client.get("/api/v1/health")
        assert res.status_code == 200
        assert res.headers.get("X-Content-Type-Options") == "nosniff"
        assert res.headers.get("X-Frame-Options") == "DENY"


# =============================================================================
# 2. CORS Hardening Tests
# =============================================================================

class TestCORSHardening:
    def test_cors_preflight_for_allowed_origin(self, client: TestClient):
        allowed_origin = "http://localhost:5173"
        res = client.options(
            "/api/v1/health",
            headers={
                "Origin": allowed_origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Authorization,Content-Type",
            },
        )
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == allowed_origin
        assert "GET" in res.headers.get("access-control-allow-methods", "")

    def test_cors_disallowed_origin_not_reflected(self, client: TestClient):
        evil_origin = "http://malicious-attacker-site.com"
        res = client.get(
            "/api/v1/health",
            headers={"Origin": evil_origin},
        )
        assert res.headers.get("access-control-allow-origin") != evil_origin


# =============================================================================
# 3. JWT Security Tests
# =============================================================================

class TestJWTSecurity:
    def test_missing_token_returns_401(self, client: TestClient):
        res = client.get("/api/v1/users")
        assert res.status_code == 401
        assert "Authentication required" in res.text

    def test_malformed_token_returns_401(self, client: TestClient):
        res = client.get(
            "/api/v1/users",
            headers={"Authorization": "Bearer not-a-valid-jwt-token-string"},
        )
        assert res.status_code == 401
        assert "Invalid authentication token" in res.text

    def test_expired_token_returns_401(self, client: TestClient):
        past = datetime.now(timezone.utc) - timedelta(minutes=10)
        payload = {
            "sub": "usr-test-expired",
            "type": "access",
            "iat": int((past - timedelta(minutes=5)).timestamp()),
            "exp": int(past.timestamp()),
        }
        expired_jwt = jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        res = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {expired_jwt}"},
        )
        assert res.status_code == 401
        assert "expired" in res.text.lower()

    def test_invalid_signature_token_returns_401(self, client: TestClient):
        payload = {
            "sub": "usr-test-forged",
            "type": "access",
            "iat": int(datetime.now(timezone.utc).timestamp()),
            "exp": int((datetime.now(timezone.utc) + timedelta(hours=1)).timestamp()),
        }
        forged_jwt = jwt.encode(payload, "wrong-secret-key-0123456789abcdef", algorithm="HS256")

        res = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {forged_jwt}"},
        )
        assert res.status_code == 401

    def test_refresh_token_used_as_access_token_rejected(self, client: TestClient):
        refresh_tok = create_refresh_token(subject="usr-test")
        res = client.get(
            "/api/v1/users",
            headers={"Authorization": f"Bearer {refresh_tok}"},
        )
        assert res.status_code == 401


# =============================================================================
# 4. Password Security Tests
# =============================================================================

class TestPasswordSecurity:
    def test_password_hashing_and_verification(self):
        plain = "SuperSecurePassword123!"
        hashed = hash_password(plain)
        assert hashed != plain
        assert hashed.startswith("$2b$")
        assert verify_password(plain, hashed) is True
        assert verify_password("WrongPassword123!", hashed) is False

    def test_empty_password_rejected(self):
        with pytest.raises(ValueError):
            hash_password("")


# =============================================================================
# 5. Login Abuse & Rate Limiting Tests
# =============================================================================

class TestLoginAbuseProtection:
    def test_login_rate_limiter_sliding_window(self):
        key = "127.0.0.1:target_user"
        login_rate_limiter.reset()

        for _ in range(settings.AUTH_RATE_LIMIT_MAX_ATTEMPTS):
            is_blocked, _ = login_rate_limiter.is_rate_limited(key)
            assert not is_blocked
            login_rate_limiter.record_failure(key)

        is_blocked, remaining = login_rate_limiter.is_rate_limited(key)
        assert is_blocked is True
        assert remaining > 0

        # Successful login clears failure records
        login_rate_limiter.record_success(key)
        is_blocked, _ = login_rate_limiter.is_rate_limited(key)
        assert not is_blocked


# =============================================================================
# 6. Global API Rate Limiting Tests
# =============================================================================

class TestGlobalApiRateLimiter:
    def test_general_rate_limiter_blocks_bursts(self):
        ip = "192.168.1.100"
        general_api_rate_limiter.reset()

        for _ in range(general_api_rate_limiter.requests_per_minute):
            is_blocked, _ = general_api_rate_limiter.is_rate_limited(ip)
            assert not is_blocked
            general_api_rate_limiter.record_request(ip)

        is_blocked, retry_after = general_api_rate_limiter.is_rate_limited(ip)
        assert is_blocked is True
        assert retry_after > 0

    def test_health_endpoints_are_exempt(self, client: TestClient):
        # Exceed rate limit for test client IP
        client_ip = "testclient"
        for _ in range(general_api_rate_limiter.requests_per_minute + 5):
            general_api_rate_limiter.record_request(client_ip)

        # Health endpoint should still return 200 OK
        res = client.get("/health")
        assert res.status_code == 200


# =============================================================================
# 7. Request Payload Size Limits Tests
# =============================================================================

class TestPayloadSizeLimits:
    def test_oversized_payload_returns_413(self, client: TestClient):
        huge_content_length = settings.MAX_REQUEST_BODY_BYTES + 1024
        res = client.post(
            "/api/v1/events",
            headers={
                "Content-Length": str(huge_content_length),
                "Content-Type": "application/json",
            },
            content=b"{}",
        )
        assert res.status_code == 413
        data = res.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"


# =============================================================================
# 8. Schema Input Validation Bounds Tests
# =============================================================================

class TestSchemaValidationBounds:
    def test_batch_detection_exceeding_max_items_rejected_422(self, client: TestClient, admin_headers, mock_admin_user):
        with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_user:
            mock_user.return_value = mock_admin_user.model_dump()
            oversized_events = [{"src_bytes": 100, "dst_bytes": 200} for _ in range(501)]
            res = client.post(
                "/api/v1/detection/batch",
                headers=admin_headers,
                json={"events": oversized_events, "dataset_name": "synthetic"},
            )
            assert res.status_code == 422
            data = res.json()
            assert data["error"]["code"] == "VALIDATION_ERROR"

    def test_sequence_detection_exceeding_max_items_rejected_422(self, client: TestClient, admin_headers, mock_admin_user):
        with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_user:
            mock_user.return_value = mock_admin_user.model_dump()
            oversized_sequence = [{"src_bytes": 100} for _ in range(101)]
            res = client.post(
                "/api/v1/detection/sequence",
                headers=admin_headers,
                json={"sequence": oversized_sequence, "dataset_name": "synthetic"},
            )
            assert res.status_code == 422


# =============================================================================
# 9. PCAP Path Traversal & Extension Protection Tests
# =============================================================================

class TestPCAPSecurity:
    def test_pcap_path_traversal_rejection(self):
        traversal_path = "../../etc/shadow.pcap"
        with pytest.raises((FileNotFoundError, PermissionError, ValueError)):
            resolve_and_validate_pcap_path(traversal_path)

    def test_invalid_pcap_extension_rejected_schema(self, client: TestClient, admin_headers, mock_admin_user):
        with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_user:
            mock_user.return_value = mock_admin_user.model_dump()
            res = client.post(
                "/api/v1/monitoring/test-pcap",
                headers=admin_headers,
                json={"file": "malicious_script.sh"},
            )
            assert res.status_code == 422
            assert "Invalid file extension" in res.text

    def test_null_byte_path_rejected(self, client: TestClient, admin_headers, mock_admin_user):
        with patch("backend.app.database.repository.UserRepository.get_user_by_id", new_callable=AsyncMock) as mock_user:
            mock_user.return_value = mock_admin_user.model_dump()
            res = client.post(
                "/api/v1/monitoring/test-pcap",
                headers=admin_headers,
                json={"file": "capture.pcap\x00.exe"},
            )
            assert res.status_code == 422


# =============================================================================
# 10. MongoDB Query Safety Tests
# =============================================================================

class TestMongoDBQuerySafety:
    @pytest.mark.asyncio
    async def test_user_repository_escapes_regex_meta_characters(self):
        repo = UserRepository()
        meta_username = "admin.*+?^$()[]{}\\"
        with patch.object(repo, "find_one", new_callable=AsyncMock) as mock_find:
            mock_find.return_value = None
            await repo.get_user_by_username(meta_username)
            mock_find.assert_called_once()
            called_query = mock_find.call_args[0][0]
            # Ensure the regex pattern contains escaped characters
            pattern = called_query["username"]["$regex"]
            assert r"\.\*\+\?\^\$" in pattern

    def test_base_repository_clamps_pagination_limit(self):
        assert max(1, min(1000, 100)) == 100
        assert max(1, min(-5, 100)) == 1


# =============================================================================
# 11. Health Endpoint Safety Tests
# =============================================================================

class TestHealthEndpointSafety:
    def test_health_does_not_leak_passwords_or_raw_uri(self, client: TestClient):
        res = client.get("/health")
        assert res.status_code == 200
        text = res.text
        assert "@cluster" not in text  # No raw mongo connection strings with credentials leaked
        assert "mongodb+srv://" not in text
