import sys
from pathlib import Path
from datetime import datetime, timezone
import pytest
from unittest.mock import AsyncMock, patch

# Ensure project root is on sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.user import UserDocument
from backend.app.auth.jwt import create_access_token


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def mock_admin_user() -> UserDocument:
    return UserDocument(
        id="usr-test-admin-01",
        user_id="usr-test-admin-01",
        username="admin_test",
        email="admin@test.ai",
        hashed_password="$2b$12$mockhashedpasswordadmin123456789012345678901234567890",
        full_name="Test Administrator",
        role="admin",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_analyst_user() -> UserDocument:
    return UserDocument(
        id="usr-test-analyst-01",
        user_id="usr-test-analyst-01",
        username="analyst_test",
        email="analyst@test.ai",
        hashed_password="$2b$12$mockhashedpasswordanalyst12345678901234567890123456789",
        full_name="Test SOC Analyst",
        role="analyst",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def mock_viewer_user() -> UserDocument:
    return UserDocument(
        id="usr-test-viewer-01",
        user_id="usr-test-viewer-01",
        username="viewer_test",
        email="viewer@test.ai",
        hashed_password="$2b$12$mockhashedpasswordviewer123456789012345678901234567890",
        full_name="Test Readonly Viewer",
        role="viewer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )


@pytest.fixture
def admin_token(mock_admin_user) -> str:
    return create_access_token(
        subject=mock_admin_user.user_id,
        claims={"username": mock_admin_user.username, "role": mock_admin_user.role},
    )


@pytest.fixture
def analyst_token(mock_analyst_user) -> str:
    return create_access_token(
        subject=mock_analyst_user.user_id,
        claims={"username": mock_analyst_user.username, "role": mock_analyst_user.role},
    )


@pytest.fixture
def viewer_token(mock_viewer_user) -> str:
    return create_access_token(
        subject=mock_viewer_user.user_id,
        claims={"username": mock_viewer_user.username, "role": mock_viewer_user.role},
    )


@pytest.fixture
def admin_headers(admin_token) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}


@pytest.fixture
def analyst_headers(analyst_token) -> dict:
    return {"Authorization": f"Bearer {analyst_token}"}


@pytest.fixture
def viewer_headers(viewer_token) -> dict:
    return {"Authorization": f"Bearer {viewer_token}"}
