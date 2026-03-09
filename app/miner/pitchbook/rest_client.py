"""PitchBook REST API v2 client.

Implements the PitchBookAdapter interface using PitchBook's RESTful API v2.

Authentication: API key passed as ``Authorization`` header (or via ``PB-API-Key``
header, depending on provisioning).  The base URL and key are sourced from
application settings.

Reference:
    PitchBook API v2 docs — https://documenter.getpostman.com/view/5190535/TzCV1iRc
    PitchBook Direct Data — https://pitchbook.com/products/direct-access-data/api
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.miner.pitchbook.adapter import PitchBookAdapter
from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("miner.pitchbook.rest")

# PitchBook API v2 entity type path segments
_ENTITY_COMPANIES = "companies"
_ENTITY_DEALS = "deals"
_ENTITY_INVESTORS = "investors"
_ENTITY_FUNDS = "funds"

# Default pagination
_DEFAULT_PAGE_SIZE = 25


class PitchBookRESTClient(PitchBookAdapter):
    """PitchBook integration via REST API v2.

    The PitchBook API v2 is a RESTful JSON API.  Entity types include
    companies, deals, investors, funds, people, limited partners, and
    service providers.  Each entity type has search and detail endpoints,
    plus relational sub-endpoints (e.g. ``/companies/{id}/deals``).
    """

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ):
        self._base_url = (base_url or settings.pitchbook_api_base_url).rstrip("/")
        self._api_key = api_key or settings.pitchbook_api_key
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.AsyncClient | None = None

    # -- lifecycle --------------------------------------------------------

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                headers=self._auth_headers(),
                timeout=self._timeout,
            )
        return self._client

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    def _auth_headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Accept": "application/json",
        }

    # -- low-level request ------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry / back-off."""
        client = await self._get_client()
        last_exc: Exception | None = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.request(method, path, params=params)

                if response.status_code == 429:
                    # Rate-limited — back off
                    retry_after = float(response.headers.get("Retry-After", 2 * attempt))
                    logger.warning(
                        "pitchbook_rate_limited",
                        attempt=attempt,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                return response.json()

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "pitchbook_http_error",
                    status=exc.response.status_code,
                    path=path,
                    attempt=attempt,
                )
                last_exc = exc
                if exc.response.status_code in {500, 502, 503, 504}:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

            except httpx.RequestError as exc:
                logger.error(
                    "pitchbook_request_error",
                    path=path,
                    error=str(exc),
                    attempt=attempt,
                )
                last_exc = exc
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"PitchBook API request failed after {self._max_retries} attempts: {path}"
        ) from last_exc

    # -- PitchBookAdapter interface ---------------------------------------

    async def search_company(self, company_name: str) -> dict | None:
        """Search PitchBook companies by name.

        PitchBook API v2 endpoint: ``GET /companies``

        Query params:
            name (str): Company name to search for.
            pageSize (int): Results per page (default 25).

        Returns the best match (first result) or None.
        """
        data = await self._request(
            "GET",
            f"/{_ENTITY_COMPANIES}",
            params={"name": company_name, "pageSize": 5},
        )
        items = data.get("items", data.get("results", []))
        if not items:
            logger.info("pitchbook_search_no_results", company=company_name)
            return None

        best = items[0]
        return _normalize_company_search_result(best, company_name)

    async def get_company_detail(self, entity_id: str) -> dict:
        """Get full company profile.

        PitchBook API v2 endpoint: ``GET /companies/{companyId}``

        Returns company overview, financials, ownership, and classification.
        """
        data = await self._request("GET", f"/{_ENTITY_COMPANIES}/{entity_id}")
        return _normalize_company_detail(data)

    async def get_competitors(self, entity_id: str) -> list[dict]:
        """Get competitor / similar companies.

        PitchBook API v2 endpoint: ``GET /companies/{companyId}/competitors``

        Returns list of competitor company summaries.
        """
        try:
            data = await self._request(
                "GET",
                f"/{_ENTITY_COMPANIES}/{entity_id}/competitors",
                params={"pageSize": _DEFAULT_PAGE_SIZE},
            )
            items = data.get("items", data.get("results", []))
            return [_normalize_competitor(c) for c in items]
        except Exception as exc:
            logger.warning("pitchbook_competitors_failed", entity_id=entity_id, error=str(exc))
            return []

    async def get_debt_details(self, entity_id: str) -> list[dict]:
        """Get debt / capital structure details.

        PitchBook API v2 endpoint: ``GET /companies/{companyId}/deals``
        filtered by deal type = debt/credit.

        Returns list of debt facility summaries.
        """
        try:
            data = await self._request(
                "GET",
                f"/{_ENTITY_COMPANIES}/{entity_id}/deals",
                params={
                    "dealType": "Debt",
                    "pageSize": _DEFAULT_PAGE_SIZE,
                },
            )
            items = data.get("items", data.get("results", []))
            return [_normalize_debt_deal(d) for d in items]
        except Exception as exc:
            logger.warning("pitchbook_debt_failed", entity_id=entity_id, error=str(exc))
            return []

    async def get_investors(self, entity_id: str) -> list[dict]:
        """Get investors for a company.

        PitchBook API v2 endpoint: ``GET /companies/{companyId}/investors``
        """
        try:
            data = await self._request(
                "GET",
                f"/{_ENTITY_COMPANIES}/{entity_id}/investors",
                params={"pageSize": _DEFAULT_PAGE_SIZE},
            )
            items = data.get("items", data.get("results", []))
            return [_normalize_investor(i) for i in items]
        except Exception as exc:
            logger.warning("pitchbook_investors_failed", entity_id=entity_id, error=str(exc))
            return []

    async def is_available(self) -> bool:
        return bool(self._base_url and self._api_key)


