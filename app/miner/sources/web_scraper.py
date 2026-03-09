"""Generic web scraper adapter for company name extraction."""

import httpx

from app.miner.sources.base_adapter import SourceAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.web_scraper")


class WebScraperAdapter(SourceAdapter):
    """Generic web scraper using httpx + basic HTML parsing."""

    adapter_type = "web_scraper"

    async def extract_companies(self, source_config: dict) -> list[RawCompany]:
        """Scrape company names from a web source.

        TODO: Implement real scraping logic per source type.
        Currently returns empty list as a stub.
        """
        url = source_config.get("url")
        if not url:
            logger.warning("web_scraper_no_url", source=source_config.get("source_name"))
            return []

        logger.info("web_scraper_extract", url=url)
        # TODO: Implement actual web scraping with BeautifulSoup
        # This is a stub — real implementation depends on source structure
        return []

    async def is_available(self, source_config: dict) -> bool:
        url = source_config.get("url")
        if not url:
            return False
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.head(url)
                return resp.status_code < 400
        except Exception:
            return False
