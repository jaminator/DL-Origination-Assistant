"""Canonical enums used across the DL Origination platform."""

from enum import Enum


class RecommendationStatus(str, Enum):
    STRONG_FIT = "strong_fit"
    MODERATE_FIT = "moderate_fit"
    WATCHLIST = "watchlist"
    AVOID = "avoid"


class SourceAccessType(str, Enum):
    PUBLIC_SCRAPE = "public_scrape"
    PUBLIC_MANUAL = "public_manual"
    LOGIN_REQUIRED = "login_required"
    PARTIAL_SCRAPE = "partial_scrape"


class SourcePriority(str, Enum):
    CORE = "core"
    USEFUL = "useful"
    OPTIONAL = "optional"
    MANUAL_ONLY = "manual_only"


class Disposition(str, Enum):
    PRIMARY = "primary"
    CASCADE_ANCHOR = "cascade_anchor"
    EXCLUDE = "exclude"
    WATCH = "watch"


class OwnershipTier(str, Enum):
    TIER_A = "tier_a"
    TIER_B = "tier_b"
    TIER_C = "tier_c"
    UNKNOWN = "unknown"


class DataQualityTag(str, Enum):
    CLEAN = "clean"
    WEB_EST = "web_est"
    STALE = "stale"
    ALL_INFERRED = "all_inferred"


class PitchBookStatus(str, Enum):
    PENDING = "pending"
    MATCHED = "matched"
    NOT_FOUND = "not_found"
    SKIPPED = "skipped"
    ERROR = "error"


class WorkflowStage(str, Enum):
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
    CASCADE_EXPANSION = "cascade_expansion"
    FINAL_DEDUP = "final_dedup"
    QA_VALIDATION = "qa_validation"
    SCORING = "scoring"
    EXPORT = "export"
    COMPLETED = "completed"


class ReviewReason(str, Enum):
    AMBIGUOUS_DUPLICATE = "ambiguous_duplicate"
    UNKNOWN_OWNERSHIP = "unknown_ownership"
    BOUNDARY_SIZE = "boundary_size"
    ACQUISITION_MERGER = "acquisition_merger"
    WEAK_GEOGRAPHY = "weak_geography"
    CONFLICTING_SIZE = "conflicting_size"
    LOW_CONFIDENCE_SUBVERTICAL = "low_confidence_subvertical"
    SOURCE_ACCESS_LIMITED = "source_access_limited"


class RunStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"


class AcceptanceStatus(str, Enum):
    PENDING = "pending"
    AUTO_ACCEPTED = "auto_accepted"
    HUMAN_ACCEPTED = "human_accepted"
    HUMAN_REJECTED = "human_rejected"
