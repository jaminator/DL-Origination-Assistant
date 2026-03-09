"""Prompt templates for web-based company enrichment."""

from app.ai.prompts.base import PromptTemplate


class WebEnrichmentPrompt(PromptTemplate):
    """Enrich a company with web-sourced data: description, size signals, geography."""

    template_id = "web_enrichment"
    version = "1.0"

    SYSTEM = """You are a financial research analyst specializing in U.S. middle-market private companies.
Given a company name and context, provide factual enrichment data.
If you cannot determine a field with reasonable confidence, return null for that field.
Always respond with valid JSON."""

    TEMPLATE = """Research the following company and provide enrichment data.

Company name: {company_name}
Sub-vertical context: {subvertical}
Source: {source_tag}

Return a JSON object:
{{
  "description": "1-2 sentence description of what the company does",
  "hq_city": "city or null",
  "hq_state": "two-letter state code or null",
  "hq_country": "country code, default US",
  "founded_year": null or integer,
  "employee_count": null or integer,
  "revenue_estimate": null or number in millions,
  "revenue_band": "$10M-$50M | $50M-$100M | $100M-$250M | $250M-$500M | $500M-$1B | null",
  "ebitda_estimate": null or number in millions,
  "recurring_revenue_estimate": null or number in millions,
  "is_public": true or false,
  "website": "url or null",
  "industry_exposure_descriptor": "brief descriptor of industry exposure or null",
  "industry_exposure_intensity": "high | medium | low | null",
  "ownership_type": "founder_owned | family_owned | family_office_backed | vc_backed | growth_equity_backed | pe_backed | public | unknown",
  "confidence": 0.0 to 1.0
}}

Be conservative with estimates. If information is not publicly available, use null."""

    def render(
        self,
        company_name: str,
        subvertical: str = "",
        source_tag: str = "",
        **kwargs: str,
    ) -> str:
        return self.TEMPLATE.format(
            company_name=company_name,
            subvertical=subvertical,
            source_tag=source_tag,
        )
