"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI

from vintagestory_api.config import Settings, configure_logging
from vintagestory_api.routers import health

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    settings = Settings()
    configure_logging(debug=settings.debug)
    logger.info("api_starting", debug_mode=settings.debug)
    yield
    logger.info("api_shutting_down")


app = FastAPI(
    title="VintageStory Server Manager",
    description="API for managing VintageStory dedicated game server",
    version="0.1.0",
    lifespan=lifespan,
)

# Health endpoints at root (NOT versioned - K8s convention)
app.include_router(health.router)


# API v1alpha1 endpoints will be added here in future stories
# from fastapi import APIRouter
# api_v1 = APIRouter(prefix="/api/v1alpha1")
# api_v1.include_router(server.router, prefix="/server", tags=["Server"])
# app.include_router(api_v1)
