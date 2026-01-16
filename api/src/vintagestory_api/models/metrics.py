"""Metrics-related models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


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
