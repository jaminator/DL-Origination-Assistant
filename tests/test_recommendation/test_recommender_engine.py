"""Tests for the RecommenderEngine — sub-vertical and source recommendation."""

import json
from pathlib import Path
from uuid import uuid4

import pytest

from app.ai.llm_service import MockLLMService
from app.platform.models.enums import RecommendationStatus, SourceAccessType, SourcePriority
from app.platform.models.run import RunConfig
from app.recommender.engine import RecommenderEngine

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "llm_responses"


@pytest.fixture
def run_id():
    return uuid4()


@pytest.fixture
def run_config():
    return RunConfig(
        theme="data center capex secular growth",
        geography_filter=["US"],
        revenue_ceiling=1000.0,
    )


@pytest.fixture
def llm_with_fixtures():
    """MockLLMService loaded with realistic fixture data."""
    llm = MockLLMService()
    theme_fixture = json.loads((FIXTURES_DIR / "theme_analysis_data_center.json").read_text())
    source_fixture = json.loads((FIXTURES_DIR / "source_discovery_data_center.json").read_text())
    llm.register_fixture("investment theme", theme_fixture)
    llm.register_fixture("confirmed sub-verticals", source_fixture)
    return llm


@pytest.fixture
def engine(llm_with_fixtures):
    return RecommenderEngine(llm_with_fixtures)


# --- Sub-vertical recommendation tests ---

@pytest.mark.asyncio
async def test_recommend_subverticals_returns_results(engine, run_id, run_config):
    """Should return a list of ThemeRecommendation objects."""
    recs = await engine.recommend_subverticals(run_id, run_config)
    assert len(recs) == 2
    assert recs[0].subvertical_name == "Electrical Contractors (Data Center / Mission-Critical)"
    assert recs[1].subvertical_name == "Mechanical / HVAC Contractors (Data Center Cooling)"


@pytest.mark.asyncio
async def test_subverticals_sorted_by_score(engine, run_id, run_config):
    """Results should be sorted by total_recommendation_score descending."""
    recs = await engine.recommend_subverticals(run_id, run_config)
    scores = [r.total_recommendation_score for r in recs]
    assert scores == sorted(scores, reverse=True)


@pytest.mark.asyncio
async def test_subvertical_scores_computed(engine, run_id, run_config):
    """Total score should be average of thematic and lender fit scores."""
    recs = await engine.recommend_subverticals(run_id, run_config)
    for r in recs:
        expected = (r.thematic_fit_score + r.lender_fit_score) / 2.0
        assert r.total_recommendation_score == expected


@pytest.mark.asyncio
async def test_subvertical_status_parsed(engine, run_id, run_config):
    """Recommendation status should be parsed from LLM response."""
    recs = await engine.recommend_subverticals(run_id, run_config)
    assert recs[0].recommendation_status == RecommendationStatus.STRONG_FIT


@pytest.mark.asyncio
async def test_subvertical_provenance_tracked(engine, run_id, run_config):
    """AI provenance should be set on each recommendation."""
    recs = await engine.recommend_subverticals(run_id, run_config)
    for r in recs:
        assert r.ai_provenance.ai_generated is True
        assert r.ai_provenance.model_source == "MockLLMService"
        assert r.ai_provenance.prompt_template_id == "theme_analysis"
        assert r.ai_provenance.acceptance_status == "pending"


@pytest.mark.asyncio
async def test_subvertical_borrower_criteria_populated(engine, run_id, run_config):
    """All 7 borrower criteria profiles should be populated."""
    recs = await engine.recommend_subverticals(run_id, run_config)
    r = recs[0]
    assert r.demand_profile != ""
    assert r.cyclicality_profile != ""
    assert r.fragmentation_profile != ""
    assert r.recurring_revenue_profile != ""
    assert r.margin_profile != ""
    assert r.capital_intensity_profile != ""
    assert r.concentration_risk_profile != ""


@pytest.mark.asyncio
async def test_subvertical_run_id_set(engine, run_id, run_config):
    """Each recommendation should reference the originating run."""
    recs = await engine.recommend_subverticals(run_id, run_config)
    for r in recs:
        assert r.run_id == run_id


# --- Source recommendation tests ---

@pytest.mark.asyncio
async def test_recommend_sources_returns_results(engine, run_id):
    """Should return SourceRecommendation objects for sub-verticals."""
    subverticals = ["Electrical Contractors (Data Center / Mission-Critical)"]
    sources = await engine.recommend_sources(run_id, subverticals)
    # Fixture has 2 sources + 2 NAICS → 4 total
    assert len(sources) == 4


@pytest.mark.asyncio
async def test_source_types_populated(engine, run_id):
    """Source type should be populated from LLM response."""
    subverticals = ["Electrical Contractors"]
    sources = await engine.recommend_sources(run_id, subverticals)
    types = {s.source_type for s in sources}
    assert "trade_journal" in types or "naics_source" in types


@pytest.mark.asyncio
async def test_source_provenance_tracked(engine, run_id):
    """AI provenance should be set on each source recommendation."""
    subverticals = ["Electrical Contractors"]
    sources = await engine.recommend_sources(run_id, subverticals)
    for s in sources:
        assert s.ai_provenance.ai_generated is True
        assert s.ai_provenance.prompt_template_id == "source_discovery"


@pytest.mark.asyncio
async def test_naics_codes_as_sources(engine, run_id):
    """NAICS codes should be converted to SourceRecommendation objects."""
    subverticals = ["Electrical Contractors"]
    sources = await engine.recommend_sources(run_id, subverticals)
    naics_sources = [s for s in sources if s.source_type == "naics_source"]
    assert len(naics_sources) == 2
    assert any("238210" in s.source_name for s in naics_sources)


# --- Edge cases ---

@pytest.mark.asyncio
async def test_default_mock_response():
    """MockLLMService without fixtures should return default response."""
    llm = MockLLMService()
    engine = RecommenderEngine(llm)
    run_id = uuid4()
    config = RunConfig(theme="generic theme")
    recs = await engine.recommend_subverticals(run_id, config)
    assert len(recs) >= 1
    assert recs[0].subvertical_name == "Mock Sub-vertical"
