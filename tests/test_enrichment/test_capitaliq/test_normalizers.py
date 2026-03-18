"""Tests for Capital IQ response normalizers."""

import json
from pathlib import Path

import pytest

from app.miner.enrichment.capitaliq.normalizers import (
    normalize_financials_response,
    normalize_ownership_response,
    normalize_search_response,
)

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "capitaliq"


@pytest.fixture
def search_response():
    with open(FIXTURES / "company_search_response.json") as f:
        return json.load(f)


@pytest.fixture
def financials_response():
    with open(FIXTURES / "company_financials_response.json") as f:
        return json.load(f)


@pytest.fixture
def no_match():
    with open(FIXTURES / "no_match_response.json") as f:
        return json.load(f)


def test_search_normalization(search_response):
    result = normalize_search_response(search_response)
    assert result["entity_id"] == "ciq-12345678"
    assert result["name"] == "Acme Solutions Inc"
    assert result["match_confidence"] == 0.88
    assert result["primary_industry"] == "Application Software"
    assert "Dallas" in result["hq_location"]


def test_financials_normalization(financials_response):
    result = normalize_financials_response(financials_response)
    assert result["entity_id"] == "ciq-12345678"
    assert result["revenue"] == 80.0
    assert result["ebitda"] == 16.0
    assert result["total_debt"] == 45.0
    assert result["net_debt"] == 38.0
    metrics = result["credit_metrics"]
    assert metrics["total_leverage"] == 2.8
    assert metrics["interest_coverage"] == 4.5


def test_ownership_normalization():
    raw = {
        "CompanyId": "ciq-99",
        "OwnershipType": "privately_held",
        "KeyInvestors": [{"Name": "Investor A"}, {"Name": "Investor B"}],
        "MAHistory": [
            {"Date": "2021-03-15", "Type": "Acquisition", "TargetName": "Target Co", "TransactionValue": 25.0}
        ],
    }
    result = normalize_ownership_response(raw)
    assert result["entity_id"] == "ciq-99"
    assert result["ownership_type"] == "privately_held"
    assert result["key_investors"] == ["Investor A", "Investor B"]
    assert len(result["ma_history"]) == 1
    assert result["ma_history"][0]["target"] == "Target Co"


def test_no_match_returns_empty(no_match):
    result = normalize_search_response(no_match)
    assert result == {}


def test_missing_financials_return_none():
    raw = {"CompanyId": "ciq-empty"}
    result = normalize_financials_response(raw)
    assert result["entity_id"] == "ciq-empty"
    assert result["revenue"] is None
    assert result["ebitda"] is None
    assert result["credit_metrics"] is None


def test_missing_ownership_returns_defaults():
    raw = {"CompanyId": "ciq-empty"}
    result = normalize_ownership_response(raw)
    assert result["entity_id"] == "ciq-empty"
    assert result["ownership_type"] == ""
    assert result["key_investors"] == []
    assert result["ma_history"] == []
