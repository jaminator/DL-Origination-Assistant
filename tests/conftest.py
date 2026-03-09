"""Test fixtures and configuration."""

import pytest


@pytest.fixture
def sample_run_config():
    return {
        "theme": "data center capex secular growth",
        "geography_filter": ["US"],
        "revenue_ceiling": 1000.0,
        "cascade_anchor_threshold": 1000.0,
    }


@pytest.fixture
def sample_company_data():
    return {
        "canonical_name": "Test Electrical Corp",
        "hq_city": "Dallas",
        "hq_state": "TX",
        "hq_country": "US",
        "subvertical_tags": ["Electrical Contractors"],
        "industry_exposure_descriptor": "Data center electrical infrastructure",
        "industry_exposure_intensity": "high",
        "ownership_tier": "tier_a",
        "revenue_estimate": 150.0,
        "revenue_band": "$100M-$250M",
        "revenue_quality": "web_est",
        "disposition": "primary",
    }
