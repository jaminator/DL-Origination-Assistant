"""ARQ worker setup for background job processing."""

import asyncio

from arq import create_pool
from arq.connections import RedisSettings

from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger, setup_logging

logger = get_logger("jobs.worker")


async def run_pipeline_job(ctx: dict, run_id: str) -> dict:
    """Background job: execute the borrower mining pipeline for a run."""
    from app.ai.llm_service import get_llm_service
    from app.miner.engine import MinerEngine
    from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
    from app.platform.persistence.database import async_session
    from app.platform.persistence.repositories import RunRepository
    from app.platform.persistence.storage import get_storage
    from app.platform.workflow.orchestrator import WorkflowOrchestrator

    from uuid import UUID

    logger.info("job_pipeline_start", run_id=run_id)

    async with async_session() as session:
        run_repo = RunRepository(session)
        storage = get_storage()
        llm = get_llm_service()
        pb = get_pitchbook_adapter()

        miner = MinerEngine(llm_service=llm, pitchbook_adapter=pb, storage=storage)
        orchestrator = WorkflowOrchestrator(run_repo=run_repo, storage=storage)

        result = await orchestrator.run_pipeline(UUID(run_id), miner_engine=miner)

    logger.info("job_pipeline_complete", run_id=run_id)
    return result


class WorkerSettings:
    """ARQ worker settings."""

    functions = [run_pipeline_job]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    max_jobs = 2
    job_timeout = 3600  # 1 hour


async def main():
    setup_logging()
    logger.info("worker_starting")
    from arq import run_worker
    run_worker(WorkerSettings)


if __name__ == "__main__":
    asyncio.run(main())
