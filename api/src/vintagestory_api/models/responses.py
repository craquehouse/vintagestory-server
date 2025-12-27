"""API response models and envelopes."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel

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


class ReadinessData(BaseModel):
    """Readiness check response data."""

    ready: bool = False
    checks: dict[str, bool] = {}
