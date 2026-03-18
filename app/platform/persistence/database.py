"""Async database engine and session factory."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.platform.config.settings import settings

_engine: AsyncEngine | None = None
_async_session: async_sessionmaker[AsyncSession] | None = None


def _get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.database_url,
            echo=False,
            pool_pre_ping=True,
        )
    return _engine


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _async_session
    if _async_session is None:
        _async_session = async_sessionmaker(
            _get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session


def configure_engine(url: str, **kwargs) -> AsyncEngine:
    """Replace the default engine. Used by tests to point at SQLite or test-specific databases."""
    global _engine, _async_session
    _engine = create_async_engine(url, **kwargs)
    _async_session = async_sessionmaker(
        _engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    return _engine


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    session_factory = _get_sessionmaker()
    async with session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise


def async_session() -> async_sessionmaker[AsyncSession]:
    """Public accessor for ARQ worker."""
    return _get_sessionmaker()


async def init_db() -> None:
    """Create all tables. Used for local dev; production uses Alembic migrations."""
    from app.platform.models.orm import Base

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    global _engine, _async_session
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        _async_session = None
