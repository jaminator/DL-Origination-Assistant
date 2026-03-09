"""Prompt templates for theme-to-sub-vertical analysis."""

from app.ai.prompts.base import PromptTemplate


class ThemeAnalysisPrompt(PromptTemplate):
    """Generate sub-vertical recommendations from an investment theme."""

    template_id = "theme_analysis"
    version = "1.0"

    SYSTEM = """You are an expert in U.S. middle-market direct lending origination.
You evaluate industry sub-verticals as potential borrower segments for direct lenders.
You score sub-verticals on both thematic fit and lender-fit (borrower quality).
Always respond with valid JSON."""

    TEMPLATE = """Analyze the following investment theme and recommend sub-verticals that would be attractive
for U.S. middle-market direct lending origination.

Theme: {theme}
{notes_section}
Geography: {geography}
Revenue ceiling: ${revenue_ceiling}M

For each recommended sub-vertical, evaluate against these direct-lending borrower criteria:
1. Demand profile: acyclical/modestly cyclical, secular growth drivers
2. Market structure: fragmented, larger players exist as strategic buyer backstop
3. Revenue quality: multi-year contracts, backlog, recurring revenue
4. Margin profile: gross margins 35-40%+, EBITDA margins 10-15%+
5. Capital intensity: limited capex and NWC intensity
6. Concentration risk: limited customer/supplier/geographic concentration
7. Use-of-proceeds: attractive DDTL applications (M&A roll-up, branch expansion, etc.)

Return a JSON object with this structure:
{{
  "subverticals": [
    {{
      "subvertical_name": "string",
      "description": "string",
      "thematic_fit_explanation": "string",
      "lender_fit_explanation": "string",
      "thematic_fit_score": 0-100,
      "lender_fit_score": 0-100,
      "recommendation_status": "strong_fit|moderate_fit|watchlist|avoid",
      "demand_profile": "string",
      "cyclicality_profile": "string",
      "fragmentation_profile": "string",
      "recurring_revenue_profile": "string",
      "margin_profile": "string",
      "capital_intensity_profile": "string",
      "concentration_risk_profile": "string",
      "ownership_landscape": "string",
      "ddtl_use_case_fit": "string",
      "example_borrower_archetypes": ["string"],
      "reasons_to_lend": ["string"],
      "reasons_not_to_lend": ["string"],
      "confidence": 0.0-1.0
    }}
  ]
}}

Include 5-10 sub-verticals. Include both attractive and unattractive sub-verticals.
For unattractive ones, explain why they fit the theme but are poor lending targets.
Rank by total attractiveness (thematic + lender fit)."""

    def render(
        self,
        theme: str,
        geography: str = "US",
        revenue_ceiling: float = 1000.0,
        theme_notes: str | None = None,
        **kwargs: str,
    ) -> str:
        notes_section = f"Additional notes: {theme_notes}" if theme_notes else ""
        return self.TEMPLATE.format(
            theme=theme,
            notes_section=notes_section,
            geography=geography,
            revenue_ceiling=revenue_ceiling,
        )


class SourceDiscoveryPrompt(PromptTemplate):
    """Generate source recommendations for confirmed sub-verticals."""

    template_id = "source_discovery"
    version = "1.0"

    SYSTEM = """You are an expert in U.S. middle-market company sourcing and industry research.
You identify public data sources useful for discovering private companies in specific sub-verticals.
Always respond with valid JSON."""

    TEMPLATE = """For the following confirmed sub-verticals, recommend data sources for discovering
U.S. middle-market private companies (revenue under ${revenue_ceiling}M).

Sub-verticals:
{subverticals_list}

For each sub-vertical, recommend relevant sources including:
- Trade journals and publications
- Rankings/top lists (e.g., "Top 100 contractors")
- Industry association member directories
- Certification directories
- Dealer/distributor locator tools
- Manufacturer partner locator tools
- Conference exhibitor lists
- Regional association directories
- NAICS codes

Return JSON:
{{
  "sources": [
    {{
      "source_name": "string",
      "source_type": "trade_journal|ranking_list|association_directory|certification_directory|dealer_locator|manufacturer_partner|conference_exhibitor|regional_directory|naics_source|other",
      "url": "string or null",
      "mapped_subverticals": ["string"],
      "rationale": "string",
      "expected_company_type": "string",
      "expected_data_quality": "high|medium|low",
      "access_type": "public_scrape|public_manual|login_required|partial_scrape",
      "recommendation_priority": "core|useful|optional|manual_only"
    }}
  ],
  "naics_codes": [
    {{
      "code": "string",
      "description": "string",
      "mapped_subverticals": ["string"],
      "relevance_explanation": "string"
    }}
  ]
}}"""

    def render(
        self,
        subverticals: list[str],
        revenue_ceiling: float = 1000.0,
        **kwargs: str,
    ) -> str:
        subverticals_list = "\n".join(f"- {sv}" for sv in subverticals)
        return self.TEMPLATE.format(
            subverticals_list=subverticals_list,
            revenue_ceiling=revenue_ceiling,
        )