# -- Response normalizers ------------------------------------------------
# The PitchBook API v2 returns JSON payloads with varying field names.
# These helpers canonicalize them into the shapes our pipeline expects.


def _normalize_company_search_result(raw: dict, query_name: str) -> dict:
    """Normalize a company search hit into the adapter contract."""
    return {
        "entity_id": raw.get("companyId") or raw.get("entityId") or raw.get("pbId", ""),
        "name": raw.get("companyName") or raw.get("name", query_name),
        "match_confidence": _compute_name_confidence(
            query_name,
            raw.get("companyName") or raw.get("name", ""),
        ),
        "ownership_status": raw.get("ownershipStatus") or raw.get("ownership", ""),
        "primary_industry": (
            raw.get("primaryIndustryCode")
            or raw.get("primaryIndustrySector")
            or (raw["verticals"][0] if isinstance(raw.get("verticals"), list) and raw["verticals"] else "")
        ),
        "employee_count": raw.get("employees") or raw.get("employeeCount"),
        "revenue_range": raw.get("revenueRange") or raw.get("revenue", ""),
        "hq_location": _format_location(raw),
    }


def _normalize_company_detail(raw: dict) -> dict:
    """Normalize a full company profile response."""
    return {
        "entity_id": raw.get("companyId") or raw.get("entityId", ""),
        "name": raw.get("companyName") or raw.get("name", ""),
        "description": raw.get("description") or raw.get("businessDescription", ""),
        "founded_year": raw.get("yearFounded") or raw.get("foundedYear"),
        "hq_location": _format_location(raw),
        "website": raw.get("website") or raw.get("companyWebsite", ""),
        "ownership_type": raw.get("ownershipStatus") or raw.get("ownership", ""),
        "primary_industry": raw.get("primaryIndustrySector") or raw.get("primaryIndustryCode", ""),
        "employees": raw.get("employees") or raw.get("employeeCount"),
        "revenue": raw.get("revenue") or raw.get("totalRevenue"),
        "ebitda": raw.get("ebitda"),
        "total_raised": raw.get("totalRaised") or raw.get("totalFundingAmount"),
        "investors": [
            _normalize_investor(inv)
            for inv in (raw.get("investors") or raw.get("activeInvestors") or [])
        ],
        "last_financing_date": raw.get("lastFinancingDate"),
        "last_financing_type": raw.get("lastFinancingDealType"),
        "status": raw.get("companyStatus") or raw.get("status", ""),
    }


def _normalize_competitor(raw: dict) -> dict:
    return {
        "entity_id": raw.get("companyId") or raw.get("entityId", ""),
        "name": raw.get("companyName") or raw.get("name", ""),
        "primary_industry": raw.get("primaryIndustrySector", ""),
        "employee_count": raw.get("employees"),
        "hq_location": _format_location(raw),
    }


def _normalize_debt_deal(raw: dict) -> dict:
    return {
        "deal_id": raw.get("dealId") or raw.get("entityId", ""),
        "facility_type": raw.get("dealType") or raw.get("dealType2", ""),
        "amount": raw.get("dealSize") or raw.get("amount"),
        "lender": _extract_lender(raw),
        "close_date": raw.get("closeDate") or raw.get("dealDate", ""),
        "maturity_date": raw.get("maturityDate", ""),
        "pricing": raw.get("pricing") or raw.get("spread", ""),
        "status": raw.get("dealStatus", ""),
    }


def _normalize_investor(raw: dict) -> dict:
    if isinstance(raw, str):
        return {"name": raw, "entity_id": ""}
    return {
        "entity_id": raw.get("investorId") or raw.get("entityId", ""),
        "name": raw.get("investorName") or raw.get("name", ""),
        "type": raw.get("investorType", ""),
    }


def _extract_lender(deal: dict) -> str:
    """Pull lead lender name from deal payload."""
    lenders = deal.get("lenders") or deal.get("investors") or []
    if isinstance(lenders, list) and lenders:
        first = lenders[0]
        if isinstance(first, dict):
            return first.get("investorName") or first.get("name", "")
        return str(first)
    return deal.get("leadInvestor") or deal.get("leadLender", "")


def _format_location(raw: dict) -> str:
    city = raw.get("hqCity") or raw.get("city", "")
    state = raw.get("hqState") or raw.get("state", "")
    country = raw.get("hqCountry") or raw.get("country", "")
    parts = [p for p in (city, state, country) if p]
    return ", ".join(parts)


def _compute_name_confidence(query: str, result: str) -> float:
    """Simple name-match confidence score."""
    if not query or not result:
        return 0.0
    q = query.lower().strip()
    r = result.lower().strip()
    if q == r:
        return 1.0
    if q in r or r in q:
        return 0.9
    # Token overlap
    q_tokens = set(q.split())
    r_tokens = set(r.split())
    if not q_tokens or not r_tokens:
        return 0.0
    overlap = len(q_tokens & r_tokens)
    return round(overlap / max(len(q_tokens), len(r_tokens)), 2)
