"""Abstract PitchBook adapter interface."""

from abc import ABC, abstractmethod


class PitchBookAdapter(ABC):
    """Interface for PitchBook company enrichment.

    Maps to PitchBook Premium Data API v2 endpoints:
      - GET /companies/search          → search_company()
      - GET /companies/{pbId}/bio      → get_company_detail()
      - GET /companies/{pbId}/similar-companies → get_competitors()
      - GET /companies/{pbId}/deals    → get_debt_details()
      - GET /companies/{pbId}/financials → get_financials()
      - GET /companies/{pbId}/most-recent-debt-financing → get_most_recent_debt_financing()
      - GET /companies/{pbId}/active-investors → get_active_investors()
      - GET /companies/{pbId}/similar-companies → get_similar_companies()
    """

    @abstractmethod
    async def search_company(self, company_name: str) -> dict | None:
        """Search PitchBook by company name. Returns match data or None."""
        ...

    @abstractmethod
    async def get_company_detail(self, entity_id: str) -> dict:
        """Get company bio by PitchBook entity ID."""
        ...

    @abstractmethod
    async def get_competitors(self, entity_id: str) -> list[dict]:
        """Get competitor/similar company list."""
        ...

    @abstractmethod
    async def get_debt_details(self, entity_id: str) -> list[dict]:
        """Get debt/capital structure details."""
        ...

    @abstractmethod
    async def get_financials(self, entity_id: str) -> dict | None:
        """Get private company financials (revenue, EBITDA, etc.)."""
        ...

    @abstractmethod
    async def get_most_recent_debt_financing(self, entity_id: str) -> dict | None:
        """Get most recent debt financing details (seniority, spread, maturity)."""
        ...

    @abstractmethod
    async def get_active_investors(self, entity_id: str) -> list[dict]:
        """Get current active investors."""
        ...

    @abstractmethod
    async def get_similar_companies(self, entity_id: str) -> list[dict]:
        """Get similar companies with similarity scores."""
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        ...
