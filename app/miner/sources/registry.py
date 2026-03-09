"""Source registry — manages adapter dispatch for different source types."""

from app.miner.sources.base_adapter import SourceAdapter
from app.miner.sources.web_scraper import WebScraperAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.registry")


class SourceRegistry:
    """Maps source types to their adapter implementations."""

    def __init__(self):
        self._adapters: dict[str, SourceAdapter] = {}
        self._register_defaults()

    def _register_defaults(self) -> None:
        web = WebScraperAdapter()
        # All source types default to web scraper for now
        for stype in [
            "trade_journal",
            "ranking_list",
            "association_directory",
            "certification_directory",
            "dealer_locator",
            "manufacturer_partner",
            "conference_exhibitor",
            "regional_directory",
            "other",
        ]:
            self._adapters[stype] = web

    def register(self, source_type: str, adapter: SourceAdapter) -> None:
        self._adapters[source_type] = adapter

    def get_adapter(self, source_type: str) -> SourceAdapter | None:
        return self._adapters.get(source_type)

    async def extract_from_source(self, source_config: dict) -> list[RawCompany]:
        source_type = source_config.get("source_type", "other")
        adapter = self.get_adapter(source_type)
        if not adapter:
            logger.warning("no_adapter_for_source_type", source_type=source_type)
            return []
        return await adapter.extract_companies(source_config)
