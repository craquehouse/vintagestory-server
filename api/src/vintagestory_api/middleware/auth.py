"""API Key authentication middleware and dependencies."""

import secrets
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


# Cached settings instance
_settings: Settings | None = None


def get_settings() -> Settings:
    """Dependency for accessing application settings.

    Returns a cached Settings instance to avoid reloading environment
    variables on every request.
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


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
    if x_api_key is None:
        raise HTTPException(
            status_code=401,
            detail={"code": ErrorCode.UNAUTHORIZED, "message": "API key required"},
        )

    # Timing-safe comparison for admin key
    if secrets.compare_digest(x_api_key, settings.api_key_admin):
        return UserRole.ADMIN

    # Timing-safe comparison for monitor key (if configured)
    if settings.api_key_monitor and secrets.compare_digest(
        x_api_key, settings.api_key_monitor
    ):
        return UserRole.MONITOR

    # Log failed authentication attempt (without the key value!)
    logger.warning(
        "auth_failed",
        path=str(request.url.path),
        method=request.method,
    )

    raise HTTPException(
        status_code=401,
        detail={"code": ErrorCode.UNAUTHORIZED, "message": "Invalid API key"},
    )


# Type alias for dependency injection
CurrentUser = Annotated[str, Depends(get_current_user)]
