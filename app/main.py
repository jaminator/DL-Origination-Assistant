"""FastAPI application factory."""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.platform.persistence.database import close_db, init_db
from app.platform.utils.logging import setup_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan — startup and shutdown."""
    setup_logging()
    await init_db()
    yield
    await close_db()


def create_app() -> FastAPI:
    """Create and configure the FastAPI application."""
    application = FastAPI(
        title="DL Origination Assistant",
        description="Direct-lending origination target mining platform",
        version="0.1.0",
        lifespan=lifespan,
    )

    # CORS — permissive for local dev; restrict for production
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    from app.platform.api.connectors import router as connectors_router
    from app.platform.api.exports import router as exports_router
    from app.platform.api.health import router as health_router
    from app.platform.api.miner_routes import router as miner_router
    from app.platform.api.recommender_routes import router as recommender_router
    from app.platform.api.runs import router as runs_router

    application.include_router(health_router, prefix="/api/v1")
    application.include_router(runs_router, prefix="/api/v1")
    application.include_router(recommender_router, prefix="/api/v1")
    application.include_router(miner_router, prefix="/api/v1")
    application.include_router(exports_router, prefix="/api/v1")
    application.include_router(connectors_router, prefix="/api/v1")

    return application


app = create_app()
