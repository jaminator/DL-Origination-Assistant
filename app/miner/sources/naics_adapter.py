"""NAICS-based source adapter for company discovery by industry code."""

from app.miner.sources.base_adapter import SourceAdapter
from app.platform.models.schemas import RawCompany
from app.platform.utils.logging import get_logger

logger = get_logger("miner.sources.naics_adapter")

# Static NAICS code → industry description mapping (common direct lending verticals)
NAICS_DESCRIPTIONS = {
    "238210": "Electrical Contractors and Other Wiring Installation",
    "238220": "Plumbing, Heating, and Air-Conditioning Contractors",
    "236220": "Commercial and Institutional Building Construction",
    "423430": "Computer Equipment Merchant Wholesalers",
    "423610": "Electrical Equipment Merchant Wholesalers",
    "518210": "Data Processing, Hosting, and Related Services",
    "541511": "Custom Computer Programming Services",
    "541512": "Computer Systems Design Services",
    "541513": "Computer Facilities Management Services",
    "541330": "Engineering Services",
    "541611": "Administrative Management Consulting",
    "541618": "Other Management Consulting",
    "561210": "Facilities Support Services",
    "238910": "Site Preparation Contractors",
    "334111": "Electronic Computer Manufacturing",
    "334112": "Computer Storage Device Manufacturing",
    "334210": "Telephone Apparatus Manufacturing",
    "334290": "Other Communications Equipment Manufacturing",
    "335311": "Power, Distribution, and Specialty Transformer Manufacturing",
    "335999": "All Other Miscellaneous Electrical Equipment",
}


class NAICSAdapter(SourceAdapter):
    """Adapter that uses NAICS codes to identify relevant company types.

    This adapter doesn't scrape live data — it generates research targets
    based on NAICS codes associated with confirmed sub-verticals.
    The generated entries serve as seeds for web enrichment.
    """

    adapter_type = "naics"

    async def extract_companies(self, source_config: dict) -> list[RawCompany]:
        """Generate research targets from NAICS code mappings."""
        naics_codes = source_config.get("naics_codes", [])
        source_name = source_config.get("source_name", "NAICS Lookup")
        subvertical = source_config.get("subvertical", "")

        if not naics_codes:
            logger.warning("naics_no_codes", source=source_name)
            return []

        logger.info("naics_extract", codes=naics_codes, source=source_name)

        companies = []
        for code in naics_codes:
            desc = NAICS_DESCRIPTIONS.get(code)
            if desc:
                companies.append(
                    RawCompany(
                        raw_name=f"[NAICS {code}] {desc}",
                        source_tag=f"{source_name}:NAICS-{code}",
                        subvertical=subvertical,
                        extra={"naics_code": code, "naics_description": desc},
                    )
                )

        logger.info("naics_complete", source=source_name, targets=len(companies))
        return companies

    async def is_available(self, source_config: dict) -> bool:
        """NAICS adapter is always available (static data)."""
        return True
