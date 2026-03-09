"""Association/directory adapter for structured member listings."""

import asyncio

import httpx
from bs4 import BeautifulSoup

from app.miner.sources.base_adapter import SourceAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.directory_adapter")

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


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
            html = await self._fetch_page(url)
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

    async def _fetch_page(self, url: str) -> str:
        """Fetch a directory page with retry and exponential backoff."""
        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; DL-Origination-Assistant/1.0)",
        }
        last_exc: Exception | None = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                    logger.info("directory_fetch_start", url=url, attempt=attempt)
                    resp = await client.get(url, headers=headers)

                    if resp.status_code in RETRYABLE_STATUS_CODES:
                        retry_after = float(resp.headers.get("Retry-After", RETRY_BACKOFF_BASE ** attempt))
                        logger.warning(
                            "directory_retryable_status",
                            url=url,
                            status=resp.status_code,
                            attempt=attempt,
                            retry_after=retry_after,
                        )
                        if attempt < MAX_RETRIES:
                            await asyncio.sleep(retry_after)
                            continue

                    resp.raise_for_status()
                    logger.info(
                        "directory_fetch_complete",
                        url=url,
                        status=resp.status_code,
                        content_length=len(resp.text),
                        attempt=attempt,
                    )
                    return resp.text

            except httpx.TimeoutException as exc:
                logger.warning("directory_timeout", url=url, attempt=attempt)
                last_exc = exc
            except httpx.RequestError as exc:
                logger.warning("directory_request_error", url=url, error=str(exc), attempt=attempt)
                last_exc = exc

            if attempt < MAX_RETRIES:
                await asyncio.sleep(RETRY_BACKOFF_BASE ** attempt)

        raise last_exc or RuntimeError(f"Failed to fetch {url} after {MAX_RETRIES} attempts")

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
