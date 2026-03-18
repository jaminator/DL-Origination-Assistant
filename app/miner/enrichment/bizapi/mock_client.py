"""Mock BizAPI client for local development and testing."""

from uuid import uuid4

from app.miner.enrichment.bizapi.adapter import BizAPIAdapter


class MockBizAPIClient(BizAPIAdapter):
    """Returns synthetic BizAPI data for local dev without credentials."""

    async def match_company(
        self,
        company_name: str,
        *,
        duns: str | None = None,
        website: str | None = None,
        state: str | None = None,
        phone: str | None = None,
    ) -> dict | None:
        # Determine match method based on available data
        if duns:
            match_method = "duns"
            confidence = 0.98
        elif website:
            match_method = "url"
            confidence = 0.92
        elif state:
            match_method = "standard"
            confidence = 0.85
        else:
            match_method = "name"
            confidence = 0.70

        return {
            "duns": duns or f"00-{uuid4().hex[:7]}",
            "match_method": match_method,
            "match_confidence": confidence,
            "verified_name": company_name,
            "verified_address": {
                "street": "123 Mock St",
                "city": "Dallas",
                "state": state or "TX",
                "zip": "75201",
                "country": "US",
            },
            "naics_code": "541512",
            "naics_description": "Computer Systems Design Services",
            "sic_code": "7372",
            "sic_description": "Prepackaged Software",
            "year_started": 2008,
            "employee_count": 250,
            "sales_volume": 75.0,  # millions
            "website": website or f"https://www.{company_name.lower().replace(' ', '')}.com",
            "corporate_linkage": {
                "parent_duns": None,
                "parent_name": None,
                "subsidiary_count": 0,
            },
        }

    async def is_available(self) -> bool:
        return True
