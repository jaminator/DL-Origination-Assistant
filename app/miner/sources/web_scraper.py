"""Generic web scraper adapter for company name extraction."""

import re

import httpx
from bs4 import BeautifulSoup

from app.miner.sources.base_adapter import SourceAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.web_scraper")

# Common patterns for company lists on web pages
COMPANY_LIST_SELECTORS = [
    "table tbody tr",        # Table rows
    "ol li",                 # Ordered lists
    "ul.companies li",       # Company-specific lists
    ".company-name",         # Class-based
    "[data-company]",        # Data attribute
    ".ranking-list li",      # Ranking lists
    "h3",                    # Section headers (some directories)
]

# Patterns to filter noise from extracted text
NOISE_PATTERNS = re.compile(
    r"^(home|about|contact|privacy|terms|copyright|menu|search|login|sign|cookie|©|\d+\.\s*$)",
    re.IGNORECASE,
)


class WebScraperAdapter(SourceAdapter):
    """Generic web scraper using httpx + BeautifulSoup.

    Extracts company names from web pages by trying multiple CSS selectors
    and heuristics. Works best with structured pages (tables, lists, directories).
    """

    adapter_type = "web_scraper"

    async def extract_companies(self, source_config: dict) -> list[RawCompany]:
        """Scrape company names from a web source."""
        url = source_config.get("url")
        if not url:
            logger.warning("web_scraper_no_url", source=source_config.get("source_name"))
            return []

        source_name = source_config.get("source_name", url)
        subvertical = source_config.get("subvertical", "")
        custom_selector = source_config.get("css_selector")

        logger.info("web_scraper_extract", url=url, source=source_name)

        try:
            html = await self._fetch_page(url)
        except Exception as e:
            logger.error("web_scraper_fetch_failed", url=url, error=str(e))
            return []

        soup = BeautifulSoup(html, "html.parser")

        # Try custom selector first, then fall back to heuristics
        if custom_selector:
            names = self._extract_with_selector(soup, custom_selector)
        else:
            names = self._extract_with_heuristics(soup)

        # Deduplicate and filter
        seen = set()
        companies = []
        for name in names:
            cleaned = self._clean_name(name)
            if not cleaned or cleaned.lower() in seen:
                continue
            if NOISE_PATTERNS.match(cleaned):
                continue
            if len(cleaned) < 3 or len(cleaned) > 200:
                continue
            seen.add(cleaned.lower())
            companies.append(
                RawCompany(
                    raw_name=cleaned,
                    source_tag=source_name,
                    source_url=url,
                    subvertical=subvertical,
                )
            )

        logger.info("web_scraper_complete", url=url, extracted=len(companies))
        return companies

    async def is_available(self, source_config: dict) -> bool:
        url = source_config.get("url")
        if not url:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.head(url, follow_redirects=True)
                return resp.status_code < 400
        except Exception:
            return False

    async def _fetch_page(self, url: str) -> str:
        """Fetch a web page with reasonable defaults."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DL-Origination-Assistant/1.0)",
            "Accept": "text/html,application/xhtml+xml",
        }
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers=headers)
            resp.raise_for_status()
            return resp.text

    def _extract_with_selector(self, soup: BeautifulSoup, selector: str) -> list[str]:
        """Extract text from elements matching a CSS selector."""
        elements = soup.select(selector)
        return [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]

    def _extract_with_heuristics(self, soup: BeautifulSoup) -> list[str]:
        """Try multiple selectors and pick the one that yields the best results."""
        best_names: list[str] = []
        best_score = 0

        for selector in COMPANY_LIST_SELECTORS:
            try:
                names = self._extract_with_selector(soup, selector)
                # Score: more items is better, but filter noise
                filtered = [n for n in names if not NOISE_PATTERNS.match(n) and 3 <= len(n) <= 200]
                score = len(filtered)
                if score > best_score:
                    best_score = score
                    best_names = filtered
            except Exception:
                continue

        # If no selector worked well, try extracting from bold/strong tags in lists
        if best_score < 3:
            for tag in ["b", "strong"]:
                elements = soup.find_all(tag)
                names = [el.get_text(strip=True) for el in elements if el.get_text(strip=True)]
                filtered = [n for n in names if not NOISE_PATTERNS.match(n) and 3 <= len(n) <= 200]
                if len(filtered) > best_score:
                    best_names = filtered

        return best_names

    def _clean_name(self, name: str) -> str:
        """Clean extracted text to get a company name."""
        # Remove leading numbers/rankings (e.g., "1. Acme Corp" -> "Acme Corp")
        cleaned = re.sub(r"^\d+[\.\)\-\s]+", "", name)
        # Remove trailing metadata in parens if very long
        if "(" in cleaned and len(cleaned) > 100:
            cleaned = cleaned[:cleaned.index("(")].strip()
        # Collapse whitespace
        cleaned = " ".join(cleaned.split())
        return cleaned.strip()
