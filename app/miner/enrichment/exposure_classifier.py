"""Industry exposure intensity classification."""

from app.platform.utils.logging import get_logger

logger = get_logger("miner.enrichment.exposure_classifier")

# Exposure intensity keywords (high > medium > low)
HIGH_EXPOSURE_SIGNALS = [
    "primary", "core", "exclusive", "dedicated", "specialized",
    "100%", "majority", "sole focus", "only serves",
]

MEDIUM_EXPOSURE_SIGNALS = [
    "significant", "substantial", "growing", "expanding",
    "division", "segment", "unit", "practice",
    "partial", "some", "includes",
]

LOW_EXPOSURE_SIGNALS = [
    "minor", "minimal", "small portion", "tangential",
    "incidental", "peripheral", "limited exposure",
    "diversified", "conglomerate",
]


def classify_exposure_intensity(
    description: str | None = None,
    subvertical_tags: list[str] | None = None,
    industry_descriptor: str | None = None,
    revenue_from_sector: float | None = None,
) -> str:
    """Classify a company's industry exposure intensity.

    Uses multiple signals:
    - Free-text description keywords
    - Revenue concentration from sector (if available)
    - Industry descriptor from enrichment

    Returns: "high", "medium", "low", or "unknown"
    """
    # Revenue concentration is the strongest signal
    if revenue_from_sector is not None:
        if revenue_from_sector >= 0.7:
            return "high"
        if revenue_from_sector >= 0.3:
            return "medium"
        return "low"

    # Keyword-based classification from description
    text = " ".join(filter(None, [
        description,
        industry_descriptor,
        " ".join(subvertical_tags or []),
    ])).lower()

    if not text:
        return "unknown"

    high_count = sum(1 for kw in HIGH_EXPOSURE_SIGNALS if kw in text)
    medium_count = sum(1 for kw in MEDIUM_EXPOSURE_SIGNALS if kw in text)
    low_count = sum(1 for kw in LOW_EXPOSURE_SIGNALS if kw in text)

    if high_count > medium_count and high_count > low_count:
        return "high"
    if low_count > medium_count and low_count > high_count:
        return "low"
    if medium_count > 0:
        return "medium"

    # Default: if company has subvertical tags, assume at least medium
    if subvertical_tags:
        return "medium"

    return "unknown"


def compute_exposure_score(intensity: str) -> float:
    """Convert exposure intensity to a numeric score (0-1)."""
    return {
        "high": 1.0,
        "medium": 0.6,
        "low": 0.3,
        "unknown": 0.0,
    }.get(intensity, 0.0)
