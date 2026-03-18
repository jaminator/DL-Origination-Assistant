"""Run CRUD + execute/resume endpoints."""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.api.deps import get_db
from app.platform.persistence.repositories import CheckpointRepository, RunRepository

router = APIRouter(prefix="/runs", tags=["runs"])


class CreateRunRequest(BaseModel):
    theme: str
    theme_notes: str | None = None
    industry_description: str | None = None
    geography_filter: list[str] = ["US"]
    revenue_ceiling: float = 1000.0
    cascade_anchor_threshold: float = 1000.0
    ebitda_soft_ceiling: float = 150.0
    max_recursion_depth: int = 3
    profile_name: str | None = None
    tier_a_scoring_bonus: float = 15.0
    tier_b_scoring_bonus: float = 8.0
    tier_c_scoring_bonus: float = 0.0
    include_cascade_anchors_in_outreach: bool = False
    boundary_treatment: str = "watch"


@router.get("")
async def list_runs(
    limit: int = 50,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """List all runs, newest first."""
    repo = RunRepository(session)
    runs = await repo.list_runs(limit=limit)
    # Apply offset in-memory (list_runs doesn't support offset yet)
    page = runs[offset : offset + limit]
    return {
        "total": len(runs),
        "limit": limit,
        "offset": offset,
        "runs": [
            {
                "id": r.id,
                "theme": r.config.get("theme", "") if r.config else "",
                "status": r.status,
                "current_stage": r.current_stage,
                "created_at": r.created_at.isoformat(),
                "updated_at": r.updated_at.isoformat(),
            }
            for r in page
        ],
    }


@router.post("")
async def create_run(req: CreateRunRequest, session: AsyncSession = Depends(get_db)):
    """Create a new origination run."""
    repo = RunRepository(session)
    run = await repo.create(req.model_dump())
    return {"id": run.id, "status": run.status, "created_at": run.created_at.isoformat()}


@router.get("/{run_id}")
async def get_run(run_id: str, session: AsyncSession = Depends(get_db)):
    """Get run details."""
    repo = RunRepository(session)
    run = await repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {
        "id": run.id,
        "config": run.config,
        "current_stage": run.current_stage,
        "status": run.status,
        "created_at": run.created_at.isoformat(),
        "updated_at": run.updated_at.isoformat(),
    }


@router.get("/{run_id}/status")
async def get_run_status(run_id: str, session: AsyncSession = Depends(get_db)):
    """Get pipeline progress."""
    repo = RunRepository(session)
    run = await repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return {"id": run.id, "current_stage": run.current_stage, "status": run.status}


@router.post("/{run_id}/execute")
async def execute_run(run_id: str, session: AsyncSession = Depends(get_db)):
    """Start the borrower mining pipeline (async background job, inline fallback)."""
    repo = RunRepository(session)
    run = await repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Try ARQ background job first
    from app.platform.jobs.tasks import enqueue_pipeline
    job_id = await enqueue_pipeline(run_id)

    if job_id:
        return {"status": "accepted", "job_id": job_id, "run_id": run_id}

    # Fallback: run inline if Redis/ARQ unavailable
    from app.ai.llm_service import get_llm_service
    from app.miner.engine import MinerEngine
    from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
    from app.platform.persistence.repositories import CheckpointRepository, CompanyRepository, ReviewRepository
    from app.platform.persistence.storage import get_storage
    from app.platform.workflow.orchestrator import WorkflowOrchestrator

    llm = get_llm_service()
    pb = get_pitchbook_adapter()
    storage = get_storage()
    from app.platform.api.deps import get_bizapi_adapter, get_capitaliq_adapter
    miner = MinerEngine(
        llm_service=llm, pitchbook_adapter=pb,
        bizapi_adapter=get_bizapi_adapter(),
        capitaliq_adapter=get_capitaliq_adapter(),
        storage=storage,
    )
    orchestrator = WorkflowOrchestrator(
        run_repo=repo,
        checkpoint_repo=CheckpointRepository(session),
        company_repo=CompanyRepository(session),
        review_repo=ReviewRepository(session),
        storage=storage,
    )
    result = await orchestrator.run_pipeline(UUID(run_id), miner_engine=miner)
    return {"status": "completed", "run_id": run_id, "result": result}


@router.post("/{run_id}/resume")
async def resume_run(run_id: str, session: AsyncSession = Depends(get_db)):
    """Resume from last checkpoint."""
    repo = RunRepository(session)
    run = await repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    # Try ARQ first
    from app.platform.jobs.tasks import enqueue_resume
    job_id = await enqueue_resume(run_id)

    if job_id:
        return {"status": "accepted", "job_id": job_id, "run_id": run_id}

    # Inline fallback
    from app.ai.llm_service import get_llm_service
    from app.miner.engine import MinerEngine
    from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
    from app.platform.persistence.repositories import CheckpointRepository, CompanyRepository, ReviewRepository
    from app.platform.persistence.storage import get_storage
    from app.platform.workflow.orchestrator import WorkflowOrchestrator

    llm = get_llm_service()
    pb = get_pitchbook_adapter()
    storage = get_storage()
    from app.platform.api.deps import get_bizapi_adapter, get_capitaliq_adapter
    miner = MinerEngine(
        llm_service=llm, pitchbook_adapter=pb,
        bizapi_adapter=get_bizapi_adapter(),
        capitaliq_adapter=get_capitaliq_adapter(),
        storage=storage,
    )
    orchestrator = WorkflowOrchestrator(
        run_repo=repo,
        checkpoint_repo=CheckpointRepository(session),
        company_repo=CompanyRepository(session),
        review_repo=ReviewRepository(session),
        storage=storage,
    )
    result = await orchestrator.resume_pipeline(UUID(run_id), miner_engine=miner)
    return {"status": "completed", "run_id": run_id, "result": result}


@router.get("/{run_id}/checkpoints")
async def list_checkpoints(run_id: str, session: AsyncSession = Depends(get_db)):
    """List all checkpoints for a run."""
    repo = CheckpointRepository(session)
    checkpoints = await repo.list_by_run(run_id)
    return [
        {
            "id": cp.id,
            "stage": cp.stage,
            "company_count": cp.company_count,
            "created_at": cp.created_at.isoformat(),
            "notes": cp.notes,
        }
        for cp in checkpoints
    ]


@router.get("/{run_id}/checkpoints/{checkpoint_id}")
async def get_checkpoint(run_id: str, checkpoint_id: str, session: AsyncSession = Depends(get_db)):
    """Inspect a specific checkpoint."""
    from app.platform.api.deps import get_file_storage
    storage = get_file_storage()
    # Try to load checkpoint data from storage
    try:
        files = await storage.list_files(f"checkpoints/{run_id}")
        matching = [f for f in files if checkpoint_id in f]
        if matching:
            data = await storage.load_json(matching[0])
            return data
    except Exception:  # noqa: S110
        pass
    raise HTTPException(status_code=404, detail="Checkpoint not found")
