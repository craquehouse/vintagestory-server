"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from vintagestory_api.config import Settings, configure_logging
from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.routers import auth, health, server, test_rbac

logger = structlog.get_logger()

# Static files directory (frontend build output)
STATIC_DIR = Path("/app/static")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    settings = Settings()
    configure_logging(debug=settings.debug)

    # Ensure data directories exist
    settings.ensure_data_directories()
    logger.info(
        "api_starting",
        debug_mode=settings.debug,
        data_dir=str(settings.data_dir),
    )
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

# API v1alpha1 endpoints (versioned, auth-protected)
api_v1 = APIRouter(prefix="/api/v1alpha1", dependencies=[Depends(get_current_user)])
api_v1.include_router(auth.router)
api_v1.include_router(server.router)

# Test RBAC endpoints - only exposed in DEBUG mode for development/testing
if Settings().debug:
    api_v1.include_router(test_rbac.router)
    logger.warning("test_rbac_router_enabled", message="RBAC test endpoints exposed (DEBUG mode)")

app.include_router(api_v1)


# Static file serving for frontend SPA
# Mount assets directory for JS, CSS, and other static files
if STATIC_DIR.exists():
    assets_dir = STATIC_DIR / "assets"
    if assets_dir.exists():
        app.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # SPA fallback - serve index.html for all non-API, non-health routes
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve static files or fall back to index.html for client-side routing."""
        # Check if it's a static file that exists
        file_path = STATIC_DIR / full_path
        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)
        # Otherwise serve index.html for client-side routing
        return FileResponse(STATIC_DIR / "index.html")
