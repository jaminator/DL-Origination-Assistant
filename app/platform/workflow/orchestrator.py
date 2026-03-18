"""Pipeline orchestrator — sequences workflow stages with checkpointing and DB persistence."""

from uuid import UUID

from app.platform.models.enums import RunStatus, WorkflowStage
from app.platform.utils.logging import get_logger

logger = get_logger("workflow.orchestrator")


# Ordered pipeline stages for the borrower miner
MINER_STAGES = [
    WorkflowStage.NAME_GENERATION,
    WorkflowStage.NAME_NORMALIZATION,
    WorkflowStage.WEB_ENHANCEMENT,
    WorkflowStage.DISPOSITIONING,
    WorkflowStage.BIZAPI_ENRICHMENT,
    WorkflowStage.PITCHBOOK_ENRICHMENT,
    WorkflowStage.CAPITALIQ_ENRICHMENT,
    WorkflowStage.CASCADE_EXPANSION,
    WorkflowStage.FINAL_DEDUP,
    WorkflowStage.QA_VALIDATION,
    WorkflowStage.SCORING,
    WorkflowStage.EXPORT,
]


class WorkflowOrchestrator:
    """Manages pipeline execution with checkpoint-after-each-stage and DB persistence."""

    def __init__(self, run_repo=None, checkpoint_repo=None, company_repo=None, review_repo=None, storage=None):
        self._run_repo = run_repo
        self._checkpoint_repo = checkpoint_repo
        self._company_repo = company_repo
        self._review_repo = review_repo
        self._storage = storage

    async def run_pipeline(self, run_id: UUID, miner_engine=None) -> dict:
        """Execute the full miner pipeline with per-stage checkpointing."""
        logger.info("pipeline_start", run_id=str(run_id))
        if self._run_repo:
            await self._run_repo.update_status(str(run_id), RunStatus.RUNNING.value)

        try:
            config = {}
            if self._run_repo:
                run = await self._run_repo.get(str(run_id))
                if run:
                    config = run.config

            result = {}
            if miner_engine:
                result = await miner_engine.execute_pipeline(run_id, config)

                # Persist companies to DB
                await self._persist_companies(run_id, miner_engine)

                # Persist review items
                await self._persist_review_items(miner_engine)

                # Save final checkpoint
                await self._save_checkpoint(
                    run_id, WorkflowStage.COMPLETED.value,
                    company_count=len(miner_engine.companies),
                    notes="Pipeline completed successfully",
                )

            if self._run_repo:
                await self._run_repo.update_stage(str(run_id), WorkflowStage.COMPLETED.value, RunStatus.COMPLETED.value)

            company_count = len(miner_engine.companies) if miner_engine else 0
            logger.info("pipeline_complete", run_id=str(run_id), companies=company_count)
            return result
        except Exception as e:
            logger.error("pipeline_failed", run_id=str(run_id), error=str(e))
            if self._run_repo:
                await self._run_repo.update_status(str(run_id), RunStatus.FAILED.value)

            # Save partial results on failure
            if miner_engine:
                await self._persist_companies(run_id, miner_engine)
                await self._persist_review_items(miner_engine)
            raise

    async def resume_pipeline(self, run_id: UUID, miner_engine=None) -> dict:
        """Resume from last checkpoint."""
        logger.info("pipeline_resume", run_id=str(run_id))

        start_from = None
        if self._checkpoint_repo:
            checkpoint = await self._checkpoint_repo.get_latest(str(run_id))
            if checkpoint:
                # Resume from the stage AFTER the last checkpoint
                stage_idx = None
                for i, stage in enumerate(MINER_STAGES):
                    if stage.value == checkpoint.stage:
                        stage_idx = i
                        break
                if stage_idx is not None and stage_idx + 1 < len(MINER_STAGES):
                    start_from = MINER_STAGES[stage_idx + 1]

        config = {}
        if self._run_repo:
            run = await self._run_repo.get(str(run_id))
            if run:
                config = run.config
            await self._run_repo.update_status(str(run_id), RunStatus.RUNNING.value)

        result = {}
        if miner_engine:
            result = await miner_engine.execute_pipeline(run_id, config, start_from=start_from)
            await self._persist_companies(run_id, miner_engine)
            await self._persist_review_items(miner_engine)

        if self._run_repo:
            await self._run_repo.update_stage(str(run_id), WorkflowStage.COMPLETED.value, RunStatus.COMPLETED.value)

        return result

    async def rerun_stage(self, run_id: UUID, stage: WorkflowStage, miner_engine=None) -> dict:
        """Re-run a single stage without advancing."""
        logger.info("stage_rerun", run_id=str(run_id), stage=stage.value)
        config = {}
        if self._run_repo:
            run = await self._run_repo.get(str(run_id))
            if run:
                config = run.config

        if miner_engine:
            return await miner_engine.rerun_stage(run_id, config, stage)
        return {}

    async def _persist_companies(self, run_id: UUID, miner_engine) -> None:
        """Persist all pipeline companies to the database."""
        if not self._company_repo:
            return
        for company in miner_engine.companies:
            company_dict = company.model_dump(mode="json")
            company_dict["run_id"] = str(run_id)
            await self._company_repo.upsert(company_dict)
        logger.info("companies_persisted", run_id=str(run_id), count=len(miner_engine.companies))

    async def _persist_review_items(self, miner_engine) -> None:
        """Persist review queue items to the database."""
        if not self._review_repo:
            return
        for item in miner_engine.review_items:
            await self._review_repo.add(item.model_dump(mode="json"))
        logger.info("review_items_persisted", count=len(miner_engine.review_items))

    async def _save_checkpoint(
        self, run_id: UUID, stage: str, company_count: int = 0, notes: str | None = None,
    ) -> None:
        """Save a checkpoint to the database."""
        if not self._checkpoint_repo:
            return
        await self._checkpoint_repo.create(
            run_id=str(run_id),
            stage=stage,
            company_count=company_count,
            artifact_path=f"checkpoints/{run_id}/{stage}",
            notes=notes,
        )
