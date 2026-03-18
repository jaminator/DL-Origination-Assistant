"""Tests for source adapters: NAICS, mock, web scraper heuristics, retry logic."""

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from app.miner.sources.mock_adapter import MockSourceAdapter
from app.miner.sources.naics_adapter import NAICS_DESCRIPTIONS, NAICSAdapter

# --- NAICS adapter tests ---


class TestNAICSAdapter:

    @pytest.mark.asyncio
    async def test_extract_known_codes(self):
        adapter = NAICSAdapter()
        companies = await adapter.extract_companies({
            "naics_codes": ["238210", "518210"],
            "source_name": "NAICS DB",
            "subvertical": "Electrical",
        })
        assert len(companies) == 2
        assert "238210" in companies[0].raw_name
        assert "Electrical Contractors" in companies[0].raw_name
        assert companies[0].subvertical == "Electrical"

    @pytest.mark.asyncio
    async def test_extract_unknown_codes(self):
        adapter = NAICSAdapter()
        companies = await adapter.extract_companies({
            "naics_codes": ["999999"],
            "source_name": "NAICS DB",
        })
        assert len(companies) == 0

    @pytest.mark.asyncio
    async def test_extract_empty_codes(self):
        adapter = NAICSAdapter()
        companies = await adapter.extract_companies({
            "source_name": "NAICS DB",
        })
        assert len(companies) == 0

    @pytest.mark.asyncio
    async def test_extra_field_populated(self):
        adapter = NAICSAdapter()
        companies = await adapter.extract_companies({
            "naics_codes": ["238210"],
        })
        assert companies[0].extra["naics_code"] == "238210"

    @pytest.mark.asyncio
    async def test_is_available(self):
        adapter = NAICSAdapter()
        assert await adapter.is_available({}) is True

    def test_naics_descriptions_coverage(self):
        """Verify we have descriptions for common data center / infra codes."""
        assert "238210" in NAICS_DESCRIPTIONS  # Electrical Contractors
        assert "518210" in NAICS_DESCRIPTIONS  # Data Processing/Hosting
        assert "541512" in NAICS_DESCRIPTIONS  # Computer Systems Design


# --- Mock adapter tests ---


class TestMockAdapter:

    @pytest.mark.asyncio
    async def test_default_extraction(self):
        adapter = MockSourceAdapter()
        companies = await adapter.extract_companies({
            "source_name": "test_source",
            "source_type": "default",
        })
        assert len(companies) > 0
        assert all(c.source_tag == "test_source" for c in companies)

    @pytest.mark.asyncio
    async def test_trade_journal_source(self):
        adapter = MockSourceAdapter()
        companies = await adapter.extract_companies({
            "source_name": "ENR",
            "source_type": "trade_journal",
        })
        assert len(companies) > 0

    @pytest.mark.asyncio
    async def test_ranking_list_source(self):
        adapter = MockSourceAdapter()
        companies = await adapter.extract_companies({
            "source_name": "Top 50",
            "source_type": "ranking_list",
        })
        assert len(companies) > 0

    @pytest.mark.asyncio
    async def test_association_directory_source(self):
        adapter = MockSourceAdapter()
        companies = await adapter.extract_companies({
            "source_name": "NECA",
            "source_type": "association_directory",
        })
        assert len(companies) > 0

    @pytest.mark.asyncio
    async def test_unknown_source_type_uses_default(self):
        adapter = MockSourceAdapter()
        companies = await adapter.extract_companies({
            "source_name": "test",
            "source_type": "nonexistent_type",
        })
        assert len(companies) > 0  # Falls back to default


# --- Web scraper adapter tests (unit tests with mocked HTTP) ---


class TestWebScraperHeuristics:

    def test_clean_name_strips_ranking(self):
        from app.miner.sources.web_scraper import WebScraperAdapter
        adapter = WebScraperAdapter()
        assert adapter._clean_name("1. Acme Corp") == "Acme Corp"
        assert adapter._clean_name("23) Test Industries") == "Test Industries"
        assert adapter._clean_name("5- Some Company") == "Some Company"

    def test_clean_name_strips_long_parens(self):
        from app.miner.sources.web_scraper import WebScraperAdapter
        adapter = WebScraperAdapter()
        long_name = "Acme Corp " + "(" + "x" * 100 + ")"
        assert adapter._clean_name(long_name) == "Acme Corp"

    def test_clean_name_preserves_short_parens(self):
        from app.miner.sources.web_scraper import WebScraperAdapter
        adapter = WebScraperAdapter()
        assert adapter._clean_name("Acme Corp (TX)") == "Acme Corp (TX)"

    @pytest.mark.asyncio
    async def test_no_url_returns_empty(self):
        from app.miner.sources.web_scraper import WebScraperAdapter
        adapter = WebScraperAdapter()
        result = await adapter.extract_companies({"source_name": "test"})
        assert result == []

    @pytest.mark.asyncio
    async def test_extract_with_selector(self):
        from bs4 import BeautifulSoup

        from app.miner.sources.web_scraper import WebScraperAdapter

        adapter = WebScraperAdapter()
        html = "<ul><li>Company A</li><li>Company B</li><li>Company C</li></ul>"
        soup = BeautifulSoup(html, "html.parser")
        names = adapter._extract_with_selector(soup, "li")
        assert names == ["Company A", "Company B", "Company C"]

    @pytest.mark.asyncio
    async def test_extract_with_heuristics_table(self):
        from bs4 import BeautifulSoup

        from app.miner.sources.web_scraper import WebScraperAdapter

        adapter = WebScraperAdapter()
        html = """
        <table>
            <tbody>
                <tr><td>Alpha Industries</td><td>Dallas</td></tr>
                <tr><td>Beta Manufacturing</td><td>Austin</td></tr>
                <tr><td>Gamma Services</td><td>Houston</td></tr>
                <tr><td>Delta Corp</td><td>NYC</td></tr>
            </tbody>
        </table>
        """
        soup = BeautifulSoup(html, "html.parser")
        names = adapter._extract_with_heuristics(soup)
        assert len(names) >= 4


