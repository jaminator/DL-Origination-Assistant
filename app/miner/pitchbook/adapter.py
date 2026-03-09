"""Abstract PitchBook adapter interface."""

from abc import ABC, abstractmethod


class PitchBookAdapter(ABC):
    """Interface for PitchBook company enrichment."""

    @abstractmethod
    async def search_company(self, company_name: str) -> dict | None:
        """Search PitchBook by company name. Returns match data or None."""
        ...

    @abstractmethod
    async def get_company_detail(self, entity_id: str) -> dict:
        """Get full company detail by PitchBook entity ID."""
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
    async def is_available(self) -> bool:
        ...
