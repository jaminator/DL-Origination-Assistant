"""PitchBook MCP connector implementation.

TODO: Requires MCP server credentials and endpoint configuration.
This is a placeholder for the real MCP integration.
"""

from app.miner.pitchbook.adapter import PitchBookAdapter
from app.platform.config.settings import settings
from app.platform.utils.logging import get_logger

logger = get_logger("miner.pitchbook.mcp")


class PitchBookMCPClient(PitchBookAdapter):
    """Real PitchBook integration via MCP connector."""

    def __init__(self):
        self._url = settings.mcp_pitchbook_url
        self._token = settings.mcp_pitchbook_token

    async def search_company(self, company_name: str) -> dict | None:
        # TODO: Implement MCP call to PitchBook search
        raise NotImplementedError("PitchBook MCP integration requires credentials")

    async def get_company_detail(self, entity_id: str) -> dict:
        raise NotImplementedError("PitchBook MCP integration requires credentials")

    async def get_competitors(self, entity_id: str) -> list[dict]:
        raise NotImplementedError("PitchBook MCP integration requires credentials")

    async def get_debt_details(self, entity_id: str) -> list[dict]:
        raise NotImplementedError("PitchBook MCP integration requires credentials")

    async def is_available(self) -> bool:
        return bool(self._url and self._token)


def get_pitchbook_adapter() -> PitchBookAdapter:
    """Factory: returns mock or real PitchBook adapter based on settings."""
    if settings.pitchbook_provider == "mcp":
        return PitchBookMCPClient()
    from app.miner.pitchbook.mock_client import MockPitchBookClient
    return MockPitchBookClient()
