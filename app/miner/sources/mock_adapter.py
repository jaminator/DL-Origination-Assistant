"""Mock source adapter for local development — returns synthetic company names."""

from app.miner.sources.base_adapter import SourceAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.mock")

# Synthetic companies by source type for realistic local test flows
MOCK_COMPANIES = {
    "trade_journal": [
        ("Apex Data Systems", "Data center infrastructure services provider"),
        ("CoolAir Technologies", "Precision cooling solutions for mission-critical facilities"),
        ("PowerGrid Solutions", "Electrical infrastructure for commercial and industrial buildings"),
        ("FiberConnect Inc", "Dark fiber and connectivity solutions provider"),
        ("SecureVault Services", "Colocation and managed hosting services"),
    ],
    "ranking_list": [
        ("Summit Mechanical Group", "Commercial HVAC and mechanical contracting"),
        ("TitanCore Infrastructure", "Modular data center construction"),
        ("NorthStar Power Systems", "Backup power and UPS systems distributor"),
        ("EdgePoint Technologies", "Edge computing infrastructure services"),
        ("DataFlow Engineering", "Data center design and engineering firm"),
    ],
    "association_directory": [
        ("GreenChill Refrigeration", "Industrial refrigeration and cooling services"),
        ("Patriot Electrical Contractors", "Electrical contracting for critical infrastructure"),
        ("BlueLine Fire Protection", "Fire suppression systems for data centers"),
        ("Continental Cable Systems", "Structured cabling and network infrastructure"),
    ],
    "default": [
        ("Horizon Tech Services", "IT infrastructure managed services"),
        ("PeakPoint Solutions", "Technology consulting and implementation"),
        ("Meridian Systems Group", "Systems integration and managed services"),
    ],
}


class MockSourceAdapter(SourceAdapter):
    """Returns synthetic company data for local development without real web scraping."""

    adapter_type = "mock"

    async def extract_companies(self, source_config: dict) -> list[RawCompany]:
        source_type = source_config.get("source_type", "default")
        source_name = source_config.get("source_name", "unknown")
        subvertical = source_config.get("subvertical", "")

        companies = MOCK_COMPANIES.get(source_type, MOCK_COMPANIES["default"])
        logger.info("mock_extract", source=source_name, count=len(companies))

        return [
            RawCompany(
                raw_name=name,
                source_tag=source_name,
                source_url=source_config.get("url"),
                subvertical=subvertical,
                raw_description=desc,
            )
            for name, desc in companies
        ]

    async def is_available(self, source_config: dict) -> bool:
        return True
