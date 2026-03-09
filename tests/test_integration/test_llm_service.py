"""Tests for ClaudeLLMService error handling, retries, and response parsing.

All tests use httpx mocking — no real API calls are made.
"""

import json
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.ai.llm_service import (
    ClaudeLLMService,
    LLMAuthError,
    LLMError,
    LLMRateLimitError,
    LLMResponseError,
    LLMTimeoutError,
)


@pytest.fixture
def mock_settings():
    """Patch settings to provide a fake API key."""
    with patch("app.ai.llm_service.settings") as s:
        s.llm_api_key = "sk-test-fake-key"
        s.llm_model = "claude-sonnet-4-6"
        yield s


def _make_success_response(content: str = "Hello world") -> httpx.Response:
    """Build a realistic Anthropic Messages API success response."""
    return httpx.Response(
        200,
        json={
            "id": "msg_test123",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": content}],
            "model": "claude-sonnet-4-6",
            "usage": {"input_tokens": 10, "output_tokens": 5},
        },
    )


class TestClaudeLLMServiceInit:
    """Test constructor validation."""

    def test_missing_api_key_raises(self):
        with patch("app.ai.llm_service.settings") as s:
            s.llm_api_key = ""
            s.llm_model = "claude-sonnet-4-6"
            with pytest.raises(LLMAuthError, match="LLM_API_KEY is required"):
                ClaudeLLMService()

    def test_valid_key_succeeds(self, mock_settings):
        svc = ClaudeLLMService()
        assert svc.api_key == "sk-test-fake-key"


class TestClaudeLLMServiceComplete:
    """Test the complete() method with various API responses."""

    async def test_success(self, mock_settings):
        svc = ClaudeLLMService()
        mock_response = _make_success_response("Test response")
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client.is_closed = False
        svc._client = mock_client

        result = await svc.complete("Hello")
        assert result.content == "Test response"
        assert result.provider == "claude"
        assert result.prompt_tokens == 10
        assert result.completion_tokens == 5

    async def test_auth_error_401(self, mock_settings):
        svc = ClaudeLLMService()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=httpx.Response(401, text="Invalid API key"))
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMAuthError, match="rejected the API key"):
            await svc.complete("Hello")

    async def test_rate_limit_429_exhausts_retries(self, mock_settings):
        svc = ClaudeLLMService()
        svc.MAX_RETRIES = 1
        svc.INITIAL_BACKOFF = 0.01
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            return_value=httpx.Response(429, text="Rate limited", headers={})
        )
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMRateLimitError):
            await svc.complete("Hello")

    async def test_rate_limit_429_with_retry_after(self, mock_settings):
        svc = ClaudeLLMService()
        svc.MAX_RETRIES = 1
        svc.INITIAL_BACKOFF = 0.01
        mock_client = AsyncMock()
        # First call: 429 with retry-after, second call: success
        mock_client.post = AsyncMock(
            side_effect=[
                httpx.Response(429, text="Rate limited", headers={"retry-after": "0.01"}),
                _make_success_response("Recovered"),
            ]
        )
        mock_client.is_closed = False
        svc._client = mock_client

        result = await svc.complete("Hello")
        assert result.content == "Recovered"

    async def test_bad_request_400(self, mock_settings):
        svc = ClaudeLLMService()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            return_value=httpx.Response(400, text="Invalid model")
        )
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMResponseError, match="Bad request"):
            await svc.complete("Hello")

    async def test_server_error_retries_then_succeeds(self, mock_settings):
        svc = ClaudeLLMService()
        svc.MAX_RETRIES = 2
        svc.INITIAL_BACKOFF = 0.01
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[
                httpx.Response(500, text="Internal error"),
                _make_success_response("OK after retry"),
            ]
        )
        mock_client.is_closed = False
        svc._client = mock_client

        result = await svc.complete("Hello")
        assert result.content == "OK after retry"

    async def test_server_error_exhausts_retries(self, mock_settings):
        svc = ClaudeLLMService()
        svc.MAX_RETRIES = 1
        svc.INITIAL_BACKOFF = 0.01
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            return_value=httpx.Response(503, text="Service unavailable")
        )
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMError, match="server error 503"):
            await svc.complete("Hello")

    async def test_timeout_retries_then_succeeds(self, mock_settings):
        svc = ClaudeLLMService()
        svc.MAX_RETRIES = 2
        svc.INITIAL_BACKOFF = 0.01
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[
                httpx.ReadTimeout("timed out"),
                _make_success_response("OK after timeout"),
            ]
        )
        mock_client.is_closed = False
        svc._client = mock_client

        result = await svc.complete("Hello")
        assert result.content == "OK after timeout"

    async def test_timeout_exhausts_retries(self, mock_settings):
        svc = ClaudeLLMService()
        svc.MAX_RETRIES = 1
        svc.INITIAL_BACKOFF = 0.01
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(side_effect=httpx.ReadTimeout("timed out"))
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMTimeoutError):
            await svc.complete("Hello")

    async def test_connection_error_retries(self, mock_settings):
        svc = ClaudeLLMService()
        svc.MAX_RETRIES = 1
        svc.INITIAL_BACKOFF = 0.01
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            side_effect=[
                httpx.ConnectError("Connection refused"),
                _make_success_response("Connected"),
            ]
        )
        mock_client.is_closed = False
        svc._client = mock_client

        result = await svc.complete("Hello")
        assert result.content == "Connected"

    async def test_malformed_json_response(self, mock_settings):
        svc = ClaudeLLMService()
        mock_client = AsyncMock()
        bad_resp = httpx.Response(200, text="not json at all")
        mock_client.post = AsyncMock(return_value=bad_resp)
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMResponseError, match="not valid JSON"):
            await svc.complete("Hello")

    async def test_missing_content_field(self, mock_settings):
        svc = ClaudeLLMService()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            return_value=httpx.Response(200, json={"id": "msg_1", "content": []})
        )
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMResponseError, match="missing 'content'"):
            await svc.complete("Hello")

    async def test_unexpected_content_structure(self, mock_settings):
        svc = ClaudeLLMService()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(
            return_value=httpx.Response(200, json={"content": [{"type": "image"}]})
        )
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMResponseError, match="Unexpected response structure"):
            await svc.complete("Hello")


class TestClaudeLLMServiceCompleteJson:
    """Test the complete_json() method."""

    async def test_valid_json_response(self, mock_settings):
        svc = ClaudeLLMService()
        payload = {"key": "value", "count": 42}
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_make_success_response(json.dumps(payload)))
        mock_client.is_closed = False
        svc._client = mock_client

        result = await svc.complete_json("Give me JSON")
        assert result == payload

    async def test_json_in_markdown_code_block(self, mock_settings):
        svc = ClaudeLLMService()
        payload = {"subverticals": [{"name": "Test"}]}
        wrapped = f"```json\n{json.dumps(payload)}\n```"
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_make_success_response(wrapped))
        mock_client.is_closed = False
        svc._client = mock_client

        result = await svc.complete_json("Give me JSON")
        assert result == payload

    async def test_invalid_json_raises(self, mock_settings):
        svc = ClaudeLLMService()
        mock_client = AsyncMock()
        mock_client.post = AsyncMock(return_value=_make_success_response("not json"))
        mock_client.is_closed = False
        svc._client = mock_client

        with pytest.raises(LLMResponseError, match="not valid JSON"):
            await svc.complete_json("Give me JSON")
