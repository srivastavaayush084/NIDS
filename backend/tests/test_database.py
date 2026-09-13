import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from backend.app.database.collections import ALL_COLLECTIONS, USERS_COLLECTION, ALERTS_COLLECTION
from backend.app.database.repository import BaseRepository
from backend.app.database.indexes import create_database_indexes


from backend.app.main import app
from backend.app.auth.dependencies import get_current_user
from backend.app.models.user import UserDocument


@pytest.fixture(autouse=True)
def override_auth_for_database_tests():
    """Ensure database test requests execute with admin credentials."""
    mock_user = UserDocument(
        id="usr-db-admin",
        user_id="usr-db-admin",
        username="db_admin",
        email="dbadmin@zeroday.ai",
        hashed_password="$2b$12$mockhashedpasswordsample123456789012345678901234567890",
        role="admin",
        is_active=True,
    )
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


def test_database_status_endpoint(client: TestClient):
    """Test /api/v1/database/status endpoint."""
    response = client.get("/api/v1/database/status")
    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert "connected" in data
    assert "database_name" in data
    assert "collections" in data
    assert "collection_counts" in data
    assert "message" in data


@pytest.mark.asyncio
async def test_base_repository_mocked():
    """Test BaseRepository CRUD operations with mock database."""
    mock_collection = MagicMock()
    mock_collection.find_one = AsyncMock(return_value={"_id": "123", "title": "Test Alert"})
    mock_collection.insert_one = AsyncMock(return_value=MagicMock(inserted_id="123"))
    mock_collection.count_documents = AsyncMock(return_value=5)

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    repo = BaseRepository(ALERTS_COLLECTION, db=mock_db)

    # Test find_one
    doc = await repo.find_one({"_id": "123"})
    assert doc is not None
    assert doc["title"] == "Test Alert"

    # Test insert_one
    inserted_id = await repo.insert_one({"title": "New Alert"})
    assert inserted_id == "123"

    # Test count
    total = await repo.count()
    assert total == 5


@pytest.mark.asyncio
async def test_create_database_indexes_mocked():
    """Verify index creation executes without uncaught errors against collections."""
    mock_collection = MagicMock()
    mock_collection.create_indexes = AsyncMock(return_value=["idx_1"])

    mock_db = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    await create_database_indexes(mock_db)
    assert mock_collection.create_indexes.called
