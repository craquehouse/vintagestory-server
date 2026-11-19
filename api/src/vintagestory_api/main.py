"""FastAPI application entry point."""

import json
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

import structlog
from fastapi import APIRouter, Depends, FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint

from vintagestory_api import __version__
from vintagestory_api.config import (
    DEFAULT_MOD_DB_URL,
    Settings,
    current_log_level,
    initialize_debug_state,
    is_debug_enabled,
)
from vintagestory_api.middleware.auth import get_current_user, get_settings
from vintagestory_api.middleware.request_context import RequestContextMiddleware
from vintagestory_api.routers import (
    auth,
    config,
    console,
    debug,
    health,
    jobs,
    metrics,
    mods,
    prometheus,
    server,
    test_rbac,
    versions,
    ws_token,
)
from vintagestory_api.services.mods import prepare_mod_files
from vintagestory_api.services.scheduler import SchedulerService
from vintagestory_api.services.server import reapply_pending_config_edits_at_api_start

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


def log_web_api_key_state(settings: Settings) -> None:
    """Warn at start-up when the web UI's key is missing, the Admin key or has no role.

    Never logs the key itself (Epic 19 ADR-5).
    """
    state = settings.web_api_key_state()
    if state == "not_set":
        logger.warning(
            "web_api_key_not_set",
            hint=(
                "/config.js serves no API key, so the web UI shows a set-up message. "
                "Set VS_API_KEY to VS_API_KEY_MONITOR (read-only) or VS_API_KEY_ADMIN "
                "(full access); anyone who can load the web UI receives that key"
            ),
        )
    elif state == "admin":
        logger.warning(
            "web_api_key_is_admin_key",
            hint=(
                "Anyone who can load the web UI receives the Admin key. Set VS_API_KEY to "
                "VS_API_KEY_MONITOR for a read-only web UI, or put the web UI behind an "
                "authenticating proxy"
            ),
        )
    elif state == "no_role":
        # The web UI would get 401 on every request
        logger.warning(
            "web_api_key_matches_no_role",
            hint="VS_API_KEY must equal VS_API_KEY_ADMIN or VS_API_KEY_MONITOR",
        )


def log_mod_db_url(settings: Settings) -> None:
    """Warn at start-up when VS_MOD_DB_URL points somewhere other than the default.

    Logs the scheme and the host only, never the whole address (Epic 20 ADR-9).
    """
    if settings.mod_db_url == DEFAULT_MOD_DB_URL:
        return
    parts = urlsplit(settings.mod_db_url)
    logger.warning(
        "mod_db_url_overridden",
        scheme=parts.scheme,
        host=parts.hostname,
        hint=(
            "VS_MOD_DB_URL is set: mod database requests and mod downloads go to this "
            "address instead of https://mods.vintagestory.at"
        ),
    )


def lifespan_for(settings: Settings) -> Callable[[FastAPI], AbstractAsyncContextManager[None]]:
    """Return the lifespan handler of an app that runs with the given settings."""

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
        """Application lifespan handler for startup and shutdown."""
        global scheduler_service

        # Apply VS_DEBUG and VS_LOG_LEVEL from the settings (FR48, Epic 21 ADR-4)
        # This must be called before any logging to ensure correct log levels
        initialize_debug_state(settings.debug, settings.log_level)

        # Ensure data directories exist
        settings.ensure_data_directories()
        log_web_api_key_state(settings)
        log_mod_db_url(settings)
        debug_enabled = is_debug_enabled()
        logger.info(
            "api_starting",
            debug_mode=debug_enabled,
            log_level=current_log_level(),
            data_dir=str(settings.data_dir),
        )

        # Recover the mods directory before any mod operation can run: after the data
        # directories exist, before the game server auto-start and the scheduler (ADR-9)
        # Any failure is logged and start-up continues (ADR-9): the API must still start
        try:
            prepare_mod_files()
        except Exception as e:
            logger.error("mod_files_startup_failed", error_type=type(e).__name__, error=str(e))

        # Put restart-required settings saved while the game ran back into serverconfig.json
        # before the auto-start (Story 22.7, Epic 22 ADR-15 decision 3); the API always starts
        try:
            reapply_pending_config_edits_at_api_start()
        except Exception as e:
            logger.error("pending_config_edits_startup_failed", error_type=type(e).__name__)

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

        # Register default periodic jobs (Story 8.0)
        from vintagestory_api.jobs import register_default_jobs

        register_default_jobs(scheduler_service)

        yield

        # Shutdown scheduler first (before other cleanup)
        if scheduler_service:
            scheduler_service.shutdown(wait=True)

        # Shutdown: close any open resources
        from vintagestory_api.services.mods import close_mod_service

        await close_mod_service()
        logger.info("api_shutting_down")

    return lifespan


