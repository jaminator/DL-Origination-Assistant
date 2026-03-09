"""Tests for miner enrichment modules: size estimator, exposure classifier, web enricher."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from app.miner.enrichment.size_estimator import (
    classify_revenue_band,
    estimate_employee_band,
    estimate_revenue_from_employees,
    extract_revenue_from_text,
)
from app.miner.enrichment.exposure_classifier import (
    classify_exposure_intensity,
    compute_exposure_score,
)


# --- Size estimator tests ---


class TestSizeEstimator:

    def test_revenue_from_employees_default(self):
        """Default multiplier: 250K/employee."""
        revenue, band = estimate_revenue_from_employees(400)
        assert revenue == 100.0  # 400 * 250K = $100M
        assert band == "$100M-$250M"  # 100.0 falls in [100, 250)

    def test_revenue_from_employees_technology(self):
        """Technology industry: 350K/employee."""
        revenue, band = estimate_revenue_from_employees(200, industry="technology")
        assert revenue == 70.0  # 200 * 350K = $70M
        assert band == "$50M-$100M"

    def test_revenue_from_employees_zero(self):
        """Zero employees returns None."""
        revenue, band = estimate_revenue_from_employees(0)
        assert revenue is None
        assert band == ""

    def test_revenue_from_employees_negative(self):
        revenue, band = estimate_revenue_from_employees(-10)
        assert revenue is None

    def test_classify_revenue_band_boundaries(self):
        assert classify_revenue_band(0) == "Under $10M"
        assert classify_revenue_band(9.9) == "Under $10M"
        assert classify_revenue_band(10) == "$10M-$25M"
        assert classify_revenue_band(100) == "$100M-$250M"
        assert classify_revenue_band(1000) == "$1B-$5B"
        assert classify_revenue_band(10000) == "$5B+"
        assert classify_revenue_band(None) == ""

    def test_extract_revenue_dollar_million(self):
        assert extract_revenue_from_text("Revenue of $85 million") == 85.0

    def test_extract_revenue_dollar_billion(self):
        assert extract_revenue_from_text("$2.5 billion in revenue") == 2500.0

    def test_extract_revenue_mm_format(self):
        assert extract_revenue_from_text("Annual revenue: $150MM") == 150.0

    def test_extract_revenue_no_signal(self):
        assert extract_revenue_from_text("Great company with good products") is None

    def test_extract_revenue_empty(self):
        assert extract_revenue_from_text("") is None
        assert extract_revenue_from_text(None) is None

    def test_employee_band_classification(self):
        assert estimate_employee_band(None) == ""
        assert estimate_employee_band(0) == ""
        assert estimate_employee_band(30) == "Under 50"
        assert estimate_employee_band(100) == "50-200"
        assert estimate_employee_band(350) == "200-500"
        assert estimate_employee_band(800) == "500-1K"
        assert estimate_employee_band(2000) == "1K-5K"
        assert estimate_employee_band(10000) == "5K+"


# --- Exposure classifier tests ---


class TestExposureClassifier:

    def test_revenue_concentration_high(self):
        assert classify_exposure_intensity(revenue_from_sector=0.85) == "high"

    def test_revenue_concentration_medium(self):
        assert classify_exposure_intensity(revenue_from_sector=0.5) == "medium"

    def test_revenue_concentration_low(self):
        assert classify_exposure_intensity(revenue_from_sector=0.1) == "low"

    def test_keyword_high(self):
        result = classify_exposure_intensity(
            description="Primary and dedicated provider of data center electrical systems",
        )
        assert result == "high"

    def test_keyword_low(self):
        result = classify_exposure_intensity(
            description="A diversified conglomerate with minor exposure to tech",
        )
        assert result == "low"

    def test_keyword_medium(self):
        result = classify_exposure_intensity(
            description="A growing division focused on significant infrastructure",
        )
        assert result == "medium"

    def test_unknown_no_signals(self):
        assert classify_exposure_intensity() == "unknown"

    def test_subvertical_tags_default_medium(self):
        """With subvertical tags but no keywords, defaults to medium."""
        result = classify_exposure_intensity(
            description="A company",
            subvertical_tags=["Electrical Contractors"],
        )
        assert result == "medium"

    def test_compute_exposure_score(self):
        assert compute_exposure_score("high") == 1.0
        assert compute_exposure_score("medium") == 0.6
        assert compute_exposure_score("low") == 0.3
        assert compute_exposure_score("unknown") == 0.0
        assert compute_exposure_score("bogus") == 0.0


# --- Web enricher tests ---


class TestWebEnricher:

    @pytest.fixture
    def company(self):
        from app.platform.models.schemas import CompanyRecord
        return CompanyRecord(
            id=uuid4(),
            run_id=uuid4(),
            canonical_name="Test Corp",
            subvertical_tags=["Electrical"],
            source_tags=["mock"],
        )

    @pytest.fixture
    def mock_llm(self):
        llm = AsyncMock()
        llm.complete_json = AsyncMock(return_value={
            "hq_city": "Dallas",
            "hq_state": "TX",
            "hq_country": "US",
            "revenue_estimate": 85.0,
            "ownership_type": "founder_owned",
            "confidence": 0.72,
            "is_public": False,
            "employee_count": 450,
        })
        llm.__class__.__name__ = "MockLLMService"
        return llm

    @pytest.mark.asyncio
    async def test_enrich_company_applies_location(self, company, mock_llm):
        from app.miner.enrichment.web_enricher import enrich_company
        result = await enrich_company(company, mock_llm)
        assert result is True
        assert company.hq_city == "Dallas"
        assert company.hq_state == "TX"
        assert company.hq_country == "US"

    @pytest.mark.asyncio
    async def test_enrich_company_applies_revenue(self, company, mock_llm):
        from app.miner.enrichment.web_enricher import enrich_company
        await enrich_company(company, mock_llm)
        assert company.revenue_estimate == 85.0
        assert company.revenue_source == "llm_web_enrichment"

    @pytest.mark.asyncio
    async def test_enrich_company_applies_ownership(self, company, mock_llm):
        from app.miner.enrichment.web_enricher import enrich_company
        from app.platform.models.enums import OwnershipTier
        await enrich_company(company, mock_llm)
        assert company.ownership_tier == OwnershipTier.TIER_A

    @pytest.mark.asyncio
    async def test_enrich_company_tracks_provenance(self, company, mock_llm):
        from app.miner.enrichment.web_enricher import enrich_company
        await enrich_company(company, mock_llm)
        prov = company.ai_provenance.get("web_enrichment")
        assert prov is not None
        assert prov.ai_generated is True
        assert prov.confidence_score == 0.72

    @pytest.mark.asyncio
    async def test_enrich_company_failure(self, company):
        """LLM failure returns False."""
        from app.miner.enrichment.web_enricher import enrich_company
        bad_llm = AsyncMock()
        bad_llm.complete_json = AsyncMock(side_effect=Exception("LLM down"))
        result = await enrich_company(company, bad_llm)
        assert result is False

    def test_map_ownership_tiers(self):
        from app.miner.enrichment.web_enricher import map_ownership_to_tier
        from app.platform.models.enums import OwnershipTier
        assert map_ownership_to_tier("founder_owned") == OwnershipTier.TIER_A
        assert map_ownership_to_tier("family_owned") == OwnershipTier.TIER_A
        assert map_ownership_to_tier("vc_backed") == OwnershipTier.TIER_B
        assert map_ownership_to_tier("pe_backed") == OwnershipTier.TIER_C
        assert map_ownership_to_tier("unknown_type") == OwnershipTier.UNKNOWN
