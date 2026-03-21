"""Abstract Capital IQ adapter interface for private-market financial enrichment.

Capital IQ uses the SPQL (S&P Query Language) paradigm — all data is fetched
via POST requests with ``inputRequests`` arrays specifying mnemonics (e.g.
``IQ_TOTAL_REV``, ``IQ_EBITDA``, ``IQ_COMPANY_NAME``).  The adapter methods
abstract over this, presenting a clean interface to the pipeline.
"""

from abc import ABC, abstractmethod


class CapitalIQAdapter(ABC):
    """Interface for S&P Capital IQ private-market data enrichment.

    Capital IQ provides audited financials (revenue, EBITDA), debt metrics,
    ownership classification, investor lists, M&A history, and credit metrics.
    """

    @abstractmethod
    async def search_company(self, company_name: str, *, duns: str | None = None) -> dict | None:
        """Search Capital IQ for a company by name or DUNS.

        Returns match data including CIQ entity ID and basic profile, or None.
        """
        ...

    @abstractmethod
    async def get_financials(self, entity_id: str) -> dict:
        """Get financial data for a matched company.

        Returns revenue, EBITDA, debt metrics, and credit ratios.
        """
        ...

    @abstractmethod
    async def get_ownership(self, entity_id: str) -> dict:
        """Get ownership and investor data.

        Returns ownership type, key investors, and M&A history.
        """
        ...

    @abstractmethod
    async def get_company_profile(self, entity_id: str) -> dict:
        """Get company profile data (industry, status, classification).

        Returns GICS code, SIC code, company status, and industry sector.
        """
        ...

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if Capital IQ credentials are configured and endpoint is reachable."""
        ...
