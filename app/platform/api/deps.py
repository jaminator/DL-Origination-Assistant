"""Dependency injection for FastAPI routes."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_service import LLMService, get_llm_service
from app.ai.mcp_manager import MCPManager, mcp_manager
from app.platform.persistence.database import get_session
from app.platform.persistence.storage import StorageBackend, get_storage


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


def get_llm() -> LLMService:
    return get_llm_service()


def get_mcp() -> MCPManager:
    return mcp_manager


def get_file_storage() -> StorageBackend:
    return get_storage()


async def get_current_user() -> dict:
    """Stub for future auth integration. Returns a default user when AUTH_ENABLED=false."""
    from app.platform.config.settings import settings
    if not settings.auth_enabled:
        return {"user_id": "local-dev", "name": "Local Developer", "roles": ["admin"]}
    # TODO: Implement real auth/SSO lookup
    raise NotImplementedError("Auth not configured")
