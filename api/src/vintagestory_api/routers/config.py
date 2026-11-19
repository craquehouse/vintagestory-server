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
- GET /config/directories - List directories (read-only)
- GET /config/files - List all JSON config files (read-only)
- GET /config/files/{filename} - Read raw config file content (read-only; secrets,
  and the text of files that are not valid JSON, for Admin only). Story 19.1: only
  regular .json files (any letter case) of UTF-8 text, up to 2 MiB, are served;
  anything else is 400 CONFIG_FILE_NOT_SUPPORTED or 413 CONFIG_FILE_TOO_LARGE
- POST /config/files/validate - Check a text against a file's parser rule (Admin only;
  Story 23.4)
- PUT /config/files/{filename} - Save an existing config file's text while the game
  server is stopped (Admin only; Story 23.4)
- GET /config/history/{filename} - List a file's earlier versions, or read one with
  ?revision= (Admin only; Story 23.6)
- POST /config/history/{filename}/restore - Restore an earlier version (Admin only;
  Story 23.6)

Story 19.1 (FR208): roles other than Admin list and read the root of the server data
directory and ModConfig only; any other directory is 403 FORBIDDEN for the three routes,
whether or not the server data directory exists. Entries resolving outside the server
data directory are not listed for any role (Epic 21 ADR-5).

The config file routes (directories, files and file content) answer with
Cache-Control: no-store, error responses included, since what they return depends
on the key's role. An unhandled error (500) carries
only "Internal Server Error", without the header.
"""

from functools import partial
from typing import Annotated, Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Path, Query, Response
from pydantic import BaseModel, Field

from vintagestory_api.jobs import apply_setting
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
    ConfigDirectoryForbiddenError,
    ConfigFileChangedError,
    ConfigFileInvalidError,
    ConfigFileNotFoundError,
    ConfigFileNotSupportedError,
    ConfigFileReadError,
    ConfigFilesService,
    ConfigFileTooLargeError,
    ConfigFileWriteError,
    ConfigPathInvalidError,
)
from vintagestory_api.services.config_history import (
    ConfigHistoryWriteError,
    Revision,
    RevisionInvalidError,
    RevisionNotFoundError,
)
from vintagestory_api.services.game_config import (
    GameConfigService,
    SettingEnvManagedError,
    SettingUnknownError,
    SettingUpdateFailedError,
    SettingValueInvalidError,
)
from vintagestory_api.services.mods import get_restart_state
from vintagestory_api.services.pending_restart import PendingRestartState
from vintagestory_api.services.scheduler import SchedulerService
from vintagestory_api.services.server import (
    GameServerNotStoppedError,
    ServerService,
    get_server_service,
)

router = APIRouter(prefix="/config", tags=["Config"])

# Type alias for authenticated user (Admin or Monitor)
RequireAuth = Annotated[str, Depends(get_current_user)]

# Story 17.5: the read endpoints answer depending on the key's role, so no response
# of theirs, error responses included, may be cached (Story 19.1: the listings too)
NO_STORE = {"Cache-Control": "no-store"}

logger = structlog.get_logger()


class SettingUpdateRequest(BaseModel):
    """Request body for updating a setting."""

    value: Any = Field(..., description="New value for the setting")


def get_pending_restart_state() -> PendingRestartState:
    """Get the one pending restart state (Story 22.2, FR306).

    The dependency of get_game_config_service. It is the state of the mods service,
    the same object /healthz and the mods list report and ServerService clears, so a
    game setting that needs a restart shows and clears like a mod change.

    Returns:
        The shared PendingRestartState from services.mods.get_restart_state().
    """
    return get_restart_state()


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
        scheduler: The running scheduler; a saved interval setting or restart times
            are applied to it through `apply_setting` (Story 17.6, Epic 17 ADR-5;
            Story 22.3, Epic 22 ADR-7).

    Returns:
        ApiSettingsService instance with settings and scheduler callback injected.
    """
    return ApiSettingsService(
        settings=server_service.settings,
        scheduler_callback=partial(apply_setting, scheduler),
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

    For scheduled_restart_times (a list of daily HH:MM times in the container's
    time zone, at most 24, at least 16 minutes apart; stored sorted without
    duplicates) the restart jobs are made to match at once: one
    `scheduled_restart_HHMM` cron job per time, firing 15 minutes before it to
    warn the players; `[]` removes them all (Story 22.3).

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
            jobs could not be rescheduled (the value applies at the next API start)
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
    role: RequireAuth,
    response: Response,
    service: ConfigFilesService = Depends(get_config_files_service),
    directory: str | None = None,
) -> ApiResponse:
    """List subdirectories in serverdata directory or a subdirectory.

    Returns a list of directory names available for browsing.
    Directories are from the serverdata directory (where VintageStory stores
    ModConfig, Playerdata, Macros, and other subdirectories).

    Admin lists every directory. Hidden directories (starting with .) are included
    in the response; the frontend may choose to filter these for display purposes.

    A Monitor key (any role but Admin) lists the root and ModConfig only: the root
    listing holds ModConfig and no other directory, and listing any other directory,
    existing or not, is 403 FORBIDDEN (Story 19.1, FR208), whether or not the server
    data directory exists. The decision is made on resolved paths, so `.`,
    `ModConfig/..` and symlinks cannot widen it. A directory resolving outside the
    server data directory is not listed for any role, Admin included (Epic 21 ADR-5).
    The response is never cached (Cache-Control: no-store), an error response included.

    Args:
        directory: Optional subdirectory path to list directories from.
                   If not provided, lists directories in the root serverdata directory.

    Returns:
        ApiResponse with data containing:
        - directories: Array of subdirectory names in the target directory

    Raises:
        HTTPException: 400 if directory contains path traversal
        HTTPException: 401 if not authenticated
        HTTPException: 403 if the key's role may not list the directory
    """
    response.headers.update(NO_STORE)
    try:
        directories = service.list_directories(directory, role)
    except ConfigPathInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": ErrorCode.CONFIG_PATH_INVALID, "message": e.message},
            headers=NO_STORE,
        )
    except ConfigDirectoryForbiddenError as e:
        raise HTTPException(
            status_code=403,
            detail={"code": ErrorCode.FORBIDDEN, "message": e.message},
            headers=NO_STORE,
        )
    return ApiResponse(status="ok", data={"directories": directories})


