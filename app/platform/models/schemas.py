"""Pydantic domain schemas for the DL Origination platform."""

from datetime import date, datetime
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.ai.confidence import AIProvenance
from app.platform.models.enums import (
    BizAPIStatus,
    CapitalIQStatus,
    DataQualityTag,
    Disposition,
    OwnershipTier,
    PitchBookStatus,
    RecommendationStatus,
    ReviewReason,
    SourceAccessType,
    SourcePriority,
    WorkflowStage,
)

# ---------------------------------------------------------------------------
# Sub-vertical Recommender schemas
# ---------------------------------------------------------------------------


class ThemeRecommendation(BaseModel):
    """A recommended sub-vertical for a given investment theme."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    subvertical_name: str
    description: str
    thematic_fit_explanation: str
    lender_fit_explanation: str
    thematic_fit_score: float = 0.0
    lender_fit_score: float = 0.0
    total_recommendation_score: float = 0.0
    recommendation_status: RecommendationStatus = RecommendationStatus.WATCHLIST
    demand_profile: str = ""
    cyclicality_profile: str = ""
    fragmentation_profile: str = ""
    recurring_revenue_profile: str = ""
    margin_profile: str = ""
    capital_intensity_profile: str = ""
    concentration_risk_profile: str = ""
    ownership_landscape: str = ""
    ddtl_use_case_fit: str = ""
    example_borrower_archetypes: list[str] = Field(default_factory=list)
    reasons_to_lend: list[str] = Field(default_factory=list)
    reasons_not_to_lend: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    supporting_notes: str | None = None
    user_selected: bool = False
    user_added: bool = False
    user_notes: str | None = None
    ai_provenance: AIProvenance = Field(default_factory=AIProvenance)


class SourceRecommendation(BaseModel):
    """A recommended data source for a sub-vertical."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    source_name: str
    source_type: str = ""  # trade_journal, ranking_list, directory, dealer_locator, etc.
    url: str | None = None
    mapped_subverticals: list[str] = Field(default_factory=list)
    naics_codes: list[str] = Field(default_factory=list)
    rationale: str = ""
    expected_company_type: str = ""
    expected_data_quality: str = ""
    access_type: SourceAccessType = SourceAccessType.PUBLIC_SCRAPE
    recommendation_priority: SourcePriority = SourcePriority.USEFUL
    selected_by_default: bool = True
    user_selected: bool = True
    user_added: bool = False
    notes: str | None = None
    ai_provenance: AIProvenance = Field(default_factory=AIProvenance)


# ---------------------------------------------------------------------------
# Company / Borrower schemas
# ---------------------------------------------------------------------------


class CompanyRecord(BaseModel):
    """Canonical company record with full provenance and enrichment data."""

    # Identity
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    canonical_name: str
    name_variants: list[str] = Field(default_factory=list)
    website: str | None = None
    hq_city: str | None = None
    hq_state: str | None = None
    hq_country: str = "US"
    founded_year: int | None = None
    employee_count: int | None = None

    # Classification
    subvertical_tags: list[str] = Field(default_factory=list)
    industry_exposure_descriptor: str | None = None
    industry_exposure_intensity: str | None = None  # high/medium/low
    ownership_tier: OwnershipTier = OwnershipTier.UNKNOWN
    ownership_source: str | None = None
    ownership_confidence: float | None = None
    disposition: Disposition = Disposition.PRIMARY
    is_public: bool | None = None

    # Size signals
    revenue_estimate: float | None = None  # in millions
    revenue_band: str | None = None
    revenue_quality: DataQualityTag | None = None
    revenue_source: str | None = None
    ebitda_estimate: float | None = None
    ebitda_quality: DataQualityTag | None = None
    recurring_revenue_estimate: float | None = None
    size_source_timestamp: datetime | None = None

    # PitchBook
    pb_status: PitchBookStatus = PitchBookStatus.PENDING
    pb_entity_id: str | None = None
    sponsor_names: list[str] = Field(default_factory=list)
    investor_names: list[str] = Field(default_factory=list)
    has_debt: bool | None = None
    lender_names: list[str] = Field(default_factory=list)
    facility_type: str | None = None
    facility_amount: float | None = None
    pricing: str | None = None
    close_date: date | None = None
    maturity_date: date | None = None
    catalyst_flags: list[str] = Field(default_factory=list)

    # BizAPI enrichment
    bizapi_status: BizAPIStatus = BizAPIStatus.PENDING
    bizapi_duns: str | None = None
    bizapi_match_method: str | None = None
    bizapi_match_confidence: float | None = None
    naics_code: str | None = None
    naics_description: str | None = None
    sic_code: str | None = None
    sic_description: str | None = None
    bizapi_year_started: int | None = None
    bizapi_employee_count: int | None = None
    bizapi_sales_volume: float | None = None  # in millions
    bizapi_verified_name: str | None = None
    bizapi_verified_address: str | None = None
    bizapi_corporate_linkage: dict | None = None

    # Capital IQ enrichment
    ciq_status: CapitalIQStatus = CapitalIQStatus.PENDING
    ciq_entity_id: str | None = None
    ciq_revenue: float | None = None  # in millions
    ciq_ebitda: float | None = None  # in millions
    ciq_total_debt: float | None = None  # in millions
    ciq_net_debt: float | None = None  # in millions
    ciq_ownership_type: str | None = None
    ciq_key_investors: list[str] = Field(default_factory=list)
    ciq_ma_history: list[dict] = Field(default_factory=list)
    ciq_credit_metrics: dict | None = None

    # Scoring
    total_score: float | None = None
    score_components: dict[str, float] = Field(default_factory=dict)
    eligible_for_outreach: bool = False

    # Provenance
    source_tags: list[str] = Field(default_factory=list)
    source_chain: list[str] = Field(default_factory=list)
    first_seen: datetime = Field(default_factory=datetime.utcnow)
    last_updated: datetime = Field(default_factory=datetime.utcnow)
    workflow_stage: WorkflowStage = WorkflowStage.NAME_GENERATION
    status_change_log: list[dict] = Field(default_factory=list)
    review_required: bool = False
    review_reasons: list[ReviewReason] = Field(default_factory=list)
    review_notes: str | None = None

    # AI provenance (keyed by operation: web_enrichment, exposure, size_estimation, etc.)
    ai_provenance: dict[str, AIProvenance] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Review and export schemas
# ---------------------------------------------------------------------------


class ReviewQueueItem(BaseModel):
    """An item requiring manual human review."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    company_id: UUID | None = None
    source_id: UUID | None = None
    reason: ReviewReason
    details: str = ""
    candidate_a: dict | None = None
    candidate_b: dict | None = None
    resolved: bool = False
    resolution: str | None = None
    resolved_at: datetime | None = None
    ai_triage: AIProvenance | None = None


class ExportManifest(BaseModel):
    """Metadata for a set of exported files from a run."""

    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    created_at: datetime = Field(default_factory=datetime.utcnow)
    exports: list[dict] = Field(default_factory=list)  # [{name, format, path, row_count}]
    ai_notes: str | None = None


# ---------------------------------------------------------------------------
# Raw company (pre-normalization)
# ---------------------------------------------------------------------------


class RawCompany(BaseModel):
    """A company name extracted from a source, before normalization."""

    raw_name: str
    source_tag: str
    source_url: str | None = None
    subvertical: str | None = None
    raw_description: str | None = None
    extra: dict = Field(default_factory=dict)
