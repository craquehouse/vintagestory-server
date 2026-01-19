"""API response models and envelopes."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_serializer

__all__ = [
    "ApiResponse",
    "DiskSpaceData",
    "GameServerStatus",
    "HealthData",
    "ReadinessData",
    "SchedulerHealthData",
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

    Uses a custom serializer to exclude None values, ensuring success responses
    don't include "error": null in the JSON output.
    """

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "error"]
    data: dict[str, Any] | None = None
    error: dict[str, Any] | None = None

    @model_serializer(mode="wrap")
    def serialize_exclude_none_error(
        self, handler: Any, info: Any
    ) -> dict[str, Any]:
        """Custom serializer that excludes null error field from success responses.

        The 'data' field can legitimately be null (e.g., no metrics available),
        but 'error' being null in success responses is just noise.
        """
        result = handler(self)
        # Only exclude 'error' when it's None (success responses)
        if result.get("error") is None:
            result.pop("error", None)
        return result


class SchedulerHealthData(BaseModel):
    """Scheduler health check data."""

    status: Literal["running", "stopped"] = Field(
        description="Current scheduler status"
    )
    job_count: int = Field(
        default=0,
        description="Number of registered scheduled jobs",
    )


class DiskSpaceData(BaseModel):
    """Disk space information for data volume."""

    total_gb: float = Field(
        description="Total disk space in gigabytes",
    )
    used_gb: float = Field(
        description="Used disk space in gigabytes",
    )
    available_gb: float = Field(
        description="Available disk space in gigabytes",
    )
    usage_percent: float = Field(
        description="Percentage of disk space used (0-100)",
    )
    warning: bool = Field(
        default=False,
        description="True if available space is below the configured warning threshold",
    )


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
    scheduler: SchedulerHealthData | None = Field(
        default=None,
        description="Scheduler service status. None if scheduler not available.",
    )
    disk_space: DiskSpaceData | None = Field(
        default=None,
        description="Data volume disk space information. None if unavailable.",
    )


class ReadinessData(BaseModel):
    """Readiness check response data."""

    ready: bool = False
    checks: dict[str, bool] = {}
