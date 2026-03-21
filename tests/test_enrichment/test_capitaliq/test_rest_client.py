"""Tests for CapitalIQRESTClient — SPQL paradigm, auth, retry."""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from app.miner.enrichment.capitaliq.rest_client import CapitalIQRESTClient


@pytest.fixture
def client():
    return CapitalIQRESTClient(
        base_url="https://api-ciq.marketintelligence.spglobal.com/gdsapi/rest",
        api_key="test-bearer-token-123",
        timeout=5.0,
        max_retries=2,
    )


def test_auth_headers_use_bearer(client):
    headers = client._auth_headers()
    assert headers["Authorization"] == "Bearer test-bearer-token-123"
    assert headers["Accept"] == "application/json"
    assert headers["Content-Type"] == "application/json"


def test_build_input_requests():
    requests = CapitalIQRESTClient._build_input_requests(
        identifier="IQ12345",
        mnemonics=["IQ_TOTAL_REV", "IQ_EBITDA"],
        function="GDSP",
        properties={"periodType": "IQ_FY"},
    )
    assert len(requests) == 2
    assert requests[0]["function"] == "GDSP"
    assert requests[0]["identifier"] == "IQ12345"
    assert requests[0]["mnemonic"] == "IQ_TOTAL_REV"
    assert requests[0]["properties"] == {"periodType": "IQ_FY"}
    assert requests[1]["mnemonic"] == "IQ_EBITDA"


