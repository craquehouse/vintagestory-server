"""API response models and envelopes."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field

__all__ = [
    "ApiResponse",
    "GameServerStatus",
    "HealthData",
    "ReadinessData",
]


class GameServerStatus(str, Enum):
    """Possible states of the game server process."""

    NOT_INSTALLED = "not_installed"
    STOPPED = "stopped"
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"


class ApiResponse(BaseModel):
    """Standard API response envelope.

    All API responses follow this format for consistency:
    - Success: {"status": "ok", "data": {...}}
    - Error: {"status": "error", "error": {...}}
    """

    status: Literal["ok", "error"]
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None


class HealthData(BaseModel):
    """Health check response data."""

    api: str = "healthy"
    game_server: GameServerStatus
    game_server_version: str | None = Field(
        default=None,
        description="Installed game server version (e.g., '1.19.8'). None if not installed.",
    )
    game_server_uptime: int | None = Field(
        default=None,
        description="Game server uptime in seconds. None if server is not running.",
    )
    game_server_pending_restart: bool = Field(
        default=False,
        description="Whether the game server needs to be restarted for changes to take effect.",
    )


class ReadinessData(BaseModel):
    """Readiness check response data."""

    ready: bool = False
    checks: dict[str, bool] = {}
