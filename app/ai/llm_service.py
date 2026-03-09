"""LLM service abstraction — provider-agnostic interface for AI operations."""

import json
import time
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel

from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("ai.llm")


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
    """Claude API via direct httpx calls."""

    def __init__(self):
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.base_url = "https://api.anthropic.com/v1"

    async def complete(
        self,
        prompt: str,
        system: str | None = None,
        response_schema: dict | None = None,
        temperature: float = 0.7,
    ) -> LLMResponse:
        start = time.monotonic()
        messages = [{"role": "user", "content": prompt}]
        body: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 4096,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            body["system"] = system

        async with httpx.AsyncClient(timeout=120.0) as client:
            resp = await client.post(
                f"{self.base_url}/messages",
                json=body,
                headers={
                    "x-api-key": self.api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        content = data["content"][0]["text"]
        latency = (time.monotonic() - start) * 1000
        usage = data.get("usage", {})

        return LLMResponse(
            content=content,
            model=self.model,
            provider="claude",
            prompt_tokens=usage.get("input_tokens", 0),
            completion_tokens=usage.get("output_tokens", 0),
            latency_ms=latency,
        )

    async def complete_json(
        self,
        prompt: str,
        system: str | None = None,
        temperature: float = 0.3,
    ) -> dict:
        resp = await self.complete(prompt, system=system, temperature=temperature)
        # Extract JSON from response (may be wrapped in markdown code blocks)
        text = resp.content.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)


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
        if not settings.llm_api_key:
            raise ValueError("LLM_API_KEY required when LLM_PROVIDER=claude")
        return ClaudeLLMService()
    return MockLLMService()
