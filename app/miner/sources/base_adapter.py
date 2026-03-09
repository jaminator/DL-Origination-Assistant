"""Abstract source adapter interface for company name extraction."""

from abc import ABC, abstractmethod

from app.platform.models.schemas import RawCompany


class SourceAdapter(ABC):
    """Base class for all source ingestion adapters."""

    adapter_type: str = ""

    @abstractmethod
    async def extract_companies(self, source_config: dict) -> list[RawCompany]:
        """Extract company names from this source.

        Args:
            source_config: Source configuration including URL, type, etc.

        Returns:
            List of raw (unnormalized) company records.
        """
        ...

    @abstractmethod
    async def is_available(self, source_config: dict) -> bool:
        """Check if this source is currently accessible."""
        ...
