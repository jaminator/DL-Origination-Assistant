"""Borrower Miner Engine — top-level orchestrator for company discovery and enrichment."""

from uuid import UUID

from app.platform.models.enums import WorkflowStage
from app.platform.utils.logging import get_logger

logger = get_logger("miner")


class MinerEngine:
    """Orchestrates the borrower mining pipeline from source extraction through scoring."""

    def __init__(self, llm_service=None, pitchbook_adapter=None, storage=None):
        self._llm = llm_service
        self._pitchbook = pitchbook_adapter
        self._storage = storage

    async def execute_pipeline(self, run_id: UUID, config: dict, start_from: WorkflowStage | None = None) -> dict:
        """Run the full borrower mining pipeline (or resume from a given stage)."""
        logger.info("miner_pipeline_start", run_id=str(run_id))

        stages = [
            (WorkflowStage.NAME_GENERATION, self._run_name_generation),
            (WorkflowStage.NAME_NORMALIZATION, self._run_name_normalization),
            (WorkflowStage.WEB_ENHANCEMENT, self._run_web_enhancement),
            (WorkflowStage.DISPOSITIONING, self._run_dispositioning),
            (WorkflowStage.PITCHBOOK_ENRICHMENT, self._run_pitchbook_enrichment),
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
            WorkflowStage.PITCHBOOK_ENRICHMENT: self._run_pitchbook_enrichment,
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

    # -- Stage stubs (to be implemented with real logic) --

    async def _run_name_generation(self, run_id: UUID, config: dict) -> dict:
        """Extract company names from confirmed sources."""
        # TODO: Implement source adapter orchestration
        logger.info("name_generation_stub", run_id=str(run_id))
        return {"stage": "name_generation", "status": "completed", "companies_found": 0}

    async def _run_name_normalization(self, run_id: UUID, config: dict) -> dict:
        """Normalize names and run dedup."""
        logger.info("name_normalization_stub", run_id=str(run_id))
        return {"stage": "name_normalization", "status": "completed", "duplicates_found": 0}

    async def _run_web_enhancement(self, run_id: UUID, config: dict) -> dict:
        """Web-enhance each company with LLM-assisted research."""
        logger.info("web_enhancement_stub", run_id=str(run_id))
        return {"stage": "web_enhancement", "status": "completed", "companies_enriched": 0}

    async def _run_dispositioning(self, run_id: UUID, config: dict) -> dict:
        """Assign disposition: Primary / Cascade Anchor / Exclude / Watch."""
        logger.info("dispositioning_stub", run_id=str(run_id))
        return {"stage": "dispositioning", "status": "completed"}

    async def _run_pitchbook_enrichment(self, run_id: UUID, config: dict) -> dict:
        """Enrich via PitchBook MCP connector."""
        logger.info("pitchbook_enrichment_stub", run_id=str(run_id))
        return {"stage": "pitchbook_enrichment", "status": "completed", "matched": 0, "not_found": 0}

    async def _run_cascade_expansion(self, run_id: UUID, config: dict) -> dict:
        """Recursive competitor discovery from cascade anchors."""
        logger.info("cascade_expansion_stub", run_id=str(run_id))
        return {"stage": "cascade_expansion", "status": "completed", "new_companies": 0}

    async def _run_final_dedup(self, run_id: UUID, config: dict) -> dict:
        """Final deduplication pass across all sources."""
        logger.info("final_dedup_stub", run_id=str(run_id))
        return {"stage": "final_dedup", "status": "completed"}

    async def _run_qa_validation(self, run_id: UUID, config: dict) -> dict:
        """Run QA gate checks."""
        logger.info("qa_validation_stub", run_id=str(run_id))
        return {"stage": "qa_validation", "status": "completed", "passed": 0, "failed": 0}

    async def _run_scoring(self, run_id: UUID, config: dict) -> dict:
        """Score eligible primary candidates."""
        logger.info("scoring_stub", run_id=str(run_id))
        return {"stage": "scoring", "status": "completed", "scored": 0}

    async def _run_export(self, run_id: UUID, config: dict) -> dict:
        """Generate export files."""
        logger.info("export_stub", run_id=str(run_id))
        return {"stage": "export", "status": "completed", "files": []}
