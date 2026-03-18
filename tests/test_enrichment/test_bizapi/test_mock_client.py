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
    assert result["match_confidence"] == 0.98
    assert result["duns"] == "08-146-3297"


async def test_match_by_url(client):
    result = await client.match_company("Acme Inc", website="https://acme.com")
    assert result is not None
    assert result["match_method"] == "url"
    assert result["match_confidence"] == 0.92


async def test_match_by_standard(client):
    result = await client.match_company("Acme Inc", state="TX")
    assert result is not None
    assert result["match_method"] == "standard"
    assert result["match_confidence"] == 0.85
    assert result["verified_address"]["state"] == "TX"


async def test_match_by_name_only(client):
    result = await client.match_company("Acme Inc")
    assert result is not None
    assert result["match_method"] == "name"
    assert result["match_confidence"] == 0.70


async def test_match_returns_firmographics(client):
    result = await client.match_company("Acme Inc", state="TX")
    assert result["naics_code"] == "541512"
    assert result["naics_description"] == "Computer Systems Design Services"
    assert result["sic_code"] == "7372"
    assert result["employee_count"] == 250
    assert result["sales_volume"] == 75.0
    assert result["year_started"] == 2008


async def test_match_returns_corporate_linkage(client):
    result = await client.match_company("Acme Inc")
    linkage = result["corporate_linkage"]
    assert "parent_duns" in linkage
    assert "subsidiary_count" in linkage


async def test_is_available(client):
    assert await client.is_available() is True
