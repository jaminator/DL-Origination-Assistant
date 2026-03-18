"""Tests for MockCapitalIQClient."""

import pytest

from app.miner.enrichment.capitaliq.mock_client import MockCapitalIQClient


@pytest.fixture
def client():
    return MockCapitalIQClient()


async def test_search_company(client):
    result = await client.search_company("Acme Inc")
    assert result is not None
    assert result["entity_id"].startswith("ciq-")
    assert result["name"] == "Acme Inc"
    assert result["match_confidence"] == 0.88


async def test_search_company_with_duns(client):
    result = await client.search_company("Acme Inc", duns="08-111-2222")
    assert result is not None
    assert "entity_id" in result


async def test_get_financials(client):
    result = await client.get_financials("ciq-12345678")
    assert result["entity_id"] == "ciq-12345678"
    assert result["revenue"] == 80.0
    assert result["ebitda"] == 16.0
    assert result["total_debt"] == 45.0
    assert result["net_debt"] == 38.0
    assert result["credit_metrics"]["total_leverage"] == 2.8


async def test_get_ownership(client):
    result = await client.get_ownership("ciq-12345678")
    assert result["entity_id"] == "ciq-12345678"
    assert result["ownership_type"] == "founder_owned"
    assert isinstance(result["ma_history"], list)
    assert len(result["ma_history"]) > 0


async def test_is_available(client):
    assert await client.is_available() is True
