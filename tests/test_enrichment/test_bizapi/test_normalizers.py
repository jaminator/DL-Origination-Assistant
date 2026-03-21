"""Tests for BizAPI V2 response normalizers."""

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


@pytest.fixture
def no_match():
    with open(FIXTURES / "no_match_response.json") as f:
        return json.load(f)


def test_standard_match_normalization(standard_match):
    result = normalize_match_response(standard_match)
    assert result is not None
    assert result["duns"] == "08-146-3297"
    assert result["match_method"] == "standard"
    assert result["verified_name"] == "Acme Solutions Inc"
    assert result["naics_code"] == "541512"
    assert result["sic_code"] == "7372"
    assert result["year_started"] == 2008
    assert result["employee_count"] == 320
    assert result["employees_on_site"] == 250
    assert result["sales_volume"] == 75.0  # $75M from "75,000,000"
    assert result["match_confidence"] == 0.9  # Confidence Code 9 / 10


def test_url_match_normalization(url_match):
    result = normalize_match_response(url_match)
    assert result is not None
    assert result["match_method"] == "url"
    assert result["match_confidence"] == 1.0  # Confidence Code 10
    assert result["website"] == "www.acmesolutions.com"


def test_duns_match_normalization(duns_match):
    result = normalize_match_response(duns_match)
    assert result is not None
    assert result["match_method"] == "duns"
    assert result["match_confidence"] == 1.0  # Confidence Code 10
    assert result["duns"] == "08-146-3297"


def test_no_match_returns_none(no_match):
    result = normalize_match_response(no_match)
    assert result is None


def test_address_extraction(standard_match):
    result = normalize_match_response(standard_match)
    addr = result["verified_address"]
    assert addr["street"] == "100 Commerce Blvd"
    assert addr["city"] == "Dallas"
    assert addr["state"] == "TX"
    assert addr["zip"] == "75201-0100"
    assert addr["country"] == "USA"


def test_corporate_linkage_extraction(standard_match):
    result = normalize_match_response(standard_match)
    linkage = result["corporate_linkage"]
    assert linkage["subsidiary_indicator"] == "not a subsidiary site"
    assert linkage["global_ult"]["indicator"] == "Y"
    assert linkage["global_ult"]["duns"] == "08-146-3297"
    assert linkage["hq_parent"]["parent_duns"] == ""
    assert linkage["hierarchy_code"] == "01"
    assert linkage["family_member_count"] == 1


def test_secondary_naics_sic(standard_match):
    result = normalize_match_response(standard_match)
    assert result["naics_code_2"] == "511210"
    assert result["naics_description_2"] == "Software Publishers"
    assert result["sic_code_2"] == "7371"
    assert result["sic_description_2"] == "Computer Services"


def test_match_grade_and_bemfab(standard_match):
    result = normalize_match_response(standard_match)
    assert result["match_grade"] == "AABAAAZ"
    assert result["bemfab"] == "M"


def test_location_type(standard_match):
    result = normalize_match_response(standard_match)
    assert result["location_type"] == "Headquarters"


def test_sales_volume_parsing():
    raw = {
        "Matching Data": {"DUNS #": "12-345-6789", "Confidence Code": 8},
        "Appended Data": {
            "Company Name": "Test",
            "Sales Volume in US$": "150,000,000",
        },
    }
    result = normalize_match_response(raw)
    assert result["sales_volume"] == 150.0  # $150M


def test_confidence_code_conversion():
    raw = {
        "Matching Data": {"DUNS #": "12-345-6789", "Confidence Code": 7},
        "Appended Data": {"Company Name": "Test"},
    }
    result = normalize_match_response(raw)
    assert result["match_confidence"] == 0.7
