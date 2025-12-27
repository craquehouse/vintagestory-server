"""API Key authentication middleware and dependencies."""

import secrets
from functools import lru_cache
from typing import Annotated

import structlog
from fastapi import Depends, Header, HTTPException, Request

from vintagestory_api.config import Settings
from vintagestory_api.models.errors import ErrorCode

logger = structlog.get_logger()


class UserRole:
    """User role constants for API authorization."""

    ADMIN = "admin"
    MONITOR = "monitor"


@lru_cache
def get_settings() -> Settings:
    """Dependency for accessing application settings.

    Returns a cached Settings instance to avoid reloading environment
    variables on every request. FastAPI caches singleton instances automatically.
    """
    return Settings()


def get_client_ip(request: Request) -> str:
    """Extract real client IP from request, accounting for reverse proxy.

    Priority:
    1. X-Forwarded-For (comma-separated, leftmost is original client)
    2. X-Real-IP
    3. Direct connection (request.client.host)

    Args:
        request: The incoming FastAPI request

    Returns:
        The real client IP address
    """
    # X-Forwarded-For: client, proxy1, proxy2
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Leftmost IP is original client
        return forwarded_for.split(",")[0].strip()

    # X-Real-IP: single IP from some proxies
    real_ip = request.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    # Fallback to direct connection (no proxy or dev environment)
    return request.client.host if request.client else "unknown"


async def get_current_user(
    request: Request,
    x_api_key: Annotated[str | None, Header()] = None,
    settings: Settings = Depends(get_settings),
) -> str:
    """Extract and validate API key from request header.

    Uses timing-safe comparison to prevent timing attacks.

    Args:
        request: The incoming FastAPI request (for logging context)
        x_api_key: The API key from X-API-Key header
        settings: Application settings with API keys

    Returns:
        The user's role (UserRole.ADMIN or UserRole.MONITOR)

    Raises:
        HTTPException: 401 if key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "API key required"},
        )

    # Timing-safe comparison for admin key
    if secrets.compare_digest(x_api_key, settings.api_key_admin):
        return UserRole.ADMIN

    # Timing-safe comparison for monitor key (if configured)
    if settings.api_key_monitor and secrets.compare_digest(x_api_key, settings.api_key_monitor):
        return UserRole.MONITOR

    # Log failed authentication attempt (without the key value!)
    logger.warning(
        "auth_failed",
        path=str(request.url.path),
        method=request.method,
        client_host=get_client_ip(request),
    )

    raise HTTPException(
        status_code=401,
        detail={"code": ErrorCode.UNAUTHORIZED, "message": "Invalid API key"},
    )


# Type alias for dependency injection
CurrentUser = Annotated[str, Depends(get_current_user)]
