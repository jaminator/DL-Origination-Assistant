"""NAICS BizAPI REST client.

Implements the BizAPIAdapter interface using the NAICS BizAPI REST API.

Authentication: HTTP Basic Auth (username/password) over SSL.
Rate limit: 3 requests per rolling second (documented).
Sandbox: Available at a separate URL for testing with real credentials.
"""

from __future__ import annotations

import asyncio
import base64
import time
from typing import Any

import httpx

from app.miner.enrichment.bizapi.adapter import BizAPIAdapter
from app.miner.enrichment.bizapi.normalizers import normalize_match_response
from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("miner.enrichment.bizapi")

# Match method endpoint paths
_MATCH_ENDPOINTS = {
    "duns": "/match/duns",
    "url": "/match/url",
    "standard": "/match/standard",
    "name": "/match/name",
    "phone": "/match/phone",
    "loose": "/match/loose",
}

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class BizAPIRESTClient(BizAPIAdapter):
    """BizAPI integration via REST API with Basic Auth.

    Supports 6 match methods: DUNS, URL, Standard, Name, Phone, Loose.
    Enforces rate limiting at 3 requests per rolling second.
    """

    def __init__(
        self,
        base_url: str | None = None,
        username: str | None = None,
        password: str | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
        rate_limit_rps: float | None = None,
    ):
        if base_url:
            self._base_url = base_url.rstrip("/")
        elif settings.bizapi_use_sandbox:
            self._base_url = settings.bizapi_sandbox_url.rstrip("/")
        else:
            self._base_url = settings.bizapi_api_url.rstrip("/")

        self._username = username or settings.bizapi_username
        self._password = password or settings.bizapi_password.get_secret_value()
        self._timeout = timeout or settings.bizapi_timeout
        self._max_retries = max_retries if max_retries is not None else settings.bizapi_max_retries
        self._rate_limit_rps = rate_limit_rps or settings.bizapi_rate_limit_rps
        self._last_request_time: float = 0.0
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
        credentials = base64.b64encode(f"{self._username}:{self._password}".encode()).decode()
        return {
            "Authorization": f"Basic {credentials}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

    async def _rate_limit(self) -> None:
        """Enforce rate limiting at configured requests per second."""
        if self._rate_limit_rps <= 0:
            return
        min_interval = 1.0 / self._rate_limit_rps
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < min_interval:
            await asyncio.sleep(min_interval - elapsed)
        self._last_request_time = time.monotonic()

    async def _request(
        self,
        method: str,
        path: str,
        json_body: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Execute an HTTP request with retry, backoff, and rate limiting."""
        await self._rate_limit()
        client = await self._get_client()
        last_exc: Exception | None = None

        logger.info("bizapi_request_start", method=method, path=path)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.request(method, path, json=json_body)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 1.0))
                    logger.warning(
                        "bizapi_rate_limited",
                        path=path,
                        attempt=attempt,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                response.raise_for_status()
                data = response.json()
                logger.info(
                    "bizapi_request_complete",
                    method=method,
                    path=path,
                    status=response.status_code,
                    attempt=attempt,
                )
                return data

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "bizapi_http_error",
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
                    "bizapi_request_error",
                    path=path,
                    error=str(exc),
                    attempt=attempt,
                )
                last_exc = exc
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"BizAPI request failed after {self._max_retries} attempts: {path}"
        ) from last_exc

    def _select_match_method(
        self,
        company_name: str,
        *,
        duns: str | None = None,
        website: str | None = None,
        state: str | None = None,
        phone: str | None = None,
    ) -> list[tuple[str, dict[str, Any]]]:
        """Select match methods in priority order based on available data.

        Returns list of (method_name, request_body) tuples to try in order.
        """
        methods: list[tuple[str, dict[str, Any]]] = []

        if duns:
            methods.append(("duns", {"DUNS": duns}))
        if website:
            methods.append(("url", {"URL": website}))
        if state:
            methods.append(("standard", {"CompanyName": company_name, "State": state}))
        methods.append(("name", {"CompanyName": company_name}))
        if phone:
            methods.append(("phone", {"Phone": phone}))
        methods.append(("loose", {"CompanyName": company_name}))

        return methods

    async def match_company(
        self,
        company_name: str,
        *,
        duns: str | None = None,
        website: str | None = None,
        state: str | None = None,
        phone: str | None = None,
    ) -> dict | None:
        """Match a company using cascading match methods."""
        methods = self._select_match_method(
            company_name, duns=duns, website=website, state=state, phone=phone,
        )

        for method_name, body in methods:
            path = _MATCH_ENDPOINTS[method_name]
            try:
                raw = await self._request("POST", path, json_body=body)

                # BizAPI returns empty or null results for no match
                if not raw or raw.get("MatchFound") is False or raw.get("match_found") is False:
                    logger.info("bizapi_no_match", method=method_name, company=company_name)
                    continue

                raw["match_method"] = method_name
                result = normalize_match_response(raw)

                if result["match_confidence"] >= 0.50:
                    logger.info(
                        "bizapi_match_found",
                        method=method_name,
                        company=company_name,
                        confidence=result["match_confidence"],
                    )
                    return result

                logger.info(
                    "bizapi_low_confidence",
                    method=method_name,
                    company=company_name,
                    confidence=result["match_confidence"],
                )

            except RuntimeError:
                logger.warning("bizapi_method_exhausted", method=method_name, company=company_name)
                continue
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 401:
                    raise
                logger.warning(
                    "bizapi_method_failed",
                    method=method_name,
                    company=company_name,
                    status=exc.response.status_code,
                )
                continue

        return None

    async def is_available(self) -> bool:
        return bool(self._base_url and self._username and self._password)
