"""Individual QA validation check implementations."""

from app.platform.config.defaults import QA_MIN_DATA_COMPLETENESS, QA_REQUIRED_FIELDS
from app.platform.models.enums import Disposition, OwnershipTier
from app.platform.models.schemas import CompanyRecord


class ValidationResult:
    def __init__(self, passed: bool, check_name: str, message: str = ""):
        self.passed = passed
        self.check_name = check_name
        self.message = message


def check_data_completeness(company: CompanyRecord) -> ValidationResult:
    """Check minimum data completeness threshold."""
    total = len(QA_REQUIRED_FIELDS)
    filled = 0
    for field in QA_REQUIRED_FIELDS:
        val = getattr(company, field, None)
        if val is not None and val != "" and val != [] and val != OwnershipTier.UNKNOWN:
            filled += 1
    ratio = filled / total if total > 0 else 0
    passed = ratio >= QA_MIN_DATA_COMPLETENESS
    return ValidationResult(passed, "data_completeness", f"{filled}/{total} required fields populated ({ratio:.0%})")


def check_unknown_ownership(company: CompanyRecord) -> ValidationResult:
    """Flag companies with unknown ownership on the outreach list."""
    if company.eligible_for_outreach and company.ownership_tier == OwnershipTier.UNKNOWN:
        return ValidationResult(False, "unknown_ownership", "Ownership tier is Unknown for outreach-eligible company")
    return ValidationResult(True, "unknown_ownership")


def check_cascade_anchor_bleed(company: CompanyRecord) -> ValidationResult:
    """Ensure cascade anchors don't appear on the outreach list."""
    if company.disposition == Disposition.CASCADE_ANCHOR and company.eligible_for_outreach:
        return ValidationResult(False, "cascade_anchor_bleed", "Cascade anchor incorrectly marked for outreach")
    return ValidationResult(True, "cascade_anchor_bleed")


def check_mega_cap(company: CompanyRecord) -> ValidationResult:
    """Sanity check: public companies with very high revenue should not be primary candidates."""
    if company.is_public and company.revenue_estimate and company.revenue_estimate > 5000:
        if company.disposition == Disposition.PRIMARY:
            return ValidationResult(False, "mega_cap_sanity", f"Public mega-cap (${company.revenue_estimate}M) as primary")
    return ValidationResult(True, "mega_cap_sanity")


def check_geography(company: CompanyRecord, allowed: list[str] | None = None) -> ValidationResult:
    """Enforce geography filter."""
    geo = allowed or ["US"]
    if company.hq_country and company.hq_country not in geo:
        return ValidationResult(False, "geography", f"HQ country {company.hq_country} not in {geo}")
    return ValidationResult(True, "geography")


def check_score_sanity(company: CompanyRecord) -> ValidationResult:
    """Ensure scores are within valid bounds."""
    if company.total_score is not None:
        if company.total_score < 0 or company.total_score > 100:
            return ValidationResult(False, "score_sanity", f"Score {company.total_score} out of [0, 100] bounds")
    return ValidationResult(True, "score_sanity")
