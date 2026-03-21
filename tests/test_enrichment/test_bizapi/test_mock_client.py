"""Tests for MockBizAPIClient."""

import pytest

from app.miner.enrichment.bizapi.mock_client import MockBizAPIClient


@pytest.fixture
def client():
    return MockBizAPIClient()


async def test_match_by_duns(client):
    result = await client.match_company("Acme Inc", duns="08-146-3297")
    assert result is not None
    assert result["match_method"] == "duns"
    assert result["match_confidence"] == 1.0
    assert result["duns"] == "08-146-3297"


async def test_match_by_url(client):
    result = await client.match_company("Acme Inc", website="https://acme.com")
    assert result is not None
    assert result["match_method"] == "url"
    assert result["match_confidence"] == 1.0


async def test_match_by_standard(client):
    result = await client.match_company("Acme Inc", state="TX")
    assert result is not None
    assert result["match_method"] == "standard"
    assert result["match_confidence"] == 0.9
    assert result["verified_address"]["state"] == "TX"


async def test_match_by_name_only(client):
    result = await client.match_company("Acme Inc")
    assert result is not None
    assert result["match_method"] == "name"
    assert result["match_confidence"] == 0.8


async def test_match_returns_firmographics(client):
    result = await client.match_company("Acme Inc", state="TX")
    assert result["naics_code"] == "541512"
    assert result["naics_description"] == "Computer Systems Design Services"
    assert result["sic_code"] == "7372"
    assert result["employee_count"] == 320
    assert result["employees_on_site"] == 250
    assert result["sales_volume"] == 75.0
    assert result["year_started"] == 2008


async def test_match_returns_secondary_codes(client):
    result = await client.match_company("Acme Inc")
    assert result["naics_code_2"] == "511210"
    assert result["sic_code_2"] == "7371"


async def test_match_returns_corporate_linkage(client):
    result = await client.match_company("Acme Inc")
    linkage = result["corporate_linkage"]
    assert "global_ult" in linkage
    assert "domestic_ult" in linkage
    assert "hq_parent" in linkage
    assert linkage["hq_parent"]["parent_duns"] == ""


async def test_match_returns_match_grade(client):
    result = await client.match_company("Acme Inc", state="TX")
    assert result["match_grade"] == "AABAAAZ"
    assert result["bemfab"] == "M"
    assert result["location_type"] == "Headquarters"


async def test_is_available(client):
    assert await client.is_available() is True
