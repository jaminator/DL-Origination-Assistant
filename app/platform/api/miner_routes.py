"""Borrower miner API endpoints — companies, review queue, stage re-runs."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.api.deps import get_db
from app.platform.persistence.repositories import CompanyRepository, ReviewRepository

router = APIRouter(prefix="/runs", tags=["miner"])


@router.get("/{run_id}/companies")
async def list_companies(
    run_id: str,
    disposition: str | None = None,
    limit: int = 100,
    offset: int = 0,
    session: AsyncSession = Depends(get_db),
):
    """List companies for a run, optionally filtered by disposition."""
    repo = CompanyRepository(session)
    companies = await repo.list_by_run(run_id, disposition=disposition, limit=limit, offset=offset)
    total = await repo.count_by_run(run_id)
    return {
        "run_id": run_id,
        "total": total,
        "limit": limit,
        "offset": offset,
        "companies": [
            {
                "id": c.id,
                "canonical_name": c.canonical_name,
                "disposition": c.disposition,
                "ownership_tier": c.ownership_tier,
                "total_score": c.total_score,
                "eligible_for_outreach": c.eligible_for_outreach,
                "review_required": c.review_required,
                "data": c.data,
            }
            for c in companies
        ],
    }


@router.get("/{run_id}/companies/{company_id}")
async def get_company(run_id: str, company_id: str, session: AsyncSession = Depends(get_db)):
    """Get full company detail."""
    repo = CompanyRepository(session)
    company = await repo.get(company_id)
    if not company or company.run_id != run_id:
        raise HTTPException(status_code=404, detail="Company not found")
    return {"id": company.id, "canonical_name": company.canonical_name, "data": company.data}


@router.get("/{run_id}/review-queue")
async def list_review_queue(
    run_id: str,
    resolved: bool | None = None,
    session: AsyncSession = Depends(get_db),
):
    """List review queue items."""
    repo = ReviewRepository(session)
    items = await repo.list_by_run(run_id, resolved=resolved)
    return [
        {
            "id": item.id,
            "reason": item.reason,
            "details": item.details,
            "resolved": item.resolved,
            "resolution": item.resolution,
            "data": item.data,
        }
        for item in items
    ]


class ResolveRequest(BaseModel):
    resolution: str  # merge | keep_both | exclude | accept


@router.post("/{run_id}/review-queue/{item_id}/resolve")
async def resolve_review_item(
    run_id: str,
    item_id: str,
    req: ResolveRequest,
    session: AsyncSession = Depends(get_db),
):
    """Resolve a review queue item."""
    repo = ReviewRepository(session)
    await repo.resolve(item_id, req.resolution)
    return {"status": "resolved", "item_id": item_id, "resolution": req.resolution}


@router.post("/{run_id}/stages/{stage}/rerun")
async def rerun_stage(run_id: str, stage: str, session: AsyncSession = Depends(get_db)):
    """Re-run a single pipeline stage (inline)."""
    from uuid import UUID

    from app.ai.llm_service import get_llm_service
    from app.miner.engine import MinerEngine
    from app.miner.pitchbook.mcp_client import get_pitchbook_adapter
    from app.platform.models.enums import WorkflowStage
    from app.platform.persistence.repositories import RunRepository
    from app.platform.persistence.storage import get_storage
    from app.platform.workflow.orchestrator import WorkflowOrchestrator

    try:
        ws = WorkflowStage(stage)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown stage: {stage}")

    run_repo = RunRepository(session)
    run = await run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    from app.platform.api.deps import get_bizapi_adapter, get_capitaliq_adapter
    llm = get_llm_service()
    pb = get_pitchbook_adapter()
    storage = get_storage()
    miner = MinerEngine(
        llm_service=llm, pitchbook_adapter=pb,
        bizapi_adapter=get_bizapi_adapter(),
        capitaliq_adapter=get_capitaliq_adapter(),
        storage=storage,
    )
    orchestrator = WorkflowOrchestrator(run_repo=run_repo, storage=storage)

    result = await orchestrator.rerun_stage(UUID(run_id), ws, miner_engine=miner)
    return {"status": "completed", "run_id": run_id, "stage": stage, "result": result}
