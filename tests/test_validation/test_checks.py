"""Tests for QA validation checks."""

from uuid import uuid4

from app.platform.models.enums import Disposition, OwnershipTier
from app.platform.models.schemas import CompanyRecord
from app.platform.validation.checks import (
    check_cascade_anchor_bleed,
    check_data_completeness,
    check_mega_cap,
    check_unknown_ownership,
)


def _make_company(**kwargs) -> CompanyRecord:
    defaults = {"run_id": uuid4(), "canonical_name": "Test Co"}
    defaults.update(kwargs)
    return CompanyRecord(**defaults)


def test_cascade_anchor_bleed_detected():
    company = _make_company(disposition=Disposition.CASCADE_ANCHOR, eligible_for_outreach=True)
    result = check_cascade_anchor_bleed(company)
    assert not result.passed


def test_cascade_anchor_excluded_from_outreach_passes():
    company = _make_company(disposition=Disposition.CASCADE_ANCHOR, eligible_for_outreach=False)
    result = check_cascade_anchor_bleed(company)
    assert result.passed


def test_unknown_ownership_on_outreach():
    company = _make_company(ownership_tier=OwnershipTier.UNKNOWN, eligible_for_outreach=True)
    result = check_unknown_ownership(company)
    assert not result.passed


def test_known_ownership_passes():
    company = _make_company(ownership_tier=OwnershipTier.TIER_A, eligible_for_outreach=True)
    result = check_unknown_ownership(company)
    assert result.passed


def test_mega_cap_public_fails():
    company = _make_company(is_public=True, revenue_estimate=10000.0, disposition=Disposition.PRIMARY)
    result = check_mega_cap(company)
    assert not result.passed


def test_data_completeness():
    # Sparse company
    sparse = _make_company()
    result = check_data_completeness(sparse)
    # Should fail because most required fields are empty
    assert not result.passed

    # Complete company
    complete = _make_company(
        hq_state="TX",
        subvertical_tags=["Electrical"],
        industry_exposure_descriptor="Data center",
        ownership_tier=OwnershipTier.TIER_A,
        revenue_estimate=200.0,
    )
    result = check_data_completeness(complete)
    assert result.passed
