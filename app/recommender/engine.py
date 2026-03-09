"""Sub-vertical Recommender Engine — top-level orchestrator."""

from uuid import UUID

from app.ai.confidence import AIProvenance
from app.ai.llm_service import LLMService
from app.ai.prompts.theme_analysis import SourceDiscoveryPrompt, ThemeAnalysisPrompt
from app.platform.models.enums import RecommendationStatus, SourceAccessType, SourcePriority
from app.platform.models.run import RunConfig
from app.platform.models.schemas import SourceRecommendation, ThemeRecommendation
from app.platform.utils.logging import get_logger

logger = get_logger("recommender")


class RecommenderEngine:
    """Accepts a theme, recommends sub-verticals, then recommends sources."""

    def __init__(self, llm: LLMService):
        self._llm = llm
        self._theme_prompt = ThemeAnalysisPrompt()
        self._source_prompt = SourceDiscoveryPrompt()

    async def recommend_subverticals(self, run_id: UUID, config: RunConfig) -> list[ThemeRecommendation]:
        """Generate ranked sub-vertical recommendations from a theme."""
        logger.info("recommend_subverticals", theme=config.theme, run_id=str(run_id))

        prompt = self._theme_prompt.render(
            theme=config.theme,
            geography=", ".join(config.geography_filter),
            revenue_ceiling=config.revenue_ceiling,
            theme_notes=config.theme_notes,
        )

        result = await self._llm.complete_json(prompt, system=self._theme_prompt.SYSTEM)

        recommendations = []
        for sv in result.get("subverticals", []):
            thematic = sv.get("thematic_fit_score", 0.0)
            lender = sv.get("lender_fit_score", 0.0)
            total = (thematic + lender) / 2.0

            rec = ThemeRecommendation(
                run_id=run_id,
                subvertical_name=sv.get("subvertical_name", ""),
                description=sv.get("description", ""),
                thematic_fit_explanation=sv.get("thematic_fit_explanation", ""),
                lender_fit_explanation=sv.get("lender_fit_explanation", ""),
                thematic_fit_score=thematic,
                lender_fit_score=lender,
                total_recommendation_score=total,
                recommendation_status=_parse_status(sv.get("recommendation_status", "watchlist")),
                demand_profile=sv.get("demand_profile", ""),
                cyclicality_profile=sv.get("cyclicality_profile", ""),
                fragmentation_profile=sv.get("fragmentation_profile", ""),
                recurring_revenue_profile=sv.get("recurring_revenue_profile", ""),
                margin_profile=sv.get("margin_profile", ""),
                capital_intensity_profile=sv.get("capital_intensity_profile", ""),
                concentration_risk_profile=sv.get("concentration_risk_profile", ""),
                ownership_landscape=sv.get("ownership_landscape", ""),
                ddtl_use_case_fit=sv.get("ddtl_use_case_fit", ""),
                example_borrower_archetypes=sv.get("example_borrower_archetypes", []),
                reasons_to_lend=sv.get("reasons_to_lend", []),
                reasons_not_to_lend=sv.get("reasons_not_to_lend", []),
                confidence=sv.get("confidence", 0.0),
                ai_provenance=AIProvenance(
                    ai_generated=True,
                    model_source=self._llm.__class__.__name__,
                    prompt_template_id=self._theme_prompt.template_id,
                    prompt_template_version=self._theme_prompt.version,
                    confidence_score=sv.get("confidence", 0.0),
                    acceptance_status="pending",
                ),
            )
            recommendations.append(rec)

        # Sort by total score descending
        recommendations.sort(key=lambda r: r.total_recommendation_score, reverse=True)
        logger.info("subverticals_generated", count=len(recommendations), run_id=str(run_id))
        return recommendations

    async def recommend_sources(
        self,
        run_id: UUID,
        subverticals: list[str],
        revenue_ceiling: float = 1000.0,
    ) -> list[SourceRecommendation]:
        """Generate source recommendations for confirmed sub-verticals."""
        logger.info("recommend_sources", subverticals=subverticals, run_id=str(run_id))

        prompt = self._source_prompt.render(
            subverticals=subverticals,
            revenue_ceiling=revenue_ceiling,
        )

        result = await self._llm.complete_json(prompt, system=self._source_prompt.SYSTEM)

        sources = []
        for src in result.get("sources", []):
            rec = SourceRecommendation(
                run_id=run_id,
                source_name=src.get("source_name", ""),
                source_type=src.get("source_type", ""),
                url=src.get("url"),
                mapped_subverticals=src.get("mapped_subverticals", []),
                rationale=src.get("rationale", ""),
                expected_company_type=src.get("expected_company_type", ""),
                expected_data_quality=src.get("expected_data_quality", ""),
                access_type=_parse_access_type(src.get("access_type", "public_scrape")),
                recommendation_priority=_parse_priority(src.get("recommendation_priority", "useful")),
                selected_by_default=True,
                user_selected=True,
                ai_provenance=AIProvenance(
                    ai_generated=True,
                    model_source=self._llm.__class__.__name__,
                    prompt_template_id=self._source_prompt.template_id,
                    prompt_template_version=self._source_prompt.version,
                    acceptance_status="pending",
                ),
            )
            sources.append(rec)

        # Add NAICS codes as sources
        for naics in result.get("naics_codes", []):
            rec = SourceRecommendation(
                run_id=run_id,
                source_name=f"NAICS {naics.get('code', '')} - {naics.get('description', '')}",
                source_type="naics_source",
                mapped_subverticals=naics.get("mapped_subverticals", []),
                naics_codes=[naics.get("code", "")],
                rationale=naics.get("relevance_explanation", ""),
                expected_company_type="Companies classified under this NAICS code",
                expected_data_quality="medium",
                access_type=SourceAccessType.PUBLIC_SCRAPE,
                recommendation_priority=SourcePriority.USEFUL,
                selected_by_default=True,
                user_selected=True,
                ai_provenance=AIProvenance(
                    ai_generated=True,
                    model_source=self._llm.__class__.__name__,
                    prompt_template_id=self._source_prompt.template_id,
                    prompt_template_version=self._source_prompt.version,
                    acceptance_status="pending",
                ),
            )
            sources.append(rec)

        logger.info("sources_generated", count=len(sources), run_id=str(run_id))
        return sources


def _parse_status(s: str) -> RecommendationStatus:
    try:
        return RecommendationStatus(s)
    except ValueError:
        return RecommendationStatus.WATCHLIST


def _parse_access_type(s: str) -> SourceAccessType:
    try:
        return SourceAccessType(s)
    except ValueError:
        return SourceAccessType.PUBLIC_SCRAPE


def _parse_priority(s: str) -> SourcePriority:
    try:
        return SourcePriority(s)
    except ValueError:
        return SourcePriority.USEFUL
