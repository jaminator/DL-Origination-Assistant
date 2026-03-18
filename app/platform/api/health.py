"""Health and readiness endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.mcp_manager import MCPManager
from app.platform.api.deps import get_db, get_mcp

router = APIRouter(tags=["health"])


@router.get("/health")
async def health_check(session: AsyncSession = Depends(get_db)):
    """Basic health check — verifies DB connectivity."""
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    return {
        "status": "healthy" if db_status == "ok" else "degraded",
        "database": db_status,
    }


@router.get("/readiness")
async def readiness_check(
    session: AsyncSession = Depends(get_db),
    mcp: MCPManager = Depends(get_mcp),
):
    """Full readiness check — DB + connectors."""
    try:
        await session.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = f"error: {e}"

    connector_report = await mcp.health_report()
    connectors = {name: {"available": h.available, "message": h.message} for name, h in connector_report.items()}

    # Enrichment provider health
    from app.platform.api.deps import get_bizapi_adapter, get_capitaliq_adapter
    try:
        bizapi = get_bizapi_adapter()
        bizapi_available = await bizapi.is_available()
    except Exception:
        bizapi_available = False
    try:
        capitaliq = get_capitaliq_adapter()
        capitaliq_available = await capitaliq.is_available()
    except Exception:
        capitaliq_available = False

    connectors["bizapi"] = {"available": bizapi_available, "message": "ok" if bizapi_available else "not configured"}
    connectors["capitaliq"] = {
        "available": capitaliq_available,
        "message": "ok" if capitaliq_available else "not configured",
    }

    return {
        "status": "ready" if db_status == "ok" else "not_ready",
        "database": db_status,
        "connectors": connectors,
    }
