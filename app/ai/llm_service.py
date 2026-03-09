"""LLM service abstraction — provider-agnostic interface for AI operations."""

import asyncio
import json
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("ai.llm")


class LLMError(Exception):
    """Base exception for LLM service errors."""


class LLMAuthError(LLMError):
    """API key is missing, invalid, or rejected."""


class LLMRateLimitError(LLMError):
    """Rate limit exceeded — caller should back off."""

    def __init__(self, message: str, retry_after: float | None = None):
        super().__init__(message)
        self.retry_after = retry_after


class LLMTimeoutError(LLMError):
    """Request timed out."""


class LLMResponseError(LLMError):
    """Response was not valid or could not be parsed."""


class LLMResponse(BaseModel):
    content: str
    parsed: dict | None = None
    model: str = ""
    provider: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    latency_ms: float = 0.0


class LLMService(ABC):
    @abstractmethod
    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        response_schema: dict | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        ...

    @abstractmethod
    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        """Complete and parse as JSON."""
        ...


class ClaudeLLMService(LLMService):
    """Claude API via httpx with retry, timeout, and error handling."""

    MAX_RETRIES = 3
    INITIAL_BACKOFF = 1.0  # seconds
    REQUEST_TIMEOUT = 120.0  # seconds

    def __init__(self):
        if not settings.llm_api_key:
            raise LLMAuthError(
                "LLM_API_KEY is required when LLM_PROVIDER=claude. "
                "Set the LLM_API_KEY environment variable to your Anthropic API key."
            )
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.base_url = "https://api.anthropic.com/v1"
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.REQUEST_TIMEOUT, connect=10.0),
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
        return self._client

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        response_schema: dict | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        messages = [{"role": "user", "content": prompt}]
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            body["system"] = system

        last_error: Exception | None = None
        for attempt in range(self.MAX_RETRIES + 1):
            if attempt > 0:
                backoff = self.INITIAL_BACKOFF * (2 ** (attempt - 1))
                logger.info("llm_retry", attempt=attempt, backoff_s=backoff)
                await asyncio.sleep(backoff)

            start = time.monotonic()
            try:
                client = await self._get_client()
                resp = await client.post(f"{self.base_url}/messages", json=body)
            except httpx.TimeoutException as exc:
                last_error = LLMTimeoutError(f"Request timed out after {self.REQUEST_TIMEOUT}s: {exc}")
                logger.warning("llm_timeout", attempt=attempt)
                continue
            except httpx.ConnectError as exc:
                last_error = LLMError(f"Connection failed: {exc}")
                logger.warning("llm_connection_error", attempt=attempt, error=str(exc))
                continue

            latency = (time.monotonic() - start) * 1000

            if resp.status_code == 401:
                raise LLMAuthError(
                    "Anthropic API rejected the API key. "
                    "Verify that LLM_API_KEY is a valid Anthropic API key."
                )
            if resp.status_code == 429:
                retry_after = resp.headers.get("retry-after")
                retry_seconds = float(retry_after) if retry_after else None
                last_error = LLMRateLimitError(
                    f"Rate limit exceeded (attempt {attempt + 1})",
                    retry_after=retry_seconds,
                )
                logger.warning("llm_rate_limited", attempt=attempt, retry_after=retry_seconds)
                if retry_seconds and attempt < self.MAX_RETRIES:
                    await asyncio.sleep(retry_seconds)
                continue
            if resp.status_code == 400:
                raise LLMResponseError(f"Bad request: {resp.text}")
            if resp.status_code in (500, 503):
                last_error = LLMError(f"Anthropic server error {resp.status_code}: {resp.text}")
                logger.warning("llm_server_error", status=resp.status_code, attempt=attempt)
                continue
            if resp.status_code != 200:
                raise LLMError(f"Unexpected status {resp.status_code}: {resp.text}")

            try:
                data = resp.json()
            except (json.JSONDecodeError, ValueError) as exc:
                raise LLMResponseError(f"Response is not valid JSON: {exc}") from exc

            if "content" not in data or not data["content"]:
                raise LLMResponseError(f"Response missing 'content' field: {data}")

            try:
                content = data["content"][0]["text"]
            except (KeyError, IndexError, TypeError) as exc:
                raise LLMResponseError(
                    f"Unexpected response structure: {exc}. Response: {data}"
                ) from exc

            usage = data.get("usage", {})
            logger.info(
                "llm_complete",
                model=self.model,
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                latency_ms=round(latency, 1),
            )

            return LLMResponse(
                content=content,
                model=self.model,
                provider="claude",
                prompt_tokens=usage.get("input_tokens", 0),
                completion_tokens=usage.get("output_tokens", 0),
                latency_ms=latency,
            )

        raise last_error or LLMError("All retry attempts exhausted")

    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        resp = await self.complete(prompt, system=system, temperature=temperature)
        text = resp.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise LLMResponseError(
                f"LLM response is not valid JSON: {exc}. Raw content: {text[:500]}"
            ) from exc

    async def close(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None


class MockLLMService(LLMService):
    """Mock LLM service for local dev without API keys."""

    def __init__(self, fixtures_path: str | None = None):
        self._fixtures: dict[str, Any] = {}
        self._default_response = {
            "subverticals": [
                {
                    "subvertical_name": "Mock Sub-vertical",
                    "description": "Mock sub-vertical for local development",
                    "thematic_fit_score": 75.0,
                    "lender_fit_score": 80.0,
                    "recommendation_status": "strong_fit",
                }
            ]
        }
        # Pre-register web enrichment fixture for mock company enrichment
        self._web_enrichment_response = {
            "description": "Mock company providing specialized services",
            "hq_city": "Dallas",
            "hq_state": "TX",
            "hq_country": "US",
            "founded_year": 2008,
            "employee_count": 175,
            "revenue_estimate": 85.0,
            "revenue_band": "$50M-$100M",
            "ebitda_estimate": 14.0,
            "recurring_revenue_estimate": 55.0,
            "is_public": False,
            "website": "https://example.com",
            "industry_exposure_descriptor": "Data center and critical infrastructure",
            "industry_exposure_intensity": "high",
            "ownership_type": "founder_owned",
            "confidence": 0.72,
        }

    def register_fixture(self, key: str, response: Any) -> None:
        self._fixtures[key] = response

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        response_schema: dict | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        logger.info("mock_llm_complete", prompt_length=len(prompt))

        # Detect web enrichment prompts and return enrichment fixture
        if "enrichment data" in prompt.lower() or "research the following company" in prompt.lower():
            content = json.dumps(self._web_enrichment_response)
            return LLMResponse(content=content, model="mock", provider="mock")

        # Check user-registered fixtures for a matching key
        for key, fixture in self._fixtures.items():
            if key.lower() in prompt.lower():
                content = json.dumps(fixture) if isinstance(fixture, (dict, list)) else str(fixture)
                return LLMResponse(content=content, model="mock", provider="mock")

        content = json.dumps(self._default_response)
        return LLMResponse(content=content, model="mock", provider="mock")

    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        resp = await self.complete(prompt, system=system, temperature=temperature)
        return json.loads(resp.content)


def get_llm_service() -> LLMService:
    """Factory for LLM service based on settings."""
    if settings.llm_provider == "claude":
        return ClaudeLLMService()  # raises LLMAuthError if key missing
    return MockLLMService()
