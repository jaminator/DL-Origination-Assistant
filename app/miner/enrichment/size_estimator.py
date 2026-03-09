"""Revenue and employee size estimation from web signals."""

import re

from app.platform.utils.logging import get_logger

logger = get_logger("miner.enrichment.size_estimator")

# Revenue band definitions (in millions USD)
REVENUE_BANDS = [
    (0, 10, "Under $10M"),
    (10, 25, "$10M-$25M"),
    (25, 50, "$25M-$50M"),
    (50, 100, "$50M-$100M"),
    (100, 250, "$100M-$250M"),
    (250, 500, "$250M-$500M"),
    (500, 1000, "$500M-$1B"),
    (1000, 5000, "$1B-$5B"),
    (5000, float("inf"), "$5B+"),
]

# Employee-to-revenue multipliers by industry type (revenue per employee, $K)
INDUSTRY_REVENUE_PER_EMPLOYEE = {
    "technology": 350,
    "software": 400,
    "manufacturing": 250,
    "services": 200,
    "consulting": 180,
    "construction": 300,
    "healthcare": 220,
    "distribution": 500,
    "default": 250,
}

# Patterns for extracting revenue mentions from text
REVENUE_PATTERNS = [
    # "$X million" / "$X billion"
    re.compile(r"\$\s*([\d,.]+)\s*(million|billion|MM|M|B|bn)", re.IGNORECASE),
    # "revenue of $X"
    re.compile(r"revenue[s]?\s+(?:of\s+)?\$\s*([\d,.]+)\s*(million|billion|MM|M|B|bn)?", re.IGNORECASE),
    # "XM in revenue"
    re.compile(r"([\d,.]+)\s*(million|billion|MM|M|B|bn)\s+(?:in\s+)?revenue", re.IGNORECASE),
]


def estimate_revenue_from_employees(
    employee_count: int,
    industry: str | None = None,
) -> tuple[float | None, str]:
    """Estimate revenue from employee count using industry multipliers.

    Returns (estimate_millions, revenue_band).
    """
    if not employee_count or employee_count <= 0:
        return None, ""

    multiplier = INDUSTRY_REVENUE_PER_EMPLOYEE.get(
        (industry or "").lower(),
        INDUSTRY_REVENUE_PER_EMPLOYEE["default"],
    )

    estimate = (employee_count * multiplier) / 1000  # Convert from $K to $M
    band = classify_revenue_band(estimate)
    return round(estimate, 1), band


def classify_revenue_band(revenue_millions: float | None) -> str:
    """Classify a revenue figure into a band."""
    if revenue_millions is None:
        return ""
    for low, high, label in REVENUE_BANDS:
        if low <= revenue_millions < high:
            return label
    return REVENUE_BANDS[-1][2]  # $5B+


def extract_revenue_from_text(text: str) -> float | None:
    """Extract revenue estimate from free-form text.

    Returns revenue in millions, or None if no signal found.
    """
    if not text:
        return None

    for pattern in REVENUE_PATTERNS:
        match = pattern.search(text)
        if match:
            value_str = match.group(1).replace(",", "")
            try:
                value = float(value_str)
            except ValueError:
                continue

            unit = (match.group(2) or "").lower() if match.lastindex >= 2 else ""
            if unit in ("billion", "b", "bn"):
                return value * 1000  # Convert to millions
            elif unit in ("million", "m", "mm", ""):
                return value

    return None


def estimate_employee_band(employee_count: int | None) -> str:
    """Classify employee count into a band."""
    if not employee_count:
        return ""
    if employee_count < 50:
        return "Under 50"
    if employee_count < 200:
        return "50-200"
    if employee_count < 500:
        return "200-500"
    if employee_count < 1000:
        return "500-1K"
    if employee_count < 5000:
        return "1K-5K"
    return "5K+"
