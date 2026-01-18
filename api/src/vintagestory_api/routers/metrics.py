"""Metrics API endpoints.

Story 12.3: Metrics API Endpoints

Provides endpoints for retrieving current and historical server metrics.
Metrics are Admin-only (AC: 4) as they contain operational data.
"""

from datetime import UTC, datetime, timedelta

import structlog
from fastapi import APIRouter, Query

from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.metrics import (
    MetricsHistoryResponse,
    MetricsSnapshot,
    MetricsSnapshotResponse,
)
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.services.metrics import get_metrics_service

logger = structlog.get_logger()

router = APIRouter(prefix="/metrics", tags=["Metrics"])


def _filter_by_minutes(
    snapshots: list[MetricsSnapshot], minutes: int
) -> list[MetricsSnapshot]:
    """Filter snapshots to only those within the last N minutes.

    Args:
        snapshots: List of metrics snapshots (oldest first).
        minutes: Number of minutes to look back.

    Returns:
        Filtered list of snapshots within the time range.
    """
    cutoff = datetime.now(UTC) - timedelta(minutes=minutes)
    return [s for s in snapshots if s.timestamp >= cutoff]


@router.get(
    "/current",
    response_model=ApiResponse,
    summary="Get current metrics",
    description="Returns the most recent metrics snapshot. "
    "Returns null for data if no metrics have been collected yet.",
)
async def get_current_metrics(
    _role: RequireAdmin,
) -> ApiResponse:
    """Get the current (most recent) metrics snapshot.

    Requires Admin role (AC: 4).

    Returns:
        ApiResponse with latest MetricsSnapshotResponse or null if buffer empty (AC: 5).
    """
    metrics_service = get_metrics_service()
    latest = metrics_service.buffer.get_latest()

    if latest is None:
        # AC: 5 - Return null when no metrics collected yet
        logger.debug("metrics_current_empty")
        return ApiResponse(status="ok", data=None)

    response = MetricsSnapshotResponse.from_snapshot(latest)
    logger.debug(
        "metrics_current_returned",
        timestamp=latest.timestamp.isoformat(),
    )

    return ApiResponse(status="ok", data=response.model_dump(mode="json", by_alias=True))


@router.get(
    "/history",
    response_model=ApiResponse,
    summary="Get metrics history",
    description="Returns historical metrics snapshots. "
    "Optionally filter by time range using the 'minutes' parameter.",
)
async def get_metrics_history(
    _role: RequireAdmin,
    minutes: int | None = Query(
        None,
        ge=1,
        le=1440,  # Max 24 hours
        description="Filter to metrics from the last N minutes (1-1440)",
    ),
) -> ApiResponse:
    """Get historical metrics with optional time filtering.

    Requires Admin role (AC: 4).

    Args:
        minutes: Optional time filter in minutes. If not specified, returns all
            available metrics up to buffer capacity (360 samples = 1 hour at 10s intervals).

    Returns:
        ApiResponse with MetricsHistoryResponse containing metrics list and count.
        Returns empty list if no metrics collected yet (AC: 5).
    """
    metrics_service = get_metrics_service()
    all_snapshots = metrics_service.buffer.get_all()

    # Filter by time if minutes specified (AC: 3)
    if minutes is not None:
        snapshots = _filter_by_minutes(all_snapshots, minutes)
        logger.debug(
            "metrics_history_filtered",
            total_available=len(all_snapshots),
            filtered_count=len(snapshots),
            minutes=minutes,
        )
    else:
        snapshots = all_snapshots
        logger.debug(
            "metrics_history_returned",
            count=len(snapshots),
        )

    # Convert to response models
    metrics = [MetricsSnapshotResponse.from_snapshot(s) for s in snapshots]
    response = MetricsHistoryResponse(metrics=metrics, count=len(metrics))

    return ApiResponse(status="ok", data=response.model_dump(mode="json", by_alias=True))
