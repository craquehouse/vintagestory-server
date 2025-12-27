"""Health check endpoints for Kubernetes probes and monitoring."""

from fastapi import APIRouter

from vintagestory_api.models.responses import (
    ApiResponse,
    GameServerStatus,
    HealthData,
    ReadinessData,
)

router = APIRouter(tags=["Health"])


@router.get("/healthz", response_model=ApiResponse)
async def health_check() -> ApiResponse:
    """Liveness probe - is the API process alive?

    Returns API health status and game server status.
    No authentication required (per K8s convention).

    Returns:
        ApiResponse with health data including API and game server status.
    """
    # TODO: Replace with actual game server status check in Epic 3
    return ApiResponse(
        status="ok",
        data=HealthData(
            api="healthy",
            game_server=GameServerStatus.NOT_INSTALLED,
        ).model_dump(),
    )


@router.get("/readyz", response_model=ApiResponse)
async def readiness_check() -> ApiResponse:
    """Readiness probe - is the API ready to serve traffic?

    Returns True when all required services are initialized.
    No authentication required (per K8s convention).

    Returns:
        ApiResponse with readiness data.
    """
    # Explicitly set ready=True after confirming API is operational
    return ApiResponse(
        status="ok",
        data=ReadinessData(
            ready=True,
            checks={"api": True},
        ).model_dump(),
    )
