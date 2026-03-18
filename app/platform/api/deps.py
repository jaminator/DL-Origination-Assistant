"""Dependency injection for FastAPI routes."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.llm_service import LLMService, get_llm_service
from app.ai.mcp_manager import MCPManager, mcp_manager
from app.miner.enrichment.bizapi.adapter import BizAPIAdapter
from app.miner.enrichment.capitaliq.adapter import CapitalIQAdapter
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


def get_bizapi_adapter() -> BizAPIAdapter:
    from app.platform.config.settings import settings
    if settings.bizapi_provider == "rest":
        from app.miner.enrichment.bizapi.rest_client import BizAPIRESTClient
        return BizAPIRESTClient()
    from app.miner.enrichment.bizapi.mock_client import MockBizAPIClient
    return MockBizAPIClient()


def get_capitaliq_adapter() -> CapitalIQAdapter:
    from app.platform.config.settings import settings
    if settings.capitaliq_provider == "rest":
        from app.miner.enrichment.capitaliq.rest_client import CapitalIQRESTClient
        return CapitalIQRESTClient()
    from app.miner.enrichment.capitaliq.mock_client import MockCapitalIQClient
    return MockCapitalIQClient()


async def get_current_user() -> dict:
    """Stub for future auth integration. Returns a default user when AUTH_ENABLED=false."""
    from app.platform.config.settings import settings
    if not settings.auth_enabled:
        return {"user_id": "local-dev", "name": "Local Developer", "roles": ["admin"]}
    # TODO: Implement real auth/SSO lookup
    raise NotImplementedError("Auth not configured")
