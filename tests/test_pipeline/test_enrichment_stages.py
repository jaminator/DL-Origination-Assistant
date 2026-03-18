"""Integration tests for BizAPI and Capital IQ enrichment pipeline stages."""

from uuid import uuid4

import pytest

from app.ai.llm_service import MockLLMService
from app.miner.engine import MinerEngine
from app.miner.enrichment.bizapi.mock_client import MockBizAPIClient
from app.miner.enrichment.capitaliq.mock_client import MockCapitalIQClient
from app.miner.pitchbook.mock_client import MockPitchBookClient
from app.platform.models.enums import (
    BizAPIStatus,
    CapitalIQStatus,
    Disposition,
    PitchBookStatus,
    WorkflowStage,
)
from app.platform.models.schemas import CompanyRecord
from app.platform.persistence.storage import LocalStorage


@pytest.fixture
def tmp_storage(tmp_path):
    return LocalStorage(str(tmp_path))


@pytest.fixture
def full_engine(tmp_storage):
    return MinerEngine(
        llm_service=MockLLMService(),
        pitchbook_adapter=MockPitchBookClient(),
        bizapi_adapter=MockBizAPIClient(),
        capitaliq_adapter=MockCapitalIQClient(),
        storage=tmp_storage,
    )


@pytest.fixture
def engine_no_bizapi(tmp_storage):
    return MinerEngine(
        llm_service=MockLLMService(),
        pitchbook_adapter=MockPitchBookClient(),
        capitaliq_adapter=MockCapitalIQClient(),
        storage=tmp_storage,
    )


@pytest.fixture
def engine_no_capitaliq(tmp_storage):
    return MinerEngine(
        llm_service=MockLLMService(),
        pitchbook_adapter=MockPitchBookClient(),
        bizapi_adapter=MockBizAPIClient(),
        storage=tmp_storage,
    )


def _seed_companies(engine: MinerEngine, run_id, count=3):
    """Inject test companies directly into the engine's in-memory state."""
    companies = []
    for i in range(count):
        c = CompanyRecord(
            id=uuid4(),
            run_id=run_id,
            canonical_name=f"Test Company {i}",
            hq_state="TX",
            website=f"https://testco{i}.com",
            disposition=Disposition.PRIMARY,
            workflow_stage=WorkflowStage.DISPOSITIONING,
        )
        companies.append(c)
    engine._companies = companies
    return companies


# -- BizAPI stage tests --

async def test_bizapi_enrichment_with_mock(full_engine):
    run_id = uuid4()
    companies = _seed_companies(full_engine, run_id)

    result = await full_engine._run_bizapi_enrichment(run_id, {})

    assert result["status"] == "completed"
    assert result["matched"] == 3
    assert result["not_found"] == 0

    for c in companies:
        assert c.bizapi_status == BizAPIStatus.MATCHED
        assert c.bizapi_duns is not None
        assert c.naics_code is not None
        assert c.bizapi_match_confidence is not None


async def test_bizapi_stage_skipped_without_adapter(engine_no_bizapi):
    run_id = uuid4()
    _seed_companies(engine_no_bizapi, run_id)

    result = await engine_no_bizapi._run_bizapi_enrichment(run_id, {})
    assert result["status"] == "skipped"
    assert result["reason"] == "no_adapter"


async def test_bizapi_skips_excluded_companies(full_engine):
    run_id = uuid4()
    companies = _seed_companies(full_engine, run_id, count=2)
    companies[1].disposition = Disposition.EXCLUDE

    result = await full_engine._run_bizapi_enrichment(run_id, {})
    assert result["matched"] == 1
    assert companies[0].bizapi_status == BizAPIStatus.MATCHED
    assert companies[1].bizapi_status == BizAPIStatus.PENDING  # not touched


async def test_bizapi_idempotent_on_resume(full_engine):
    run_id = uuid4()
    companies = _seed_companies(full_engine, run_id, count=2)
    companies[0].bizapi_status = BizAPIStatus.MATCHED  # already enriched

    result = await full_engine._run_bizapi_enrichment(run_id, {})
    assert result["matched"] == 1  # only the second company


