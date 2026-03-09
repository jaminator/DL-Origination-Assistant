"""Project-level defaults for scoring weights, thresholds, and quality parameters."""

# Revenue / size
DEFAULT_REVENUE_CEILING = 1000.0  # $1B in millions
DEFAULT_CASCADE_ANCHOR_THRESHOLD = 1000.0
DEFAULT_EBITDA_SOFT_CEILING = 150.0  # soft screen, NOT a hard exclude
DEFAULT_MIN_REVENUE_FLOOR = None

# Geography
DEFAULT_GEOGRAPHY_FILTER = ["US"]

# Ownership scoring bonuses
DEFAULT_TIER_A_BONUS = 15.0  # founder/family-owned
DEFAULT_TIER_B_BONUS = 8.0   # family office/VC/growth equity
DEFAULT_TIER_C_BONUS = 0.0   # traditional PE sponsor

# Company scoring weights (sum to 100)
SCORING_WEIGHTS = {
    "revenue_scale": 20.0,
    "ebitda_margin": 15.0,
    "recurring_revenue": 15.0,
    "industry_exposure": 20.0,
    "ownership_tier": 15.0,
    "data_completeness": 15.0,
}

# Sub-vertical recommendation scoring weights (sum to 100)
SUBVERTICAL_SCORING_WEIGHTS = {
    "acyclicality": 12.0,
    "secular_growth": 12.0,
    "fragmentation": 10.0,
    "strategic_buyer_backstop": 5.0,
    "recurring_revenue": 12.0,
    "margin_quality": 10.0,
    "capex_intensity": 8.0,
    "nwc_intensity": 6.0,
    "concentration_risk": 8.0,
    "sponsor_saturation": 7.0,
    "ddtl_use_case": 10.0,
}

# Dedup
FUZZY_DEDUP_AUTO_MERGE_THRESHOLD = 95  # RapidFuzz score
FUZZY_DEDUP_REVIEW_THRESHOLD = 80      # Below this = distinct; above auto-merge = review queue

# Data quality
STALE_DATA_THRESHOLD_DAYS = 365

# Workflow
DEFAULT_MAX_RECURSION_DEPTH = 3
DEFAULT_BOUNDARY_TREATMENT = "watch"  # include | watch | exclude | review
DEFAULT_INCLUDE_CASCADE_ANCHORS_IN_OUTREACH = False

# QA thresholds
QA_MIN_DATA_COMPLETENESS = 0.6  # 60% of key fields populated
QA_REQUIRED_FIELDS = [
    "canonical_name",
    "hq_state",
    "subvertical_tags",
    "industry_exposure_descriptor",
    "ownership_tier",
    "revenue_estimate",
]
