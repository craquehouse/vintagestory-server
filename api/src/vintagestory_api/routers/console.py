"""Console API endpoints for history and streaming."""

import json
import secrets
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket
from starlette.websockets import WebSocketDisconnect

from vintagestory_api.config import Settings
from vintagestory_api.middleware.auth import get_settings
from vintagestory_api.middleware.permissions import RequireConsoleAccess
from vintagestory_api.models.console import (
    ConsoleCommandData,
    ConsoleCommandRequest,
    ConsoleHistoryData,
    LogFileInfo,
    LogFilesResponse,
)
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.models.responses import ApiResponse
from vintagestory_api.services.server import ServerService, get_server_service
from vintagestory_api.services.ws_token_service import (
    WebSocketTokenService,
    get_ws_token_service,
)

logger = structlog.get_logger()

# HTTP router for console endpoints (included under api_v1 with auth dependency)
router = APIRouter(prefix="/console", tags=["Console"])

# WebSocket router for real-time streaming (no auth dependency at router level)
# WebSocket handles its own authentication via query parameter
ws_router = APIRouter(prefix="/console", tags=["Console"])


@router.get("/history")
async def get_console_history(
    _role: RequireConsoleAccess,
    lines: Annotated[int | None, Query(ge=1, le=10000, description="Max lines to return")] = None,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Get console history from the buffer.

    Returns console output lines from the server's stdout/stderr.
    Oldest lines are returned first. Lines are stored as-is from the server
    (VintageStory includes its own timestamps).

    Requires Admin role (console access is restricted to administrators).

    Args:
        _role: Enforces Admin-only access via RequireConsoleAccess dependency.
        lines: Optional limit on number of lines to return (most recent N lines).
        service: ServerService containing the console buffer.

    Returns:
        API envelope with lines array and total count.
    """
    history = service.console_buffer.get_history(limit=lines)

    data = ConsoleHistoryData(
        lines=history,
        total=len(service.console_buffer),
        limit=lines,
    )

    return ApiResponse(status="ok", data=data.model_dump())


@router.post("/command")
async def send_console_command(
    _role: RequireConsoleAccess,
    body: ConsoleCommandRequest,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Send a command to the game server console.

    Writes the command to the server's stdin, which is equivalent to typing
    the command directly into the server console.

    Requires Admin role (console commands are restricted to administrators).

    Args:
        _role: Enforces Admin-only access via RequireConsoleAccess dependency.
        body: Request body with command to send.
        service: ServerService for command execution.

    Returns:
        API envelope with command that was sent.

    Raises:
        HTTPException: 400 if server is not running.
    """
    success = await service.send_command(body.command)

    if not success:
        raise HTTPException(
            status_code=400,
            detail={
                "code": ErrorCode.SERVER_NOT_RUNNING,
                "message": "Cannot send command: server is not running",
            },
        )

    data = ConsoleCommandData(command=body.command, sent=True)

    return ApiResponse(status="ok", data=data.model_dump())


@router.get("/logs")
async def list_log_files(
    _role: RequireConsoleAccess,
    settings: Settings = Depends(get_settings),
) -> ApiResponse:
    """List available log files in the serverdata/Logs directory.

    Returns information about each log file including name, size, and modification time.
    Files are sorted by modification time (most recent first).

    Requires Admin role (log access is restricted to administrators).

    Args:
        _role: Enforces Admin-only access via RequireConsoleAccess dependency.
        settings: Application settings for paths.

    Returns:
        API envelope with list of log files and logs directory path.
    """
    from datetime import UTC, datetime

    logs_dir = settings.serverdata_dir / "Logs"
    files: list[LogFileInfo] = []

    if logs_dir.exists() and logs_dir.is_dir():
        try:
            dir_entries = list(logs_dir.iterdir())
        except OSError as e:
            logger.warning("logs_dir_read_failed", logs_dir=str(logs_dir), error=str(e))
            dir_entries = []

        for path in dir_entries:
            # Only include regular files with log-like extensions
            if path.is_file() and path.suffix in (".log", ".txt"):
                try:
                    stat = path.stat()
                    modified_at = datetime.fromtimestamp(stat.st_mtime, tz=UTC)
                    files.append(
                        LogFileInfo(
                            name=path.name,
                            size_bytes=stat.st_size,
                            modified_at=modified_at.isoformat(),
                        )
                    )
                except OSError as e:
                    logger.warning("log_file_stat_failed", file=path.name, error=str(e))

    # Sort by modification time, most recent first
    files.sort(key=lambda f: f.modified_at, reverse=True)

    data = LogFilesResponse(files=files, logs_dir=str(logs_dir))

    return ApiResponse(status="ok", data=data.model_dump())


def _get_websocket_client_ip(websocket: WebSocket) -> str:
    """Extract client IP from WebSocket, accounting for proxies.

    Args:
        websocket: The WebSocket connection

    Returns:
        Client IP address string
    """
    # Check proxy headers first
    forwarded_for = websocket.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()

    real_ip = websocket.headers.get("x-real-ip")
    if real_ip:
        return real_ip

    return websocket.client.host if websocket.client else "unknown"


def _verify_api_key_with_settings(
    api_key: str | None, admin_key: str, monitor_key: str | None
) -> str | None:
    """Verify API key and return role or None if invalid.

    Uses timing-safe comparison to prevent timing attacks.

    Args:
        api_key: The API key to verify
        admin_key: The admin API key to compare against
        monitor_key: The monitor API key to compare against (optional)

    Returns:
        "admin", "monitor", or None if invalid/missing
    """
    if not api_key:
        return None

    # Timing-safe comparison for admin key
    if secrets.compare_digest(api_key, admin_key):
        return "admin"

    # Timing-safe comparison for monitor key (if configured)
    if monitor_key and secrets.compare_digest(api_key, monitor_key):
        return "monitor"

    return None


async def _verify_ws_auth(
    token: str | None,
    api_key: str | None,
    token_service: WebSocketTokenService,
    settings: Settings,
    client_ip: str,
) -> str | None:
    """Verify WebSocket authentication using token or legacy API key.

    Token authentication takes precedence over API key. If a token is provided,
    the API key is ignored. This enables gradual migration from API key to token auth.

    If api_key is used (token is None), a deprecation warning is logged.

    Args:
        token: WebSocket auth token from query parameter
        api_key: Legacy API key from query parameter (deprecated)
        token_service: Service for token validation
        settings: Application settings with API keys
        client_ip: Client IP for logging

    Returns:
        Role string ("admin" or "monitor") if authenticated, None otherwise.
    """
    # Prefer token auth over api_key
    if token:
        role = await token_service.validate_token(token)
        if role:
            logger.debug("ws_auth_via_token", client_ip=client_ip, role=role)
        return role

    # Fall back to legacy API key (deprecated)
    if api_key:
        logger.warning(
            "ws_auth_deprecated_api_key",
            client_ip=client_ip,
            message="Deprecated api_key param used. Use token auth instead.",
        )
        return _verify_api_key_with_settings(
            api_key, settings.api_key_admin, settings.api_key_monitor
        )

    return None


@ws_router.websocket("/ws")
async def console_websocket(
    websocket: WebSocket,
    token: Annotated[str | None, Query(description="WebSocket auth token")] = None,
    api_key: Annotated[str | None, Query(description="API key (deprecated, use token)")] = None,
    history_lines: Annotated[
        int | None, Query(ge=1, le=10000, description="Number of history lines to send on connect")
    ] = None,
    settings: Settings = Depends(get_settings),
    service: ServerService = Depends(get_server_service),
    token_service: WebSocketTokenService = Depends(get_ws_token_service),
) -> None:
    """WebSocket endpoint for real-time console streaming.

    Connects authenticated Admin users to the console buffer for real-time
    output streaming. On connection, sends recent buffer history then streams
    new lines as they arrive.

    Authentication options (token preferred, api_key deprecated):
    - token: Short-lived WebSocket token from POST /auth/ws-token
    - api_key: Legacy API key (deprecated, will be removed in future version)

    Args:
        websocket: The WebSocket connection
        token: WebSocket auth token (preferred)
        api_key: Legacy API key for authentication (deprecated)
        history_lines: Number of history lines to send on connect (default from settings)
        settings: Application settings (injected via dependency)
        service: Server service for console buffer access (injected via dependency)
        token_service: WebSocket token service for token validation

    Close Codes:
        4001: Unauthorized - Missing or invalid token/API key
        4003: Forbidden - Valid token but insufficient role (Monitor, not Admin)
    """
    client_ip = _get_websocket_client_ip(websocket)

    # Verify authentication (token preferred, api_key as fallback)
    role = await _verify_ws_auth(token, api_key, token_service, settings, client_ip)

    if role is None:
        # Log failed auth attempt
        if token:
            logger.warning(
                "websocket_auth_failed",
                client_ip=client_ip,
                reason="invalid_token",
            )
            await websocket.accept()
            await websocket.close(code=4001, reason="Unauthorized: Invalid or expired token")
        else:
            key_info = f"{api_key[:8]}..." if api_key else "none"
            logger.warning(
                "websocket_auth_failed",
                client_ip=client_ip,
                key_prefix=key_info,
                reason="invalid_key",
            )
            await websocket.accept()
            await websocket.close(code=4001, reason="Unauthorized: Invalid API key")
        return

    if role != "admin":
        # Valid token/key but wrong role
        logger.warning(
            "websocket_auth_forbidden",
            client_ip=client_ip,
            role=role,
            reason="admin_required",
        )
        await websocket.accept()
        await websocket.close(code=4003, reason="Forbidden: Admin role required")
        return

    # Authentication successful - accept connection
    await websocket.accept()
    logger.info("websocket_connected", client_ip=client_ip)

    # Send buffer history first (use settings default if not specified)
    effective_history_lines = (
        history_lines if history_lines is not None else settings.console_history_lines
    )
    history = service.console_buffer.get_history(limit=effective_history_lines)
    for line in history:
        await websocket.send_text(line)

    # Create callback for real-time streaming
    async def on_new_line(line: str) -> None:
        """Send new console line to WebSocket client.

        Errors during send are logged but don't propagate - the ConsoleBuffer
        will automatically remove failed subscribers.
        """
        try:
            await websocket.send_text(line)
        except Exception as e:
            logger.warning(
                "websocket_send_failed",
                client_ip=client_ip,
                error=str(e),
            )
            raise  # Re-raise so ConsoleBuffer removes this subscriber

    # Subscribe to new lines
    service.console_buffer.subscribe(on_new_line)

    try:
        # Receive and process client messages
        while True:
            message_text = await websocket.receive_text()

            # Parse JSON message
            try:
                message = json.loads(message_text)
            except json.JSONDecodeError:
                logger.warning(
                    "websocket_invalid_json",
                    client_ip=client_ip,
                )
                await websocket.send_json({"type": "error", "content": "Invalid message format"})
                continue

            # Handle command messages
            if message.get("type") == "command":
                command = message.get("content", "")

                # Validate command (match REST endpoint validation)
                if not command:
                    await websocket.send_json(
                        {"type": "error", "content": "Empty command"}
                    )
                    continue

                if len(command) > 1000:
                    await websocket.send_json(
                        {"type": "error", "content": "Command too long (max 1000 characters)"}
                    )
                    continue

                # Log command attempt (without content for security)
                logger.info("websocket_command_received", client_ip=client_ip)

                # Try to send command to server
                success = await service.send_command(command)

                if not success:
                    await websocket.send_json(
                        {"type": "error", "content": "Server is not running"}
                    )
            else:
                # Unknown message type
                logger.debug(
                    "websocket_unknown_message_type",
                    client_ip=client_ip,
                    message_type=message.get("type"),
                )

    except WebSocketDisconnect as e:
        logger.info("websocket_disconnected", client_ip=client_ip, code=e.code)
    finally:
        # Always unsubscribe on disconnect
        service.console_buffer.unsubscribe(on_new_line)


@ws_router.websocket("/logs/ws")
async def logs_websocket(
    websocket: WebSocket,
    file: Annotated[str, Query(description="Log file name to stream (e.g., 'server-main.log')")],
    token: Annotated[str | None, Query(description="WebSocket auth token")] = None,
    api_key: Annotated[str | None, Query(description="API key (deprecated, use token)")] = None,
    history_lines: Annotated[
        int, Query(ge=1, le=10000, description="Number of history lines to send on connect")
    ] = 100,
    settings: Settings = Depends(get_settings),
    token_service: WebSocketTokenService = Depends(get_ws_token_service),
) -> None:
    """WebSocket endpoint for real-time log file streaming.

    Streams a specific log file from the serverdata/Logs directory.
    On connection, sends recent file history then streams new lines as they appear.

    Authentication options (token preferred, api_key deprecated):
    - token: Short-lived WebSocket token from POST /auth/ws-token
    - api_key: Legacy API key (deprecated, will be removed in future version)

    Args:
        websocket: The WebSocket connection
        file: Log file name to stream (validated, no path traversal)
        token: WebSocket auth token (preferred)
        api_key: Legacy API key for authentication (deprecated)
        history_lines: Number of history lines to send on connect (default 100)
        settings: Application settings (injected via dependency)
        token_service: WebSocket token service for token validation

    Close Codes:
        4001: Unauthorized - Missing or invalid token/API key
        4003: Forbidden - Valid token but insufficient role (Monitor, not Admin)
        4004: Not Found - Log file does not exist
        4005: Invalid Request - Invalid filename or access error
    """
    import asyncio

    from vintagestory_api.services.logs import (
        LogFileAccessError,
        LogFileNotFoundError,
        tail_log_file,
        validate_log_filename,
    )

    client_ip = _get_websocket_client_ip(websocket)

    # Verify authentication (token preferred, api_key as fallback)
    role = await _verify_ws_auth(token, api_key, token_service, settings, client_ip)

    if role is None:
        if token:
            logger.warning(
                "logs_websocket_auth_failed",
                client_ip=client_ip,
                reason="invalid_token",
            )
            await websocket.accept()
            await websocket.close(code=4001, reason="Unauthorized: Invalid or expired token")
        else:
            key_info = f"{api_key[:8]}..." if api_key else "none"
            logger.warning(
                "logs_websocket_auth_failed",
                client_ip=client_ip,
                key_prefix=key_info,
                reason="invalid_key",
            )
            await websocket.accept()
            await websocket.close(code=4001, reason="Unauthorized: Invalid API key")
        return

    if role != "admin":
        logger.warning(
            "logs_websocket_auth_forbidden",
            client_ip=client_ip,
            role=role,
            reason="admin_required",
        )
        await websocket.accept()
        await websocket.close(code=4003, reason="Forbidden: Admin role required")
        return

    # Validate filename before accepting
    if not validate_log_filename(file):
        logger.warning(
            "logs_websocket_invalid_filename",
            client_ip=client_ip,
            filename=file,
        )
        await websocket.accept()
        await websocket.close(code=4005, reason=f"Invalid filename: {file}")
        return

    logs_dir = settings.serverdata_dir / "Logs"
    file_path = logs_dir / file

    # Resolve path and verify it's within logs_dir (prevents symlink attacks)
    try:
        resolved_path = file_path.resolve()
        resolved_logs_dir = logs_dir.resolve()
        resolved_path.relative_to(resolved_logs_dir)
    except (ValueError, OSError):
        logger.warning(
            "logs_websocket_path_traversal",
            client_ip=client_ip,
            filename=file,
        )
        await websocket.accept()
        await websocket.close(code=4005, reason=f"Invalid path: {file}")
        return

    # Check file exists before accepting
    if not file_path.exists():
        logger.warning(
            "logs_websocket_file_not_found",
            client_ip=client_ip,
            filename=file,
        )
        await websocket.accept()
        await websocket.close(code=4004, reason=f"Log file not found: {file}")
        return

    # Accept connection
    await websocket.accept()
    logger.info("logs_websocket_connected", client_ip=client_ip, filename=file)

    try:
        # Send history first
        try:
            history = await tail_log_file(logs_dir, file, lines=history_lines)
            for line in history:
                await websocket.send_text(line)
        except (LogFileNotFoundError, LogFileAccessError) as e:
            logger.warning("logs_websocket_history_failed", filename=file, error=str(e))
            await websocket.close(code=4005, reason=str(e))
            return

        # Track file position for streaming
        last_position = file_path.stat().st_size
        poll_interval = 1.0  # seconds

        # Stream new content
        while True:
            # Wait for poll interval or client message
            try:
                # Use wait_for with a short timeout to allow polling
                await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=poll_interval,
                )
                # Client sent a message - could handle ping/pong or commands here
                # For now, just ignore client messages on log streams
                logger.debug("logs_websocket_message_ignored", client_ip=client_ip)

            except TimeoutError:
                # No message received, check for new file content
                pass

            # Check for new content
            try:
                # Get file size in executor to avoid blocking event loop
                loop = asyncio.get_event_loop()
                current_size = await loop.run_in_executor(
                    None, lambda: file_path.stat().st_size
                )

                # File was truncated or rotated
                if current_size < last_position:
                    logger.info(
                        "log_file_rotated",
                        filename=file,
                        old_size=last_position,
                        new_size=current_size,
                    )
                    last_position = 0
                    # Send a marker to the client
                    await websocket.send_text("--- Log file rotated ---")

                # New content available
                if current_size > last_position:
                    # Limit chunk size to prevent memory exhaustion (1MB max)
                    max_chunk_size = 1024 * 1024
                    bytes_to_read = min(current_size - last_position, max_chunk_size)

                    def read_new_content() -> tuple[list[str], int]:
                        with open(file_path, encoding="utf-8", errors="replace") as f:
                            f.seek(last_position)
                            content = f.read(bytes_to_read)
                            new_position = f.tell()
                            return content.splitlines(), new_position

                    new_lines, new_position = await loop.run_in_executor(None, read_new_content)

                    for line in new_lines:
                        if line:  # splitlines already strips newlines
                            await websocket.send_text(line)

                    last_position = new_position

            except FileNotFoundError:
                logger.warning("logs_websocket_file_deleted", filename=file)
                await websocket.send_text("--- Log file was deleted ---")
                await websocket.close(code=4004, reason="Log file was deleted")
                return
            except OSError as e:
                logger.warning("logs_websocket_read_error", filename=file, error=str(e))

    except WebSocketDisconnect as e:
        logger.info("logs_websocket_disconnected", client_ip=client_ip, filename=file, code=e.code)
