"""S&P Capital IQ GDS API client (SPQL paradigm).

Implements the CapitalIQAdapter interface using Capital IQ's GDS
(Global Data Solutions) API with SPQL queries.

Authentication: Bearer token obtained from the authenticate endpoint.
All data queries go through POST /v3/clientservice.json with
``inputRequests`` arrays specifying mnemonics.

Reference:
    CIQ GDS API v3 — POST /v3/clientservice.json
    Authentication — POST /catalog-service/authenticate
    Mnemonics: IQ_TOTAL_REV, IQ_EBITDA, IQ_TOTAL_DEBT, IQ_NET_DEBT,
               IQ_COMPANY_NAME, IQ_PRIMARY_INDUSTRY, IQ_GICS_CODE, etc.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.miner.enrichment.capitaliq.adapter import CapitalIQAdapter
from app.miner.enrichment.capitaliq.normalizers import (
    normalize_financials_response,
    normalize_ownership_response,
    normalize_profile_response,
    normalize_search_response,
)
from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("miner.enrichment.capitaliq")

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}

# SPQL endpoint path (all queries go through this single endpoint)
_SPQL_ENDPOINT = "/v3/clientservice.json"

# Common SPQL mnemonics
_SEARCH_MNEMONICS = [
    "IQ_COMPANY_NAME",
    "IQ_PRIMARY_INDUSTRY",
    "IQ_COMPANY_CITY",
    "IQ_COMPANY_STATE",
    "IQ_COMPANY_COUNTRY",
]

_FINANCIAL_MNEMONICS = [
    "IQ_TOTAL_REV",
    "IQ_EBITDA",
    "IQ_TOTAL_DEBT",
    "IQ_NET_DEBT",
    "IQ_TOTAL_LEVERAGE",
    "IQ_NET_LEVERAGE",
    "IQ_INTEREST_COVERAGE",
]

_OWNERSHIP_MNEMONICS = [
    "IQ_OWNERSHIP_STATUS",
    "IQ_KEY_INVESTORS",
]

_PROFILE_MNEMONICS = [
    "IQ_GICS_CODE",
    "IQ_PRIMARY_SIC_CODE",
    "IQ_COMPANY_STATUS",
    "IQ_INDUSTRY_SECTOR",
]


class CapitalIQRESTClient(CapitalIQAdapter):
    """Capital IQ integration via GDS SPQL API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        self._base_url = (base_url or settings.capitaliq_api_url).rstrip("/")
        self._api_key = api_key or settings.capitaliq_api_key.get_secret_value()
        self._timeout = timeout or settings.capitaliq_timeout
        self._max_retries = max_retries if max_retries is not None else settings.capitaliq_max_retries
        self._client: httpx.AsyncClient | None = None
        self._bearer_token: str | None = None

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
        token = self._bearer_token or self._api_key
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _refresh_auth_headers(self) -> None:
        """Refresh the client headers after token change."""
        if self._client and not self._client.is_closed:
            self._client.headers.update(self._auth_headers())

    # -- SPQL query building -----------------------------------------------

    @staticmethod
    def _build_input_requests(
        identifier: str,
        mnemonics: list[str],
        function: str = "GDSP",
        properties: dict[str, str] | None = None,
    ) -> list[dict[str, Any]]:
        """Build SPQL inputRequests array for a batch of mnemonics."""
        return [
            {
                "function": function,
                "identifier": identifier,
                "mnemonic": mnemonic,
                "properties": properties or {},
            }
            for mnemonic in mnemonics
        ]

    # -- low-level request -------------------------------------------------

    async def _request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry and backoff."""
        client = await self._get_client()
        last_exc: Exception | None = None

        logger.info("capitaliq_request_start", method=method, path=path)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.request(method, path, params=params, json=json_body)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 2 * attempt))
                    logger.warning(
                        "capitaliq_rate_limited",
                        path=path,
                        attempt=attempt,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                logger.info(
                    "capitaliq_request_complete",
                    method=method,
                    path=path,
                    status=response.status_code,
                    attempt=attempt,
                )
                return data

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "capitaliq_http_error",
                    status=exc.response.status_code,
                    path=path,
                    attempt=attempt,
                )
                last_exc = exc
                if exc.response.status_code in _RETRYABLE_STATUS_CODES:
                    await asyncio.sleep(2 ** attempt)
                    continue
                raise

            except httpx.RequestError as exc:
                logger.error(
                    "capitaliq_request_error",
                    path=path,
                    error=str(exc),
                    attempt=attempt,
                )
                last_exc = exc
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"Capital IQ request failed after {self._max_retries} attempts: {path}"
        ) from last_exc

    async def _spql_query(
        self,
        identifier: str,
        mnemonics: list[str],
        function: str = "GDSP",
        properties: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Execute an SPQL query via POST to /v3/clientservice.json."""
        input_requests = self._build_input_requests(
            identifier, mnemonics, function, properties
        )
        body = {"inputRequests": input_requests}
        return await self._request("POST", _SPQL_ENDPOINT, json_body=body)

    # -- CapitalIQAdapter interface ----------------------------------------

    async def search_company(self, company_name: str, *, duns: str | None = None) -> dict | None:
        """Search Capital IQ for a company by name or DUNS.

        Uses SPQL GDSP function with company identifier. If a DUNS is
        provided, uses it as the identifier; otherwise uses the company name.
        """
        # CIQ identifiers: use DUNS if available, otherwise company name
        identifier = f"DUNS:{duns}" if duns else company_name

        try:
            raw = await self._spql_query(identifier, _SEARCH_MNEMONICS)
        except (httpx.HTTPStatusError, RuntimeError):
            return None

        result = normalize_search_response(raw)
        if not result or not result.get("entity_id"):
            logger.info("capitaliq_search_no_results", company=company_name)
            return None

        logger.info(
            "capitaliq_match_found",
            company=company_name,
            entity_id=result["entity_id"],
            confidence=result.get("match_confidence"),
        )
        return result

    async def get_financials(self, entity_id: str) -> dict:
        """Get financial data via SPQL mnemonics."""
        ciq_id = f"IQ{entity_id}"
        raw = await self._spql_query(
            ciq_id,
            _FINANCIAL_MNEMONICS,
            properties={"periodType": "IQ_FY"},
        )
        return normalize_financials_response(raw)

    async def get_ownership(self, entity_id: str) -> dict:
        """Get ownership and investor data via SPQL mnemonics."""
        ciq_id = f"IQ{entity_id}"
        raw = await self._spql_query(ciq_id, _OWNERSHIP_MNEMONICS)
        return normalize_ownership_response(raw)

    async def get_company_profile(self, entity_id: str) -> dict:
        """Get company profile (GICS, SIC, status, sector) via SPQL."""
        ciq_id = f"IQ{entity_id}"
        raw = await self._spql_query(ciq_id, _PROFILE_MNEMONICS)
        return normalize_profile_response(raw)

    async def is_available(self) -> bool:
        return bool(self._base_url and self._api_key)
