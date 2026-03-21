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
            "name": "Mock Company",
            "description": "Mock company description from PitchBook",
            "founded_year": 2005,
            "hq_location": "Dallas, TX",
            "ownership_type": "founder_owned",
            "financing_status": "Generating Revenue",
            "total_raised": 25.0,
            "investors": [],
            "last_financing_date": None,
            "last_financing_type": None,
            "status": "Active",
            "also_known_as": "",
            "sic_codes": [],
        }

    async def get_competitors(self, entity_id: str) -> list[dict]:
        return [
            {
                "name": f"Mock Competitor A of {entity_id}",
                "entity_id": f"pb-comp-{uuid4().hex[:6]}",
                "primary_industry": "Business Services",
                "employee_count": 200,
                "hq_location": "Austin, TX",
                "similarity_score": 0.92,
                "is_competitor": True,
            },
            {
                "name": f"Mock Competitor B of {entity_id}",
                "entity_id": f"pb-comp-{uuid4().hex[:6]}",
                "primary_industry": "Technology",
                "employee_count": 150,
                "hq_location": "Denver, CO",
                "similarity_score": 0.85,
                "is_competitor": True,
            },
        ]

    async def get_debt_details(self, entity_id: str) -> list[dict]:
        return [
            {
                "deal_id": f"d-{uuid4().hex[:6]}",
                "facility_type": "Term Loan",
                "amount": 75_000_000,
                "lender": "Mock Lender",
                "close_date": "2023-06-15",
                "maturity_date": "2028-06-15",
                "pricing": "S+500",
                "status": "Closed",
            }
        ]

    async def get_financials(self, entity_id: str) -> dict | None:
        return {
            "revenue": 80.0,
            "ebitda": 16.0,
            "ebit": 12.0,
            "net_income": 8.0,
            "enterprise_value": 400.0,
            "total_debt": 100.0,
            "net_debt": 85.0,
        }

    async def get_most_recent_debt_financing(self, entity_id: str) -> dict | None:
        return {
            "deal_id": f"d-{uuid4().hex[:6]}",
            "seniority": "Senior Secured",
            "security": "First Lien",
            "spread": "S+450",
            "maturity_date": "2028-12-31",
            "deal_size": 75.0,
            "lender": "Mock Capital Partners",
            "close_date": "2023-06-15",
        }

    async def get_active_investors(self, entity_id: str) -> list[dict]:
        return [
            {
                "entity_id": f"inv-{uuid4().hex[:6]}",
                "name": "Mock Growth Partners",
                "type": "Private Equity",
            },
            {
                "entity_id": f"inv-{uuid4().hex[:6]}",
                "name": "Mock Venture Fund",
                "type": "Venture Capital",
            },
        ]

    async def get_similar_companies(self, entity_id: str) -> list[dict]:
        return [
            {
                "entity_id": f"pb-sim-{uuid4().hex[:6]}",
                "name": "Mock Similar Co A",
                "primary_industry": "Business Services",
                "employee_count": 300,
                "hq_location": "Chicago, IL",
                "similarity_score": 0.94,
                "is_competitor": True,
            },
            {
                "entity_id": f"pb-sim-{uuid4().hex[:6]}",
                "name": "Mock Similar Co B",
                "primary_industry": "Technology",
                "employee_count": 180,
                "hq_location": "Seattle, WA",
                "similarity_score": 0.88,
                "is_competitor": False,
            },
        ]

    async def is_available(self) -> bool:
        return True