# The web UI's Content-Security-Policy (Epic 19 ADR-6 decision 3). The API tests compare
# the whole string; do not loosen a directive without the maintainer
CONTENT_SECURITY_POLICY = "; ".join(
    (
        "default-src 'self'",
        "script-src 'self'",
        "style-src 'self' 'unsafe-inline'",
        "img-src 'self' data: https:",
        "font-src 'self'",
        "connect-src 'self'",
        "frame-src 'none'",
        "object-src 'none'",
        "base-uri 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
    )
)


def frontend_security_headers(csp_mode: str) -> dict[str, str]:
    """Return the security headers of a web UI page for a validated VS_CSP_MODE.

    X-Frame-Options follows the policy, so report-only and off also allow framing.
    """
    headers = {"X-Content-Type-Options": "nosniff", "Referrer-Policy": "no-referrer"}
    if csp_mode == "enforce":
        return {
            "Content-Security-Policy": CONTENT_SECURITY_POLICY,
            "X-Frame-Options": "DENY",
            **headers,
        }
    if csp_mode == "report-only":
        return {"Content-Security-Policy-Report-Only": CONTENT_SECURITY_POLICY, **headers}
    return headers


def runtime_config_script(api_key: str) -> str:
    """Return the /config.js body: the key JSON-encoded, with <, > and & escaped.

    The escapes keep the body from ever closing a script element (Story 19.2 review L-1).
    """
    config = (
        json.dumps({"apiKey": api_key})
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("&", "\\u0026")
    )
    return f"window.__VSM_CONFIG__ = {config};\n"


def _resolve_frontend_file(static_root: Path, requested: str) -> Path:
    """Return the file to serve for a request path, or index.html for client-side routing.

    The request path is untrusted and may be absolute or contain traversal segments, so a
    file is served only if its real path is inside static_root.
    """
    index = static_root / "index.html"
    try:
        candidate = (static_root / requested).resolve()
    except ValueError:  # For example, an embedded null byte
        return index
    if candidate.is_relative_to(static_root) and candidate.is_file():
        return candidate
    return index


def register_frontend(target: FastAPI, static_dir: Path, settings: Settings) -> None:
    """Serve the built frontend from static_dir on the given app, with the given settings.

    The web UI's pages and files carry the security headers of settings.csp_mode;
    /assets and /config.js do not.
    """
    static_root = static_dir.resolve()

    # Mount assets directory for JS, CSS, and other static files
    assets_dir = static_dir / "assets"
    if assets_dir.exists():
        target.mount("/assets", StaticFiles(directory=assets_dir), name="assets")

    # Runtime web configuration (Epic 15 ADR-5), registered before the SPA fallback so it
    # wins over the placeholder config.js in the build. Unauthenticated by design: the
    # page needs the key before it can authenticate. Never cached, never logged. A classic
    # <script> load skips CORS, so Cross-Origin-Resource-Policy stops other sites'
    # pages from including it and reading the key.
    @target.get("/config.js", include_in_schema=False)
    async def serve_runtime_config() -> Response:
        """Serve the web UI's runtime configuration as a classic script."""
        return Response(
            content=runtime_config_script(settings.web_api_key),
            media_type="application/javascript",
            headers={
                "Cache-Control": "no-store",
                "Cross-Origin-Resource-Policy": "same-origin",
                "X-Content-Type-Options": "nosniff",
            },
        )

    security_headers = frontend_security_headers(settings.csp_mode)

    # SPA fallback - serve index.html for all non-API, non-health routes, with the
    # Content-Security-Policy and the other security headers (Epic 19 ADR-6)
    @target.get("/{full_path:path}")
    async def serve_spa(full_path: str) -> FileResponse:
        """Serve static files or fall back to index.html for client-side routing."""
        return FileResponse(
            _resolve_frontend_file(static_root, full_path), headers=security_headers
        )


