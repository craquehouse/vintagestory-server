"""Server installation and lifecycle API endpoints."""

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.models.server import InstallRequest, ServerState
from vintagestory_api.services.server import ServerService

router = APIRouter(prefix="/server", tags=["Server"])

# Module-level service instance (singleton pattern for state tracking)
_server_service: ServerService | None = None


def get_server_service() -> ServerService:
    """Get or create the server service singleton."""
    global _server_service
    if _server_service is None:
        _server_service = ServerService()
    return _server_service


@router.post("/install", response_model=ApiResponse)
async def install_server(
    request: InstallRequest,
    background_tasks: BackgroundTasks,
    _: RequireAdmin,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Install VintageStory server with specified version.

    Downloads, extracts, and configures the server. This is a long-running
    operation that runs in the background. Use GET /install/status to
    poll for progress.

    Args:
        request: Installation request with version number

    Returns:
        ApiResponse with initial installation status

    Raises:
        HTTPException: 422 if version format is invalid
        HTTPException: 409 if server is already installed or installation in progress
        HTTPException: 404 if version not found
    """
    version = request.version

    # Validate version format (422 per AC4)
    if not service.validate_version(version):
        raise HTTPException(
            status_code=422,
            detail={
                "code": ErrorCode.INVALID_VERSION,
                "message": f"Version must be in format X.Y.Z or X.Y.Z-pre.N, got: {version}",
            },
        )

    # Check if already installed
    if service.is_installed():
        installed_version = service.get_installed_version()
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.SERVER_ALREADY_INSTALLED,
                "message": f"Server version {installed_version} is already installed",
            },
        )

    # Check if installation already in progress
    progress = service.get_install_progress()
    if progress.state == ServerState.INSTALLING:
        raise HTTPException(
            status_code=409,
            detail={
                "code": ErrorCode.INSTALLATION_IN_PROGRESS,
                "message": "Server installation is already in progress",
            },
        )

    # Check version availability before starting background task
    available, _channel = await service.check_version_available(version)
    if not available:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.VERSION_NOT_FOUND,
                "message": f"Version {version} not found in stable or unstable channels",
            },
        )

    # Start installation in background
    background_tasks.add_task(service.install_server, version)

    # Return initial progress
    return ApiResponse(
        status="ok",
        data={
            "state": ServerState.INSTALLING.value,
            "stage": "downloading",
            "version": version,
            "message": f"Starting installation of version {version}",
        },
    )


@router.get("/install/status", response_model=ApiResponse)
async def get_install_status(
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Get current server installation status.

    Returns progress information during installation or final state.
    Can be polled by clients to track installation progress.

    Returns:
        ApiResponse with InstallProgress data
    """
    progress = service.get_install_progress()

    return ApiResponse(
        status="ok",
        data={
            "state": progress.state.value,
            "stage": progress.stage.value if progress.stage else None,
            "percentage": progress.percentage,
            "version": progress.version,
            "error": progress.error,
            "error_code": progress.error_code,
            "message": progress.message,
        },
    )
