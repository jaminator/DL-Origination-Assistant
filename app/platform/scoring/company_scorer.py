"""Company-level borrower scoring — deterministic weighted formula."""

from app.platform.config.defaults import SCORING_WEIGHTS
from app.platform.models.enums import OwnershipTier
from app.platform.models.schemas import CompanyRecord
from app.platform.utils.logging import get_logger

logger = get_logger("scoring.company")


def score_company(
    company: CompanyRecord,
    weights: dict | None = None,
    tier_a_bonus: float = 15.0,
    tier_b_bonus: float = 8.0,
    tier_c_bonus: float = 0.0,
) -> tuple[float, dict[str, float]]:
    """Score a company on borrower attractiveness. Returns (total_score, component_scores).

    Deterministic: given the same inputs, always returns the same score.
    Missing data does NOT silently award maximum points.
    """
    w = weights or SCORING_WEIGHTS
    components: dict[str, float] = {}

    # Revenue scale (0-100 raw, weighted)
    rev_raw = _score_revenue_scale(company.revenue_estimate)
    components["revenue_scale"] = rev_raw * w.get("revenue_scale", 20) / 100

    # EBITDA margin (0-100 raw, weighted) — soft, best-effort
    margin_raw = _score_ebitda_margin(company.ebitda_estimate, company.revenue_estimate)
    components["ebitda_margin"] = margin_raw * w.get("ebitda_margin", 15) / 100

    # Recurring revenue (0-100 raw, weighted)
    recur_raw = _score_recurring_revenue(company.recurring_revenue_estimate, company.revenue_estimate)
    components["recurring_revenue"] = recur_raw * w.get("recurring_revenue", 15) / 100

    # Industry exposure (0-100 raw, weighted)
    exposure_raw = _score_exposure(company.industry_exposure_intensity)
    components["industry_exposure"] = exposure_raw * w.get("industry_exposure", 20) / 100

    # Ownership tier bonus
    tier_bonus = _ownership_bonus(company.ownership_tier, tier_a_bonus, tier_b_bonus, tier_c_bonus)
    components["ownership_tier"] = tier_bonus

    # Data completeness (0-100 raw, weighted)
    completeness_raw = _score_completeness(company)
    components["data_completeness"] = completeness_raw * w.get("data_completeness", 15) / 100

    total = sum(components.values())

    # Sanity bounds
    total = max(0.0, min(100.0, total))

    return total, components


def _score_revenue_scale(revenue: float | None) -> float:
    """Score revenue on a 0-100 scale. Sweet spot: $50M-$500M."""
    if revenue is None:
        return 25.0  # Partial credit — not zero, not max
    if revenue < 10:
        return 20.0
    if revenue < 50:
        return 50.0
    if revenue <= 500:
        return 90.0
    if revenue <= 1000:
        return 70.0
    return 40.0  # Over $1B, still gets some credit if somehow present


def _score_ebitda_margin(ebitda: float | None, revenue: float | None) -> float:
    if ebitda is None or revenue is None or revenue == 0:
        return 30.0  # Partial credit for missing data
    margin = ebitda / revenue
    if margin >= 0.20:
        return 95.0
    if margin >= 0.15:
        return 85.0
    if margin >= 0.10:
        return 70.0
    if margin >= 0.05:
        return 50.0
    return 30.0


def _score_recurring_revenue(recurring: float | None, revenue: float | None) -> float:
    if recurring is None or revenue is None or revenue == 0:
        return 25.0
    ratio = recurring / revenue
    if ratio >= 0.7:
        return 95.0
    if ratio >= 0.5:
        return 80.0
    if ratio >= 0.3:
        return 60.0
    return 35.0


def _score_exposure(intensity: str | None) -> float:
    mapping = {"high": 95.0, "medium": 65.0, "low": 35.0}
    return mapping.get((intensity or "").lower(), 30.0)


def _ownership_bonus(tier: OwnershipTier, a: float, b: float, c: float) -> float:
    bonuses = {
        OwnershipTier.TIER_A: a,
        OwnershipTier.TIER_B: b,
        OwnershipTier.TIER_C: c,
        OwnershipTier.UNKNOWN: 0.0,
    }
    return bonuses.get(tier, 0.0)


def _score_completeness(company: CompanyRecord) -> float:
    """Score based on how many key fields are populated."""
    fields = [
        company.canonical_name,
        company.hq_state,
        company.subvertical_tags,
        company.industry_exposure_descriptor,
        company.revenue_estimate,
        company.ownership_tier != OwnershipTier.UNKNOWN,
        company.website,
    ]
    filled = sum(1 for f in fields if f)
    return (filled / len(fields)) * 100
