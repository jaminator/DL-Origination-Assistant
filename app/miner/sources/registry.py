"""Source registry — manages adapter dispatch for different source types."""

from app.miner.sources.base_adapter import SourceAdapter
from app.miner.sources.directory_adapter import DirectoryAdapter
from app.miner.sources.naics_adapter import NAICSAdapter
from app.miner.sources.web_scraper import WebScraperAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.registry")

# Source types that use the directory adapter (structured member listings)
DIRECTORY_SOURCE_TYPES = {
    "association_directory",
    "certification_directory",
    "regional_directory",
}

# Source types that use the web scraper (unstructured pages, ranking lists)
WEB_SCRAPER_SOURCE_TYPES = {
    "trade_journal",
    "ranking_list",
    "dealer_locator",
    "manufacturer_partner",
    "conference_exhibitor",
    "other",
}


class SourceRegistry:
    """Maps source types to their adapter implementations."""

    def __init__(self, use_mock: bool | None = None):
        self._adapters: dict[str, SourceAdapter] = {}
        # Auto-detect mock mode from settings if not explicitly set
        if use_mock is None:
            from app.platform.config.settings import settings
            use_mock = settings.llm_provider == "mock"
        self._use_mock = use_mock
        self._register_defaults()

    def _register_defaults(self) -> None:
        if self._use_mock:
            from app.miner.sources.mock_adapter import MockSourceAdapter
            mock = MockSourceAdapter()
            for stype in WEB_SCRAPER_SOURCE_TYPES | DIRECTORY_SOURCE_TYPES | {"naics_source"}:
                self._adapters[stype] = mock
        else:
            web_scraper = WebScraperAdapter()
            directory = DirectoryAdapter()
            naics = NAICSAdapter()
            for stype in WEB_SCRAPER_SOURCE_TYPES:
                self._adapters[stype] = web_scraper
            for stype in DIRECTORY_SOURCE_TYPES:
                self._adapters[stype] = directory
            self._adapters["naics_source"] = naics

    def register(self, source_type: str, adapter: SourceAdapter) -> None:
        self._adapters[source_type] = adapter

    def get_adapter(self, source_type: str) -> SourceAdapter | None:
        return self._adapters.get(source_type, self._adapters.get("other"))

    async def extract_from_source(self, source_config: dict) -> list[RawCompany]:
        source_type = source_config.get("source_type", "other")
        adapter = self.get_adapter(source_type)
        if not adapter:
            logger.warning("no_adapter_for_source_type", source_type=source_type)
            return []
        return await adapter.extract_companies(source_config)
