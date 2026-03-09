"""Smoke tests — verify core modules import, wire up correctly, and produce valid output.

These tests run without any external services (no DB, no Redis, no API keys).
They validate that the application can start, config loads, and end-to-end flows
produce consistent results through mock providers.
"""

import json
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# ---- Module import smoke tests ----

class TestImports:
    """Verify all core modules import without errors."""

    def test_import_main(self):
        from app.main import app
        assert app is not None
        assert app.title == "DL Origination Assistant"

    def test_import_cli(self):
        from app.cli import app
        assert app is not None

    def test_import_llm_service(self):
        from app.ai.llm_service import MockLLMService, get_llm_service
        with patch("app.ai.llm_service.settings") as mock_settings:
            mock_settings.llm_provider = "mock"
            svc = get_llm_service()
        assert isinstance(svc, MockLLMService)

    def test_import_mcp_manager(self):
        from app.ai.mcp_manager import mcp_manager
        assert mcp_manager is not None

    def test_import_recommender(self):
        from app.recommender.engine import RecommenderEngine
        assert RecommenderEngine is not None

    def test_import_miner(self):
        from app.miner.engine import MinerEngine
        assert MinerEngine is not None

    def test_import_all_enums(self):
        from app.platform.models.enums import (
            Disposition,
            WorkflowStage,
        )
        assert len(WorkflowStage) == 16
        assert len(Disposition) == 4


# ---- Config smoke tests ----

class TestConfig:
    """Verify config system loads correctly."""

    def test_settings_load(self):
        from app.platform.config.settings import settings
        assert settings.llm_provider in ("mock", "claude")
        assert settings.storage_backend in ("local", "s3")

    def test_defaults_loaded(self):
        from app.platform.config.defaults import (
            SCORING_WEIGHTS,
            SUBVERTICAL_SCORING_WEIGHTS,
        )
        assert abs(sum(SCORING_WEIGHTS.values()) - 100.0) < 0.01
        assert abs(sum(SUBVERTICAL_SCORING_WEIGHTS.values()) - 100.0) < 0.01

    def test_profile_loader(self):
        from app.platform.config.loader import list_profiles, load_profile
        profiles = list_profiles()
        assert "generic" in profiles
        generic = load_profile("generic")
        assert isinstance(generic, dict)

    def test_nonexistent_profile_returns_empty(self):
        from app.platform.config.loader import load_profile
        result = load_profile("nonexistent_profile_xyz")
        assert result == {}


# ---- Schema smoke tests ----

class TestSchemas:
    """Verify Pydantic schemas construct and serialize correctly."""

    def test_company_record_defaults(self):
        from app.platform.models.schemas import CompanyRecord
        company = CompanyRecord(run_id=uuid4(), canonical_name="Test Corp")
        assert company.hq_country == "US"
        assert company.disposition.value == "primary"
        assert company.ownership_tier.value == "unknown"
        assert company.eligible_for_outreach is False

    def test_company_record_serialization(self):
        from app.platform.models.schemas import CompanyRecord
        company = CompanyRecord(
            run_id=uuid4(),
            canonical_name="Test Corp",
            revenue_estimate=100.0,
        )
        data = company.model_dump(mode="json")
        assert data["canonical_name"] == "Test Corp"
        assert data["revenue_estimate"] == 100.0
        # Ensure JSON-serializable
        json_str = json.dumps(data, default=str)
        assert "Test Corp" in json_str

    def test_run_config_defaults(self):
        from app.platform.models.run import RunConfig
        config = RunConfig(theme="test theme")
        assert config.geography_filter == ["US"]
        assert config.revenue_ceiling == 1000.0

    def test_review_queue_item(self):
        from app.platform.models.enums import ReviewReason
        from app.platform.models.schemas import ReviewQueueItem
        item = ReviewQueueItem(
            run_id=uuid4(),
            reason=ReviewReason.AMBIGUOUS_DUPLICATE,
            details="Test",
        )
        assert item.resolved is False

    def test_ai_provenance(self):
        from app.ai.confidence import AIProvenance
        prov = AIProvenance(
            ai_generated=True,
            confidence_score=0.9,
        )
        assert prov.auto_accept(0.85) is True
        assert prov.acceptance_status == "auto_accepted"

    def test_ai_provenance_below_threshold(self):
        from app.ai.confidence import AIProvenance
        prov = AIProvenance(ai_generated=True, confidence_score=0.5)
        assert prov.auto_accept(0.85) is False
        assert prov.acceptance_status == "pending"


# ---- Mock LLM smoke tests ----

