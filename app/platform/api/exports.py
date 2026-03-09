"""Export API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.api.deps import get_db, get_file_storage
from app.platform.persistence.repositories import CompanyRepository, ExportRepository, RunRepository

router = APIRouter(prefix="/runs", tags=["exports"])


@router.get("/{run_id}/exports")
async def list_exports(run_id: str, session: AsyncSession = Depends(get_db)):
    """List available exports for a run."""
    repo = ExportRepository(session)
    manifests = await repo.list_by_run(run_id)
    return [{"id": m.id, "created_at": m.created_at.isoformat(), "data": m.data} for m in manifests]


@router.post("/{run_id}/exports")
async def trigger_export(
    run_id: str,
    format: str = "excel",
    session: AsyncSession = Depends(get_db),
):
    """Trigger export generation."""
    from uuid import UUID

    from app.platform.exports.service import ExportService

    run_repo = RunRepository(session)
    run = await run_repo.get(run_id)
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    company_repo = CompanyRepository(session)
    companies = await company_repo.list_by_run(run_id, limit=10000)
    company_dicts = [c.data for c in companies]

    storage = get_file_storage()
    export_svc = ExportService(storage)
    manifest = await export_svc.export_run(UUID(run_id), company_dicts, format=format, config_snapshot=run.config)

    # Persist manifest
    export_repo = ExportRepository(session)
    await export_repo.save_manifest({"run_id": run_id, **manifest})

    return manifest


@router.get("/{run_id}/exports/{export_id}/download")
async def download_export(run_id: str, export_id: str):
    """Download an export file."""
    storage = get_file_storage()
    # Look for the export in storage
    files = await storage.list_files(f"exports/{run_id}")
    if not files:
        raise HTTPException(status_code=404, detail="No exports found")

    # Return the first matching file
    for f in files:
        if not f.endswith("manifest.json"):
            data = await storage.load(f)
            content_type = "application/octet-stream"
            if f.endswith(".csv"):
                content_type = "text/csv"
            elif f.endswith(".xlsx"):
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif f.endswith(".jsonl"):
                content_type = "application/jsonl"
            filename = f.split("/")[-1]
            headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
            return Response(content=data, media_type=content_type, headers=headers)

    raise HTTPException(status_code=404, detail="Export file not found")
