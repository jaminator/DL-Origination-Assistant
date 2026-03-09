"""Tests for company-level scoring."""

from uuid import uuid4

from app.platform.models.enums import OwnershipTier
from app.platform.models.schemas import CompanyRecord
from app.platform.scoring.company_scorer import score_company


def _make_company(**kwargs) -> CompanyRecord:
    defaults = {
        "run_id": uuid4(),
        "canonical_name": "Test Company",
    }
    defaults.update(kwargs)
    return CompanyRecord(**defaults)


def test_basic_scoring():
    company = _make_company(
        revenue_estimate=200.0,
        ownership_tier=OwnershipTier.TIER_A,
        industry_exposure_intensity="high",
    )
    total, components = score_company(company)
    assert 0 <= total <= 100
    assert "revenue_scale" in components
    assert "ownership_tier" in components


def test_tier_a_gets_bonus():
    c_a = _make_company(ownership_tier=OwnershipTier.TIER_A, revenue_estimate=200.0)
    c_c = _make_company(ownership_tier=OwnershipTier.TIER_C, revenue_estimate=200.0)
    total_a, _ = score_company(c_a)
    total_c, _ = score_company(c_c)
    assert total_a > total_c


def test_tier_b_between_a_and_c():
    c_a = _make_company(ownership_tier=OwnershipTier.TIER_A, revenue_estimate=200.0)
    c_b = _make_company(ownership_tier=OwnershipTier.TIER_B, revenue_estimate=200.0)
    c_c = _make_company(ownership_tier=OwnershipTier.TIER_C, revenue_estimate=200.0)
    total_a, _ = score_company(c_a)
    total_b, _ = score_company(c_b)
    total_c, _ = score_company(c_c)
    assert total_a > total_b > total_c


def test_missing_data_does_not_max_score():
    """Missing data should NOT silently award maximum points."""
    complete = _make_company(
        revenue_estimate=200.0,
        ebitda_estimate=30.0,
        recurring_revenue_estimate=100.0,
        industry_exposure_intensity="high",
        ownership_tier=OwnershipTier.TIER_A,
        hq_state="TX",
        website="https://example.com",
    )
    incomplete = _make_company(canonical_name="Sparse Company")

    total_complete, _ = score_company(complete)
    total_incomplete, _ = score_company(incomplete)
    assert total_complete > total_incomplete


def test_score_bounds():
    company = _make_company(revenue_estimate=200.0)
    total, _ = score_company(company)
    assert 0 <= total <= 100
