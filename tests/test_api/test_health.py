"""API endpoint tests using FastAPI TestClient."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client with mocked DB session."""
    mock_session = AsyncMock()
    # Make SELECT 1 succeed
    mock_session.execute = AsyncMock(return_value=MagicMock())

    async def override_get_db():
        yield mock_session

    with patch("app.platform.persistence.database.init_db", new_callable=AsyncMock), \
         patch("app.platform.persistence.database.close_db", new_callable=AsyncMock):
        from app.main import app
        from app.platform.api.deps import get_db

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


def test_health_endpoint(client):
    """Health endpoint should return 200 with healthy status."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "ok"


def test_readiness_endpoint(client):
    """Readiness endpoint should return 200."""
    response = client.get("/api/v1/readiness")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ready"
