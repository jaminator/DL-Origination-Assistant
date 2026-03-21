"""Tests for Capital IQ SPQL response normalizers."""

import json
from pathlib import Path

import pytest

from app.miner.enrichment.capitaliq.normalizers import (
    normalize_financials_response,
    normalize_ownership_response,
    normalize_profile_response,
    normalize_search_response,
    normalize_spql_response,
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


def test_spql_response_parsing(search_response):
    values = normalize_spql_response(search_response)
    assert values["IQ_COMPANY_NAME"] == "Acme Solutions Inc"
    assert values["IQ_PRIMARY_INDUSTRY"] == "Application Software"
    assert values["IQ_COMPANY_CITY"] == "Dallas"
    assert values["IQ_COMPANY_STATE"] == "TX"


def test_spql_data_unavailable_returns_none():
    raw = {
        "GDSSDKResponse": [
            {
                "Identifier": "IQ999",
                "Mnemonic": "IQ_TOTAL_REV",
                "Rows": [{"Row": ["Data Unavailable"]}],
            }
        ]
    }
    values = normalize_spql_response(raw)
    assert values["IQ_TOTAL_REV"] is None


def test_search_normalization_spql(search_response):
    result = normalize_search_response(search_response)
    assert result["entity_id"] == "12345678"
    assert result["name"] == "Acme Solutions Inc"
    assert result["match_confidence"] == 1.0  # SPQL uses exact ID matching
    assert result["primary_industry"] == "Application Software"
    assert "Dallas" in result["hq_location"]


def test_financials_normalization_spql(financials_response):
    result = normalize_financials_response(financials_response)
    assert result["entity_id"] == "12345678"
    assert result["revenue"] == 80.0
    assert result["ebitda"] == 16.0
    assert result["total_debt"] == 45.0
    assert result["net_debt"] == 38.0
    metrics = result["credit_metrics"]
    assert metrics["total_leverage"] == 2.8
    assert metrics["interest_coverage"] == 4.5


def test_ownership_normalization_spql():
    raw = {
        "GDSSDKResponse": [
            {
                "Identifier": "IQ99",
                "Mnemonic": "IQ_OWNERSHIP_STATUS",
                "Rows": [{"Row": ["privately_held"]}],
            },
            {
                "Identifier": "IQ99",
                "Mnemonic": "IQ_KEY_INVESTORS",
                "Rows": [{"Row": ["Investor A; Investor B"]}],
            },
        ]
    }
    result = normalize_ownership_response(raw)
    assert result["entity_id"] == "99"
    assert result["ownership_type"] == "privately_held"
    assert result["key_investors"] == ["Investor A", "Investor B"]
    assert result["ma_history"] == []


def test_profile_normalization_spql():
    raw = {
        "GDSSDKResponse": [
            {
                "Identifier": "IQ12345",
                "Mnemonic": "IQ_GICS_CODE",
                "Rows": [{"Row": ["45101010"]}],
            },
            {
                "Identifier": "IQ12345",
                "Mnemonic": "IQ_PRIMARY_SIC_CODE",
                "Rows": [{"Row": ["7372"]}],
            },
            {
                "Identifier": "IQ12345",
                "Mnemonic": "IQ_COMPANY_STATUS",
                "Rows": [{"Row": ["Operating"]}],
            },
            {
                "Identifier": "IQ12345",
                "Mnemonic": "IQ_INDUSTRY_SECTOR",
                "Rows": [{"Row": ["Information Technology"]}],
            },
        ]
    }
    result = normalize_profile_response(raw)
    assert result["entity_id"] == "12345"
    assert result["gics_code"] == "45101010"
    assert result["sic_code"] == "7372"
    assert result["company_status"] == "Operating"
    assert result["industry_sector"] == "Information Technology"


def test_ownership_normalization_legacy():
    """Legacy REST format still works."""
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
    assert result == {} or not result.get("entity_id")


def test_missing_financials_return_none_spql():
    raw = {
        "GDSSDKResponse": [
            {
                "Identifier": "IQempty",
                "Mnemonic": "IQ_TOTAL_REV",
                "Rows": [{"Row": ["Data Unavailable"]}],
            },
            {
                "Identifier": "IQempty",
                "Mnemonic": "IQ_EBITDA",
                "Rows": [],
            },
        ]
    }
    result = normalize_financials_response(raw)
    assert result["revenue"] is None
    assert result["ebitda"] is None


def test_missing_ownership_returns_defaults_spql():
    raw = {
        "GDSSDKResponse": [
            {
                "Identifier": "IQempty",
                "Mnemonic": "IQ_OWNERSHIP_STATUS",
                "Rows": [{"Row": ["Data Unavailable"]}],
            },
        ]
    }
    result = normalize_ownership_response(raw)
    assert result["ownership_type"] is None or result["ownership_type"] == ""
    assert result["key_investors"] == []
