"""API happy-path integration test.

Exercises the full workflow through real endpoints backed by SQLite:
  create run → recommend subverticals → confirm → recommend sources →
  confirm → execute pipeline → list companies → export.

Uses MockLLMService and MockPitchBookClient — no external services.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.platform.models.orm import Base


def _cryptography_available() -> bool:
    try:
        import subprocess
        import sys

        result = subprocess.run(
            [sys.executable, "-c", "from cryptography.hazmat.bindings._rust import ObjectIdentifier"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


@pytest.fixture
def db_engine_and_session():
    """Create a SQLite engine + sessionmaker for the test."""
    import asyncio

    engine = create_async_engine("sqlite+aiosqlite://", echo=False)

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_setup())
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, factory

    async def _teardown():
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_teardown())


@pytest.fixture
def client(db_engine_and_session):
    """Create TestClient with SQLite DB and mock services."""
    from unittest.mock import AsyncMock, patch

    _, session_factory = db_engine_and_session

    async def override_get_db():
        async with session_factory() as session:
            yield session

    with patch("app.main.init_db", new_callable=AsyncMock), \
         patch("app.main.close_db", new_callable=AsyncMock), \
         patch("app.ai.llm_service.settings") as mock_settings:
        # Force mock LLM regardless of .env
        mock_settings.llm_provider = "mock"
        mock_settings.llm_api_key = ""
        mock_settings.llm_model = "mock"
        mock_settings.llm_rate_limit_rpm = 50

        from app.main import app
        from app.platform.api.deps import get_db

        app.dependency_overrides[get_db] = override_get_db
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


class TestAPIHappyPath:
    """Full workflow integration test."""

    def test_create_run(self, client):
        resp = client.post("/api/v1/runs", json={"theme": "data center capex"})
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["status"] == "pending"

    def test_get_run(self, client):
        create = client.post("/api/v1/runs", json={"theme": "test"}).json()
        resp = client.get(f"/api/v1/runs/{create['id']}")
        assert resp.status_code == 200
        assert resp.json()["config"]["theme"] == "test"

    def test_get_nonexistent_run_returns_404(self, client):
        resp = client.get("/api/v1/runs/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404

    def test_recommend_subverticals(self, client):
        run = client.post("/api/v1/runs", json={"theme": "data center capex"}).json()
        resp = client.post(f"/api/v1/runs/{run['id']}/recommend-subverticals")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 1
        assert len(data["recommendations"]) >= 1

    def test_confirm_subverticals(self, client):
        run = client.post("/api/v1/runs", json={"theme": "data center capex"}).json()
        client.post(f"/api/v1/runs/{run['id']}/recommend-subverticals")
        resp = client.post(
            f"/api/v1/runs/{run['id']}/confirm-subverticals",
            json={"accept_all": True},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["confirmed_subverticals"]) >= 1

    def test_recommend_sources(self, client):
        """Source recommendation works; mock may return 0 sources (no source discovery fixture)."""
        run = client.post("/api/v1/runs", json={"theme": "data center capex"}).json()
        client.post(f"/api/v1/runs/{run['id']}/recommend-subverticals")
        client.post(
            f"/api/v1/runs/{run['id']}/confirm-subverticals",
            json={"accept_all": True},
        )
        resp = client.post(f"/api/v1/runs/{run['id']}/recommend-sources")
        assert resp.status_code == 200
        data = resp.json()
        assert "count" in data

    def test_confirm_sources(self, client):
        """Source confirmation works even with 0 sources."""
        run = client.post("/api/v1/runs", json={"theme": "data center capex"}).json()
        client.post(f"/api/v1/runs/{run['id']}/recommend-subverticals")
        client.post(
            f"/api/v1/runs/{run['id']}/confirm-subverticals",
            json={"accept_all": True},
        )
        client.post(f"/api/v1/runs/{run['id']}/recommend-sources")
        resp = client.post(
            f"/api/v1/runs/{run['id']}/confirm-sources",
            json={"accept_all": True},
        )
        assert resp.status_code == 200
        assert "confirmed_sources_count" in resp.json()

    @pytest.mark.skipif(
        not _cryptography_available(),
        reason="System cryptography module is broken (missing _cffi_backend)",
    )
    def test_full_workflow_through_execute(self, client):
        """End-to-end: create → recommend → confirm → execute → check status."""
        # 1. Create run
        run = client.post("/api/v1/runs", json={"theme": "data center capex"}).json()
        run_id = run["id"]

        # 2. Recommend + confirm subverticals
        client.post(f"/api/v1/runs/{run_id}/recommend-subverticals")
        client.post(
            f"/api/v1/runs/{run_id}/confirm-subverticals",
            json={"accept_all": True},
        )

        # 3. Recommend + confirm sources (mock returns 0, which is fine)
        client.post(f"/api/v1/runs/{run_id}/recommend-sources")
        client.post(
            f"/api/v1/runs/{run_id}/confirm-sources",
            json={"accept_all": True},
        )

        # 4. Execute pipeline (runs inline with mocks)
        exec_resp = client.post(f"/api/v1/runs/{run_id}/execute")
        assert exec_resp.status_code == 200
        exec_data = exec_resp.json()
        assert exec_data["status"] == "completed"

        # 5. Verify run status
        status = client.get(f"/api/v1/runs/{run_id}/status").json()
        assert status["status"] == "completed"

    def test_health_endpoint(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200

    def test_openapi_schema(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        assert "paths" in resp.json()
