"""Borrower Miner Engine — top-level orchestrator for company discovery and enrichment."""

from uuid import UUID, uuid4

from app.ai.confidence import AIProvenance
from app.ai.llm_service import LLMService
from app.ai.prompts.web_enrichment import WebEnrichmentPrompt
from app.miner.dedup import DedupResult, deduplicate_names
from app.miner.dispositioning import assign_disposition
from app.miner.enrichment.bizapi.adapter import BizAPIAdapter
from app.miner.enrichment.capitaliq.adapter import CapitalIQAdapter
from app.miner.pitchbook.adapter import PitchBookAdapter
from app.miner.sources.registry import SourceRegistry
from app.platform.config.defaults import DEFAULT_GEOGRAPHY_FILTER
from app.platform.exports.service import ExportService
from app.platform.models.enums import (
    BizAPIStatus,
    CapitalIQStatus,
    DataQualityTag,
    Disposition,
    OwnershipTier,
    PitchBookStatus,
    ReviewReason,
    WorkflowStage,
)
from app.platform.models.schemas import CompanyRecord, RawCompany
from app.platform.persistence.storage import StorageBackend
from app.platform.review.queue import (
    generate_review_items_from_dedup,
    generate_review_items_from_enrichment_conflict,
)
from app.platform.scoring.company_scorer import score_company
from app.platform.utils.logging import get_logger
from app.platform.utils.normalization import canonical_form, normalize_company_name
from app.platform.validation.qa_gates import run_qa_gates

logger = get_logger("miner")


