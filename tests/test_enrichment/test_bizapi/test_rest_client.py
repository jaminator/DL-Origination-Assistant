"""Tests for BizAPIRESTClient — auth, retry, rate limiting, cosearch endpoint."""

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.miner.enrichment.bizapi.rest_client import BizAPIRESTClient


@pytest.fixture
def client():
    return BizAPIRESTClient(
        base_url="https://test.bizapi.com/cosearch",
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


def test_build_request_body_duns_only(client):
    body = client._build_request_body("Acme", duns="08-146-3297")
    assert body == {"duns": "08-146-3297"}
    assert "companyName" not in body


def test_build_request_body_standard(client):
    body = client._build_request_body("Acme Corp", state="TX")
    assert body == {"companyName": "Acme Corp", "state": "TX"}


def test_build_request_body_name_only(client):
    body = client._build_request_body("Acme Corp")
    assert body == {"companyName": "Acme Corp"}


def test_build_request_body_with_all_fields(client):
    body = client._build_request_body(
        "Acme Corp", duns="123", website="https://acme.com", state="TX", phone="555",
    )
    # DUNS takes priority — sends only duns
    assert body == {"duns": "123"}


def test_build_request_body_name_state_url_phone(client):
    body = client._build_request_body(
        "Acme Corp", website="https://acme.com", state="TX", phone="555",
    )
    assert body == {
        "companyName": "Acme Corp",
        "state": "TX",
        "url": "https://acme.com",
        "phone": "555",
    }


async def test_match_company_returns_none_on_no_match(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Search Terms": {"companyName": "Nonexistent Corp"},
        "Matching Data": {"Request ID": 1, "Match Method": ""},
        "Appended Data": {"Message": "No match found"},
    }
    mock_response.raise_for_status = MagicMock()

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.match_company("Nonexistent Corp")
        assert result is None


async def test_match_company_returns_match(client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "Search Terms": {"companyName": "Acme Corp", "state": "TX"},
        "Matching Data": {
            "Request ID": 2,
            "Match Method": "Standard Match",
            "Match Grade": "AABAAAZ",
            "Confidence Code": 9,
            "BEMFAB": "M",
            "DUNS #": "08-111-2222",
        },
        "Appended Data": {
            "Company Name": "Acme Corp",
            "NAICS 1 Code": "541512",
            "Employees Total": "200",
            "Sales Volume in US$": "50,000,000",
        },
    }
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.match_company("Acme Corp", state="TX")
        assert result is not None
        assert result["duns"] == "08-111-2222"
        assert result["match_confidence"] == 0.9
        assert result["match_method"] == "standard"


async def test_retry_on_503(client):
    fail_response = MagicMock()
    fail_response.status_code = 503
    fail_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=fail_response)
    )

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = {
        "Search Terms": {"companyName": "Retry Corp"},
        "Matching Data": {
            "Match Method": "Name Match",
            "Confidence Code": 8,
            "DUNS #": "08-333-4444",
        },
        "Appended Data": {"Company Name": "Retry Corp"},
    }
    ok_response.raise_for_status = MagicMock()
    ok_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[fail_response, ok_response])
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
        "Search Terms": {"companyName": "Rate Corp"},
        "Matching Data": {
            "Match Method": "Name Match",
            "Confidence Code": 8,
            "DUNS #": "08-555-6666",
        },
        "Appended Data": {"Company Name": "Rate Corp"},
    }
    ok_response.raise_for_status = MagicMock()
    ok_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=[rate_response, ok_response])
        mock_get.return_value = mock_client
        with patch("app.miner.enrichment.bizapi.rest_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.match_company("Rate Corp")
            assert result is not None


async def test_exhausted_retries_returns_none(client):
    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=fail_response)
    )

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_get.return_value = mock_client
        with patch("app.miner.enrichment.bizapi.rest_client.asyncio.sleep", new_callable=AsyncMock):
            # match_company catches RuntimeError from exhausted retries
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
        mock_client.post = AsyncMock(return_value=fail_response)
        mock_get.return_value = mock_client
        with pytest.raises(httpx.HTTPStatusError):
            await client.match_company("Auth Fail Corp")


async def test_is_available_true(client):
    assert await client.is_available() is True


async def test_is_available_false():
    c = BizAPIRESTClient(base_url="https://test.com", username="", password="")
    assert await c.is_available() is False
