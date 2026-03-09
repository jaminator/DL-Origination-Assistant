"""Background task definitions — thin wrappers that enqueue ARQ jobs."""

from arq import create_pool
from arq.connections import RedisSettings

from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("jobs.tasks")


async def enqueue_pipeline(run_id: str) -> str | None:
    """Enqueue a pipeline execution job. Returns the ARQ job ID."""
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        job = await redis.enqueue_job("run_pipeline_job", run_id)
        logger.info("job_enqueued", run_id=run_id, job_id=job.job_id if job else None)
        return job.job_id if job else None
    except Exception as e:
        logger.error("job_enqueue_failed", run_id=run_id, error=str(e))
        return None


async def enqueue_resume(run_id: str) -> str | None:
    """Enqueue a pipeline resume job. Returns the ARQ job ID."""
    try:
        redis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        job = await redis.enqueue_job("resume_pipeline_job", run_id)
        logger.info("resume_enqueued", run_id=run_id, job_id=job.job_id if job else None)
        return job.job_id if job else None
    except Exception as e:
        logger.error("resume_enqueue_failed", run_id=run_id, error=str(e))
        return None
