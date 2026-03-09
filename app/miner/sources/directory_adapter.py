"""Association/directory adapter for structured member listings."""

import httpx
from bs4 import BeautifulSoup

from app.miner.sources.base_adapter import SourceAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.directory_adapter")


class DirectoryAdapter(SourceAdapter):
    """Adapter for association/directory member listings.

    Handles structured directories that list member companies,
    typically with consistent formatting per entry.
    """

    adapter_type = "directory"

    async def extract_companies(self, source_config: dict) -> list[RawCompany]:
        """Extract member companies from a directory listing."""
        url = source_config.get("url")
        if not url:
            logger.warning("directory_no_url", source=source_config.get("source_name"))
            return []

        source_name = source_config.get("source_name", url)
        subvertical = source_config.get("subvertical", "")
        member_selector = source_config.get("member_selector", ".member, .company, .listing")

        logger.info("directory_extract", url=url, source=source_name)

        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (compatible; DL-Origination-Assistant/1.0)",
                })
                resp.raise_for_status()
                html = resp.text
        except Exception as e:
            logger.error("directory_fetch_failed", url=url, error=str(e))
            return []

        soup = BeautifulSoup(html, "html.parser")
        elements = soup.select(member_selector)

        companies = []
        seen = set()
        for el in elements:
            # Try to get company name from heading or first text
            name_el = el.find(["h2", "h3", "h4", "a", "strong", "b"])
            name = (name_el.get_text(strip=True) if name_el else el.get_text(strip=True))

            if not name or len(name) < 3 or name.lower() in seen:
                continue
            seen.add(name.lower())

            companies.append(
                RawCompany(
                    raw_name=name,
                    source_tag=source_name,
                    source_url=url,
                    subvertical=subvertical,
                )
            )

        logger.info("directory_complete", url=url, extracted=len(companies))
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
