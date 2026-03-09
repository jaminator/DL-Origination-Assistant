"""Dispositioning rules — deterministic classification of companies."""

from app.platform.config.defaults import DEFAULT_CASCADE_ANCHOR_THRESHOLD, DEFAULT_GEOGRAPHY_FILTER, DEFAULT_REVENUE_CEILING
from app.platform.models.enums import Disposition
from app.platform.models.schemas import CompanyRecord
from app.platform.utils.logging import get_logger

logger = get_logger("miner.dispositioning")


def assign_disposition(
    company: CompanyRecord,
    revenue_ceiling: float = DEFAULT_REVENUE_CEILING,
    cascade_anchor_threshold: float = DEFAULT_CASCADE_ANCHOR_THRESHOLD,
    geography_filter: list[str] | None = None,
    boundary_treatment: str = "watch",
) -> Disposition:
    """Assign disposition based on deterministic rules.

    - Revenue > cascade_anchor_threshold → CASCADE_ANCHOR
    - Revenue > revenue_ceiling → CASCADE_ANCHOR (same effect)
    - Out of geography → EXCLUDE
    - No meaningful industry signal → EXCLUDE
    - Boundary cases → configurable (watch/include/exclude/review)
    """
    geo = geography_filter or DEFAULT_GEOGRAPHY_FILTER

    # Geography check
    if company.hq_country and company.hq_country not in geo:
        return Disposition.EXCLUDE

    # Public mega-cap check (before cascade anchor — these are never lending targets)
    if company.is_public is True and company.revenue_estimate and company.revenue_estimate > 5000:
        return Disposition.EXCLUDE

    # Revenue-based disposition (deterministic)
    if company.revenue_estimate is not None:
        if company.revenue_estimate > cascade_anchor_threshold:
            return Disposition.CASCADE_ANCHOR

        if company.revenue_estimate > revenue_ceiling:
            return Disposition.CASCADE_ANCHOR

        # Boundary: very small or very large relative to target
        if company.revenue_estimate < 5.0:  # Under $5M — likely too small
            return Disposition.EXCLUDE

    return Disposition.PRIMARY
