"""End-to-end API integration tests using FastAPI TestClient.

Tests the full workflow: create run → recommend → confirm → execute pipeline.
Uses mocked DB session and dependency overrides.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def mock_session():
    """Create a mock async DB session with chainable query results."""
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    session.execute = AsyncMock()
    return session


@pytest.fixture
def client(mock_session):
    """Create TestClient with overridden DB dependency."""
    async def override_get_db():
        yield mock_session

    with patch("app.platform.persistence.database.init_db", new_callable=AsyncMock), \
         patch("app.platform.persistence.database.close_db", new_callable=AsyncMock):
        from app.main import app
        from app.platform.api.deps import get_db
        app.dependency_overrides[get_db] = override_get_db
        # Mock DB session.execute for health check
        mock_session.execute.return_value = MagicMock()
        with TestClient(app) as c:
            yield c
        app.dependency_overrides.clear()


class TestRunEndpoints:
    """Test run CRUD endpoints."""

    def test_create_run(self, client, mock_session):
        """POST /runs should create a run."""
        mock_run = MagicMock()
        mock_run.id = "test-run-123"
        mock_run.status = "created"
        mock_run.created_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00")

        mock_session.add = MagicMock()
        mock_session.refresh = AsyncMock(side_effect=lambda r: setattr(r, '__dict__', mock_run.__dict__))

        with patch("app.platform.persistence.repositories.RunRepository.create", new_callable=AsyncMock) as mock_create:
            mock_create.return_value = mock_run
            response = client.post("/api/v1/runs", json={
                "theme": "data center capex secular growth"
            })

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "test-run-123"
        assert data["status"] == "created"

    def test_get_run_not_found(self, client, mock_session):
        """GET /runs/{id} should 404 for unknown run."""
        with patch("app.platform.persistence.repositories.RunRepository.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = None
            response = client.get("/api/v1/runs/nonexistent")

        assert response.status_code == 404

    def test_get_run_found(self, client, mock_session):
        """GET /runs/{id} should return run details."""
        mock_run = MagicMock()
        mock_run.id = "run-abc"
        mock_run.config = {"theme": "test"}
        mock_run.current_stage = "created"
        mock_run.status = "created"
        mock_run.created_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00")
        mock_run.updated_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00")

        with patch("app.platform.persistence.repositories.RunRepository.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_run
            response = client.get("/api/v1/runs/run-abc")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == "run-abc"
        assert data["config"]["theme"] == "test"

    def test_get_run_status(self, client, mock_session):
        """GET /runs/{id}/status should return pipeline progress."""
        mock_run = MagicMock()
        mock_run.id = "run-abc"
        mock_run.current_stage = "name_generation"
        mock_run.status = "running"

        with patch("app.platform.persistence.repositories.RunRepository.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_run
            response = client.get("/api/v1/runs/run-abc/status")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "running"
        assert data["current_stage"] == "name_generation"


class TestMinerEndpoints:
    """Test miner-related endpoints."""

    def test_list_companies(self, client, mock_session):
        """GET /runs/{id}/companies should list companies."""
        mock_company = MagicMock()
        mock_company.id = "comp-1"
        mock_company.canonical_name = "Acme Electrical"
        mock_company.disposition = "primary"
        mock_company.ownership_tier = "tier_a"
        mock_company.total_score = 72.5
        mock_company.eligible_for_outreach = True
        mock_company.review_required = False
        mock_company.data = {}

        list_path = "app.platform.persistence.repositories.CompanyRepository.list_by_run"
        count_path = "app.platform.persistence.repositories.CompanyRepository.count_by_run"
        with patch(list_path, new_callable=AsyncMock) as mock_list, \
             patch(count_path, new_callable=AsyncMock) as mock_count:
            mock_list.return_value = [mock_company]
            mock_count.return_value = 1
            response = client.get("/api/v1/runs/run-abc/companies")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["companies"][0]["canonical_name"] == "Acme Electrical"

    def test_list_review_queue(self, client, mock_session):
        """GET /runs/{id}/review-queue should list items."""
        mock_item = MagicMock()
        mock_item.id = "review-1"
        mock_item.reason = "ambiguous_duplicate"
        mock_item.details = "Acme Corp vs Acme Corporation"
        mock_item.resolved = False
        mock_item.resolution = None
        mock_item.data = {}

        review_path = "app.platform.persistence.repositories.ReviewRepository.list_by_run"
        with patch(review_path, new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [mock_item]
            response = client.get("/api/v1/runs/run-abc/review-queue")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["reason"] == "ambiguous_duplicate"

    def test_resolve_review_item(self, client, mock_session):
        """POST resolve should mark item resolved."""
        resolve_path = "app.platform.persistence.repositories.ReviewRepository.resolve"
        with patch(resolve_path, new_callable=AsyncMock) as mock_resolve:
            response = client.post(
                "/api/v1/runs/run-abc/review-queue/item-1/resolve",
                json={"resolution": "merge"},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "resolved"
        assert data["resolution"] == "merge"
        mock_resolve.assert_called_once_with("item-1", "merge")

    def test_rerun_stage_invalid(self, client, mock_session):
        """POST rerun with invalid stage should 400."""
        mock_run = MagicMock()
        mock_run.id = "run-abc"
        mock_run.config = {}

        with patch("app.platform.persistence.repositories.RunRepository.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_run
            response = client.post("/api/v1/runs/run-abc/stages/invalid_stage/rerun")

        assert response.status_code == 400


class TestExportEndpoints:
    """Test export endpoints."""

    def test_list_exports(self, client, mock_session):
        """GET /runs/{id}/exports should list manifests."""
        mock_manifest = MagicMock()
        mock_manifest.id = "exp-1"
        mock_manifest.created_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00")
        mock_manifest.data = {"exports": [{"format": "csv", "path": "test.csv"}]}

        export_path = "app.platform.persistence.repositories.ExportRepository.list_by_run"
        with patch(export_path, new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [mock_manifest]
            response = client.get("/api/v1/runs/run-abc/exports")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1

    def test_list_checkpoints(self, client, mock_session):
        """GET /runs/{id}/checkpoints should list checkpoints."""
        mock_cp = MagicMock()
        mock_cp.id = "cp-1"
        mock_cp.stage = "scoring"
        mock_cp.company_count = 42
        mock_cp.created_at = MagicMock(isoformat=lambda: "2026-01-01T00:00:00")
        mock_cp.notes = "Post-scoring checkpoint"

        cp_path = "app.platform.persistence.repositories.CheckpointRepository.list_by_run"
        with patch(cp_path, new_callable=AsyncMock) as mock_list:
            mock_list.return_value = [mock_cp]
            response = client.get("/api/v1/runs/run-abc/checkpoints")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["stage"] == "scoring"
        assert data[0]["company_count"] == 42