class TestMockLLM:
    """Verify MockLLM returns valid structured responses."""

    @pytest.mark.asyncio
    async def test_mock_llm_default_response(self):
        from app.ai.llm_service import MockLLMService
        llm = MockLLMService()
        result = await llm.complete_json("test prompt")
        assert "subverticals" in result

    @pytest.mark.asyncio
    async def test_mock_llm_enrichment_response(self):
        from app.ai.llm_service import MockLLMService
        llm = MockLLMService()
        result = await llm.complete_json("Research the following company for enrichment data")
        assert "hq_state" in result
        assert "revenue_estimate" in result

    @pytest.mark.asyncio
    async def test_mock_llm_fixture_registration(self):
        from app.ai.llm_service import MockLLMService
        llm = MockLLMService()
        llm.register_fixture("special_key", {"custom": True})
        result = await llm.complete_json("prompt with special_key in it")
        assert result["custom"] is True


# ---- Recommender smoke tests ----

class TestRecommenderSmoke:
    """Verify recommender engine produces valid output with mock LLM."""

    @pytest.mark.asyncio
    async def test_recommend_subverticals_produces_output(self):
        from app.ai.llm_service import MockLLMService
        from app.platform.models.run import RunConfig
        from app.recommender.engine import RecommenderEngine

        llm = MockLLMService()
        engine = RecommenderEngine(llm)
        config = RunConfig(theme="test theme")
        recs = await engine.recommend_subverticals(uuid4(), config)
        assert len(recs) > 0
        assert recs[0].subvertical_name != ""
        assert recs[0].ai_provenance.ai_generated is True

    @pytest.mark.asyncio
    async def test_recommend_sources_produces_output(self):
        from app.ai.llm_service import MockLLMService
        from app.recommender.engine import RecommenderEngine

        llm = MockLLMService()
        # Register a fixture for source discovery
        llm.register_fixture("sub-verticals", {
            "sources": [{"source_name": "Test Source", "source_type": "trade_journal",
                         "mapped_subverticals": ["Test SV"], "rationale": "test"}],
            "naics_codes": [],
        })
        engine = RecommenderEngine(llm)
        sources = await engine.recommend_sources(uuid4(), ["Test SV"], 1000.0)
        assert len(sources) > 0


# ---- Miner pipeline smoke tests ----

class TestMinerSmoke:
    """Verify miner pipeline runs end-to-end with all mocks."""

    @pytest.mark.asyncio
    async def test_full_pipeline_smoke(self):
        from app.ai.llm_service import MockLLMService
        from app.miner.engine import MinerEngine
        from app.miner.pitchbook.mock_client import MockPitchBookClient
        from app.platform.persistence.storage import LocalStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            llm = MockLLMService()
            pb = MockPitchBookClient()
            storage = LocalStorage(tmpdir)
            from app.miner.sources.registry import SourceRegistry
            miner = MinerEngine(
                llm_service=llm,
                pitchbook_adapter=pb,
                storage=storage,
                source_registry=SourceRegistry(use_mock=True),
            )

            run_id = uuid4()
            config = {
                "selected_sources": [
                    {"source_name": "Test Source", "source_type": "trade_journal"},
                ],
                "geography_filter": ["US"],
                "revenue_ceiling": 1000.0,
            }

            results = await miner.execute_pipeline(run_id, config)

            # Verify all stages ran
            assert "name_generation" in results
            assert "scoring" in results
            assert "export" in results

            # Verify companies were produced
            assert len(miner.companies) > 0

            # Verify export files were created
            export_files = await storage.list_files(f"exports/{run_id}")
            assert len(export_files) > 0

    @pytest.mark.asyncio
    async def test_pipeline_without_sources(self):
        from app.miner.engine import MinerEngine
        miner = MinerEngine()
        result = await miner.execute_pipeline(uuid4(), {})
        assert result["name_generation"]["companies_found"] == 0


# ---- Export smoke tests ----

class TestExportSmoke:
    """Verify export formats produce valid output."""

    def test_csv_export(self):
        from app.platform.exports.csv_exporter import export_csv
        companies = [{"canonical_name": "Test Corp", "hq_state": "TX"}]
        result = export_csv(companies)
        assert b"canonical_name" in result
        assert b"Test Corp" in result

    def test_json_export(self):
        from app.platform.exports.json_exporter import export_json
        companies = [{"canonical_name": "Test Corp"}]
        result = export_json(companies)
        parsed = json.loads(result.decode())
        assert parsed["canonical_name"] == "Test Corp"

    def test_excel_export(self):
        from app.platform.exports.excel_exporter import export_excel
        companies = [
            {"canonical_name": "Test Corp", "eligible_for_outreach": True,
             "total_score": 75.0, "has_debt": True, "facility_type": "TL"},
        ]
        result = export_excel(companies)
        assert len(result) > 100  # Valid XLSX should be more than 100 bytes

    @pytest.mark.asyncio
    async def test_export_service_manifest(self):
        from app.platform.exports.service import ExportService
        from app.platform.persistence.storage import LocalStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            svc = ExportService(storage)
            manifest = await svc.export_run(
                uuid4(),
                [{"canonical_name": "Test"}],
                format="all",
            )
            assert "exports" in manifest
            assert len(manifest["exports"]) == 3  # csv, jsonl, xlsx


