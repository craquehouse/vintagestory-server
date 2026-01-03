"""Health check endpoints for Kubernetes probes and monitoring."""

import shutil

from fastapi import APIRouter

from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.models.responses import (
    ApiResponse,
    DiskSpaceData,
    GameServerStatus,
    HealthData,
    ReadinessData,
    SchedulerHealthData,
)
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.mods import get_restart_state
from vintagestory_api.services.server import get_server_service

router = APIRouter(tags=["Health"])

BYTES_PER_GB = 1024 * 1024 * 1024


def get_disk_space_data() -> DiskSpaceData | None:
    """Get disk space information for the data volume.

    Returns:
        DiskSpaceData with disk usage stats, or None if unavailable.
    """
    try:
        settings = get_settings()
        usage = shutil.disk_usage(settings.data_dir)

        total_gb = round(usage.total / BYTES_PER_GB, 2)
        used_gb = round(usage.used / BYTES_PER_GB, 2)
        available_gb = round(usage.free / BYTES_PER_GB, 2)
        usage_percent = round((usage.used / usage.total) * 100, 1)
        warning = available_gb < settings.disk_space_warning_threshold_gb

        return DiskSpaceData(
            total_gb=total_gb,
            used_gb=used_gb,
            available_gb=available_gb,
            usage_percent=usage_percent,
            warning=warning,
        )
    except Exception:
        return None


def get_scheduler():
    """Get scheduler service with deferred import.

    Deferred import to avoid circular import with main.py.

    Returns:
        SchedulerService instance from main module.
    """
    from vintagestory_api.main import get_scheduler_service

    return get_scheduler_service()


@router.get("/healthz", response_model=ApiResponse)
async def health_check() -> ApiResponse:
    """Liveness probe - is the API process alive?

    Returns API health status and game server status.
    No authentication required (per K8s convention).

    Returns:
        ApiResponse with health data including API and game server status.
    """
    server_service = get_server_service()
    server_status = server_service.get_server_status()

    # Map ServerState to GameServerStatus
    state_to_status = {
        ServerState.NOT_INSTALLED: GameServerStatus.NOT_INSTALLED,
        ServerState.INSTALLED: GameServerStatus.STOPPED,
        ServerState.INSTALLING: GameServerStatus.STOPPED,
        ServerState.STARTING: GameServerStatus.STARTING,
        ServerState.RUNNING: GameServerStatus.RUNNING,
        ServerState.STOPPING: GameServerStatus.STOPPING,
        ServerState.ERROR: GameServerStatus.STOPPED,
    }
    game_server_status = state_to_status.get(
        server_status.state, GameServerStatus.NOT_INSTALLED
    )

    # Get pending restart state - don't fail health checks if this errors
    try:
        restart_state = get_restart_state()
        pending_restart = restart_state.pending_restart
    except Exception:
        pending_restart = False

    # Get scheduler status - don't fail health checks if this errors
    try:
        scheduler = get_scheduler()
        scheduler_data = SchedulerHealthData(
            status="running" if scheduler.is_running else "stopped",
            job_count=len(scheduler.get_jobs()),
        )
    except RuntimeError:
        # Scheduler not initialized
        scheduler_data = SchedulerHealthData(status="stopped", job_count=0)
    except Exception:
        # Unexpected error - default to stopped
        scheduler_data = SchedulerHealthData(status="stopped", job_count=0)

    # Get disk space data - don't fail health checks if this errors
    disk_space_data = get_disk_space_data()

    return ApiResponse(
        status="ok",
        data=HealthData(
            api="healthy",
            game_server=game_server_status,
            game_server_version=server_status.version,
            game_server_uptime=server_status.uptime_seconds,
            game_server_pending_restart=pending_restart,
            scheduler=scheduler_data,
            disk_space=disk_space_data,
        ).model_dump(),
    )


@router.get("/readyz", response_model=ApiResponse)
async def readiness_check() -> ApiResponse:
    """Readiness probe - is the API ready to serve traffic?

    Returns True when all required services are initialized.
    No authentication required (per K8s convention).

    The game_server check reports whether the game server process is running.
    This is informational only - API readiness is not dependent on game server state.

    Returns:
        ApiResponse with readiness data.
    """
    server_service = get_server_service()
    server_status = server_service.get_server_status()

    # Game server is considered "ready" when it is running
    game_server_ready = server_status.state == ServerState.RUNNING

    return ApiResponse(
        status="ok",
        data=ReadinessData(
            ready=True,
            checks={
                "api": True,
                "game_server": game_server_ready,
            },
        ).model_dump(),
    )
