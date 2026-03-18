"""Tests for BizAPIRESTClient — auth, retry, rate limiting, match selection."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.miner.enrichment.bizapi.rest_client import BizAPIRESTClient


@pytest.fixture
def client():
    return BizAPIRESTClient(
        base_url="https://test.bizapi.com/v1",
        username="testuser",
        password="testpass",
        timeout=5.0,
        max_retries=2,
        rate_limit_rps=100.0,  # high limit so tests don't slow down
    )


def test_auth_headers(client):
    headers = client._auth_headers()
    assert "Authorization" in headers
    assert headers["Authorization"].startswith("Basic ")
    assert headers["Accept"] == "application/json"


def test_match_method_selection_duns(client):
    methods = client._select_match_method("Acme", duns="123")
    assert methods[0][0] == "duns"


def test_match_method_selection_url(client):
    methods = client._select_match_method("Acme", website="https://acme.com")
    assert methods[0][0] == "url"


def test_match_method_selection_standard(client):
    methods = client._select_match_method("Acme", state="TX")
    assert methods[0][0] == "standard"


def test_match_method_selection_name_only(client):
    methods = client._select_match_method("Acme")
    assert methods[0][0] == "name"
    assert methods[1][0] == "loose"


def test_match_method_priority_order(client):
    methods = client._select_match_method(
        "Acme", duns="123", website="https://acme.com", state="TX", phone="555-1234",
    )
    method_names = [m[0] for m in methods]
    assert method_names == ["duns", "url", "standard", "name", "phone", "loose"]


async def test_match_company_returns_none_on_no_match(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"MatchFound": False}
    mock_response.raise_for_status = MagicMock()

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.match_company("Nonexistent Corp")
        assert result is None


async def test_match_company_returns_match(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "MatchFound": True,
        "DUNS": "08-111-2222",
        "CompanyName": "Acme Corp",
        "MatchScore": 85,
        "NAICSCode": "541512",
        "EmployeesTotal": 200,
        "SalesVolume": 50000000,
    }
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.match_company("Acme Corp", state="TX")
        assert result is not None
        assert result["duns"] == "08-111-2222"
        assert result["match_confidence"] == 0.85


async def test_retry_on_503(client):
    fail_response = MagicMock()
    fail_response.status_code = 503
    fail_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=fail_response)
    )

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = {
        "MatchFound": True,
        "DUNS": "08-333-4444",
        "CompanyName": "Retry Corp",
        "MatchScore": 90,
    }
    ok_response.raise_for_status = MagicMock()
    ok_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[fail_response, ok_response])
        mock_get.return_value = mock_client
        with patch("app.miner.enrichment.bizapi.rest_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.match_company("Retry Corp")
            assert result is not None


async def test_retry_on_429_with_retry_after(client):
    rate_response = MagicMock()
    rate_response.status_code = 429
    rate_response.headers = {"Retry-After": "0.1"}
    rate_response.raise_for_status = MagicMock()

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = {
        "MatchFound": True,
        "DUNS": "08-555-6666",
        "CompanyName": "Rate Corp",
        "MatchScore": 80,
    }
    ok_response.raise_for_status = MagicMock()
    ok_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[rate_response, ok_response])
        mock_get.return_value = mock_client
        with patch("app.miner.enrichment.bizapi.rest_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.match_company("Rate Corp")
            assert result is not None


async def test_exhausted_retries_raises(client):
    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=fail_response)
    )

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=fail_response)
        mock_get.return_value = mock_client
        with patch("app.miner.enrichment.bizapi.rest_client.asyncio.sleep", new_callable=AsyncMock):
            # Should exhaust retries and return None (match_company catches RuntimeError)
            result = await client.match_company("Fail Corp")
            assert result is None


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
            await client.match_company("Auth Fail Corp")


def test_is_available_true(client):
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(client.is_available()) is True


def test_is_available_false():
    c = BizAPIRESTClient(base_url="https://test.com", username="", password="")
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(c.is_available()) is False
