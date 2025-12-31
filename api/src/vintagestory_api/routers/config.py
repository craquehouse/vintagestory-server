"""Configuration API endpoints.

Story 6.2: Game Settings API
Story 6.3: API Settings Service

Provides endpoints for reading and updating server configuration.

Game Settings (6.2):
- GET /config/game - Read all game settings with metadata
- POST /config/game/settings/{key} - Update a specific game setting

API Settings (6.3):
- GET /config/api - Read API operational settings (Admin only)
- POST /config/api/settings/{key} - Update a specific API setting (Admin only)
"""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel, Field

from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.routers.server import get_server_service
from vintagestory_api.services.api_settings import (
    ApiSettingInvalidError,
    ApiSettingsService,
    ApiSettingUnknownError,
)
from vintagestory_api.services.game_config import (
    GameConfigService,
    SettingEnvManagedError,
    SettingUnknownError,
    SettingUpdateFailedError,
    SettingValueInvalidError,
)
from vintagestory_api.services.pending_restart import PendingRestartState

router = APIRouter(prefix="/config", tags=["Config"])

# Type alias for authenticated user (Admin or Monitor)
RequireAuth = Annotated[str, Depends(get_current_user)]


class SettingUpdateRequest(BaseModel):
    """Request body for updating a setting."""

    value: Any = Field(..., description="New value for the setting")


# Singleton instance for pending restart state (shared with mod service)
_pending_restart_state: PendingRestartState | None = None


def get_pending_restart_state() -> PendingRestartState:
    """Get the shared pending restart state singleton.

    Returns:
        PendingRestartState instance shared across services.
    """
    global _pending_restart_state
    if _pending_restart_state is None:
        _pending_restart_state = PendingRestartState()
    return _pending_restart_state


def get_game_config_service(
    server_service: Any = Depends(get_server_service),
    pending_restart_state: PendingRestartState = Depends(get_pending_restart_state),
) -> GameConfigService:
    """Dependency to get GameConfigService instance.

    Args:
        server_service: ServerService for checking state and sending commands.
        pending_restart_state: Shared pending restart state.

    Returns:
        GameConfigService instance with injected dependencies.
    """
    return GameConfigService(
        settings=server_service.settings,
        server_service=server_service,
        pending_restart_state=pending_restart_state,
    )


@router.get("/game", response_model=ApiResponse, summary="Get game settings")
async def get_game_settings(
    _: RequireAuth,
    service: GameConfigService = Depends(get_game_config_service),
) -> ApiResponse:
    """Get all game settings with metadata.

    Returns all managed settings from serverconfig.json with metadata including:
    - Current value
    - Data type (string, int, bool, float)
    - Whether the setting supports live updates
    - Whether the setting is managed by an environment variable

    Both Admin and Monitor roles can access this read-only endpoint.

    Returns:
        ApiResponse with data containing:
        - settings: Array of setting objects with metadata
        - source_file: Name of the config file
        - last_modified: ISO timestamp of last modification

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if serverconfig.json not found
    """
    try:
        response = service.get_settings()
        return ApiResponse(status="ok", data=response.to_dict())
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.CONFIG_NOT_FOUND,
                "message": "Server configuration file not found. Start the server first.",
            },
        )


