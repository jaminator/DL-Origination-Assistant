"""AI-assisted web enrichment for company records."""

from app.ai.confidence import AIProvenance
from app.ai.llm_service import LLMService
from app.ai.prompts.web_enrichment import WebEnrichmentPrompt
from app.miner.enrichment.size_estimator import classify_revenue_band
from app.platform.models.enums import DataQualityTag, OwnershipTier
from app.platform.models.schemas import CompanyRecord
from app.platform.utils.logging import get_logger

logger = get_logger("miner.enrichment.web_enricher")

# Ownership type string → tier mapping
_TIER_A = {"founder_owned", "family_owned", "privately_held", "founder/family"}
_TIER_B = {
    "family_office_backed", "vc_backed", "growth_equity_backed",
    "family_office", "venture_capital", "growth_equity",
}
_TIER_C = {"pe_backed", "private_equity", "sponsor_backed"}


def map_ownership_to_tier(ownership_type: str) -> OwnershipTier:
    """Map ownership type strings to tier enum."""
    ot = ownership_type.lower().replace(" ", "_")
    if ot in _TIER_A:
        return OwnershipTier.TIER_A
    if ot in _TIER_B:
        return OwnershipTier.TIER_B
    if ot in _TIER_C:
        return OwnershipTier.TIER_C
    return OwnershipTier.UNKNOWN


async def enrich_company(
    company: CompanyRecord,
    llm: LLMService,
    prompt_template: WebEnrichmentPrompt | None = None,
) -> bool:
    """Enrich a single company with LLM-assisted web research.

    Returns True if enrichment succeeded, False otherwise.
    """
    template = prompt_template or WebEnrichmentPrompt()

    try:
        prompt = template.render(
            company_name=company.canonical_name,
            subvertical=", ".join(company.subvertical_tags),
            source_tag=", ".join(company.source_tags),
        )
        data = await llm.complete_json(prompt, system=template.SYSTEM)
    except Exception as e:
        logger.error("enrichment_llm_failed", company=company.canonical_name, error=str(e))
        return False

    # Apply enrichment data to company
    _apply_location(company, data)
    _apply_size_signals(company, data)
    _apply_classification(company, data)
    _apply_ownership(company, data)

    # Track provenance
    company.ai_provenance["web_enrichment"] = AIProvenance(
        ai_generated=True,
        model_source=llm.__class__.__name__,
        prompt_template_id=template.template_id,
        prompt_template_version=template.version,
        confidence_score=data.get("confidence", 0.0),
        acceptance_status="pending",
    )

    return True


def _apply_location(company: CompanyRecord, data: dict) -> None:
    """Apply location fields from enrichment data."""
    if data.get("hq_city"):
        company.hq_city = data["hq_city"]
    if data.get("hq_state"):
        company.hq_state = data["hq_state"]
    if data.get("hq_country"):
        company.hq_country = data["hq_country"]
    if data.get("founded_year"):
        company.founded_year = data["founded_year"]
    if data.get("website"):
        company.website = data["website"]


def _apply_size_signals(company: CompanyRecord, data: dict) -> None:
    """Apply revenue, EBITDA, employee count from enrichment data."""
    if data.get("employee_count"):
        company.employee_count = data["employee_count"]
    if data.get("revenue_estimate") is not None:
        company.revenue_estimate = data["revenue_estimate"]
        company.revenue_quality = DataQualityTag.WEB_EST
        company.revenue_source = "llm_web_enrichment"
        company.revenue_band = data.get("revenue_band") or classify_revenue_band(data["revenue_estimate"])
    if data.get("ebitda_estimate") is not None:
        company.ebitda_estimate = data["ebitda_estimate"]
        company.ebitda_quality = DataQualityTag.WEB_EST
    if data.get("recurring_revenue_estimate") is not None:
        company.recurring_revenue_estimate = data["recurring_revenue_estimate"]
    if data.get("is_public") is not None:
        company.is_public = data["is_public"]


def _apply_classification(company: CompanyRecord, data: dict) -> None:
    """Apply industry exposure classification from enrichment data."""
    if data.get("industry_exposure_descriptor"):
        company.industry_exposure_descriptor = data["industry_exposure_descriptor"]
    if data.get("industry_exposure_intensity"):
        company.industry_exposure_intensity = data["industry_exposure_intensity"]


def _apply_ownership(company: CompanyRecord, data: dict) -> None:
    """Apply ownership classification from enrichment data."""
    ownership_type = data.get("ownership_type", "unknown")
    company.ownership_tier = map_ownership_to_tier(ownership_type)
    company.ownership_source = "llm_web_enrichment"
    company.ownership_confidence = data.get("confidence")
