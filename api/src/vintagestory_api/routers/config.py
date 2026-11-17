"""Configuration API endpoints.

Story 6.2: Game Settings API
Story 6.3: API Settings Service
Story 6.5: Raw Config Viewer
Story 17.5: Monitor keys cannot read the server password (FR186)
Story 17.6: A saved refresh interval reschedules its job (FR187)

Provides endpoints for reading and updating server configuration.

Game Settings (6.2):
- GET /config/game - Read all game settings with metadata (secrets for Admin only)
- POST /config/game/settings/{key} - Update a specific game setting

API Settings (6.3):
- GET /config/api - Read API operational settings (Admin only)
- POST /config/api/settings/{key} - Update a specific API setting (Admin only)

Config Files (6.5):
- GET /config/files - List all JSON config files (read-only)
- GET /config/files/{filename} - Read raw config file content (read-only; secrets,
  and the text of files that are not valid JSON, for Admin only). Story 19.1: only
  regular .json files (any letter case) of UTF-8 text, up to 2 MiB, are served;
  anything else is 400 CONFIG_FILE_NOT_SUPPORTED or 413 CONFIG_FILE_TOO_LARGE

Both read endpoints answer with Cache-Control: no-store, error responses included,
since what they return depends on the key's role. An unhandled error (500) carries
only "Internal Server Error", without the header.
"""

from functools import partial
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Path, Response
from pydantic import BaseModel, Field

from vintagestory_api.jobs import apply_interval_setting
from vintagestory_api.middleware.auth import get_current_user
from vintagestory_api.middleware.permissions import RequireAdmin
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.routers.jobs import get_scheduler
from vintagestory_api.services.api_settings import (
    ApiSettingInvalidError,
    ApiSettingNotAppliedError,
    ApiSettingsService,
    ApiSettingUnknownError,
)
from vintagestory_api.services.config_files import (
    ConfigFileNotFoundError,
    ConfigFileNotSupportedError,
    ConfigFileReadError,
    ConfigFilesService,
    ConfigFileTooLargeError,
    ConfigPathInvalidError,
)
from vintagestory_api.services.game_config import (
    GameConfigService,
    SettingEnvManagedError,
    SettingUnknownError,
    SettingUpdateFailedError,
    SettingValueInvalidError,
)
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.scheduler import SchedulerService
from vintagestory_api.services.server import get_server_service

router = APIRouter(prefix="/config", tags=["Config"])

# Type alias for authenticated user (Admin or Monitor)
RequireAuth = Annotated[str, Depends(get_current_user)]

# Story 17.5: the two read endpoints answer depending on the key's role, so no response
# of theirs, error responses included, may be cached
NO_STORE = {"Cache-Control": "no-store"}


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
    role: RequireAuth,
    response: Response,
    service: GameConfigService = Depends(get_game_config_service),
) -> ApiResponse:
    """Get all game settings with metadata.

    Returns all managed settings from serverconfig.json with metadata including:
    - Current value
    - Data type (string, int, bool, float)
    - Whether the setting supports live updates
    - Whether the setting is managed by an environment variable

    Both Admin and Monitor roles can access this read-only endpoint. Monitor
    receives secret settings (Password) redacted: `value` is null, `secret` is
    true and `configured` says whether the secret is set (Story 17.5, FR186).
    The response, an error included, is never cached (Cache-Control: no-store).

    Returns:
        ApiResponse with data containing:
        - settings: Array of setting objects with metadata
        - source_file: Name of the config file
        - last_modified: ISO timestamp of last modification

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 404 if serverconfig.json not found
    """
    response.headers.update(NO_STORE)
    try:
        settings = service.get_settings(role)
        return ApiResponse(status="ok", data=settings.to_dict())
    except FileNotFoundError:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.CONFIG_NOT_FOUND,
                "message": "Server configuration file not found. Start the server first.",
            },
            headers=NO_STORE,
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
    scheduler: SchedulerService = Depends(get_scheduler),
) -> ApiSettingsService:
    """Dependency to get ApiSettingsService instance.

    Args:
        server_service: ServerService for accessing application settings.
        scheduler: The running scheduler; a saved interval setting is applied to it
            through `apply_interval_setting` (Story 17.6, Epic 17 ADR-5).

    Returns:
        ApiSettingsService instance with settings and scheduler callback injected.
    """
    return ApiSettingsService(
        settings=server_service.settings,
        scheduler_callback=partial(apply_interval_setting, scheduler),
    )


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
    # Secrets such as the mod update webhook are reported only as configured (FR149)
    return ApiResponse(status="ok", data={"settings": settings.redacted()})


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
    For the refresh interval settings (mod_list_refresh_interval,
    server_versions_refresh_interval, metrics_collection_interval) the
    setting's job is then rescheduled without an API restart: its next run is
    one new interval after the save, and 0 removes the job (Story 17.6).
    Intervals are at most 31,536,000 seconds (365 days).

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
        HTTPException: 500 API_SETTING_NOT_APPLIED if the value was saved but its
            job could not be rescheduled (the value applies at the next API start)
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

    except ApiSettingNotAppliedError as e:
        raise HTTPException(
            status_code=500,
            detail={
                "code": ErrorCode.API_SETTING_NOT_APPLIED,
                "message": e.message,
            },
        )


# =============================================================================
# Config Files Endpoints (Story 6.5)
# =============================================================================


def get_config_files_service(
    server_service: Any = Depends(get_server_service),
) -> ConfigFilesService:
    """Dependency to get ConfigFilesService instance.

    Args:
        server_service: ServerService for accessing application settings.

    Returns:
        ConfigFilesService instance with settings dependency injected.
    """
    return ConfigFilesService(settings=server_service.settings)


