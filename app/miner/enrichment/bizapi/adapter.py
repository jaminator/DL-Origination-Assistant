"""Abstract BizAPI adapter interface for company verification and firmographic enrichment."""

from abc import ABC, abstractmethod


class BizAPIAdapter(ABC):
    """Interface for NAICS BizAPI company enrichment.

    BizAPI provides company verification, NAICS/SIC codes, firmographic data
    (employee count, sales volume, year started), and corporate linkage.
    """

    @abstractmethod
    async def match_company(
        self,
        company_name: str,
        *,
        duns: str | None = None,
        website: str | None = None,
        state: str | None = None,
        phone: str | None = None,
    ) -> dict | None:
        """Match a company using the best available method.

        Match method priority: DUNS > URL > Standard (name+state) > Name > Phone > Loose.
        Returns match data including DUNS, confidence, firmographics, or None if no match.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if BizAPI credentials are configured and endpoint is reachable."""
        ...
