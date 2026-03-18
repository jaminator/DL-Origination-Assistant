"""Canonical enums used across the DL Origination platform."""

from enum import StrEnum


class RecommendationStatus(StrEnum):
    STRONG_FIT = "strong_fit"
    MODERATE_FIT = "moderate_fit"
    WATCHLIST = "watchlist"
    AVOID = "avoid"


class SourceAccessType(StrEnum):
    PUBLIC_SCRAPE = "public_scrape"
    PUBLIC_MANUAL = "public_manual"
    LOGIN_REQUIRED = "login_required"
    PARTIAL_SCRAPE = "partial_scrape"


class SourcePriority(StrEnum):
    CORE = "core"
    USEFUL = "useful"
    OPTIONAL = "optional"
    MANUAL_ONLY = "manual_only"


class Disposition(StrEnum):
    PRIMARY = "primary"
    CASCADE_ANCHOR = "cascade_anchor"
    EXCLUDE = "exclude"
    WATCH = "watch"


class OwnershipTier(StrEnum):
    TIER_A = "tier_a"
    TIER_B = "tier_b"
    TIER_C = "tier_c"
    UNKNOWN = "unknown"


class DataQualityTag(StrEnum):
    CLEAN = "clean"
    WEB_EST = "web_est"
    STALE = "stale"
    ALL_INFERRED = "all_inferred"


class PitchBookStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"
    ERROR = "error"


class BizAPIStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"
    ERROR = "error"


class CapitalIQStatus(StrEnum):
    PENDING = "pending"
    MATCHED = "matched"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"
    ERROR = "error"


class WorkflowStage(StrEnum):
    THEME_INTAKE = "theme_intake"
    SUBVERTICAL_RECOMMENDATION = "subvertical_recommendation"
    SUBVERTICAL_CONFIRMATION = "subvertical_confirmation"
    SOURCE_RECOMMENDATION = "source_recommendation"
    SOURCE_CONFIRMATION = "source_confirmation"
    NAME_GENERATION = "name_generation"
    NAME_NORMALIZATION = "name_normalization"
    WEB_ENHANCEMENT = "web_enhancement"
    DISPOSITIONING = "dispositioning"
    PITCHBOOK_ENRICHMENT = "pitchbook_enrichment"
    BIZAPI_ENRICHMENT = "bizapi_enrichment"
    CAPITALIQ_ENRICHMENT = "capitaliq_enrichment"
    CASCADE_EXPANSION = "cascade_expansion"
    FINAL_DEDUP = "final_dedup"
    QA_VALIDATION = "qa_validation"
    SCORING = "scoring"
    EXPORT = "export"
    COMPLETED = "completed"


class ReviewReason(StrEnum):
    AMBIGUOUS_DUPLICATE = "ambiguous_duplicate"
    UNKNOWN_OWNERSHIP = "unknown_ownership"
    BOUNDARY_SIZE = "boundary_size"
    ACQUISITION_MERGER = "acquisition_merger"
    WEAK_GEOGRAPHY = "weak_geography"
    CONFLICTING_SIZE = "conflicting_size"
    LOW_CONFIDENCE_SUBVERTICAL = "low_confidence_subvertical"
    SOURCE_ACCESS_LIMITED = "source_access_limited"
    WEAK_ENRICHMENT_MATCH = "weak_enrichment_match"
    CONFLICTING_ENRICHMENT = "conflicting_enrichment"


class RunStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AcceptanceStatus(StrEnum):
    PENDING = "pending"
    AUTO_ACCEPTED = "auto_accepted"
    HUMAN_ACCEPTED = "human_accepted"
    HUMAN_REJECTED = "human_rejected"
