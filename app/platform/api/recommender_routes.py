"""Sub-vertical and source recommendation API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.api.deps import get_db, get_llm
from app.platform.persistence.repositories import RecommendationRepository, RunRepository

router = APIRouter(prefix="/runs", tags=["recommender"])


class ConfirmSubverticalsRequest(BaseModel):
    selected_ids: list[str] | None = None
    accept_all: bool = False


class ConfirmSourcesRequest(BaseModel):
    selected_ids: list[str] | None = None
    accept_all: bool = False
    deselected_ids: list[str] | None = None


@router.post("/{run_id}/recommend-subverticals")
async def recommend_subverticals(run_id: str, session: AsyncSession = Depends(get_db)):
    """Generate AI sub-vertical recommendations for a run's theme."""
    from uuid import UUID

    from app.platform.models.run import RunConfig
    from app.recommender.engine import RecommenderEngine

    run_repo = RunRepository(session)
    run = await run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    llm = get_llm()
    engine = RecommenderEngine(llm)
    config = RunConfig(**run.config)

    recommendations = await engine.recommend_subverticals(UUID(run_id), config)

    # Persist recommendations
    rec_repo = RecommendationRepository(session)
    rec_dicts = [r.model_dump(mode="json") for r in recommendations]
    for d in rec_dicts:
        d["run_id"] = run_id
    await rec_repo.save_theme_recommendations(rec_dicts)

    # Update run stage
    await run_repo.update_stage(run_id, "subvertical_recommendation")

    return {"run_id": run_id, "count": len(recommendations), "recommendations": rec_dicts}


@router.get("/{run_id}/subverticals")
async def list_subverticals(run_id: str, session: AsyncSession = Depends(get_db)):
    """List current sub-vertical recommendations with full detail from stored data."""
    repo = RecommendationRepository(session)
    recs = await repo.list_theme_recommendations(run_id)
    results = []
    for r in recs:
        # Spread the full data dict, then overlay indexed columns
        entry = dict(r.data) if r.data else {}
        entry.update(
            {
                "id": r.id,
                "subvertical_name": r.subvertical_name,
                "recommendation_status": r.recommendation_status,
                "total_recommendation_score": r.total_recommendation_score,
                "user_selected": r.user_selected,
            }
        )
        results.append(entry)
    return results


@router.post("/{run_id}/confirm-subverticals")
async def confirm_subverticals(
    run_id: str,
    req: ConfirmSubverticalsRequest,
    session: AsyncSession = Depends(get_db),
):
    """Lock in sub-vertical selections."""
    rec_repo = RecommendationRepository(session)
    recs = await rec_repo.list_theme_recommendations(run_id)

    if req.accept_all:
        for r in recs:
            await rec_repo.update_selection(r.id, True)
        selected = [r.subvertical_name for r in recs]
    elif req.selected_ids:
        for r in recs:
            selected_flag = r.id in req.selected_ids
            await rec_repo.update_selection(r.id, selected_flag)
        selected = [r.subvertical_name for r in recs if r.id in req.selected_ids]
    else:
        selected = [r.subvertical_name for r in recs if r.user_selected]

    # Persist selected subverticals into run config
    run_repo = RunRepository(session)
    run = await run_repo.get(run_id)
    if run:
        config = run.config.copy()
        config["selected_subverticals"] = selected
        await run_repo.update_config(run_id, config)
        await run_repo.update_stage(run_id, "subvertical_confirmation")

    return {"run_id": run_id, "confirmed_subverticals": selected}


@router.post("/{run_id}/recommend-sources")
async def recommend_sources(run_id: str, session: AsyncSession = Depends(get_db)):
    """Generate AI source recommendations for confirmed sub-verticals."""
    from uuid import UUID

    from app.recommender.engine import RecommenderEngine

    run_repo = RunRepository(session)
    run = await run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    subverticals = run.config.get("selected_subverticals", [])
    if not subverticals:
        raise HTTPException(status_code=400, detail="No sub-verticals confirmed yet")

    llm = get_llm()
    engine = RecommenderEngine(llm)
    revenue_ceiling = run.config.get("revenue_ceiling", 1000.0)

    sources = await engine.recommend_sources(UUID(run_id), subverticals, revenue_ceiling)

    rec_repo = RecommendationRepository(session)
    src_dicts = [s.model_dump(mode="json") for s in sources]
    for d in src_dicts:
        d["run_id"] = run_id
    await rec_repo.save_source_recommendations(src_dicts)

    await run_repo.update_stage(run_id, "source_recommendation")

    return {"run_id": run_id, "count": len(sources), "sources": src_dicts}


@router.get("/{run_id}/sources")
async def list_sources(run_id: str, session: AsyncSession = Depends(get_db)):
    """List current source recommendations with full detail from stored data."""
    repo = RecommendationRepository(session)
    sources = await repo.list_source_recommendations(run_id)
    results = []
    for s in sources:
        entry = dict(s.data) if s.data else {}
        entry.update(
            {
                "id": s.id,
                "source_name": s.source_name,
                "source_type": s.source_type,
                "user_selected": s.user_selected,
            }
        )
        results.append(entry)
    return results


@router.post("/{run_id}/confirm-sources")
async def confirm_sources(
    run_id: str,
    req: ConfirmSourcesRequest,
    session: AsyncSession = Depends(get_db),
):
    """Lock in source selections."""
    rec_repo = RecommendationRepository(session)
    sources = await rec_repo.list_source_recommendations(run_id)

    confirmed = []
    for s in sources:
        if req.accept_all:
            confirmed.append(s.data)
        elif req.deselected_ids and s.id in req.deselected_ids:
            continue
        elif (req.selected_ids and s.id in req.selected_ids) or s.user_selected:
            confirmed.append(s.data)

    run_repo = RunRepository(session)
    run = await run_repo.get(run_id)
    if run:
        config = run.config.copy()
        config["selected_sources"] = confirmed
        await run_repo.update_config(run_id, config)
        await run_repo.update_stage(run_id, "source_confirmation")

    return {"run_id": run_id, "confirmed_sources_count": len(confirmed)}