@router.post(
    "/game/settings/{key}",
    response_model=ApiResponse,
    summary="Update game setting",
)
async def update_game_setting(
    key: Annotated[
        str,
        Path(
            description="Setting key to update (e.g., 'ServerName', 'Port')",
            min_length=1,
            max_length=100,
        ),
    ],
    request: SettingUpdateRequest,
    _: RequireAdmin,
    service: GameConfigService = Depends(get_game_config_service),
) -> ApiResponse:
    """Update a specific game setting.

    Updates a setting using either:
    1. Console command (if server is running and setting supports live updates)
    2. File update (if server is stopped or setting requires restart)

    Admin role required for this write operation.

    Args:
        key: The setting key to update.
        request: Request body containing the new value.

    Returns:
        ApiResponse with data containing:
        - key: The setting that was updated
        - value: The new value
        - method: "console_command" or "file_update"
        - pending_restart: Whether a restart is now required

    Raises:
        HTTPException: 400 if setting unknown or env-managed
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not Admin role
        HTTPException: 500 if update fails
    """
    try:
        result = await service.update_setting(key, request.value)
        return ApiResponse(status="ok", data=result.to_dict())

    except SettingUnknownError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.SETTING_UNKNOWN,
                "message": e.message,
            },
        )

    except SettingEnvManagedError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.SETTING_ENV_MANAGED,
                "message": e.message,
            },
        )

    except SettingValueInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.SETTING_VALUE_INVALID,
                "message": e.message,
            },
        )

    except SettingUpdateFailedError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": ErrorCode.SETTING_UPDATE_FAILED,
                "message": e.message,
            },
        )


# =============================================================================
# API Settings Endpoints (Story 6.3)
# =============================================================================


def get_api_settings_service(
    server_service: Any = Depends(get_server_service),
) -> ApiSettingsService:
    """Dependency to get ApiSettingsService instance.

    Args:
        server_service: ServerService for accessing application settings.

    Returns:
        ApiSettingsService instance with settings dependency injected.

    Note:
        TODO(Epic-7): When implementing the scheduler service, inject the
        scheduler_callback parameter here to enable automatic rescheduling
        when mod_list_refresh_interval or server_versions_refresh_interval
        settings are updated. Example:

            scheduler = get_scheduler_service()
            return ApiSettingsService(
                settings=server_service.settings,
                scheduler_callback=scheduler.reschedule_job,
            )
    """
    return ApiSettingsService(settings=server_service.settings)


@router.get("/api", response_model=ApiResponse, summary="Get API settings")
async def get_api_settings(
    _: RequireAdmin,
    service: ApiSettingsService = Depends(get_api_settings_service),
) -> ApiResponse:
    """Get API operational settings.

    Returns all API settings including:
    - auto_start_server: Start game server on API launch
    - block_env_managed_settings: Block UI changes to env-controlled settings
    - mod_list_refresh_interval: Seconds between mod cache refreshes
    - server_versions_refresh_interval: Seconds between version checks

    **Admin role required.** API settings contain sensitive configuration
    that should only be accessible to administrators.

    Returns:
        ApiResponse with data containing:
        - settings: Object with all API settings and their values

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not Admin role
    """
    settings = service.get_settings()
    return ApiResponse(status="ok", data={"settings": settings.model_dump()})


@router.post(
    "/api/settings/{key}",
    response_model=ApiResponse,
    summary="Update API setting",
)
async def update_api_setting(
    key: Annotated[
        str,
        Path(
            description="Setting key to update (e.g., 'auto_start_server')",
            min_length=1,
            max_length=100,
        ),
    ],
    request: SettingUpdateRequest,
    _: RequireAdmin,
    service: ApiSettingsService = Depends(get_api_settings_service),
) -> ApiResponse:
    """Update a specific API setting.

    Updates the setting in api-settings.json and returns the updated value.
    For refresh interval settings (mod_list_refresh_interval,
    server_versions_refresh_interval), the scheduler will be notified
    to reschedule the job (Epic 7 integration).

    **Admin role required.**

    Args:
        key: The setting key to update.
        request: Request body containing the new value.

    Returns:
        ApiResponse with data containing:
        - key: The setting that was updated
        - value: The new value

    Raises:
        HTTPException: 400 if setting unknown or value invalid
        HTTPException: 401 if not authenticated
        HTTPException: 403 if not Admin role
    """
    try:
        result = await service.update_setting(key, request.value)
        return ApiResponse(status="ok", data=result)

    except ApiSettingUnknownError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.API_SETTING_UNKNOWN,
                "message": e.message,
            },
        )

    except ApiSettingInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.API_SETTING_INVALID,
                "message": e.message,
            },
        )