async def test_search_company_returns_match_spql(client):
    spql_response = {
        "GDSSDKResponse": [
            {"Identifier": "IQ12345", "Mnemonic": "IQ_COMPANY_NAME", "Rows": [{"Row": ["Test Corp"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_PRIMARY_INDUSTRY", "Rows": [{"Row": ["Software"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_COMPANY_CITY", "Rows": [{"Row": ["Dallas"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_COMPANY_STATE", "Rows": [{"Row": ["TX"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_COMPANY_COUNTRY", "Rows": [{"Row": ["US"]}]},
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = spql_response
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.search_company("Test Corp")
        assert result is not None
        assert result["entity_id"] == "12345"
        assert result["name"] == "Test Corp"
        assert result["match_confidence"] == 1.0

        # Verify the request was POST to /v3/clientservice.json
        call_args = mock_client.request.call_args
        assert call_args[0][0] == "POST"
        assert "/v3/clientservice.json" in call_args[0][1]
        body = call_args[1].get("json") or call_args.kwargs.get("json")
        assert "inputRequests" in body


async def test_search_company_no_results_spql(client):
    spql_response = {
        "GDSSDKResponse": [
            {"Identifier": "", "Mnemonic": "IQ_COMPANY_NAME", "Rows": [{"Row": ["Data Unavailable"]}]},
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = spql_response
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.search_company("Nonexistent Corp")
        assert result is None


async def test_get_financials_spql(client):
    spql_response = {
        "GDSSDKResponse": [
            {"Identifier": "IQ12345", "Mnemonic": "IQ_TOTAL_REV", "Rows": [{"Row": ["100.0"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_EBITDA", "Rows": [{"Row": ["20.0"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_TOTAL_DEBT", "Rows": [{"Row": ["50.0"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_NET_DEBT", "Rows": [{"Row": ["40.0"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_TOTAL_LEVERAGE", "Rows": [{"Row": ["2.5"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_NET_LEVERAGE", "Rows": [{"Row": ["2.0"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_INTEREST_COVERAGE", "Rows": [{"Row": ["5.0"]}]},
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = spql_response
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.get_financials("12345")
        assert result["revenue"] == 100.0
        assert result["ebitda"] == 20.0
        assert result["credit_metrics"]["total_leverage"] == 2.5

        # Verify identifier is prefixed with IQ
        call_args = mock_client.request.call_args
        body = call_args[1].get("json") or call_args.kwargs.get("json")
        assert body["inputRequests"][0]["identifier"] == "IQ12345"


async def test_get_company_profile_spql(client):
    spql_response = {
        "GDSSDKResponse": [
            {"Identifier": "IQ12345", "Mnemonic": "IQ_GICS_CODE", "Rows": [{"Row": ["45101010"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_PRIMARY_SIC_CODE", "Rows": [{"Row": ["7372"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_COMPANY_STATUS", "Rows": [{"Row": ["Operating"]}]},
            {"Identifier": "IQ12345", "Mnemonic": "IQ_INDUSTRY_SECTOR", "Rows": [{"Row": ["Information Technology"]}]},
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = spql_response
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.get_company_profile("12345")
        assert result["gics_code"] == "45101010"
        assert result["sic_code"] == "7372"
        assert result["company_status"] == "Operating"
        assert result["industry_sector"] == "Information Technology"


async def test_retry_on_500(client):
    fail_response = MagicMock()
    fail_response.status_code = 500
    fail_response.raise_for_status = MagicMock(
        side_effect=httpx.HTTPStatusError("500", request=MagicMock(), response=fail_response)
    )

    ok_response = MagicMock()
    ok_response.status_code = 200
    ok_response.json.return_value = {
        "GDSSDKResponse": [
            {"Identifier": "IQretry", "Mnemonic": "IQ_TOTAL_REV", "Rows": [{"Row": ["100.0"]}]},
            {"Identifier": "IQretry", "Mnemonic": "IQ_EBITDA", "Rows": []},
            {"Identifier": "IQretry", "Mnemonic": "IQ_TOTAL_DEBT", "Rows": []},
            {"Identifier": "IQretry", "Mnemonic": "IQ_NET_DEBT", "Rows": []},
            {"Identifier": "IQretry", "Mnemonic": "IQ_TOTAL_LEVERAGE", "Rows": []},
            {"Identifier": "IQretry", "Mnemonic": "IQ_NET_LEVERAGE", "Rows": []},
            {"Identifier": "IQretry", "Mnemonic": "IQ_INTEREST_COVERAGE", "Rows": []},
        ]
    }
    ok_response.raise_for_status = MagicMock()
    ok_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(side_effect=[fail_response, ok_response])
        mock_get.return_value = mock_client
        with patch("app.miner.enrichment.capitaliq.rest_client.asyncio.sleep", new_callable=AsyncMock):
            result = await client.get_financials("retry")
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


async def test_search_with_duns_uses_duns_identifier(client):
    spql_response = {
        "GDSSDKResponse": [
            {"Identifier": "DUNS:08-111-2222", "Mnemonic": "IQ_COMPANY_NAME", "Rows": [{"Row": ["DUNS Corp"]}]},
            {"Identifier": "DUNS:08-111-2222", "Mnemonic": "IQ_PRIMARY_INDUSTRY", "Rows": [{"Row": ["Software"]}]},
            {"Identifier": "DUNS:08-111-2222", "Mnemonic": "IQ_COMPANY_CITY", "Rows": []},
            {"Identifier": "DUNS:08-111-2222", "Mnemonic": "IQ_COMPANY_STATE", "Rows": []},
            {"Identifier": "DUNS:08-111-2222", "Mnemonic": "IQ_COMPANY_COUNTRY", "Rows": []},
        ]
    }
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = spql_response
    mock_response.raise_for_status = MagicMock()
    mock_response.headers = {}

    with patch.object(client, "_get_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.request = AsyncMock(return_value=mock_response)
        mock_get.return_value = mock_client

        result = await client.search_company("DUNS Corp", duns="08-111-2222")
        assert result is not None
        # Verify DUNS identifier was used in inputRequests
        call_args = mock_client.request.call_args
        body = call_args[1].get("json") or call_args.kwargs.get("json")
        assert body["inputRequests"][0]["identifier"] == "DUNS:08-111-2222"


def test_is_available_true(client):
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(client.is_available()) is True


def test_is_available_false():
    c = CapitalIQRESTClient(base_url="https://test.com", api_key="")
    loop = asyncio.get_event_loop()
    assert loop.run_until_complete(c.is_available()) is False
