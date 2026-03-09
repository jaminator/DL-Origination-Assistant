"""Tests for PitchBook REST API v2 client."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.miner.pitchbook.rest_client import (
    PitchBookRESTClient,
    _compute_name_confidence,
    _format_location,
    _normalize_company_detail,
    _normalize_company_search_result,
    _normalize_competitor,
    _normalize_debt_deal,
    _normalize_investor,
)

# -- Normalizer unit tests -----------------------------------------------


class TestNormalizers:
    def test_compute_name_confidence_exact(self):
        assert _compute_name_confidence("Acme Corp", "Acme Corp") == 1.0

    def test_compute_name_confidence_case_insensitive(self):
        assert _compute_name_confidence("acme corp", "ACME CORP") == 1.0

    def test_compute_name_confidence_substring(self):
        assert _compute_name_confidence("Acme", "Acme Corp International") == 0.9

    def test_compute_name_confidence_partial_token_overlap(self):
        score = _compute_name_confidence("Acme Industries", "Acme Corp")
        assert 0.0 < score < 1.0

    def test_compute_name_confidence_no_match(self):
        score = _compute_name_confidence("Alpha", "Beta")
        assert score == 0.0

    def test_compute_name_confidence_empty(self):
        assert _compute_name_confidence("", "Acme") == 0.0
        assert _compute_name_confidence("Acme", "") == 0.0

    def test_format_location_full(self):
        raw = {"hqCity": "Dallas", "hqState": "TX", "hqCountry": "US"}
        assert _format_location(raw) == "Dallas, TX, US"

    def test_format_location_partial(self):
        raw = {"city": "Austin", "state": "TX"}
        assert _format_location(raw) == "Austin, TX"

    def test_format_location_empty(self):
        assert _format_location({}) == ""

    def test_normalize_company_search_result(self):
        raw = {
            "companyId": "123-45",
            "companyName": "Acme Corp",
            "ownershipStatus": "Privately Held",
            "primaryIndustrySector": "Industrials",
            "employees": 250,
            "revenueRange": "$50M-$100M",
            "hqCity": "Dallas",
            "hqState": "TX",
        }
        result = _normalize_company_search_result(raw, "Acme Corp")
        assert result["entity_id"] == "123-45"
        assert result["name"] == "Acme Corp"
        assert result["match_confidence"] == 1.0
        assert result["ownership_status"] == "Privately Held"
        assert result["employee_count"] == 250

    def test_normalize_company_detail(self):
        raw = {
            "companyId": "123-45",
            "companyName": "Acme Corp",
            "description": "Industrial company",
            "yearFounded": 2005,
            "ownershipStatus": "founder_owned",
            "revenue": 75000000,
            "ebitda": 12000000,
            "investors": [
                {"investorId": "inv-1", "investorName": "GrowthCo"}
            ],
        }
        detail = _normalize_company_detail(raw)
        assert detail["entity_id"] == "123-45"
        assert detail["founded_year"] == 2005
        assert detail["ownership_type"] == "founder_owned"
        assert detail["revenue"] == 75000000
        assert len(detail["investors"]) == 1

    def test_normalize_competitor(self):
        raw = {"companyId": "789", "companyName": "Beta Inc", "employees": 100}
        comp = _normalize_competitor(raw)
        assert comp["entity_id"] == "789"
        assert comp["name"] == "Beta Inc"

    def test_normalize_debt_deal(self):
        raw = {
            "dealId": "d-001",
            "dealType": "Term Loan",
            "dealSize": 75000000,
            "closeDate": "2023-06-15",
            "leadInvestor": "Big Bank",
        }
        deal = _normalize_debt_deal(raw)
        assert deal["facility_type"] == "Term Loan"
        assert deal["amount"] == 75000000
        assert deal["lender"] == "Big Bank"

    def test_normalize_investor_dict(self):
        raw = {"investorId": "inv-1", "investorName": "GrowthCo", "investorType": "PE"}
        inv = _normalize_investor(raw)
        assert inv["name"] == "GrowthCo"
        assert inv["type"] == "PE"

    def test_normalize_investor_string(self):
        inv = _normalize_investor("Simple Investor Name")
        assert inv["name"] == "Simple Investor Name"
        assert inv["entity_id"] == ""


# -- Client method tests (mocked HTTP) -----------------------------------


@pytest.fixture
def client():
    return PitchBookRESTClient(
        base_url="https://api.pitchbook.com/v2",
        api_key="test-key-123",
        timeout=5.0,
        max_retries=1,
    )


class TestPitchBookRESTClient:
    @pytest.mark.asyncio
    async def test_is_available_with_credentials(self, client):
        assert await client.is_available() is True

    @pytest.mark.asyncio
    async def test_is_available_without_credentials(self):
        c = PitchBookRESTClient(base_url="", api_key="")
        assert await c.is_available() is False

    @pytest.mark.asyncio
    async def test_search_company_found(self, client):
        mock_response = httpx.Response(
            200,
            json={
                "items": [
                    {
                        "companyId": "pb-123",
                        "companyName": "Acme Corp",
                        "ownershipStatus": "Privately Held",
                        "employees": 250,
                    }
                ]
            },
            request=httpx.Request("GET", "https://api.pitchbook.com/v2/companies"),
        )
        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.search_company("Acme Corp")
            assert result is not None
            assert result["entity_id"] == "pb-123"
            assert result["name"] == "Acme Corp"
            assert result["match_confidence"] == 1.0

    @pytest.mark.asyncio
    async def test_search_company_not_found(self, client):
        mock_response = httpx.Response(
            200,
            json={"items": []},
            request=httpx.Request("GET", "https://api.pitchbook.com/v2/companies"),
        )
        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            result = await client.search_company("Nonexistent Corp")
            assert result is None

    @pytest.mark.asyncio
    async def test_get_company_detail(self, client):
        mock_response = httpx.Response(
            200,
            json={
                "companyId": "pb-123",
                "companyName": "Acme Corp",
                "yearFounded": 2005,
                "ownershipStatus": "founder_owned",
                "revenue": 75000000,
            },
            request=httpx.Request("GET", "https://api.pitchbook.com/v2/companies/pb-123"),
        )
        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            detail = await client.get_company_detail("pb-123")
            assert detail["entity_id"] == "pb-123"
            assert detail["founded_year"] == 2005
            assert detail["revenue"] == 75000000

    @pytest.mark.asyncio
    async def test_get_competitors(self, client):
        mock_response = httpx.Response(
            200,
            json={
                "items": [
                    {"companyId": "c-1", "companyName": "Competitor A"},
                    {"companyId": "c-2", "companyName": "Competitor B"},
                ]
            },
            request=httpx.Request("GET", "https://api.pitchbook.com/v2/companies/pb-123/competitors"),
        )
        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            comps = await client.get_competitors("pb-123")
            assert len(comps) == 2
            assert comps[0]["name"] == "Competitor A"

    @pytest.mark.asyncio
    async def test_get_competitors_error_returns_empty(self, client):
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.RequestError("Network error"),
        ):
            comps = await client.get_competitors("pb-123")
            assert comps == []

    @pytest.mark.asyncio
    async def test_get_debt_details(self, client):
        mock_response = httpx.Response(
            200,
            json={
                "items": [
                    {
                        "dealId": "d-1",
                        "dealType": "Term Loan",
                        "dealSize": 50000000,
                        "leadInvestor": "Big Bank",
                    }
                ]
            },
            request=httpx.Request("GET", "https://api.pitchbook.com/v2/companies/pb-123/deals"),
        )
        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            debts = await client.get_debt_details("pb-123")
            assert len(debts) == 1
            assert debts[0]["facility_type"] == "Term Loan"
            assert debts[0]["amount"] == 50000000

    @pytest.mark.asyncio
    async def test_get_debt_details_error_returns_empty(self, client):
        with patch.object(
            httpx.AsyncClient,
            "request",
            new_callable=AsyncMock,
            side_effect=httpx.RequestError("Network error"),
        ):
            debts = await client.get_debt_details("pb-123")
            assert debts == []

    @pytest.mark.asyncio
    async def test_get_investors(self, client):
        mock_response = httpx.Response(
            200,
            json={
                "items": [
                    {"investorId": "inv-1", "investorName": "VC Fund", "investorType": "VC"},
                ]
            },
            request=httpx.Request("GET", "https://api.pitchbook.com/v2/companies/pb-123/investors"),
        )
        with patch.object(
            httpx.AsyncClient, "request", new_callable=AsyncMock, return_value=mock_response
        ):
            investors = await client.get_investors("pb-123")
            assert len(investors) == 1
            assert investors[0]["name"] == "VC Fund"

    @pytest.mark.asyncio
    async def test_auth_headers(self, client):
        headers = client._auth_headers()
        assert headers["Authorization"] == "Bearer test-key-123"
        assert headers["Accept"] == "application/json"

    @pytest.mark.asyncio
    async def test_close(self, client):
        # Getting client creates the httpx client
        await client._get_client()
        assert client._client is not None
        await client.close()
        assert client._client is None


# -- Factory tests -------------------------------------------------------


class TestFactory:
    def test_factory_returns_mock_by_default(self):
        from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
        from app.miner.pitchbook.mock_client import MockPitchBookClient

        adapter = get_pitchbook_adapter()
        assert isinstance(adapter, MockPitchBookClient)

    def test_factory_returns_rest_client(self):
        from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
        from app.miner.pitchbook.rest_client import PitchBookRESTClient

        with patch("app.miner.pitchbook.mcp_client.settings") as mock_settings:
            mock_settings.pitchbook_provider = "rest"
            mock_settings.pitchbook_api_base_url = "https://api.pitchbook.com/v2"
            mock_settings.pitchbook_api_key = "test-key"
            mock_settings.pitchbook_api_timeout = 30.0
            mock_settings.pitchbook_api_max_retries = 3
            adapter = get_pitchbook_adapter()
            assert isinstance(adapter, PitchBookRESTClient)

    def test_factory_returns_mcp_client(self):
        from app.miner.pitchbook.mcp_client import PitchBookMCPClient, get_pitchbook_adapter

        with patch("app.miner.pitchbook.mcp_client.settings") as mock_settings:
            mock_settings.pitchbook_provider = "mcp"
            mock_settings.mcp_pitchbook_url = "http://localhost:3000"
            mock_settings.mcp_pitchbook_token = "test-token"
            adapter = get_pitchbook_adapter()
            assert isinstance(adapter, PitchBookMCPClient)
