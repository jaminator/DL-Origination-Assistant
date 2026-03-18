"""Tests for CapitalIQRESTClient — auth, retry, search, financials."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.miner.enrichment.capitaliq.rest_client import CapitalIQRESTClient


@pytest.fixture
def client():
    return CapitalIQRESTClient(
        base_url="https://test.capitaliq.com/v1",
        api_key="test-key-123",
        timeout=5.0,
        max_retries=2,
    )


def test_auth_headers(client):
    headers = client._auth_headers()
    assert headers["X-API-Key"] == "test-key-123"
    assert headers["Accept"] == "application/json"


async def test_search_company_returns_match(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Results": [
            {
                "CompanyId": "ciq-test-001",
                "CompanyName": "Test Corp",
                "PrimaryIndustry": "Software",
                "MatchScore": 90,
            }
        ]
    }
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.search_company("Test Corp")
        assert result is not None
        assert result["entity_id"] == "ciq-test-001"
        assert result["match_confidence"] == 0.9


async def test_search_company_no_results(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"Results": []}
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.search_company("Nonexistent Corp")
        assert result is None


async def test_retry_on_500(client):
    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=fail_response)
    )

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = {"CompanyId": "ciq-retry", "TotalRevenue": 100.0}
    ok_response.raise_for_status = MagicMock()
    ok_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[fail_response, ok_response])
        mock_get.return_value = mock_client
        with patch("app.miner.enrichment.capitaliq.rest_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_financials("ciq-retry")
            assert result["revenue"] == 100.0


async def test_401_raises_immediately(client):
    fail_response = MagicMock()
    fail_response.status_code = 401
    fail_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("401", request=MagicMock(), response=fail_response)
    )

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=fail_response)
        mock_get.return_value = mock_client
        with pytest.raises(httpx.HTTPStatusError):
            await client.get_financials("ciq-auth-fail")


async def test_search_with_duns(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Results": [{"CompanyId": "ciq-duns-001", "CompanyName": "DUNS Corp", "MatchScore": 95}]
    }
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.search_company("DUNS Corp", duns="08-111-2222")
        assert result is not None
        # Verify DUNS was passed in request body
        call_args = mock_client.request.call_args
        assert call_args.kwargs.get("json", {}).get("DUNS") == "08-111-2222"


def test_is_available_true(client):
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(client.is_available()) is True


def test_is_available_false():
    c = CapitalIQRESTClient(base_url="https://test.com", api_key="")
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(c.is_available()) is False
