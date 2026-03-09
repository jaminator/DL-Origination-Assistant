"""Research orchestration for batch AI/MCP workflows with retries and rate limiting."""

import asyncio
from collections.abc import Callable, Coroutine
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.platform.utils.logging import get_logger

logger = get_logger("ai.research")


class RetryPolicy(BaseModel):
    max_retries: int = 3
    backoff_base: float = 2.0
    backoff_max: float = 60.0
    retry_on: list[str] = Field(default_factory=lambda: ["timeout", "rate_limit", "server_error"])
    skip_on: list[str] = Field(default_factory=lambda: ["not_found", "auth_error"])


class ResearchTask(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    item_id: str = ""
    params: dict = Field(default_factory=dict)


class ResearchTaskResult(BaseModel):
    task_id: str
    item_id: str
    status: str = "pending"  # succeeded | failed | skipped
    result: Any = None
    error: str | None = None
    retries: int = 0
    latency_ms: float = 0.0


class ResearchBatchResult(BaseModel):
    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    items: list[ResearchTaskResult] = Field(default_factory=list)
    checkpoint_id: UUID | None = None
    partial: bool = False


default_retry = RetryPolicy()


class ResearchOrchestrator:
    """Manages batched AI/MCP calls with retries, rate limiting, and partial completion."""

    def __init__(self, rate_limit_rpm: int = 50):
        self._semaphore = asyncio.Semaphore(5)
        self._rate_limit = rate_limit_rpm
        self._interval = 60.0 / max(rate_limit_rpm, 1)

    async def research_batch(
        self,
        items: list[ResearchTask],
        worker_fn: Callable[[ResearchTask], Coroutine[Any, Any, Any]],
        max_concurrent: int = 5,
        retry_policy: RetryPolicy = default_retry,
        checkpoint_every: int = 25,
        checkpoint_fn: Callable[[list[ResearchTaskResult]], Coroutine[Any, Any, None]] | None = None,
    ) -> ResearchBatchResult:
        self._semaphore = asyncio.Semaphore(max_concurrent)
        results: list[ResearchTaskResult] = []

        for i, task in enumerate(items):
            result = await self._execute_with_retry(task, worker_fn, retry_policy)
            results.append(result)

            # Checkpoint periodically
            if checkpoint_fn and (i + 1) % checkpoint_every == 0:
                await checkpoint_fn(results)
                logger.info("research_checkpoint", completed=i + 1, total=len(items))

            # Rate limiting
            await asyncio.sleep(self._interval)

        succeeded = sum(1 for r in results if r.status == "succeeded")
        failed = sum(1 for r in results if r.status == "failed")
        skipped = sum(1 for r in results if r.status == "skipped")

        return ResearchBatchResult(
            total=len(items),
            succeeded=succeeded,
            failed=failed,
            skipped=skipped,
            items=results,
            partial=failed > 0,
        )

    async def _execute_with_retry(
        self,
        task: ResearchTask,
        worker_fn: Callable[[ResearchTask], Coroutine[Any, Any, Any]],
        policy: RetryPolicy,
    ) -> ResearchTaskResult:
        import time

        retries = 0
        while True:
            try:
                start = time.monotonic()
                async with self._semaphore:
                    result = await worker_fn(task)
                latency = (time.monotonic() - start) * 1000

                return ResearchTaskResult(
                    task_id=task.id,
                    item_id=task.item_id,
                    status="succeeded",
                    result=result,
                    retries=retries,
                    latency_ms=latency,
                )
            except Exception as e:
                error_type = _classify_error(e)

                if error_type in policy.skip_on:
                    return ResearchTaskResult(
                        task_id=task.id,
                        item_id=task.item_id,
                        status="skipped",
                        error=str(e),
                        retries=retries,
                    )

                if error_type in policy.retry_on and retries < policy.max_retries:
                    retries += 1
                    wait = min(policy.backoff_base ** retries, policy.backoff_max)
                    logger.warning("research_retry", task_id=task.id, retry=retries, wait=wait, error=str(e))
                    await asyncio.sleep(wait)
                    continue

                return ResearchTaskResult(
                    task_id=task.id,
                    item_id=task.item_id,
                    status="failed",
                    error=str(e),
                    retries=retries,
                )


def _classify_error(e: Exception) -> str:
    """Classify an exception into a retry category."""
    msg = str(e).lower()
    if "timeout" in msg:
        return "timeout"
    if "rate" in msg or "429" in msg:
        return "rate_limit"
    if "500" in msg or "502" in msg or "503" in msg:
        return "server_error"
    if "401" in msg or "403" in msg:
        return "auth_error"
    if "404" in msg or "not found" in msg:
        return "not_found"
    return "unknown"
