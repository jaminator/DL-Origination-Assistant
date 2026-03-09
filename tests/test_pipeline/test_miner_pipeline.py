"""Integration tests for the full miner pipeline with mock adapters."""

import tempfile
from uuid import uuid4

import pytest

from app.ai.llm_service import MockLLMService
from app.miner.engine import MinerEngine
from app.miner.pitchbook.mock_client import MockPitchBookClient
from app.miner.sources.mock_adapter import MockSourceAdapter
from app.miner.sources.registry import SourceRegistry
from app.platform.models.enums import Disposition, OwnershipTier, PitchBookStatus, WorkflowStage
from app.platform.persistence.storage import LocalStorage


@pytest.fixture
def run_id():
    return uuid4()


@pytest.fixture
def run_config():
    return {
        "theme": "data center capex secular growth",
        "geography_filter": ["US"],
        "revenue_ceiling": 1000.0,
        "cascade_anchor_threshold": 1000.0,
        "tier_a_scoring_bonus": 15.0,
        "tier_b_scoring_bonus": 8.0,
        "tier_c_scoring_bonus": 0.0,
        "include_cascade_anchors_in_outreach": False,
        "boundary_treatment": "watch",
        "max_recursion_depth": 3,
        "selected_sources": [
            {"source_name": "Data Center Magazine Top 50", "source_type": "ranking_list"},
            {"source_name": "ASHRAE Member Directory", "source_type": "association_directory"},
        ],
    }


@pytest.fixture
def mock_storage(tmp_path):
    return LocalStorage(str(tmp_path))


@pytest.fixture
def mock_registry():
    registry = SourceRegistry(use_mock=True)
    return registry


@pytest.fixture
def miner(mock_storage, mock_registry):
    return MinerEngine(
        llm_service=MockLLMService(),
        pitchbook_adapter=MockPitchBookClient(),
        storage=mock_storage,
        source_registry=mock_registry,
    )


@pytest.mark.asyncio
async def test_full_pipeline(miner, run_id, run_config):
    """Run the full 10-stage pipeline with all mock adapters."""
    results = await miner.execute_pipeline(run_id, run_config)

    # All 10 stages should have completed
    assert len(results) == 10
    for stage_result in results.values():
        assert stage_result["status"] in ("completed", "skipped")

    # Should have discovered companies
    assert len(miner.companies) > 0


@pytest.mark.asyncio
async def test_name_generation(miner, run_id, run_config):
    """Name generation should extract companies from mock sources."""
    result = await miner._run_name_generation(run_id, run_config)
    assert result["status"] == "completed"
    assert result["companies_found"] > 0
    assert len(miner._raw_companies) > 0


@pytest.mark.asyncio
async def test_name_normalization(miner, run_id, run_config):
    """Normalization should deduplicate and create canonical records."""
    await miner._run_name_generation(run_id, run_config)
    result = await miner._run_name_normalization(run_id, run_config)
    assert result["status"] == "completed"
    assert result["distinct_companies"] > 0
    assert len(miner.companies) == result["distinct_companies"]
    # All companies should have a canonical name
    for c in miner.companies:
        assert c.canonical_name
        assert c.run_id == run_id


@pytest.mark.asyncio
async def test_web_enhancement(miner, run_id, run_config):
    """Web enhancement should enrich companies via mock LLM."""
    await miner._run_name_generation(run_id, run_config)
    await miner._run_name_normalization(run_id, run_config)
    result = await miner._run_web_enhancement(run_id, run_config)
    assert result["status"] == "completed"
    assert result["companies_enriched"] > 0

    # Mock LLM should populate enrichment fields
    for c in miner.companies:
        assert c.hq_state == "TX"
        assert c.revenue_estimate == 85.0
        assert c.ownership_tier == OwnershipTier.TIER_A


@pytest.mark.asyncio
async def test_dispositioning(miner, run_id, run_config):
    """Dispositioning should classify companies."""
    await miner._run_name_generation(run_id, run_config)
    await miner._run_name_normalization(run_id, run_config)
    await miner._run_web_enhancement(run_id, run_config)
    result = await miner._run_dispositioning(run_id, run_config)
    assert result["status"] == "completed"
    assert "counts" in result

    # Mock companies with $85M revenue should be PRIMARY
    for c in miner.companies:
        assert c.disposition in (Disposition.PRIMARY, Disposition.CASCADE_ANCHOR, Disposition.EXCLUDE, Disposition.WATCH)


@pytest.mark.asyncio
async def test_pitchbook_enrichment(miner, run_id, run_config):
    """PitchBook enrichment should match companies via mock adapter."""
    await miner._run_name_generation(run_id, run_config)
    await miner._run_name_normalization(run_id, run_config)
    await miner._run_web_enhancement(run_id, run_config)
    await miner._run_dispositioning(run_id, run_config)
    result = await miner._run_pitchbook_enrichment(run_id, run_config)
    assert result["status"] == "completed"
    assert result["matched"] > 0

    matched = [c for c in miner.companies if c.pb_status == PitchBookStatus.MATCHED]
    assert len(matched) > 0
    for c in matched:
        assert c.pb_entity_id is not None


@pytest.mark.asyncio
async def test_scoring(miner, run_id, run_config):
    """Scoring should produce valid scores for primary companies."""
    await miner._run_name_generation(run_id, run_config)
    await miner._run_name_normalization(run_id, run_config)
    await miner._run_web_enhancement(run_id, run_config)
    await miner._run_dispositioning(run_id, run_config)
    await miner._run_pitchbook_enrichment(run_id, run_config)
    await miner._run_cascade_expansion(run_id, run_config)
    await miner._run_final_dedup(run_id, run_config)
    await miner._run_qa_validation(run_id, run_config)
    result = await miner._run_scoring(run_id, run_config)

    assert result["status"] == "completed"
    assert result["scored"] > 0

    scored = [c for c in miner.companies if c.total_score is not None]
    assert len(scored) > 0
    for c in scored:
        assert 0 <= c.total_score <= 100
        assert len(c.score_components) > 0


@pytest.mark.asyncio
async def test_export(miner, run_id, run_config):
    """Export should generate files in all formats."""
    results = await miner.execute_pipeline(run_id, run_config)
    export_result = results.get("export", {})
    assert export_result["status"] == "completed"
    assert len(export_result["files"]) == 3  # csv, jsonl, xlsx


@pytest.mark.asyncio
async def test_pipeline_without_sources():
    """Pipeline with no selected sources should complete gracefully."""
    run_id = uuid4()
    config = {"theme": "test", "geography_filter": ["US"], "selected_sources": []}
    engine = MinerEngine(llm_service=MockLLMService())
    results = await engine.execute_pipeline(run_id, config)
    assert results["name_generation"]["companies_found"] == 0


@pytest.mark.asyncio
async def test_pipeline_without_llm(mock_storage, mock_registry):
    """Pipeline without LLM should skip web enhancement."""
    run_id = uuid4()
    config = {
        "selected_sources": [{"source_name": "test", "source_type": "ranking_list"}],
        "geography_filter": ["US"],
        "revenue_ceiling": 1000.0,
        "cascade_anchor_threshold": 1000.0,
    }
    engine = MinerEngine(
        llm_service=None,
        pitchbook_adapter=MockPitchBookClient(),
        storage=mock_storage,
        source_registry=mock_registry,
    )
    results = await engine.execute_pipeline(run_id, config)
    assert results["web_enhancement"]["status"] == "skipped"
    assert results["name_generation"]["companies_found"] > 0
