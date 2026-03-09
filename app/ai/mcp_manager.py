"""MCP client manager / connector registry."""

from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel

from app.platform.utils.logging import get_logger

logger = get_logger("ai.mcp")


class ConnectorHealth(BaseModel):
    name: str
    available: bool
    message: str = ""


class MCPConnector(ABC):
    """Abstract MCP connector interface."""

    name: str = ""

    @abstractmethod
    async def is_available(self) -> bool:
        ...

    @abstractmethod
    async def health_check(self) -> ConnectorHealth:
        ...

    @abstractmethod
    async def call(self, method: str, params: dict | None = None) -> Any:
        ...


class MCPManager:
    """Registry for MCP connectors. Connectors registered at app startup."""

    def __init__(self):
        self._connectors: dict[str, MCPConnector] = {}

    def register(self, connector: MCPConnector) -> None:
        logger.info("mcp_register", connector=connector.name)
        self._connectors[connector.name] = connector

    async def get(self, name: str) -> MCPConnector | None:
        connector = self._connectors.get(name)
        if connector and await connector.is_available():
            return connector
        return None

    async def health_report(self) -> dict[str, ConnectorHealth]:
        report = {}
        for name, connector in self._connectors.items():
            report[name] = await connector.health_check()
        return report

    @property
    def registered_names(self) -> list[str]:
        return list(self._connectors.keys())


# Global singleton
mcp_manager = MCPManager()
