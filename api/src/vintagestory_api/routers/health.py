"""Health check endpoints for Kubernetes probes and monitoring."""

from fastapi import APIRouter

from vintagestory_api.models.responses import (
    ApiResponse,
    GameServerStatus,
    HealthData,
    ReadinessData,
)
from vintagestory_api.models.server import ServerState
from vintagestory_api.services.mods import get_restart_state
from vintagestory_api.services.server import get_server_service

router = APIRouter(tags=["Health"])


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

    return ApiResponse(
        status="ok",
        data=HealthData(
            api="healthy",
            game_server=game_server_status,
            game_server_version=server_status.version,
            game_server_uptime=server_status.uptime_seconds,
            game_server_pending_restart=pending_restart,
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
