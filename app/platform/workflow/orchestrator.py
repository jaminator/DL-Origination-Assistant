"""Pipeline orchestrator — sequences workflow stages with checkpointing."""

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
    WorkflowStage.PITCHBOOK_ENRICHMENT,
    WorkflowStage.CASCADE_EXPANSION,
    WorkflowStage.FINAL_DEDUP,
    WorkflowStage.QA_VALIDATION,
    WorkflowStage.SCORING,
    WorkflowStage.EXPORT,
]


class WorkflowOrchestrator:
    """Manages pipeline execution with checkpoint-after-each-stage."""

    def __init__(self, run_repo=None, checkpoint_repo=None, storage=None):
        self._run_repo = run_repo
        self._checkpoint_repo = checkpoint_repo
        self._storage = storage

    async def run_pipeline(self, run_id: UUID, miner_engine=None) -> dict:
        """Execute the full miner pipeline."""
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

            if self._run_repo:
                await self._run_repo.update_stage(str(run_id), WorkflowStage.COMPLETED.value, RunStatus.COMPLETED.value)

            return result
        except Exception as e:
            logger.error("pipeline_failed", run_id=str(run_id), error=str(e))
            if self._run_repo:
                await self._run_repo.update_status(str(run_id), RunStatus.FAILED.value)
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

        if miner_engine:
            return await miner_engine.execute_pipeline(run_id, config, start_from=start_from)
        return {}

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
