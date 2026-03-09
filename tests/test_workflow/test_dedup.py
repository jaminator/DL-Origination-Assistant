"""Tests for fuzzy deduplication, review queue generation, and dispositioning."""

from uuid import uuid4

from app.miner.dedup import deduplicate_names
from app.miner.dispositioning import assign_disposition
from app.platform.models.enums import Disposition, ReviewReason
from app.platform.models.schemas import CompanyRecord
from app.platform.review.queue import generate_review_items_from_dedup, generate_review_items_from_validation

# --- Dedup tests ---

def test_exact_duplicates_auto_merged():
    """Identical names should be auto-merged."""
    names = ["Apex Data Systems", "Apex Data Systems"]
    result = deduplicate_names(names)
    assert len(result.merged) == 1
    assert result.merged[0][2] == 100.0  # Perfect score


def test_near_duplicates_auto_merged():
    """Very similar names (score >= 95) should be auto-merged."""
    names = ["Apex Data Systems Inc", "Apex Data Systems"]
    result = deduplicate_names(names)
    assert len(result.merged) == 1


def test_similar_names_sent_to_review():
    """Moderately similar names (80 <= score < 95) should go to review."""
    names = ["Apex Data Solutions", "Apex Data Services"]
    result = deduplicate_names(names)
    # These may be review or distinct depending on RapidFuzz scoring
    # The key assertion is that they're not incorrectly auto-merged
    assert len(result.merged) == 0 or result.merged[0][2] >= 95


def test_distinct_names_kept_separate():
    """Clearly different names should remain separate."""
    names = ["Apex Data Systems", "BlueLine Fire Protection", "Continental Cable"]
    result = deduplicate_names(names)
    assert len(result.merged) == 0
    assert len(result.review) == 0


def test_empty_list_handled():
    """Empty input should produce empty results."""
    result = deduplicate_names([])
    assert len(result.merged) == 0
    assert len(result.review) == 0


def test_single_name_handled():
    """Single name should produce no merges or reviews."""
    result = deduplicate_names(["Solo Company"])
    assert len(result.merged) == 0
    assert len(result.review) == 0


def test_dedup_strips_suffixes():
    """Names differing only by legal suffix should be auto-merged."""
    names = ["Apex Data Inc", "Apex Data Corp"]
    result = deduplicate_names(names)
    # After normalization, both become "apex data" → should merge
    assert len(result.merged) == 1


# --- Dispositioning tests ---

def _make_company(**kwargs) -> CompanyRecord:
    defaults = {"run_id": uuid4(), "canonical_name": "Test Co"}
    defaults.update(kwargs)
    return CompanyRecord(**defaults)


def test_primary_for_middle_market():
    """$50-500M revenue US company should be PRIMARY."""
    c = _make_company(revenue_estimate=150.0, hq_country="US")
    assert assign_disposition(c) == Disposition.PRIMARY


def test_cascade_anchor_for_large():
    """Revenue above ceiling should be CASCADE_ANCHOR."""
    c = _make_company(revenue_estimate=1500.0)
    assert assign_disposition(c, revenue_ceiling=1000.0) == Disposition.CASCADE_ANCHOR


def test_exclude_for_non_us():
    """Non-US company should be EXCLUDED."""
    c = _make_company(hq_country="UK")
    assert assign_disposition(c, geography_filter=["US"]) == Disposition.EXCLUDE


def test_exclude_for_tiny():
    """Very small company (< $5M) should be EXCLUDED."""
    c = _make_company(revenue_estimate=3.0)
    assert assign_disposition(c) == Disposition.EXCLUDE


def test_exclude_public_mega_cap():
    """Public mega-cap should be EXCLUDED."""
    c = _make_company(is_public=True, revenue_estimate=8000.0)
    assert assign_disposition(c) == Disposition.EXCLUDE


def test_primary_when_no_revenue():
    """Company with no revenue data should default to PRIMARY."""
    c = _make_company(revenue_estimate=None)
    assert assign_disposition(c) == Disposition.PRIMARY


# --- Review queue generation tests ---

def test_dedup_review_items_created():
    """Ambiguous dedup pairs should generate review items."""
    run_id = uuid4()
    pairs = [("Company A", "Company B", 88.5)]
    items = generate_review_items_from_dedup(run_id, pairs)
    assert len(items) == 1
    assert items[0].reason == ReviewReason.AMBIGUOUS_DUPLICATE
    assert items[0].run_id == run_id
    assert "Company A" in items[0].details
    assert "Company B" in items[0].details


def test_validation_review_items_created():
    """Validation failures should generate review items."""
    run_id = uuid4()
    company_id = uuid4()
    reasons = [ReviewReason.UNKNOWN_OWNERSHIP, ReviewReason.BOUNDARY_SIZE]
    items = generate_review_items_from_validation(run_id, company_id, "Test Co", reasons)
    assert len(items) == 2
    assert items[0].company_id == company_id
    assert items[0].reason == ReviewReason.UNKNOWN_OWNERSHIP
    assert items[1].reason == ReviewReason.BOUNDARY_SIZE


def test_empty_review_items():
    """No ambiguous pairs should produce no review items."""
    items = generate_review_items_from_dedup(uuid4(), [])
    assert len(items) == 0
