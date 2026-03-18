"""Tests for BizAPI response normalizers."""

import json
from pathlib import Path

import pytest

from app.miner.enrichment.bizapi.normalizers import normalize_match_response

FIXTURES = Path(__file__).resolve().parent.parent.parent / "fixtures" / "bizapi"


@pytest.fixture
def standard_match():
    with open(FIXTURES / "standard_match_response.json") as f:
        return json.load(f)


@pytest.fixture
def url_match():
    with open(FIXTURES / "url_match_response.json") as f:
        return json.load(f)


@pytest.fixture
def duns_match():
    with open(FIXTURES / "duns_match_response.json") as f:
        return json.load(f)


def test_standard_match_normalization(standard_match):
    standard_match["match_method"] = "standard"
    result = normalize_match_response(standard_match)
    assert result["duns"] == "08-146-3297"
    assert result["verified_name"] == "Acme Solutions Inc"
    assert result["naics_code"] == "541512"
    assert result["sic_code"] == "7372"
    assert result["year_started"] == 2008
    assert result["employee_count"] == 250
    assert result["sales_volume"] == 75.0  # 75M from 75000000
    assert result["match_confidence"] == 0.85  # MatchScore 85 / 100


def test_url_match_normalization(url_match):
    url_match["match_method"] = "url"
    result = normalize_match_response(url_match)
    assert result["match_confidence"] == 0.92  # MatchScore 92 / 100
    assert result["website"] == "https://www.acmesolutions.com"


def test_duns_match_normalization(duns_match):
    duns_match["match_method"] = "duns"
    result = normalize_match_response(duns_match)
    assert result["match_confidence"] == 0.98  # MatchScore 98 / 100
    assert result["duns"] == "08-146-3297"


def test_address_extraction(standard_match):
    standard_match["match_method"] = "standard"
    result = normalize_match_response(standard_match)
    addr = result["verified_address"]
    assert addr["street"] == "100 Commerce Blvd"
    assert addr["city"] == "Dallas"
    assert addr["state"] == "TX"
    assert addr["zip"] == "75201"
    assert addr["country"] == "US"


def test_corporate_linkage_extraction(standard_match):
    standard_match["match_method"] = "standard"
    result = normalize_match_response(standard_match)
    linkage = result["corporate_linkage"]
    assert linkage["parent_duns"] is None
    assert linkage["parent_name"] is None
    assert linkage["subsidiary_count"] == 0


def test_missing_fields_return_none():
    raw = {"match_method": "name", "CompanyName": "Unknown Co"}
    result = normalize_match_response(raw)
    assert result["verified_name"] == "Unknown Co"
    assert result["naics_code"] == ""
    assert result["employee_count"] is None
    assert result["sales_volume"] is None
    assert result["year_started"] is None


def test_sales_volume_normalization_large_value():
    raw = {"match_method": "standard", "SalesVolume": 150000000}
    result = normalize_match_response(raw)
    assert result["sales_volume"] == 150.0  # 150M


def test_sales_volume_normalization_already_millions():
    raw = {"match_method": "standard", "SalesVolume": 75.5}
    result = normalize_match_response(raw)
    assert result["sales_volume"] == 75.5  # already in millions