class MinerEngine:
    """Orchestrates the borrower mining pipeline from source extraction through scoring."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        pitchbook_adapter: PitchBookAdapter | None = None,
        bizapi_adapter: BizAPIAdapter | None = None,
        capitaliq_adapter: CapitalIQAdapter | None = None,
        storage: StorageBackend | None = None,
        source_registry: SourceRegistry | None = None,
    ):
        self._llm = llm_service
        self._pitchbook = pitchbook_adapter
        self._bizapi = bizapi_adapter
        self._capitaliq = capitaliq_adapter
        self._storage = storage
        self._source_registry = source_registry or SourceRegistry()
        self._enrichment_prompt = WebEnrichmentPrompt()

        # In-memory pipeline state (per-run)
        self._raw_companies: list[RawCompany] = []
        self._companies: list[CompanyRecord] = []
        self._dedup_result: DedupResult | None = None
        self._review_items: list = []

    async def execute_pipeline(self, run_id: UUID, config: dict, start_from: WorkflowStage | None = None) -> dict:
        """Run the full borrower mining pipeline (or resume from a given stage)."""
        logger.info("miner_pipeline_start", run_id=str(run_id))

        stages = [
            (WorkflowStage.NAME_GENERATION, self._run_name_generation),
            (WorkflowStage.NAME_NORMALIZATION, self._run_name_normalization),
            (WorkflowStage.WEB_ENHANCEMENT, self._run_web_enhancement),
            (WorkflowStage.DISPOSITIONING, self._run_dispositioning),
            (WorkflowStage.BIZAPI_ENRICHMENT, self._run_bizapi_enrichment),
            (WorkflowStage.PITCHBOOK_ENRICHMENT, self._run_pitchbook_enrichment),
            (WorkflowStage.CAPITALIQ_ENRICHMENT, self._run_capitaliq_enrichment),
            (WorkflowStage.CASCADE_EXPANSION, self._run_cascade_expansion),
            (WorkflowStage.FINAL_DEDUP, self._run_final_dedup),
            (WorkflowStage.QA_VALIDATION, self._run_qa_validation),
            (WorkflowStage.SCORING, self._run_scoring),
            (WorkflowStage.EXPORT, self._run_export),
        ]

        # If resuming, skip to the start_from stage
        executing = start_from is None
        results = {}

        for stage, handler in stages:
            if not executing:
                if stage == start_from:
                    executing = True
                else:
                    continue

            logger.info("miner_stage_start", stage=stage.value, run_id=str(run_id))
            result = await handler(run_id, config)
            results[stage.value] = result
            logger.info("miner_stage_complete", stage=stage.value, run_id=str(run_id))

        logger.info("miner_pipeline_complete", run_id=str(run_id))
        return results

    async def rerun_stage(self, run_id: UUID, config: dict, stage: WorkflowStage) -> dict:
        """Re-run a single stage without advancing the pipeline."""
        handler_map = {
            WorkflowStage.NAME_GENERATION: self._run_name_generation,
            WorkflowStage.NAME_NORMALIZATION: self._run_name_normalization,
            WorkflowStage.WEB_ENHANCEMENT: self._run_web_enhancement,
            WorkflowStage.DISPOSITIONING: self._run_dispositioning,
            WorkflowStage.BIZAPI_ENRICHMENT: self._run_bizapi_enrichment,
            WorkflowStage.PITCHBOOK_ENRICHMENT: self._run_pitchbook_enrichment,
            WorkflowStage.CAPITALIQ_ENRICHMENT: self._run_capitaliq_enrichment,
            WorkflowStage.CASCADE_EXPANSION: self._run_cascade_expansion,
            WorkflowStage.FINAL_DEDUP: self._run_final_dedup,
            WorkflowStage.QA_VALIDATION: self._run_qa_validation,
            WorkflowStage.SCORING: self._run_scoring,
            WorkflowStage.EXPORT: self._run_export,
        }
        handler = handler_map.get(stage)
        if not handler:
            raise ValueError(f"Unknown stage: {stage}")
        return await handler(run_id, config)

    # -- Stage implementations --

    async def _run_name_generation(self, run_id: UUID, config: dict) -> dict:
        """Extract company names from confirmed sources via source adapters."""
        sources = config.get("selected_sources", [])
        if not sources:
            logger.warning("name_generation_no_sources", run_id=str(run_id))
            return {"stage": "name_generation", "status": "completed", "companies_found": 0}

        all_raw: list[RawCompany] = []
        for source in sources:
            try:
                raw = await self._source_registry.extract_from_source(source)
                all_raw.extend(raw)
                logger.info("source_extracted", source=source.get("source_name", ""), count=len(raw))
            except Exception as e:
                logger.error("source_extraction_failed", source=source.get("source_name", ""), error=str(e))

        self._raw_companies = all_raw
        logger.info("name_generation_complete", run_id=str(run_id), total=len(all_raw))
        return {"stage": "name_generation", "status": "completed", "companies_found": len(all_raw)}

    async def _run_name_normalization(self, run_id: UUID, config: dict) -> dict:
        """Normalize names and run fuzzy dedup."""
        names = [rc.raw_name for rc in self._raw_companies]

        # Dedup
        dedup_result = deduplicate_names(names)
        self._dedup_result = dedup_result

        # Build canonical CompanyRecords for distinct names
        merged_names = {merged for _, merged, _ in dedup_result.merged}
        self._companies = []

        for raw in self._raw_companies:
            if raw.raw_name in merged_names:
                continue  # Skip auto-merged duplicates

            company = CompanyRecord(
                id=uuid4(),
                run_id=run_id,
                canonical_name=canonical_form(raw.raw_name),
                name_variants=[raw.raw_name],
                subvertical_tags=[raw.subvertical] if raw.subvertical else [],
                source_tags=[raw.source_tag],
                workflow_stage=WorkflowStage.NAME_NORMALIZATION,
            )
            self._companies.append(company)

        # Generate review items for ambiguous matches
        if dedup_result.review:
            self._review_items.extend(
                generate_review_items_from_dedup(run_id, dedup_result.review)
            )

        logger.info(
            "name_normalization_complete",
            run_id=str(run_id),
            distinct=len(self._companies),
            auto_merged=len(dedup_result.merged),
            review=len(dedup_result.review),
        )
        return {
            "stage": "name_normalization",
            "status": "completed",
            "distinct_companies": len(self._companies),
            "auto_merged": len(dedup_result.merged),
            "review_queue": len(dedup_result.review),
        }

    async def _run_web_enhancement(self, run_id: UUID, config: dict) -> dict:
        """Web-enhance each company with LLM-assisted research."""
        if not self._llm:
            logger.warning("web_enhancement_no_llm", run_id=str(run_id))
            for c in self._companies:
                c.workflow_stage = WorkflowStage.WEB_ENHANCEMENT
            return {"stage": "web_enhancement", "status": "skipped", "reason": "no_llm_service"}

        enriched = 0
        for company in self._companies:
            try:
                prompt = self._enrichment_prompt.render(
                    company_name=company.canonical_name,
                    subvertical=", ".join(company.subvertical_tags),
                    source_tag=", ".join(company.source_tags),
                )
                data = await self._llm.complete_json(prompt, system=self._enrichment_prompt.SYSTEM)

                # Apply enrichment data
                if data.get("hq_city"):
                    company.hq_city = data["hq_city"]
                if data.get("hq_state"):
                    company.hq_state = data["hq_state"]
                if data.get("hq_country"):
                    company.hq_country = data["hq_country"]
                if data.get("founded_year"):
                    company.founded_year = data["founded_year"]
                if data.get("employee_count"):
                    company.employee_count = data["employee_count"]
                if data.get("revenue_estimate") is not None:
                    company.revenue_estimate = data["revenue_estimate"]
                    company.revenue_quality = DataQualityTag.WEB_EST
                    company.revenue_source = "llm_web_enrichment"
                if data.get("revenue_band"):
                    company.revenue_band = data["revenue_band"]
                if data.get("ebitda_estimate") is not None:
                    company.ebitda_estimate = data["ebitda_estimate"]
                    company.ebitda_quality = DataQualityTag.WEB_EST
                if data.get("recurring_revenue_estimate") is not None:
                    company.recurring_revenue_estimate = data["recurring_revenue_estimate"]
                if data.get("is_public") is not None:
                    company.is_public = data["is_public"]
                if data.get("website"):
                    company.website = data["website"]
                if data.get("industry_exposure_descriptor"):
                    company.industry_exposure_descriptor = data["industry_exposure_descriptor"]
                if data.get("industry_exposure_intensity"):
                    company.industry_exposure_intensity = data["industry_exposure_intensity"]

                # Map ownership_type to tier
                ownership_type = data.get("ownership_type", "unknown")
                company.ownership_tier = _map_ownership_to_tier(ownership_type)
                company.ownership_source = "llm_web_enrichment"
                company.ownership_confidence = data.get("confidence")

                # Track provenance
                company.ai_provenance["web_enrichment"] = AIProvenance(
                    ai_generated=True,
                    model_source=self._llm.__class__.__name__,
                    prompt_template_id=self._enrichment_prompt.template_id,
                    prompt_template_version=self._enrichment_prompt.version,
                    confidence_score=data.get("confidence", 0.0),
                    acceptance_status="pending",
                )

                company.workflow_stage = WorkflowStage.WEB_ENHANCEMENT
                enriched += 1

            except Exception as e:
                logger.error("web_enrichment_failed", company=company.canonical_name, error=str(e))
                company.workflow_stage = WorkflowStage.WEB_ENHANCEMENT

        logger.info("web_enhancement_complete", run_id=str(run_id), enriched=enriched)
        return {"stage": "web_enhancement", "status": "completed", "companies_enriched": enriched}

    async def _run_dispositioning(self, run_id: UUID, config: dict) -> dict:
        """Assign disposition: Primary / Cascade Anchor / Exclude / Watch."""
        revenue_ceiling = config.get("revenue_ceiling", 1000.0)
        cascade_threshold = config.get("cascade_anchor_threshold", 1000.0)
        geo = config.get("geography_filter", DEFAULT_GEOGRAPHY_FILTER)
        boundary = config.get("boundary_treatment", "watch")

        counts: dict[str, int] = {}
        for company in self._companies:
            disposition = assign_disposition(
                company,
                revenue_ceiling=revenue_ceiling,
                cascade_anchor_threshold=cascade_threshold,
                geography_filter=geo,
                boundary_treatment=boundary,
            )
            company.disposition = disposition
            company.workflow_stage = WorkflowStage.DISPOSITIONING
            counts[disposition.value] = counts.get(disposition.value, 0) + 1

        logger.info("dispositioning_complete", run_id=str(run_id), counts=counts)
        return {"stage": "dispositioning", "status": "completed", "counts": counts}

    async def _run_bizapi_enrichment(self, run_id: UUID, config: dict) -> dict:
        """Verify and enrich companies via NAICS BizAPI."""
        if not self._bizapi:
            logger.warning("bizapi_no_adapter", run_id=str(run_id))
            return {"stage": "bizapi_enrichment", "status": "skipped", "reason": "no_adapter"}

        if not await self._bizapi.is_available():
            logger.warning("bizapi_unavailable", run_id=str(run_id))
            return {"stage": "bizapi_enrichment", "status": "skipped", "reason": "unavailable"}

        eligible = (Disposition.PRIMARY, Disposition.WATCH, Disposition.CASCADE_ANCHOR)
        targets = [
            c for c in self._companies
            if c.disposition in eligible and c.bizapi_status == BizAPIStatus.PENDING
        ]

        matched = 0
        not_found = 0
        errors = 0

        for company in targets:
            try:
                result = await self._bizapi.match_company(
                    company.canonical_name,
                    duns=company.bizapi_duns,
                    website=company.website,
                    state=company.hq_state,
                )

                if not result:
                    company.bizapi_status = BizAPIStatus.NOT_FOUND
                    not_found += 1
                    company.workflow_stage = WorkflowStage.BIZAPI_ENRICHMENT
                    continue

                company.bizapi_status = BizAPIStatus.MATCHED
                company.bizapi_duns = result.get("duns")
                company.bizapi_match_method = result.get("match_method")
                company.bizapi_match_confidence = result.get("match_confidence")

                # Store source-specific fields
                company.naics_code = result.get("naics_code") or company.naics_code
                company.naics_description = result.get("naics_description") or company.naics_description
                company.sic_code = result.get("sic_code") or company.sic_code
                company.sic_description = result.get("sic_description") or company.sic_description
                company.bizapi_year_started = result.get("year_started")
                company.bizapi_employee_count = result.get("employee_count")
                company.bizapi_sales_volume = result.get("sales_volume")
                company.bizapi_verified_name = result.get("verified_name")
                company.bizapi_corporate_linkage = result.get("corporate_linkage")

                # Verified address
                addr = result.get("verified_address", {})
                if addr:
                    company.bizapi_verified_address = (
                        f"{addr.get('street', '')}, {addr.get('city', '')}, "
                        f"{addr.get('state', '')} {addr.get('zip', '')}".strip(", ")
                    )

                # Update canonical fields — BizAPI priority: above Web, below PB/CIQ
                confidence = result.get("match_confidence", 0.0)

                if confidence >= 0.80:
                    # BizAPI is authoritative for employee count
                    if result.get("employee_count") and company.employee_count is None:
                        company.employee_count = result["employee_count"]

                    # BizAPI address upgrades web-enrichment address
                    if addr.get("city") and (not company.hq_city or company.ownership_source == "llm_web_enrichment"):
                        company.hq_city = addr["city"]
                    if addr.get("state") and (not company.hq_state or company.ownership_source == "llm_web_enrichment"):
                        company.hq_state = addr["state"]

                    # BizAPI sales volume upgrades web estimates
                    if result.get("sales_volume") and (
                        company.revenue_source in (None, "llm_web_enrichment")
                    ):
                        company.revenue_estimate = result["sales_volume"]
                        company.revenue_source = "bizapi"
                        company.revenue_quality = DataQualityTag.CLEAN

                    # Founded year
                    if result.get("year_started") and not company.founded_year:
                        company.founded_year = result["year_started"]

                # Weak match → flag for review
                if 0.50 <= confidence < 0.80:
                    company.review_required = True
                    if ReviewReason.WEAK_ENRICHMENT_MATCH not in company.review_reasons:
                        company.review_reasons.append(ReviewReason.WEAK_ENRICHMENT_MATCH)

                # Corporate linkage → flag subsidiary
                linkage = result.get("corporate_linkage", {})
                if linkage.get("parent_duns"):
                    company.review_required = True
                    if ReviewReason.ACQUISITION_MERGER not in company.review_reasons:
                        company.review_reasons.append(ReviewReason.ACQUISITION_MERGER)

                # Track provenance
                company.ai_provenance["bizapi_enrichment"] = AIProvenance(
                    ai_generated=False,
                    connector_source="bizapi",
                    confidence_score=confidence,
                    acceptance_status="auto_accepted" if confidence >= 0.80 else "pending",
                )

                company.workflow_stage = WorkflowStage.BIZAPI_ENRICHMENT
                matched += 1

            except Exception as e:
                logger.error("bizapi_enrichment_failed", company=company.canonical_name, error=str(e))
                company.bizapi_status = BizAPIStatus.ERROR
                errors += 1

        logger.info(
            "bizapi_enrichment_complete",
            run_id=str(run_id),
            matched=matched,
            not_found=not_found,
            errors=errors,
        )
        return {
            "stage": "bizapi_enrichment",
            "status": "completed",
            "matched": matched,
            "not_found": not_found,
            "errors": errors,
        }

    async def _run_pitchbook_enrichment(self, run_id: UUID, config: dict) -> dict:
        """Enrich via PitchBook adapter (mock or MCP)."""
        if not self._pitchbook:
            logger.warning("pitchbook_no_adapter", run_id=str(run_id))
            return {"stage": "pitchbook_enrichment", "status": "skipped", "reason": "no_adapter"}

        if not await self._pitchbook.is_available():
            logger.warning("pitchbook_unavailable", run_id=str(run_id))
            return {"stage": "pitchbook_enrichment", "status": "skipped", "reason": "unavailable"}

        matched = 0
        not_found = 0

        # Only enrich primary, watch, and cascade anchor companies (skip excluded)
        eligible = (Disposition.PRIMARY, Disposition.WATCH, Disposition.CASCADE_ANCHOR)
        targets = [c for c in self._companies if c.disposition in eligible]

        for company in targets:
            try:
                search = await self._pitchbook.search_company(company.canonical_name)
                if not search:
                    company.pb_status = PitchBookStatus.NOT_FOUND
                    not_found += 1
                    continue

                company.pb_status = PitchBookStatus.MATCHED
                company.pb_entity_id = search.get("entity_id")
                matched += 1

                # Get detail
                if company.pb_entity_id:
                    detail = await self._pitchbook.get_company_detail(company.pb_entity_id)
                    if detail.get("ownership_type"):
                        pb_tier = _map_ownership_to_tier(detail["ownership_type"])
                        # PitchBook overrides web enrichment for ownership
                        company.ownership_tier = pb_tier
                        company.ownership_source = "pitchbook"
                        company.ownership_confidence = search.get("match_confidence")

                    if detail.get("investors"):
                        company.investor_names = [
                            inv if isinstance(inv, str) else inv.get("name", "")
                            for inv in detail["investors"]
                        ]

                    # Debt details
                    debt = await self._pitchbook.get_debt_details(company.pb_entity_id)
                    if debt:
                        company.has_debt = True
                        first = debt[0]
                        company.facility_type = first.get("facility_type")
                        company.facility_amount = first.get("amount")
                        company.pricing = first.get("pricing")
                        company.lender_names = [d.get("lender", "") for d in debt if d.get("lender")]
                    else:
                        company.has_debt = False

                    # Competitors (for cascade expansion)
                    competitors = await self._pitchbook.get_competitors(company.pb_entity_id)
                    if competitors:
                        company.catalyst_flags.append(f"pb_competitors:{len(competitors)}")

                company.workflow_stage = WorkflowStage.PITCHBOOK_ENRICHMENT

            except Exception as e:
                logger.error("pitchbook_enrichment_failed", company=company.canonical_name, error=str(e))
                company.pb_status = PitchBookStatus.ERROR

        logger.info("pitchbook_enrichment_complete", run_id=str(run_id), matched=matched, not_found=not_found)
        return {"stage": "pitchbook_enrichment", "status": "completed", "matched": matched, "not_found": not_found}

    async def _run_capitaliq_enrichment(self, run_id: UUID, config: dict) -> dict:
        """Enrich companies with S&P Capital IQ private-market data."""
        if not self._capitaliq:
            logger.warning("capitaliq_no_adapter", run_id=str(run_id))
            return {"stage": "capitaliq_enrichment", "status": "skipped", "reason": "no_adapter"}

        if not await self._capitaliq.is_available():
            logger.warning("capitaliq_unavailable", run_id=str(run_id))
            return {"stage": "capitaliq_enrichment", "status": "skipped", "reason": "unavailable"}

        skip_if_pb_complete = config.get("capitaliq_skip_if_pb_complete", True)
        eligible = (Disposition.PRIMARY, Disposition.WATCH, Disposition.CASCADE_ANCHOR)
        targets = [
            c for c in self._companies
            if c.disposition in eligible and c.ciq_status == CapitalIQStatus.PENDING
        ]

        matched = 0
        not_found = 0
        skipped = 0
        errors = 0

        for company in targets:
            # Skip if PitchBook already provided complete data
            if skip_if_pb_complete and _pb_is_complete(company):
                company.ciq_status = CapitalIQStatus.SKIPPED
                company.workflow_stage = WorkflowStage.CAPITALIQ_ENRICHMENT
                skipped += 1
                continue

            try:
                search = await self._capitaliq.search_company(
                    company.canonical_name,
                    duns=company.bizapi_duns,
                )

                if not search:
                    company.ciq_status = CapitalIQStatus.NOT_FOUND
                    not_found += 1
                    company.workflow_stage = WorkflowStage.CAPITALIQ_ENRICHMENT
                    continue

                company.ciq_status = CapitalIQStatus.MATCHED
                company.ciq_entity_id = search.get("entity_id")
                matched += 1

                if company.ciq_entity_id:
                    # Get financials
                    financials = await self._capitaliq.get_financials(company.ciq_entity_id)
                    company.ciq_revenue = financials.get("revenue")
                    company.ciq_ebitda = financials.get("ebitda")
                    company.ciq_total_debt = financials.get("total_debt")
                    company.ciq_net_debt = financials.get("net_debt")
                    company.ciq_credit_metrics = financials.get("credit_metrics")

                    # Get ownership
                    ownership = await self._capitaliq.get_ownership(company.ciq_entity_id)
                    company.ciq_ownership_type = ownership.get("ownership_type")
                    company.ciq_key_investors = ownership.get("key_investors", [])
                    company.ciq_ma_history = ownership.get("ma_history", [])

                    # CIQ has highest priority for financial canonical fields
                    if company.ciq_revenue is not None:
                        # Conflict detection vs existing revenue
                        _detect_revenue_conflict(company, company.ciq_revenue, "capitaliq", self._review_items, run_id)
                        company.revenue_estimate = company.ciq_revenue
                        company.revenue_source = "capitaliq"
                        company.revenue_quality = DataQualityTag.CLEAN

                    if company.ciq_ebitda is not None:
                        company.ebitda_estimate = company.ciq_ebitda
                        company.ebitda_quality = DataQualityTag.CLEAN

                    # CIQ overrides PB for ownership (highest priority)
                    if company.ciq_ownership_type:
                        ciq_tier = _map_ownership_to_tier(company.ciq_ownership_type)
                        if ciq_tier != OwnershipTier.UNKNOWN:
                            # Conflict detection vs PitchBook ownership
                            if (
                                company.ownership_source == "pitchbook"
                                and company.ownership_tier != ciq_tier
                            ):
                                company.review_required = True
                                if ReviewReason.CONFLICTING_ENRICHMENT not in company.review_reasons:
                                    company.review_reasons.append(ReviewReason.CONFLICTING_ENRICHMENT)
                                self._review_items.extend(
                                    generate_review_items_from_enrichment_conflict(
                                        run_id=run_id,
                                        company_id=company.id,
                                        company_name=company.canonical_name,
                                        field="ownership_tier",
                                        source_a="pitchbook",
                                        value_a=company.ownership_tier,
                                        source_b="capitaliq",
                                        value_b=ciq_tier,
                                    )
                                )
                            company.ownership_tier = ciq_tier
                            company.ownership_source = "capitaliq"
                            company.ownership_confidence = search.get("match_confidence")

                # Track provenance
                company.ai_provenance["capitaliq_enrichment"] = AIProvenance(
                    ai_generated=False,
                    connector_source="capitaliq",
                    confidence_score=search.get("match_confidence", 0.0),
                    acceptance_status="auto_accepted",
                )

                company.workflow_stage = WorkflowStage.CAPITALIQ_ENRICHMENT

            except Exception as e:
                logger.error("capitaliq_enrichment_failed", company=company.canonical_name, error=str(e))
                company.ciq_status = CapitalIQStatus.ERROR
                errors += 1

        logger.info(
            "capitaliq_enrichment_complete",
            run_id=str(run_id),
            matched=matched,
            not_found=not_found,
            skipped=skipped,
            errors=errors,
        )
        return {
            "stage": "capitaliq_enrichment",
            "status": "completed",
            "matched": matched,
            "not_found": not_found,
            "skipped": skipped,
            "errors": errors,
        }

    async def _run_cascade_expansion(self, run_id: UUID, config: dict) -> dict:
        """Recursive competitor discovery from cascade anchors."""
        if not self._pitchbook:
            return {"stage": "cascade_expansion", "status": "skipped", "reason": "no_adapter"}

        anchors = [c for c in self._companies if c.disposition == Disposition.CASCADE_ANCHOR and c.pb_entity_id]

        new_companies = 0
        existing_names = {normalize_company_name(c.canonical_name) for c in self._companies}

        for anchor in anchors:
            try:
                competitors = await self._pitchbook.get_competitors(anchor.pb_entity_id)
                for comp in competitors:
                    comp_name = comp.get("name", "")
                    if not comp_name:
                        continue
                    normalized = normalize_company_name(comp_name)
                    if normalized in existing_names:
                        continue

                    new_company = CompanyRecord(
                        id=uuid4(),
                        run_id=run_id,
                        canonical_name=canonical_form(comp_name),
                        name_variants=[comp_name],
                        source_tags=[f"cascade:{anchor.canonical_name}"],
                        source_chain=[anchor.canonical_name],
                        pb_entity_id=comp.get("entity_id"),
                        pb_status=PitchBookStatus.MATCHED if comp.get("entity_id") else PitchBookStatus.PENDING,
                        workflow_stage=WorkflowStage.CASCADE_EXPANSION,
                    )
                    self._companies.append(new_company)
                    existing_names.add(normalized)
                    new_companies += 1

            except Exception as e:
                logger.error("cascade_expansion_failed", anchor=anchor.canonical_name, error=str(e))

        logger.info("cascade_expansion_complete", run_id=str(run_id), new_companies=new_companies)
        return {"stage": "cascade_expansion", "status": "completed", "new_companies": new_companies}

    async def _run_final_dedup(self, run_id: UUID, config: dict) -> dict:
        """Final deduplication pass across all sources (including cascade-added)."""
        names = [c.canonical_name for c in self._companies]
        dedup = deduplicate_names(names)

        # Remove auto-merged duplicates
        merged_names = {merged for _, merged, _ in dedup.merged}
        before = len(self._companies)
        self._companies = [c for c in self._companies if c.canonical_name not in merged_names]

        # Add review items for ambiguous
        if dedup.review:
            self._review_items.extend(
                generate_review_items_from_dedup(run_id, dedup.review)
            )

        for c in self._companies:
            c.workflow_stage = WorkflowStage.FINAL_DEDUP

        removed = before - len(self._companies)
        logger.info("final_dedup_complete", run_id=str(run_id), removed=removed, review=len(dedup.review))
        return {
            "stage": "final_dedup",
            "status": "completed",
            "removed": removed,
            "remaining": len(self._companies),
            "review_queue": len(dedup.review),
        }

    async def _run_qa_validation(self, run_id: UUID, config: dict) -> dict:
        """Run QA gate checks on all primary companies."""
        geo = config.get("geography_filter")
        primary = [c for c in self._companies if c.disposition == Disposition.PRIMARY]

        report = run_qa_gates(primary, geography_filter=geo)

        # Mark companies that failed QA
        failed_names = {name for name, checks in report.failures()}
        for company in self._companies:
            if company.canonical_name in failed_names:
                company.review_required = True
            company.workflow_stage = WorkflowStage.QA_VALIDATION

        logger.info("qa_validation_complete", run_id=str(run_id), passed=report.passed, failed=report.failed)
        return {
            "stage": "qa_validation",
            "status": "completed",
            "passed": report.passed,
            "failed": report.failed,
            "total": report.total,
        }

    async def _run_scoring(self, run_id: UUID, config: dict) -> dict:
        """Score eligible primary candidates."""
        tier_a_bonus = config.get("tier_a_scoring_bonus", 15.0)
        tier_b_bonus = config.get("tier_b_scoring_bonus", 8.0)
        tier_c_bonus = config.get("tier_c_scoring_bonus", 0.0)
        include_anchors = config.get("include_cascade_anchors_in_outreach", False)

        scored = 0
        for company in self._companies:
            if company.disposition == Disposition.EXCLUDE:
                company.eligible_for_outreach = False
                company.workflow_stage = WorkflowStage.SCORING
                continue

            if company.disposition == Disposition.CASCADE_ANCHOR and not include_anchors:
                company.eligible_for_outreach = False
                company.workflow_stage = WorkflowStage.SCORING
                continue

            total, components = score_company(
                company,
                tier_a_bonus=tier_a_bonus,
                tier_b_bonus=tier_b_bonus,
                tier_c_bonus=tier_c_bonus,
            )
            company.total_score = total
            company.score_components = components
            company.eligible_for_outreach = (
                company.disposition == Disposition.PRIMARY and not company.review_required
            )
            company.workflow_stage = WorkflowStage.SCORING
            scored += 1

        logger.info("scoring_complete", run_id=str(run_id), scored=scored)
        return {"stage": "scoring", "status": "completed", "scored": scored}

    async def _run_export(self, run_id: UUID, config: dict) -> dict:
        """Generate export files."""
        if not self._storage:
            logger.warning("export_no_storage", run_id=str(run_id))
            return {"stage": "export", "status": "skipped", "reason": "no_storage"}

        # Convert companies to dicts for export
        company_dicts = [c.model_dump(mode="json") for c in self._companies]

        export_service = ExportService(self._storage)
        manifest = await export_service.export_run(
            run_id=run_id,
            companies=company_dicts,
            format="all",
            config_snapshot=config,
        )

        for c in self._companies:
            c.workflow_stage = WorkflowStage.EXPORT

        logger.info("export_complete", run_id=str(run_id), exports=len(manifest.get("exports", [])))
        return {"stage": "export", "status": "completed", "files": manifest.get("exports", [])}

    @property
    def companies(self) -> list[CompanyRecord]:
        """Access pipeline results."""
        return self._companies

    @property
    def review_items(self) -> list:
        """Access generated review queue items."""
        return self._review_items


def _pb_is_complete(company: CompanyRecord) -> bool:
    """Check if PitchBook already provided complete financial data."""
    return (
        company.pb_status == PitchBookStatus.MATCHED
        and company.revenue_estimate is not None
        and company.ebitda_estimate is not None
        and company.ownership_tier != OwnershipTier.UNKNOWN
    )


def _detect_revenue_conflict(
    company: CompanyRecord,
    new_revenue: float,
    new_source: str,
    review_items: list,
    run_id: UUID,
) -> None:
    """Flag review if new revenue diverges >50% from existing estimate."""
    if company.revenue_estimate is None or company.revenue_estimate == 0:
        return
    ratio = abs(new_revenue - company.revenue_estimate) / company.revenue_estimate
    if ratio > 0.50:
        company.review_required = True
        if ReviewReason.CONFLICTING_ENRICHMENT not in company.review_reasons:
            company.review_reasons.append(ReviewReason.CONFLICTING_ENRICHMENT)
        review_items.extend(
            generate_review_items_from_enrichment_conflict(
                run_id=run_id,
                company_id=company.id,
                company_name=company.canonical_name,
                field="revenue_estimate",
                source_a=company.revenue_source or "unknown",
                value_a=str(company.revenue_estimate),
                source_b=new_source,
                value_b=str(new_revenue),
            )
        )


def _map_ownership_to_tier(ownership_type: str) -> OwnershipTier:
    """Map ownership type strings to tier enum."""
    tier_a = {"founder_owned", "family_owned", "privately_held", "founder/family"}
    tier_b = {
        "family_office_backed", "vc_backed", "growth_equity_backed",
        "family_office", "venture_capital", "growth_equity",
    }
    tier_c = {"pe_backed", "private_equity", "sponsor_backed"}

    ot = ownership_type.lower().replace(" ", "_")
    if ot in tier_a:
        return OwnershipTier.TIER_A
    if ot in tier_b:
        return OwnershipTier.TIER_B
    if ot in tier_c:
        return OwnershipTier.TIER_C
    return OwnershipTier.UNKNOWN