@router.get("/files", response_model=ApiResponse, summary="List config files")
async def list_config_files(
    role: RequireAuth,
    response: Response,
    service: ConfigFilesService = Depends(get_config_files_service),
    directory: str | None = None,
) -> ApiResponse:
    """List JSON configuration files in serverdata directory or subdirectory.

    Returns a list of configuration file names available for viewing: the files
    that GET /config/files/{filename} can serve to the key (regular files whose
    names end in .json, any letter case, resolving inside the server data directory).
    Files are from the serverdata directory (where VintageStory stores
    serverconfig.json and other configuration files).

    Admin lists files in every directory. A Monitor key (any role but Admin) lists
    files in the root and under ModConfig only; another directory, existing or not,
    is 403 FORBIDDEN whether or not the server data directory exists, and files that
    resolve elsewhere are not listed (Story 19.1, FR208). A file resolving outside the
    server data directory is not listed for any role (Epic 21 ADR-5). The response is
    never cached (Cache-Control: no-store), an error response included.

    Args:
        directory: Optional subdirectory name to list files from.
                   If not provided, lists files in the root serverdata directory.

    Returns:
        ApiResponse with data containing:
        - files: Array of JSON filenames in the target directory

    Raises:
        HTTPException: 400 if directory contains path traversal
        HTTPException: 401 if not authenticated
        HTTPException: 403 if the key's role may not list the directory
    """
    response.headers.update(NO_STORE)
    try:
        files = service.list_files(directory=directory, role=role)
        return ApiResponse(status="ok", data={"files": files})
    except ConfigPathInvalidError as e:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.CONFIG_PATH_INVALID,
                "message": e.message,
            },
            headers=NO_STORE,
        )
    except ConfigDirectoryForbiddenError as e:
        raise HTTPException(
            status_code=403,
            detail={"code": ErrorCode.FORBIDDEN, "message": e.message},
            headers=NO_STORE,
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

    Returns the parsed content of the specified configuration file.
    Path traversal attempts (e.g., ../secrets.json) are rejected with 400.

    Both Admin and Monitor roles can access this read-only endpoint. A Monitor key
    (any role but Admin) reads files in the root and under ModConfig only; a file in
    any other directory, existing or not, is 403 FORBIDDEN, checked on the resolved
    path after the path is found to stay inside the data directory and before the
    file name (Story 19.1, FR208).

    Monitor receives secrets redacted at every depth (Story 19.1, FR207): the value of a key
    whose name looks like a secret (Password, token, secret, API key, webhook and
    similar, any letter case or separator), StartupCommands, URLs with user info and
    Discord webhook URLs are "[redacted]" (null and "" stay), and a file that does
    not parse has `_raw: "[redacted]"` instead of its text (Story 17.5, FR186).
    The response is never cached (Cache-Control: no-store), an error response
    included.

    Args:
        filename: Name of the file to read (must be in serverdata directory).

    Returns:
        ApiResponse with data containing:
        - filename: The requested filename
        - content: Parsed content from the file
        - parse_error: null, or {message, line, column} when it does not parse
        - text, version: Admin only; the file's text (with comments) and the SHA-256
          of its bytes (Story 23.1)

    Only regular files whose requested and resolved names end in .json (any letter
    case), of at most 2 MiB and UTF-8 text, are served (Story 19.1). Files are
    parsed as JSON5: comments, trailing commas, single quotes and unquoted keys
    (Story 23.1, FR309); content that does not parse, nests more than 200 levels
    deep or holds Infinity or NaN is returned as `_raw` and `_parse_error`.

    Raises:
        HTTPException: 400 CONFIG_PATH_INVALID if path traversal detected
        HTTPException: 400 CONFIG_FILE_NOT_SUPPORTED if the name does not end in .json,
            or it is a directory, not a regular file, does not resolve to a .json name,
            or is not UTF-8 text
        HTTPException: 401 if not authenticated
        HTTPException: 403 FORBIDDEN if the key's role may not read the file's directory
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

    except ConfigDirectoryForbiddenError as e:
        raise HTTPException(
            status_code=403,
            detail={"code": ErrorCode.FORBIDDEN, "message": e.message},
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


# ==============================================================================
# Saving config files (Story 23.4, FR314-FR318, Epic 23 ADR-4)
# ==============================================================================

VERSION_PATTERN = r"^[0-9a-f]{64}$"


class ConfigTextCheckRequest(BaseModel):
    """Body of POST /config/files/validate."""

    filename: str = Field(min_length=1, max_length=255)
    text: str


class ConfigFileSaveRequest(BaseModel):
    """Body of PUT /config/files/{filename}: the text, and the version it was edited from."""

    text: str
    version: str = Field(pattern=VERSION_PATTERN)


def _path_error(
    e: ConfigPathInvalidError | ConfigDirectoryForbiddenError | ConfigFileNotSupportedError,
) -> HTTPException:
    """The read's answer for a path a save or check refuses."""
    if isinstance(e, ConfigPathInvalidError):
        status, code = 400, ErrorCode.CONFIG_PATH_INVALID
    elif isinstance(e, ConfigDirectoryForbiddenError):
        status, code = 403, ErrorCode.FORBIDDEN
    else:
        status, code = 400, ErrorCode.CONFIG_FILE_NOT_SUPPORTED
    return HTTPException(
        status_code=status, detail={"code": code, "message": e.message}, headers=NO_STORE
    )


def _too_large(e: ConfigFileTooLargeError) -> HTTPException:
    return HTTPException(
        status_code=413,
        detail={"code": ErrorCode.CONFIG_FILE_TOO_LARGE, "message": e.message},
        headers=NO_STORE,
    )


def _save_error(e: Exception, filename: str) -> Exception:
    """The HTTP answer for a refused save or restore (Stories 23.4, 23.6); anything else
    is returned as is, to be raised unchanged."""
    if isinstance(e, GameServerNotStoppedError):
        if e.reason == "running":
            code = ErrorCode.CONFIG_FILE_SERVER_RUNNING
            message = "Stop the game server to save config files"
        else:
            code = ErrorCode.CONFIG_FILE_SERVER_BUSY
            message = (
                "The game server is starting, stopping or being installed; "
                "try again when it is stopped"
            )
        logger.info("config_file_save_refused", filename=filename, reason=e.reason)
        return HTTPException(
            status_code=409, detail={"code": code, "message": message}, headers=NO_STORE
        )
    if isinstance(
        e, (ConfigPathInvalidError, ConfigDirectoryForbiddenError, ConfigFileNotSupportedError)
    ):
        return _path_error(e)
    if isinstance(e, ConfigFileTooLargeError):
        return _too_large(e)
    simple: list[tuple[type[Exception], int, str]] = [
        (ConfigFileNotFoundError, 404, ErrorCode.CONFIG_FILE_NOT_FOUND),
        (ConfigFileChangedError, 409, ErrorCode.CONFIG_FILE_CHANGED),
        (ConfigFileWriteError, 500, ErrorCode.CONFIG_FILE_WRITE_FAILED),
        (ConfigFileReadError, 500, ErrorCode.INTERNAL_ERROR),
        (ConfigHistoryWriteError, 500, ErrorCode.CONFIG_HISTORY_WRITE_FAILED),
        (RevisionInvalidError, 400, ErrorCode.CONFIG_REVISION_INVALID),
        (RevisionNotFoundError, 404, ErrorCode.CONFIG_REVISION_NOT_FOUND),
    ]
    for error_type, status, code in simple:
        if isinstance(e, error_type):
            message = getattr(e, "message", str(e))
            return HTTPException(
                status_code=status, detail={"code": code, "message": message}, headers=NO_STORE
            )
    if isinstance(e, ConfigFileInvalidError):
        return HTTPException(
            status_code=422,
            detail={
                "code": ErrorCode.CONFIG_FILE_INVALID,
                "message": e.message,
                "parse_error": e.info.to_dict(),
            },
            headers=NO_STORE,
        )
    return e


@router.post("/files/validate", response_model=ApiResponse, summary="Check a config file text")
async def validate_config_file_text(
    body: ConfigTextCheckRequest,
    _: RequireAdmin,
    response: Response,
    service: ConfigFilesService = Depends(get_config_files_service),
) -> ApiResponse:
    """Check a text against the parser rule a save of the file would use (Story 23.4).

    Admin only. The rule is JSON5, or strict JSON for serverconfig.json in the data
    root (Epic 23 ADR-1 decision 5). The path rules of a save apply, but the file need
    not exist; nothing is read or written, and the game server's state does not matter
    (ADR-4 decision 10). The response is never cached.

    Returns:
        ApiResponse with data: valid (bool) and parse_error ({message, line, column}
        or null).

    Raises:
        HTTPException: 400 CONFIG_PATH_INVALID or CONFIG_FILE_NOT_SUPPORTED for a path a
            save refuses; 403 for a key that is not Admin; 413 CONFIG_FILE_TOO_LARGE for a
            text over 2 MiB.
    """
    response.headers.update(NO_STORE)
    try:
        info = service.check_text(body.filename, body.text)
    except (
        ConfigPathInvalidError,
        ConfigDirectoryForbiddenError,
        ConfigFileNotSupportedError,
    ) as e:
        raise _path_error(e)
    except ConfigFileTooLargeError as e:
        raise _too_large(e)
    return ApiResponse(
        status="ok",
        data={"valid": info is None, "parse_error": info.to_dict() if info else None},
    )


@router.put("/files/{filename:path}", response_model=ApiResponse, summary="Save config file")
async def save_config_file(
    filename: Annotated[
        str,
        Path(description="Path of the config file to save", min_length=1, max_length=255),
    ],
    body: ConfigFileSaveRequest,
    _: RequireAdmin,
    response: Response,
    service: ConfigFilesService = Depends(get_config_files_service),
    server_service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Save an existing config file's text while the game server is stopped (Story 23.4).

    Admin only (FR314-FR318, Epic 23 ADR-4). The text is written exactly as sent
    (comments, key order and formatting kept), atomically, keeping the file's mode. It
    must parse as JSON5 (strict JSON for serverconfig.json in the data root), be at most
    2 MiB of UTF-8, and `version` must be the version of the file as it is now (from the
    read), else nothing is written. Only existing files are saved. The save holds the
    server's lifecycle lock, so a start requested meanwhile waits for it. A save of the
    root serverconfig.json drops the pending restart-required edits (Story 22.7) whose
    setting it changes. The response is never cached.

    Returns:
        ApiResponse with data: filename and version (the SHA-256 of the bytes written).

    Raises:
        HTTPException: 400 CONFIG_PATH_INVALID or CONFIG_FILE_NOT_SUPPORTED; 403 for a key
            that is not Admin; 404 CONFIG_FILE_NOT_FOUND; 409 CONFIG_FILE_SERVER_RUNNING
            (the game is running, starting or stopping), CONFIG_FILE_SERVER_BUSY (a start,
            stop, restart, install or uninstall is in progress) or CONFIG_FILE_CHANGED
            (the file changed since it was read); 413 CONFIG_FILE_TOO_LARGE; 422
            CONFIG_FILE_INVALID with parse_error; 500 CONFIG_FILE_WRITE_FAILED (the file is
            unchanged) or INTERNAL_ERROR (it could not be read).
    """
    response.headers.update(NO_STORE)
    try:
        async with server_service.config_write():
            saved = service.save_file(filename, body.text, body.version)
            if saved.is_root_serverconfig:
                server_service.drop_pending_edits_changed_by_save(saved.previous_bytes, saved.value)
    except Exception as e:
        raise _save_error(e, filename)
    return ApiResponse(status="ok", data={"filename": saved.filename, "version": saved.version})


# ==============================================================================
# Config file history (Story 23.6, FR321-FR323, Epic 23 ADR-7)
# ==============================================================================


class RevisionRestoreRequest(BaseModel):
    """Body of POST /config/history/{filename}/restore."""

    revision: str = Field(min_length=1, max_length=64)
    version: str = Field(pattern=VERSION_PATTERN)


def _revision_dict(revision: Revision) -> dict[str, object]:
    return revision.model_dump(mode="json")


@router.get("/history/{filename:path}", response_model=ApiResponse, summary="Config file history")
async def read_config_history(
    filename: Annotated[
        str, Path(description="Path of the config file", min_length=1, max_length=255)
    ],
    _: RequireAdmin,
    response: Response,
    revision: Annotated[str | None, Query(max_length=64)] = None,
    service: ConfigFilesService = Depends(get_config_files_service),
) -> ApiResponse:
    """List a config file's earlier versions, or read one (Story 23.6, Admin only).

    Earlier versions are kept for saves made through the API (PUT /config/files/{path}
    and restores), newest first; a file with none, existing or not, has an empty list.
    With `revision`, the answer is that version's text (UTF-8, a byte order mark
    dropped, an undecodable byte replaced). The response is never cached.

    Returns:
        ApiResponse with data: filename and revisions [{id, saved_at, saved_by, size,
        sha256}]; or, with `revision`, filename, revision and text.

    Raises:
        HTTPException: 400 CONFIG_PATH_INVALID, CONFIG_FILE_NOT_SUPPORTED or
            CONFIG_REVISION_INVALID; 403 for a key that is not Admin; 404
            CONFIG_REVISION_NOT_FOUND.
    """
    response.headers.update(NO_STORE)
    try:
        relative = service.relative_path(service.target_for_history(filename))
        if revision is None:
            revisions = service.history.list(relative)
            return ApiResponse(
                status="ok",
                data={"filename": filename, "revisions": [_revision_dict(r) for r in revisions]},
            )
        found, data = service.history.read(relative, revision)
    except Exception as e:
        raise _save_error(e, filename)
    return ApiResponse(
        status="ok",
        data={
            "filename": filename,
            "revision": _revision_dict(found),
            "text": data.decode("utf-8-sig", errors="replace"),
        },
    )


@router.post(
    "/history/{filename:path}/restore",
    response_model=ApiResponse,
    summary="Restore an earlier version of a config file",
)
async def restore_config_revision(
    filename: Annotated[
        str, Path(description="Path of the config file", min_length=1, max_length=255)
    ],
    body: RevisionRestoreRequest,
    _: RequireAdmin,
    response: Response,
    service: ConfigFilesService = Depends(get_config_files_service),
    server_service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Save an earlier version of a config file over it (Story 23.6, Admin only).

    Every rule of PUT /config/files/{path} applies (the game server stopped, the
    version check, the parser rule, the size, the pending-edit drop for
    serverconfig.json), and the current text is kept as a new earlier version first.
    The response is never cached.

    Returns:
        ApiResponse with data: filename and version (the SHA-256 of the bytes written).

    Raises:
        HTTPException: The save's errors, and 400 CONFIG_REVISION_INVALID or 404
            CONFIG_REVISION_NOT_FOUND for the revision.
    """
    response.headers.update(NO_STORE)
    try:
        async with server_service.config_write():
            saved = service.restore_revision(filename, body.revision, body.version)
            if saved.is_root_serverconfig:
                server_service.drop_pending_edits_changed_by_save(saved.previous_bytes, saved.value)
    except Exception as e:
        raise _save_error(e, filename)
    return ApiResponse(status="ok", data={"filename": saved.filename, "version": saved.version})