# ---- Checkpoint smoke tests ----

class TestCheckpointSmoke:
    """Verify checkpoint save/load round-trips correctly."""

    @pytest.mark.asyncio
    async def test_checkpoint_save_load(self):
        from app.platform.persistence.storage import LocalStorage
        from app.platform.workflow.checkpoint import CheckpointManager

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            mgr = CheckpointManager(storage)
            run_id = uuid4()

            saved = await mgr.save_checkpoint(
                run_id, "scoring",
                data={"companies": [{"name": "Test"}]},
                company_count=1,
            )
            assert saved["stage"] == "scoring"

            loaded = await mgr.load_checkpoint(run_id, "scoring")
            assert loaded is not None
            assert loaded["company_count"] == 1
            assert loaded["data"]["companies"][0]["name"] == "Test"


# ---- Storage smoke tests ----

class TestStorageSmoke:
    """Verify local storage operations."""

    @pytest.mark.asyncio
    async def test_save_load_bytes(self):
        from app.platform.persistence.storage import LocalStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            await storage.save("test/file.txt", b"hello")
            data = await storage.load("test/file.txt")
            assert data == b"hello"

    @pytest.mark.asyncio
    async def test_save_load_json(self):
        from app.platform.persistence.storage import LocalStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            await storage.save_json("test/data.json", {"key": "value"})
            data = await storage.load_json("test/data.json")
            assert data["key"] == "value"

    @pytest.mark.asyncio
    async def test_list_files(self):
        from app.platform.persistence.storage import LocalStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            await storage.save("prefix/a.txt", b"a")
            await storage.save("prefix/b.txt", b"b")
            files = await storage.list_files("prefix")
            assert len(files) == 2

    @pytest.mark.asyncio
    async def test_exists(self):
        from app.platform.persistence.storage import LocalStorage

        with tempfile.TemporaryDirectory() as tmpdir:
            storage = LocalStorage(tmpdir)
            assert not await storage.exists("nope.txt")
            await storage.save("yes.txt", b"x")
            assert await storage.exists("yes.txt")


# ---- API smoke tests (with mocked DB) ----

class TestAPISmoke:
    """Verify API starts and health endpoints respond."""

    @pytest.fixture
    def client(self):
        mock_session = AsyncMock()
        mock_session.execute.return_value = MagicMock()

        async def override_get_db():
            yield mock_session

        with patch(
            "app.main.init_db",
            new_callable=AsyncMock,
        ), patch(
            "app.main.close_db",
            new_callable=AsyncMock,
        ):
            from fastapi.testclient import TestClient

            from app.main import app
            from app.platform.api.deps import get_db

            app.dependency_overrides[get_db] = override_get_db
            with TestClient(app) as c:
                yield c
            app.dependency_overrides.clear()

    def test_health(self, client):
        resp = client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

    def test_readiness(self, client):
        resp = client.get("/api/v1/readiness")
        assert resp.status_code == 200

    def test_connector_status(self, client):
        resp = client.get("/api/v1/connectors/status")
        assert resp.status_code == 200
        assert "connectors" in resp.json()

    def test_openapi_schema(self, client):
        resp = client.get("/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert schema["info"]["title"] == "DL Origination Assistant"
        paths = schema["paths"]
        assert "/api/v1/health" in paths
        assert "/api/v1/runs" in paths


# ---- Scoring determinism smoke test ----

class TestScoringDeterminism:
    """Verify scoring is deterministic and bounded."""

    def test_identical_inputs_identical_output(self):
        from app.platform.models.schemas import CompanyRecord
        from app.platform.scoring.company_scorer import score_company

        company = CompanyRecord(
            run_id=uuid4(),
            canonical_name="Determinism Test",
            revenue_estimate=200.0,
            industry_exposure_intensity="high",
        )
        score1, comp1 = score_company(company)
        score2, comp2 = score_company(company)
        assert score1 == score2
        assert comp1 == comp2

    def test_score_always_bounded(self):
        from app.platform.models.enums import OwnershipTier
        from app.platform.models.schemas import CompanyRecord
        from app.platform.scoring.company_scorer import score_company

        # Minimal company
        c1 = CompanyRecord(run_id=uuid4(), canonical_name="Minimal")
        s1, _ = score_company(c1)
        assert 0 <= s1 <= 100

        # Maximal company
        c2 = CompanyRecord(
            run_id=uuid4(), canonical_name="Maximal",
            revenue_estimate=200.0, ebitda_estimate=50.0,
            recurring_revenue_estimate=160.0,
            industry_exposure_intensity="high",
            ownership_tier=OwnershipTier.TIER_A,
            hq_state="TX", subvertical_tags=["Test"],
            industry_exposure_descriptor="Test",
            website="https://test.com",
        )
        s2, _ = score_company(c2)
        assert 0 <= s2 <= 100
