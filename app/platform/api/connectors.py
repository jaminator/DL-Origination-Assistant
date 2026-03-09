"""Connector status / health endpoints."""

from fastapi import APIRouter, Depends

from app.ai.mcp_manager import MCPManager
from app.platform.api.deps import get_mcp

router = APIRouter(prefix="/connectors", tags=["connectors"])


@router.get("/status")
async def connector_status(mcp: MCPManager = Depends(get_mcp)):
    """Get health report for all registered connectors."""
    report = await mcp.health_report()
    return {
        "connectors": {
            name: {"available": h.available, "message": h.message}
            for name, h in report.items()
        },
        "registered": mcp.registered_names,
    }
