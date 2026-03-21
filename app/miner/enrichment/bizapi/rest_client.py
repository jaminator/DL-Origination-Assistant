"""NAICS BizAPI V2 REST client.

Implements the BizAPIAdapter interface using the real BizAPI V2 cosearch endpoint.

API docs: BizAPI-V2-Documentation.pdf
Endpoint: POST /wp-json/naicsapi/v2/cosearch (single endpoint, auto-detects match method)
Authentication: HTTP Basic Auth (username/password) over SSL.
Rate limit: 3 requests per rolling second.
Sandbox: POST /wp-json/naicsapi/v2/cosearchtest
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

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class BizAPIRESTClient(BizAPIAdapter):
    """BizAPI V2 integration via the cosearch REST endpoint.

    The API auto-detects the match method based on which fields are present
    in the request body:
      - duns only → DUNS Match (highest precision)
      - url only → URL Match (US only)
      - phone only → Phone Match
      - companyName + address + city + state + postalCode + country → Standard Match
      - companyName + state (minimum) → Loose Match
      - companyName only → Name Match
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

    async def _request(self, json_body: dict[str, Any]) -> dict[str, Any]:
        """POST to the cosearch endpoint with retry, backoff, and rate limiting."""
        await self._rate_limit()
        client = await self._get_client()
        last_exc: Exception | None = None

        logger.info("bizapi_request_start", url=self._base_url)

        for attempt in range(1, self._max_retries + 1):
            try:
                response = await client.post(self._base_url, json=json_body)

                if response.status_code == 429:
                    retry_after = float(response.headers.get("Retry-After", 1.0))
                    logger.warning(
                        "bizapi_rate_limited",
                        attempt=attempt,
                        retry_after=retry_after,
                    )
                    await asyncio.sleep(retry_after)
                    continue

                if response.status_code == 403:
                    logger.error("bizapi_no_credits", status=403)
                    raise httpx.HTTPStatusError(
                        "No credits remaining on BizAPI account",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                data = response.json()
                logger.info(
                    "bizapi_request_complete",
                    status=response.status_code,
                    attempt=attempt,
                )
                return data

            except httpx.HTTPStatusError as exc:
                logger.error(
                    "bizapi_http_error",
                    status=exc.response.status_code,
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
                    error=str(exc),
                    attempt=attempt,
                )
                last_exc = exc
                await asyncio.sleep(2 ** attempt)

        raise RuntimeError(
            f"BizAPI request failed after {self._max_retries} attempts"
        ) from last_exc

    def _build_request_body(
        self,
        company_name: str,
        *,
        duns: str | None = None,
        website: str | None = None,
        state: str | None = None,
        phone: str | None = None,
    ) -> dict[str, str]:
        """Build the cosearch POST body using camelCase field names.

        The API auto-detects match method from which fields are present:
        - duns only → DUNS Match
        - url only → URL Match
        - phone only → Phone Match
        - companyName + state + ... → Standard/Loose Match
        - companyName only → Name Match
        """
        body: dict[str, str] = {}

        # Priority: if we have DUNS, send only that for highest precision
        if duns:
            body["duns"] = duns
            return body

        # URL-only match
        if website and not company_name:
            body["url"] = website
            return body

        # Phone-only match
        if phone and not company_name:
            body["phone"] = phone
            return body

        # Standard/Loose/Name match: always include companyName
        body["companyName"] = company_name
        if state:
            body["state"] = state
        if website:
            body["url"] = website
        if phone:
            body["phone"] = phone

        return body

    async def match_company(
        self,
        company_name: str,
        *,
        duns: str | None = None,
        website: str | None = None,
        state: str | None = None,
        phone: str | None = None,
    ) -> dict | None:
        """Match a company via the BizAPI V2 cosearch endpoint.

        Sends a single POST request. The API auto-detects the best match
        method based on which fields are provided.
        """
        body = self._build_request_body(
            company_name, duns=duns, website=website, state=state, phone=phone,
        )

        try:
            raw = await self._request(json_body=body)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                raise
            logger.warning(
                "bizapi_request_failed",
                company=company_name,
                status=exc.response.status_code,
            )
            return None
        except RuntimeError:
            logger.warning("bizapi_retries_exhausted", company=company_name)
            return None

        result = normalize_match_response(raw)
        if result is None:
            logger.info("bizapi_no_match", company=company_name)
            return None

        logger.info(
            "bizapi_match_found",
            company=company_name,
            method=result["match_method"],
            confidence=result["match_confidence"],
        )
        return result

    async def is_available(self) -> bool:
        return bool(self._base_url and self._username and self._password)
