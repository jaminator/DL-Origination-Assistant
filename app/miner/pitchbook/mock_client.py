"""Mock PitchBook client for local development and testing."""

from uuid import uuid4

from app.miner.pitchbook.adapter import PitchBookAdapter


class MockPitchBookClient(PitchBookAdapter):
    """Returns synthetic PitchBook data for local dev without credentials."""

    async def search_company(self, company_name: str) -> dict | None:
        # Return a synthetic match for demo purposes
        return {
            "entity_id": f"pb-{uuid4().hex[:8]}",
            "name": company_name,
            "match_confidence": 0.85,
            "ownership_status": "privately_held",
            "primary_industry": "Business Services",
            "employee_count": 250,
            "revenue_range": "$50M-$100M",
        }

    async def get_company_detail(self, entity_id: str) -> dict:
        return {
            "entity_id": entity_id,
            "description": "Mock company description from PitchBook",
            "founded_year": 2005,
            "hq_location": "Dallas, TX",
            "ownership_type": "founder_owned",
            "investors": [],
            "total_raised": None,
        }

    async def get_competitors(self, entity_id: str) -> list[dict]:
        return [
            {"name": f"Mock Competitor A of {entity_id}", "entity_id": f"pb-comp-{uuid4().hex[:6]}"},
            {"name": f"Mock Competitor B of {entity_id}", "entity_id": f"pb-comp-{uuid4().hex[:6]}"},
        ]

    async def get_debt_details(self, entity_id: str) -> list[dict]:
        return [
            {
                "facility_type": "Term Loan",
                "amount": 75_000_000,
                "lender": "Mock Lender",
                "close_date": "2023-06-15",
                "maturity_date": "2028-06-15",
                "pricing": "S+500",
            }
        ]

    async def is_available(self) -> bool:
        return True
