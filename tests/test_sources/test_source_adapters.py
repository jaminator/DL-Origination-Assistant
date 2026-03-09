"""Tests for source adapters: NAICS, mock, web scraper heuristics."""


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
