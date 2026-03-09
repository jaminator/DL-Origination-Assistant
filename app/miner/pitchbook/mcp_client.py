"""PitchBook MCP connector implementation.

When a PitchBook MCP server is configured (either via ``.mcp.json`` or
user-level Claude Code settings), this client calls the MCP tools to
retrieve PitchBook data.

Expected MCP tool contract (based on PitchBook API v2 entity model):

    Tool: pitchbook_search_companies
        Input:  { "name": str, "pageSize": int }
        Output: { "items": [CompanySearchResult ...] }

    Tool: pitchbook_get_company
        Input:  { "companyId": str }
        Output: CompanyDetail

    Tool: pitchbook_get_company_competitors
        Input:  { "companyId": str, "pageSize": int }
        Output: { "items": [CompanySummary ...] }

    Tool: pitchbook_get_company_deals
        Input:  { "companyId": str, "dealType": str, "pageSize": int }
        Output: { "items": [DealSummary ...] }

    Tool: pitchbook_get_company_investors
        Input:  { "companyId": str, "pageSize": int }
        Output: { "items": [InvestorSummary ...] }

See ``docs/pitchbook_mcp_contract.md`` for the full schema reference.
"""

from __future__ import annotations

from typing import Any

from app.ai.mcp_manager import ConnectorHealth, MCPConnector, mcp_manager
from app.miner.pitchbook.adapter import PitchBookAdapter
from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("miner.pitchbook.mcp")

# MCP tool names — must match what the PitchBook MCP server exposes
TOOL_SEARCH_COMPANIES = "pitchbook_search_companies"
TOOL_GET_COMPANY = "pitchbook_get_company"
TOOL_GET_COMPETITORS = "pitchbook_get_company_competitors"
TOOL_GET_DEALS = "pitchbook_get_company_deals"

CONNECTOR_NAME = "pitchbook"


class PitchBookMCPConnector(MCPConnector):
    """MCPConnector implementation for PitchBook.

    Wraps the low-level MCP transport (URL + token) and provides
    typed ``call()`` for PitchBook MCP tools.
    """

    name: str = CONNECTOR_NAME

    def __init__(self) -> None:
        self._url = settings.mcp_pitchbook_url
        self._token = settings.mcp_pitchbook_token

    async def is_available(self) -> bool:
        return bool(self._url and self._token)

    async def health_check(self) -> ConnectorHealth:
        available = await self.is_available()
        return ConnectorHealth(
            name=self.name,
            available=available,
            message="PitchBook MCP configured" if available else "Missing URL or token",
        )

    async def call(self, method: str, params: dict | None = None) -> Any:
        """Call a PitchBook MCP tool.

        In a live MCP environment, this would dispatch through the MCP
        transport layer (stdio / SSE / HTTP).  This implementation is a
        placeholder that raises ``NotImplementedError`` until the MCP
        server is actually connected.
        """
        if not await self.is_available():
            raise RuntimeError("PitchBook MCP connector is not configured")
        # TODO: Replace with real MCP transport call once server is connected.
        # The call would look like:
        #   response = await mcp_transport.call_tool(method, params)
        #   return response.content
        raise NotImplementedError(
            f"PitchBook MCP tool '{method}' call requires a running MCP server. "
            "Configure the server via .mcp.json or ~/.claude/settings.json."
        )


class PitchBookMCPClient(PitchBookAdapter):
    """PitchBook integration via MCP connector.

    Delegates to ``PitchBookMCPConnector.call()`` for each adapter method,
    mapping to the expected MCP tool names and normalising responses into
    the shapes the pipeline expects.
    """

    def __init__(self, connector: PitchBookMCPConnector | None = None):
        self._connector = connector or PitchBookMCPConnector()

    async def search_company(self, company_name: str) -> dict | None:
        data = await self._connector.call(
            TOOL_SEARCH_COMPANIES,
            {"name": company_name, "pageSize": 5},
        )
        items = data.get("items", []) if isinstance(data, dict) else []
        if not items:
            return None
        best = items[0]
        return {
            "entity_id": best.get("companyId", ""),
            "name": best.get("companyName", company_name),
            "match_confidence": best.get("matchConfidence", 0.8),
            "ownership_status": best.get("ownershipStatus", ""),
            "primary_industry": best.get("primaryIndustrySector", ""),
            "employee_count": best.get("employees"),
            "revenue_range": best.get("revenueRange", ""),
        }

    async def get_company_detail(self, entity_id: str) -> dict:
        data = await self._connector.call(
            TOOL_GET_COMPANY,
            {"companyId": entity_id},
        )
        if not isinstance(data, dict):
            return {}
        return {
            "entity_id": data.get("companyId", entity_id),
            "description": data.get("description", ""),
            "founded_year": data.get("yearFounded"),
            "hq_location": data.get("hqLocation", ""),
            "ownership_type": data.get("ownershipStatus", ""),
            "investors": data.get("investors", []),
            "total_raised": data.get("totalRaised"),
        }

    async def get_competitors(self, entity_id: str) -> list[dict]:
        data = await self._connector.call(
            TOOL_GET_COMPETITORS,
            {"companyId": entity_id, "pageSize": 25},
        )
        items = data.get("items", []) if isinstance(data, dict) else []
        return [
            {
                "name": c.get("companyName", ""),
                "entity_id": c.get("companyId", ""),
            }
            for c in items
        ]

    async def get_debt_details(self, entity_id: str) -> list[dict]:
        data = await self._connector.call(
            TOOL_GET_DEALS,
            {"companyId": entity_id, "dealType": "Debt", "pageSize": 25},
        )
        items = data.get("items", []) if isinstance(data, dict) else []
        return [
            {
                "facility_type": d.get("dealType", ""),
                "amount": d.get("dealSize"),
                "lender": d.get("leadInvestor", ""),
                "close_date": d.get("closeDate", ""),
                "maturity_date": d.get("maturityDate", ""),
                "pricing": d.get("pricing", ""),
            }
            for d in items
        ]

    async def is_available(self) -> bool:
        return await self._connector.is_available()


def get_pitchbook_adapter() -> PitchBookAdapter:
    """Factory: returns mock, REST, or MCP PitchBook adapter based on settings."""
    provider = settings.pitchbook_provider.lower()
    if provider == "rest":
        from app.miner.pitchbook.rest_client import PitchBookRESTClient
        return PitchBookRESTClient()
    if provider == "mcp":
        connector = PitchBookMCPConnector()
        # Register with global MCP manager for health monitoring
        mcp_manager.register(connector)
        return PitchBookMCPClient(connector)
    from app.miner.pitchbook.mock_client import MockPitchBookClient
    return MockPitchBookClient()
