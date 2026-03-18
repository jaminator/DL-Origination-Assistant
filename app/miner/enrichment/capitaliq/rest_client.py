"""S&P Capital IQ REST API client.

Implements the CapitalIQAdapter interface using Capital IQ's API.

Authentication: API key passed as header.
"""

from __future__ import annotations

import asyncio
from typing import Any

import httpx

from app.miner.enrichment.capitaliq.adapter import CapitalIQAdapter
from app.miner.enrichment.capitaliq.normalizers import (
    normalize_financials_response,
    normalize_ownership_response,
    normalize_search_response,
)
from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("miner.enrichment.capitaliq")

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class CapitalIQRESTClient(CapitalIQAdapter):
    """Capital IQ integration via REST API."""

    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ):
        self._base_url = (base_url or settings.capitaliq_api_url).rstrip("/")
        self._api_key = api_key or settings.capitaliq_api_key
        self._timeout = timeout or settings.capitaliq_timeout
        self._max_retries = max_retries if max_retries is not None else settings.capitaliq_max_retries
        self._client: httpx.AsyncClient | None = None

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
            "X-API-Key": self._api_key,
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

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

    async def search_company(self, company_name: str, *, duns: str | None = None) -> dict | None:
        """Search Capital IQ for a company by name or DUNS."""
        body: dict[str, Any] = {"CompanyName": company_name}
        if duns:
            body["DUNS"] = duns

        try:
            raw = await self._request("POST", "/companies/search", json_body=body)
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
        """Get financial data for a matched company."""
        raw = await self._request("GET", f"/companies/{entity_id}/financials")
        return normalize_financials_response(raw)

    async def get_ownership(self, entity_id: str) -> dict:
        """Get ownership and investor data."""
        raw = await self._request("GET", f"/companies/{entity_id}/ownership")
        return normalize_ownership_response(raw)

    async def is_available(self) -> bool:
        return bool(self._base_url and self._api_key)
