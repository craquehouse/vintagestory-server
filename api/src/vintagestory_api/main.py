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
from vintagestory_api.routers import auth, health, server, test_rbac

logger = structlog.get_logger()

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
