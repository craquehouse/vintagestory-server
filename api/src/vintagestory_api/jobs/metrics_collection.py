"""Metrics collection job.

Story 12.2: Metrics Collection Service

This job periodically collects server metrics (memory, CPU) from both the
API server and game server processes. Metrics are stored in a ring buffer
for later retrieval via API.

AC 1: Collects timestamp, api_memory_mb, api_cpu_percent
AC 5: Runs at configured interval (default 10 seconds)
"""

from __future__ import annotations

import structlog

from vintagestory_api.jobs.base import safe_job
from vintagestory_api.services.metrics import get_metrics_service

logger = structlog.get_logger()


@safe_job("metrics_collection")
async def collect_metrics() -> None:
    """Collect current server metrics and store in buffer.

    This job:
    1. Gets the MetricsService singleton
    2. Calls collect() to gather API and game server metrics
    3. Metrics are automatically stored in the ring buffer

    The job uses psutil to gather process-level metrics. If the game
    server is not running, game metrics are recorded as None (graceful
    degradation, AC: 3).

    Returns:
        None. Metrics are stored in the service's ring buffer.

    Note:
        This job is intentionally simple - all complexity is encapsulated
        in MetricsService.collect(). The job just invokes collection at
        the configured interval.
    """
    metrics_service = get_metrics_service()
    snapshot = metrics_service.collect()

    logger.debug(
        "metrics_collection_snapshot",
        api_memory_mb=round(snapshot.api_memory_mb, 2),
        api_cpu_percent=round(snapshot.api_cpu_percent, 2),
        game_memory_mb=round(snapshot.game_memory_mb, 2)
        if snapshot.game_memory_mb
        else None,
        game_cpu_percent=round(snapshot.game_cpu_percent, 2)
        if snapshot.game_cpu_percent
        else None,
        buffer_size=len(metrics_service.buffer),
    )
