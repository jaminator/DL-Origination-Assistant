"""Mock BizAPI client for local development and testing."""

from uuid import uuid4

from app.miner.enrichment.bizapi.adapter import BizAPIAdapter


class MockBizAPIClient(BizAPIAdapter):
    """Returns synthetic BizAPI data matching the real V2 cosearch response shape."""

    async def match_company(
        self,
        company_name: str,
        *,
        duns: str | None = None,
        website: str | None = None,
        state: str | None = None,
        phone: str | None = None,
    ) -> dict | None:
        # Determine match method based on available data (mirrors API auto-detection)
        if duns:
            match_method = "duns"
            confidence = 1.0  # Confidence Code 10
            match_grade = "ZZZZZZZ"
        elif website:
            match_method = "url"
            confidence = 1.0  # Confidence Code 10
            match_grade = "ZZZZZZZ"
        elif state:
            match_method = "standard"
            confidence = 0.9  # Confidence Code 9
            match_grade = "AABAAAZ"
        else:
            match_method = "name"
            confidence = 0.8  # Confidence Code 8
            match_grade = "AZZZZAZ"

        mock_duns = duns or f"00-{uuid4().hex[:3]}-{uuid4().hex[:4]}"

        return {
            "duns": mock_duns,
            "match_method": match_method,
            "match_confidence": confidence,
            "match_grade": match_grade,
            "bemfab": "M",
            "matches_remaining": 99999,
            "verified_name": company_name,
            "secondary_name": "",
            "verified_address": {
                "street": "123 Mock St",
                "city": "Dallas",
                "state": state or "TX",
                "zip": "75201",
                "country": "US",
            },
            "phone": phone or "2145551234",
            "website": website or f"https://www.{company_name.lower().replace(' ', '')}.com",
            "ceo_name": "Jane Doe",
            "ceo_title": "Chief Executive Officer",
            "line_of_business": "Computer programming, data processing",
            "location_type": "Headquarters",
            "year_started": 2008,
            "employees_on_site": 250,
            "employee_count": 320,
            "sales_volume": 75.0,  # millions
            "naics_code": "541512",
            "naics_description": "Computer Systems Design Services",
            "naics_code_2": "511210",
            "naics_description_2": "Software Publishers",
            "sic_code": "7372",
            "sic_description": "Prepackaged Software",
            "sic_code_2": "7371",
            "sic_description_2": "Computer Services",
            "sic_code_8_1": "73720000",
            "sic_description_8_1": "Prepackaged software",
            "sic_code_8_2": "73710000",
            "sic_description_8_2": "Computer services",
            "corporate_linkage": {
                "subsidiary_indicator": "not a subsidiary site",
                "global_ult": {
                    "indicator": "Y",
                    "duns": mock_duns,
                    "name": company_name,
                    "state": state or "TX",
                    "country": "USA",
                },
                "domestic_ult": {
                    "duns": mock_duns,
                    "name": company_name,
                    "state": state or "TX",
                    "country": "USA",
                },
                "hq_parent": {
                    "parent_duns": "",
                    "hq_duns": "",
                    "name": "",
                    "state": "",
                    "country": "",
                },
                "hierarchy_code": "01",
                "family_member_count": 1,
            },
        }

    async def is_available(self) -> bool:
        return True