def create_app(settings: Settings, static_dir: Path = STATIC_DIR) -> FastAPI:
    """Build the application for the given settings."""
    app = FastAPI(
        title="VintageStory Server Manager",
        description="API for managing VintageStory dedicated game server",
        version=__version__,
        lifespan=lifespan_for(settings),
        # The API documentation and schema only in debug mode (Epic 19 ADR-7). Without
        # them, these paths reach the web UI's page in the image, and 404 otherwise
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url="/openapi.json" if settings.debug else None,
    )

    # Configure CORS middleware for cross-origin requests
    # Origins come from the settings' VS_CORS_ORIGINS (comma-separated)
    # allow_credentials=True is required for X-API-Key header authentication.
    # This is safe because: (1) origins are controlled via VS_CORS_ORIGINS,
    # (2) we don't use cookie-based auth, and (3) API validates all requests.

    # Middleware registration order note:
    # FastAPI/Starlette processes middleware in reverse registration order.
    # Registered last = runs first. So our order is:
    # 1. CORSMiddleware (registered first, runs last for outgoing)
    # 2. CORSLoggingMiddleware (logs CORS requests)
    # 3. RequestContextMiddleware (registered last, runs FIRST to set up request_id)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins.split(","),
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type", "Authorization"],
        max_age=600,  # Cache preflight requests for 10 minutes
    )

    # Add CORS logging middleware
    app.add_middleware(CORSLoggingMiddleware)

    # Request context middleware runs FIRST (registered last due to reverse order)
    # Sets up request_id for all log entries within the request
    app.add_middleware(RequestContextMiddleware)

    # Health endpoints at root (NOT versioned - K8s convention), and /metrics for
    # Prometheus beside them, open like /healthz (Epic 22 ADR-3)
    app.include_router(health.router)
    app.include_router(prometheus.router)

    # API v1alpha1 endpoints (versioned, auth-protected)
    api_v1 = APIRouter(prefix="/api/v1alpha1", dependencies=[Depends(get_current_user)])
    api_v1.include_router(auth.router)
    api_v1.include_router(config.router)
    api_v1.include_router(console.router)
    api_v1.include_router(debug.router)
    api_v1.include_router(jobs.router)
    api_v1.include_router(metrics.router)
    api_v1.include_router(mods.router)
    api_v1.include_router(server.router)
    api_v1.include_router(versions.router)
    api_v1.include_router(ws_token.router)

    # Test RBAC endpoints - only exposed in DEBUG mode for development/testing
    if settings.debug:
        api_v1.include_router(test_rbac.router)
        logger.warning(
            "test_rbac_router_enabled", message="RBAC test endpoints exposed (DEBUG mode)"
        )

    app.include_router(api_v1)

    # WebSocket endpoints (separate from api_v1 to avoid auth dependency issues)
    # WebSocket handles its own authentication via query parameter
    app.include_router(console.ws_router, prefix="/api/v1alpha1")

    # Static file serving for frontend SPA
    if static_dir.exists():
        register_frontend(app, static_dir, settings)

    return app


app = create_app(get_settings())