# -- Capital IQ stage tests --

async def test_capitaliq_enrichment_with_mock(full_engine):
    run_id = uuid4()
    companies = _seed_companies(full_engine, run_id)

    result = await full_engine._run_capitaliq_enrichment(run_id, {})

    assert result["status"] == "completed"
    assert result["matched"] == 3

    for c in companies:
        assert c.ciq_status == CapitalIQStatus.MATCHED
        assert c.ciq_entity_id is not None
        assert c.ciq_revenue is not None
        assert c.ciq_ebitda is not None


async def test_capitaliq_stage_skipped_without_adapter(engine_no_capitaliq):
    run_id = uuid4()
    _seed_companies(engine_no_capitaliq, run_id)

    result = await engine_no_capitaliq._run_capitaliq_enrichment(run_id, {})
    assert result["status"] == "skipped"
    assert result["reason"] == "no_adapter"


async def test_capitaliq_skips_pb_complete(full_engine):
    run_id = uuid4()
    companies = _seed_companies(full_engine, run_id, count=2)
    # Mark first company as PB-complete
    companies[0].pb_status = PitchBookStatus.MATCHED
    companies[0].revenue_estimate = 100.0
    companies[0].ebitda_estimate = 20.0
    companies[0].ownership_tier = "tier_a"

    result = await full_engine._run_capitaliq_enrichment(run_id, {"capitaliq_skip_if_pb_complete": True})
    assert result["skipped"] == 1
    assert result["matched"] == 1
    assert companies[0].ciq_status == CapitalIQStatus.SKIPPED
    assert companies[1].ciq_status == CapitalIQStatus.MATCHED


async def test_capitaliq_no_skip_when_disabled(full_engine):
    run_id = uuid4()
    companies = _seed_companies(full_engine, run_id, count=1)
    companies[0].pb_status = PitchBookStatus.MATCHED
    companies[0].revenue_estimate = 100.0
    companies[0].ebitda_estimate = 20.0
    companies[0].ownership_tier = "tier_a"

    result = await full_engine._run_capitaliq_enrichment(run_id, {"capitaliq_skip_if_pb_complete": False})
    assert result["matched"] == 1
    assert companies[0].ciq_status == CapitalIQStatus.MATCHED


# -- Full pipeline test --

async def test_full_12_stage_pipeline(full_engine):
    """Verify the full 12-stage pipeline completes with all mock providers."""
    run_id = uuid4()
    config = {
        "theme": "test",
        "geography_filter": ["US"],
        "selected_sources": [],
        "revenue_ceiling": 1000.0,
        "cascade_anchor_threshold": 1000.0,
    }
    results = await full_engine.execute_pipeline(run_id, config)

    expected_stages = [
        "name_generation", "name_normalization", "web_enhancement",
        "dispositioning", "bizapi_enrichment", "pitchbook_enrichment",
        "capitaliq_enrichment", "cascade_expansion", "final_dedup",
        "qa_validation", "scoring", "export",
    ]
    for stage in expected_stages:
        assert stage in results, f"Missing stage: {stage}"


# -- Conflict detection test --

async def test_revenue_conflict_generates_review(full_engine):
    run_id = uuid4()
    companies = _seed_companies(full_engine, run_id, count=1)
    # Set existing revenue from BizAPI (much lower than CIQ mock will provide)
    companies[0].revenue_estimate = 20.0  # $20M
    companies[0].revenue_source = "bizapi"
    # Mock CIQ returns $80M → 300% divergence

    result = await full_engine._run_capitaliq_enrichment(run_id, {})
    assert result["matched"] == 1

    # Should have generated conflict review items
    assert len(full_engine.review_items) > 0
    conflict_items = [
        item for item in full_engine.review_items
        if item.reason.value == "conflicting_enrichment"
    ]
    assert len(conflict_items) > 0
