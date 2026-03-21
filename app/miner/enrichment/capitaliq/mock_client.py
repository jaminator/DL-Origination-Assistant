"""Mock Capital IQ client for local development and testing."""

from uuid import uuid4

from app.miner.enrichment.capitaliq.adapter import CapitalIQAdapter


class MockCapitalIQClient(CapitalIQAdapter):
    """Returns synthetic Capital IQ data for local dev without credentials."""

    async def search_company(self, company_name: str, *, duns: str | None = None) -> dict | None:
        return {
            "entity_id": f"ciq-{uuid4().hex[:8]}",
            "name": company_name,
            "match_confidence": 0.88,
            "primary_industry": "Application Software",
            "hq_location": "Dallas, TX, US",
        }

    async def get_financials(self, entity_id: str) -> dict:
        return {
            "entity_id": entity_id,
            "revenue": 80.0,  # millions
            "ebitda": 16.0,  # millions
            "total_debt": 45.0,  # millions
            "net_debt": 38.0,  # millions
            "credit_metrics": {
                "total_leverage": 2.8,
                "net_leverage": 2.4,
                "interest_coverage": 4.5,
            },
        }

    async def get_ownership(self, entity_id: str) -> dict:
        return {
            "entity_id": entity_id,
            "ownership_type": "founder_owned",
            "key_investors": [],
            "ma_history": [
                {
                    "date": "2021-03-15",
                    "type": "Acquisition",
                    "target": "Mock Acquired Co",
                    "value": 12.5,
                },
            ],
        }

    async def get_company_profile(self, entity_id: str) -> dict:
        return {
            "entity_id": entity_id,
            "gics_code": "45101010",
            "sic_code": "7372",
            "company_status": "Operating",
            "industry_sector": "Information Technology",
        }

    async def is_available(self) -> bool:
        return True
