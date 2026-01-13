"""Server installation and lifecycle API endpoints."""

import structlog
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.models.server import (
    InstallRequest,
    ServerState,
)
from vintagestory_api.services.server import ServerService, get_server_service

logger = structlog.get_logger()

router = APIRouter(prefix="/server", tags=["Server"])


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
        request: Installation request with version number. Can be a specific
            version (e.g., "1.21.3") or an alias ("stable" or "unstable") to
            install the latest version from that channel. Set force=true to
            reinstall, upgrade, or downgrade an existing installation.

    Returns:
        ApiResponse with initial installation status

    Raises:
        HTTPException: 422 if version format is invalid
        HTTPException: 409 if already installed (without force) or install in progress
        HTTPException: 404 if version not found
    """
    version = request.version

    # Handle version aliases (e.g., "stable", "unstable")
    if service.is_version_alias(version):
        resolved = await service.resolve_version_alias(version)
        if resolved is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": ErrorCode.VERSION_NOT_FOUND,
                    "message": f"Could not find latest version for channel: {version}",
                },
            )
        version = resolved

    # Validate version format (422 per AC4)
    if not service.validate_version(version):
        raise HTTPException(
            status_code=422,
            detail={
                "code": ErrorCode.INVALID_VERSION,
                "message": f"Version must be in format X.Y.Z or X.Y.Z-pre.N, got: {version}",
            },
        )

    if service.is_installed() and not request.force:
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

    logger.debug("router_install_server_start", version=version, force=request.force)
    background_tasks.add_task(service.install_server, version, force=request.force)

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
    logger.debug("router_install_status_start")
    progress = service.get_install_progress()
    logger.debug("router_install_status_complete", state=progress.state.value)

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


@router.get("/status", response_model=ApiResponse)
async def get_server_status(
    _: str = Depends(get_current_user),  # Both Admin and Monitor
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Get current server status.

    Returns server state, version, uptime (if running), and last exit code.
    Available to both Admin and Monitor roles.

    Note: This endpoint does not acquire the lifecycle lock, intentionally.
    During state transitions, it may return the transitional state (starting/
    stopping). This is acceptable for monitoring purposes and avoids blocking
    status checks during slow lifecycle operations.

    Returns:
        ApiResponse with ServerStatus data
    """
    logger.debug("router_server_status_start")
    status = service.get_server_status()
    logger.debug("router_server_status_complete", state=status.state.value)
    return ApiResponse(status="ok", data=status.model_dump())


# ============================================
# Server Lifecycle Control Endpoints
# ============================================


@router.post("/start", response_model=ApiResponse)
async def start_server(
    _: RequireAdmin,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Start the game server.

    Starts the VintageStory dedicated server as a background subprocess.
    Requires Admin role.

    Returns:
        ApiResponse with lifecycle action result

    Raises:
        HTTPException: 400 if server not installed
        HTTPException: 409 if server already running
    """
    logger.debug("router_start_server_start")
    try:
        response = await service.start_server()
        logger.debug("router_start_server_complete", new_state=response.new_state.value)
        return ApiResponse(
            status="ok",
            data={
                "action": response.action.value,
                "previous_state": response.previous_state.value,
                "new_state": response.new_state.value,
                "message": response.message,
            },
        )
    except RuntimeError as e:
        error_code = str(e)
        if error_code == ErrorCode.SERVER_NOT_INSTALLED:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": ErrorCode.SERVER_NOT_INSTALLED,
                    "message": "No server is installed. Install a server version first.",
                },
            )
        elif error_code == ErrorCode.SERVER_ALREADY_RUNNING:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": ErrorCode.SERVER_ALREADY_RUNNING,
                    "message": "Server is already running.",
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": ErrorCode.SERVER_START_FAILED,
                    "message": f"Failed to start server: {error_code}",
                },
            )


@router.post("/stop", response_model=ApiResponse)
async def stop_server(
    _: RequireAdmin,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Stop the game server gracefully.

    Sends SIGTERM for graceful shutdown. If server doesn't stop within
    10 seconds, sends SIGKILL.
    Requires Admin role.

    Returns:
        ApiResponse with lifecycle action result

    Raises:
        HTTPException: 400 if server not installed
        HTTPException: 409 if server not running
    """
    logger.debug("router_stop_server_start")
    try:
        response = await service.stop_server()
        logger.debug("router_stop_server_complete", new_state=response.new_state.value)
        return ApiResponse(
            status="ok",
            data={
                "action": response.action.value,
                "previous_state": response.previous_state.value,
                "new_state": response.new_state.value,
                "message": response.message,
            },
        )
    except RuntimeError as e:
        error_code = str(e)
        if error_code == ErrorCode.SERVER_NOT_INSTALLED:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": ErrorCode.SERVER_NOT_INSTALLED,
                    "message": "No server is installed. Install a server version first.",
                },
            )
        elif error_code == ErrorCode.SERVER_NOT_RUNNING:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": ErrorCode.SERVER_NOT_RUNNING,
                    "message": "Server is not running.",
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": ErrorCode.SERVER_STOP_FAILED,
                    "message": f"Failed to stop server: {error_code}",
                },
            )


@router.post("/restart", response_model=ApiResponse)
async def restart_server(
    _: RequireAdmin,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Restart the game server.

    Stops the server gracefully (if running) then starts it again.
    Requires Admin role.

    Returns:
        ApiResponse with lifecycle action result

    Raises:
        HTTPException: 400 if server not installed
        HTTPException: 500 if stop or start phase fails
    """
    logger.debug("router_restart_server_start")
    try:
        response = await service.restart_server()
        logger.debug("router_restart_server_complete", new_state=response.new_state.value)
        return ApiResponse(
            status="ok",
            data={
                "action": response.action.value,
                "previous_state": response.previous_state.value,
                "new_state": response.new_state.value,
                "message": response.message,
            },
        )
    except RuntimeError as e:
        error_code = str(e)
        if error_code == ErrorCode.SERVER_NOT_INSTALLED:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": ErrorCode.SERVER_NOT_INSTALLED,
                    "message": "No server is installed. Install a server version first.",
                },
            )
        elif error_code == ErrorCode.SERVER_STOP_FAILED:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": ErrorCode.SERVER_STOP_FAILED,
                    "message": "Failed to stop server during restart.",
                },
            )
        elif error_code == ErrorCode.SERVER_START_FAILED:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": ErrorCode.SERVER_START_FAILED,
                    "message": "Failed to start server after stop during restart.",
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": f"Failed to restart server: {error_code}",
                },
            )