@router.get("/directories", response_model=ApiResponse, summary="List directories")
async def list_config_directories(
    _: RequireAuth,
    service: ConfigFilesService = Depends(get_config_files_service),
    directory: str | None = None,
) -> ApiResponse:
    """List subdirectories in serverdata directory or a subdirectory.

    Returns a list of directory names available for browsing.
    Directories are from the serverdata directory (where VintageStory stores
    ModConfigs, Playerdata, Macros, and other subdirectories).

    Note: Hidden directories (starting with .) are included in the response.
    Frontend may choose to filter these for display purposes.

    Both Admin and Monitor roles can access this read-only endpoint.

    Args:
        directory: Optional subdirectory path to list directories from.
                   If not provided, lists directories in the root serverdata directory.

    Returns:
        ApiResponse with data containing:
        - directories: Array of subdirectory names in the target directory

    Raises:
        HTTPException: 401 if not authenticated
        HTTPException: 400 if directory contains path traversal
    """
    try:
        directories = service.list_directories(directory)
    except ConfigPathInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.CONFIG_PATH_INVALID, "message": e.message},
        )
    return ApiResponse(status="ok", data={"directories": directories})


@router.get("/files", response_model=ApiResponse, summary="List config files")
async def list_config_files(
    _: RequireAuth,
    service: ConfigFilesService = Depends(get_config_files_service),
    directory: str | None = None,
) -> ApiResponse:
    """List JSON configuration files in serverdata directory or subdirectory.

    Returns a list of configuration file names available for viewing.
    Files are from the serverdata directory (where VintageStory stores
    serverconfig.json and other configuration files).

    Both Admin and Monitor roles can access this read-only endpoint.

    Args:
        directory: Optional subdirectory name to list files from.
                   If not provided, lists files in the root serverdata directory.

    Returns:
        ApiResponse with data containing:
        - files: Array of JSON filenames in the target directory

    Raises:
        HTTPException: 400 if directory contains path traversal
        HTTPException: 401 if not authenticated
    """
    try:
        files = service.list_files(directory=directory)
        return ApiResponse(status="ok", data={"files": files})
    except ConfigPathInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.CONFIG_PATH_INVALID,
                "message": e.message,
            },
        )


@router.get(
    "/files/{filename:path}",
    response_model=ApiResponse,
    summary="Read config file",
)
async def read_config_file(
    filename: Annotated[
        str,
        Path(
            description="Name of the config file to read (e.g., 'serverconfig.json')",
            min_length=1,
            max_length=255,
        ),
    ],
    role: RequireAuth,
    response: Response,
    service: ConfigFilesService = Depends(get_config_files_service),
) -> ApiResponse:
    """Read raw content of a configuration file.

    Returns the raw JSON content of the specified configuration file.
    Path traversal attempts (e.g., ../secrets.json) are rejected with 400.

    Both Admin and Monitor roles can access this read-only endpoint. Monitor
    receives secrets redacted at every depth (Story 19.1, FR207): the value of a key
    whose name looks like a secret (Password, token, secret, API key, webhook and
    similar, any letter case or separator), StartupCommands, URLs with user info and
    Discord webhook URLs are "[redacted]" (null and "" stay), and a file that is not
    valid JSON has `_raw: "[redacted]"` instead of its text (Story 17.5, FR186).
    The response is never cached (Cache-Control: no-store), an error response
    included.

    Args:
        filename: Name of the file to read (must be in serverdata directory).

    Returns:
        ApiResponse with data containing:
        - filename: The requested filename
        - content: Parsed JSON content from the file

    Only regular files whose requested and resolved names end in .json (any letter
    case), of at most 2 MiB and UTF-8 text, are served (Story 19.1); content that
    does not parse or nests more than 200 levels deep is returned as `_raw` and
    `_parse_error`.

    Raises:
        HTTPException: 400 CONFIG_PATH_INVALID if path traversal detected
        HTTPException: 400 CONFIG_FILE_NOT_SUPPORTED if the name does not end in .json,
            or it is a directory, not a regular file, does not resolve to a .json name,
            or is not UTF-8 text
        HTTPException: 401 if not authenticated
        HTTPException: 404 if file not found
        HTTPException: 413 CONFIG_FILE_TOO_LARGE if the file is larger than 2 MiB
        HTTPException: 500 INTERNAL_ERROR if the file cannot be read
    """
    response.headers.update(NO_STORE)
    try:
        result = service.read_file(filename, role)
        return ApiResponse(status="ok", data=result)

    except ConfigPathInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.CONFIG_PATH_INVALID,
                "message": e.message,
            },
            headers=NO_STORE,
        )

    except ConfigFileNotSupportedError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.CONFIG_FILE_NOT_SUPPORTED, "message": e.message},
            headers=NO_STORE,
        )

    except ConfigFileNotFoundError as e:
        raise HTTPException(
            status_code=404,
            detail={
                "code": ErrorCode.CONFIG_FILE_NOT_FOUND,
                "message": e.message,
            },
            headers=NO_STORE,
        )

    except ConfigFileTooLargeError as e:
        raise HTTPException(
            status_code=413,
            detail={"code": ErrorCode.CONFIG_FILE_TOO_LARGE, "message": e.message},
            headers=NO_STORE,
        )

    except ConfigFileReadError as e:
        raise HTTPException(
            status_code=500,
            detail={"code": ErrorCode.INTERNAL_ERROR, "message": e.message},
            headers=NO_STORE,
        )