# --- Web scraper retry tests ---


def _make_response(status_code: int, text: str = "", headers: dict | None = None):
    """Create a mock httpx.Response."""
    return httpx.Response(
        status_code=status_code,
        text=text,
        headers=headers or {},
        request=httpx.Request("GET", "https://example.com"),
    )


class TestWebScraperRetry:

    @pytest.mark.asyncio
    async def test_fetch_page_retries_on_503(self):
        """_fetch_page retries on 503 status codes."""
        from app.miner.sources.web_scraper import WebScraperAdapter

        adapter = WebScraperAdapter()
        call_count = 0

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response(503, "Service Unavailable")
            return _make_response(200, "<html>OK</html>")

        with patch.object(httpx.AsyncClient, "get", mock_get), \
             patch("app.miner.sources.web_scraper.asyncio.sleep", new_callable=AsyncMock):
            text = await adapter._fetch_page("https://example.com")
            assert call_count == 2
            assert "OK" in text

    @pytest.mark.asyncio
    async def test_fetch_page_retries_on_429_with_retry_after(self):
        """_fetch_page respects Retry-After header on 429."""
        from app.miner.sources.web_scraper import WebScraperAdapter

        adapter = WebScraperAdapter()
        call_count = 0
        sleep_durations = []

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response(429, "Rate limited", {"Retry-After": "1"})
            return _make_response(200, "<html>OK</html>")

        async def track_sleep(duration):
            sleep_durations.append(duration)

        with patch.object(httpx.AsyncClient, "get", mock_get), \
             patch("app.miner.sources.web_scraper.asyncio.sleep", side_effect=track_sleep):
            await adapter._fetch_page("https://example.com")
            assert call_count == 2
            assert sleep_durations[0] == 1.0

    @pytest.mark.asyncio
    async def test_fetch_page_retries_on_timeout(self):
        """_fetch_page retries on timeout and succeeds."""
        from app.miner.sources.web_scraper import WebScraperAdapter

        adapter = WebScraperAdapter()
        call_count = 0

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ReadTimeout("timed out")
            return _make_response(200, "<html>OK</html>")

        with patch.object(httpx.AsyncClient, "get", mock_get), \
             patch("app.miner.sources.web_scraper.asyncio.sleep", new_callable=AsyncMock):
            text = await adapter._fetch_page("https://example.com")
            assert call_count == 2
            assert "OK" in text

    @pytest.mark.asyncio
    async def test_fetch_page_exhausted_retries_raises(self):
        """_fetch_page raises after all retries are exhausted."""
        from app.miner.sources.web_scraper import WebScraperAdapter

        adapter = WebScraperAdapter()

        async def mock_get(self_client, url, **kwargs):
            raise httpx.ConnectError("connection refused")

        with patch.object(httpx.AsyncClient, "get", mock_get), \
             patch("app.miner.sources.web_scraper.asyncio.sleep", new_callable=AsyncMock), \
             pytest.raises(httpx.ConnectError):
            await adapter._fetch_page("https://example.com")

    @pytest.mark.asyncio
    async def test_extract_companies_returns_empty_on_fetch_failure(self):
        """extract_companies returns empty list when _fetch_page fails."""
        from app.miner.sources.web_scraper import WebScraperAdapter

        adapter = WebScraperAdapter()

        async def mock_fetch(url):
            raise httpx.ConnectError("connection refused")

        adapter._fetch_page = mock_fetch
        result = await adapter.extract_companies({
            "url": "https://example.com/down",
            "source_name": "test",
        })
        assert result == []


class TestDirectoryAdapterRetry:

    @pytest.mark.asyncio
    async def test_fetch_page_retries_on_500(self):
        """Directory _fetch_page retries on 500 and succeeds."""
        from app.miner.sources.directory_adapter import DirectoryAdapter

        adapter = DirectoryAdapter()
        call_count = 0

        async def mock_get(self_client, url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return _make_response(500, "Internal Server Error")
            return _make_response(200, "<html>OK</html>")

        with patch.object(httpx.AsyncClient, "get", mock_get), \
             patch("app.miner.sources.directory_adapter.asyncio.sleep", new_callable=AsyncMock):
            text = await adapter._fetch_page("https://example.com")
            assert call_count == 2
            assert "OK" in text

    @pytest.mark.asyncio
    async def test_extract_companies_returns_empty_on_fetch_failure(self):
        """Directory adapter returns empty after fetch failure."""
        from app.miner.sources.directory_adapter import DirectoryAdapter

        adapter = DirectoryAdapter()

        async def mock_fetch(url):
            raise httpx.ConnectError("connection refused")

        adapter._fetch_page = mock_fetch
        result = await adapter.extract_companies({
            "url": "https://example.com/down",
            "source_name": "test_dir",
        })
        assert result == []
