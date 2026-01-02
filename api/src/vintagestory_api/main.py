"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

import structlog
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from vintagestory_api.config import Settings, configure_logging
from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.routers import auth, config, console, health, mods, server, test_rbac
from vintagestory_api.services.scheduler import SchedulerService

logger = structlog.get_logger()

# Global scheduler service instance
scheduler_service: SchedulerService | None = None


def get_scheduler_service() -> SchedulerService:
    """Get the scheduler service instance.

    Returns:
        The global SchedulerService instance.

    Raises:
        RuntimeError: If called before scheduler is initialized (during startup).
    """
    if scheduler_service is None:
        raise RuntimeError("Scheduler service not initialized")
    return scheduler_service

# Static files directory (frontend build output)
STATIC_DIR = Path("/app/static")


class CORSLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log CORS requests for debugging and security monitoring."""

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        """Log CORS request details before passing to next handler.

        Logs origin, method, and path for cross-origin requests.
        """
        origin = request.headers.get("origin")
        if origin:
            logger.debug(
                "cors_request",
                origin=origin,
                method=request.method,
                path=request.url.path,
                user_agent=request.headers.get("user-agent", "unknown"),
            )

        response = await call_next(request)

        if origin:
            logger.debug(
                "cors_response",
                origin=origin,
                method=request.method,
                path=request.url.path,
                status_code=response.status_code,
                allowed_headers=response.headers.get("access-control-allow-headers", "none"),
            )

        return response


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan handler for startup and shutdown."""
    global scheduler_service

    settings = Settings()
    configure_logging(debug=settings.debug, log_level=settings.log_level)

    # Ensure data directories exist
    settings.ensure_data_directories()
    logger.info(
        "api_starting",
        debug_mode=settings.debug,
        log_level=settings.log_level or ("DEBUG" if settings.debug else "INFO"),
        data_dir=str(settings.data_dir),
    )

    # Auto-start game server if enabled in API settings
    from vintagestory_api.models.server import ServerState
    from vintagestory_api.services.api_settings import ApiSettingsService
    from vintagestory_api.services.server import get_server_service

    api_settings_service = ApiSettingsService(settings)
    api_settings = api_settings_service.get_settings()

    if api_settings.auto_start_server:
        logger.info("auto_start_server_enabled", auto_start=True)
        try:
            server_service = get_server_service()
            # Only start if server is installed and not already running
            status = server_service.get_server_status()
            if status.state == ServerState.INSTALLED:
                logger.info("auto_starting_game_server")
                await server_service.start_server()
            elif status.state == ServerState.NOT_INSTALLED:
                logger.warning("auto_start_skipped", reason="server_not_installed")
            else:
                logger.info("auto_start_skipped", reason=f"server_state_{status.state.value}")
        except Exception as e:
            logger.error("auto_start_failed", error=str(e))
    else:
        logger.debug("auto_start_server_disabled")

    # Initialize and start scheduler (after auto-start, before yield)
    scheduler_service = SchedulerService()
    scheduler_service.start()

    yield

    # Shutdown scheduler first (before other cleanup)
    if scheduler_service:
        scheduler_service.shutdown(wait=True)

    # Shutdown: close any open resources
    from vintagestory_api.services.mods import close_mod_service

    await close_mod_service()
    logger.info("api_shutting_down")


app = FastAPI(
    title="VintageStory Server Manager",
    description="API for managing VintageStory dedicated game server",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS middleware for cross-origin requests
# Origins are loaded from VS_CORS_ORIGINS environment variable (comma-separated)
# allow_credentials=True is required for X-API-Key header authentication.
# This is safe because: (1) origins are controlled via VS_CORS_ORIGINS,
# (2) we don't use cookie-based auth, and (3) API validates all requests.
settings = Settings()

# Add CORS logging middleware (runs before CORS middleware)
app.add_middleware(CORSLoggingMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
    allow_headers=["X-API-Key", "Content-Type", "Authorization"],
    max_age=600,  # Cache preflight requests for 10 minutes
)

# Health endpoints at root (NOT versioned - K8s convention)
app.include_router(health.router)

# API v1alpha1 endpoints (versioned, auth-protected)
api_v1 = APIRouter(prefix="/api/v1alpha1", dependencies=[Depends(get_current_user)])
api_v1.include_router(auth.router)
api_v1.include_router(config.router)
api_v1.include_router(console.router)
api_v1.include_router(mods.router)
api_v1.include_router(server.router)

# Test RBAC endpoints - only exposed in DEBUG mode for development/testing
if Settings().debug:
    api_v1.include_router(test_rbac.router)
    logger.warning("test_rbac_router_enabled", message="RBAC test endpoints exposed (DEBUG mode)")

app.include_router(api_v1)

# WebSocket endpoints (separate from api_v1 to avoid auth dependency issues)
# WebSocket handles its own authentication via query parameter
app.include_router(console.ws_router, prefix="/api/v1alpha1")


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
