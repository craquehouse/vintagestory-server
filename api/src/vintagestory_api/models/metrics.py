"""Metrics-related models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic import BaseModel, Field


@dataclass(frozen=True)
class MetricsSnapshot:
    """Immutable metrics sample point.

    Represents a single point-in-time measurement of server metrics.
    The dataclass is frozen (immutable) to ensure thread-safety when
    stored in the ring buffer and read by multiple consumers.
    """

    timestamp: datetime
    # API server metrics (always available)
    api_memory_mb: float
    api_cpu_percent: float
    # Game server metrics (None if game server is not running)
    game_memory_mb: float | None
    game_cpu_percent: float | None


class MetricsSnapshotResponse(BaseModel):
    """Single metrics snapshot for API response.

    Converts internal MetricsSnapshot dataclass to camelCase JSON format
    for frontend consumption.
    """

    timestamp: datetime
    api_memory_mb: float = Field(serialization_alias="apiMemoryMb")
    api_cpu_percent: float = Field(serialization_alias="apiCpuPercent")
    game_memory_mb: float | None = Field(serialization_alias="gameMemoryMb")
    game_cpu_percent: float | None = Field(serialization_alias="gameCpuPercent")

    model_config = {"populate_by_name": True}

    @classmethod
    def from_snapshot(cls, snapshot: MetricsSnapshot) -> MetricsSnapshotResponse:
        """Create response model from internal MetricsSnapshot.

        Args:
            snapshot: Internal metrics snapshot dataclass.

        Returns:
            Pydantic model for API response.
        """
        return cls(
            timestamp=snapshot.timestamp,
            api_memory_mb=snapshot.api_memory_mb,
            api_cpu_percent=snapshot.api_cpu_percent,
            game_memory_mb=snapshot.game_memory_mb,
            game_cpu_percent=snapshot.game_cpu_percent,
        )


class MetricsHistoryResponse(BaseModel):
    """Historical metrics response.

    Contains a list of metrics snapshots and total count for pagination awareness.
    """

    metrics: list[MetricsSnapshotResponse]
    count: int
