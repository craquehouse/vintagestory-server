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
from vintagestory_api.models.console import ConsoleCommandRequest
from vintagestory_api.models.errors import ErrorCode
from vintagestory_api.services.server import ServerService, get_server_service

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
) -> dict[str, object]:
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

    return {
        "status": "ok",
        "data": {
            "lines": history,
            "total": len(service.console_buffer),
            "limit": lines,
        },
    }


@router.post("/command")
async def send_console_command(
    _role: RequireConsoleAccess,
    body: ConsoleCommandRequest,
    service: ServerService = Depends(get_server_service),
) -> dict[str, object]:
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

    return {
        "status": "ok",
        "data": {"command": body.command, "sent": True},
    }


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


@ws_router.websocket("/ws")
async def console_websocket(
    websocket: WebSocket,
    api_key: Annotated[str | None, Query(description="API key for authentication")] = None,
    history_lines: Annotated[
        int | None, Query(ge=1, le=10000, description="Number of history lines to send on connect")
    ] = None,
    settings: Settings = Depends(get_settings),
    service: ServerService = Depends(get_server_service),
) -> None:
    """WebSocket endpoint for real-time console streaming.

    Connects authenticated Admin users to the console buffer for real-time
    output streaming. On connection, sends recent buffer history then streams
    new lines as they arrive.

    Authentication is via query parameter since WebSocket in browsers cannot
    use custom headers.

    Args:
        websocket: The WebSocket connection
        api_key: Admin API key for authentication (query parameter)
        history_lines: Number of history lines to send on connect (default from settings)
        settings: Application settings (injected via dependency)
        service: Server service for console buffer access (injected via dependency)

    Close Codes:
        4001: Unauthorized - Missing or invalid API key
        4003: Forbidden - Valid key but insufficient role (Monitor, not Admin)
    """
    client_ip = _get_websocket_client_ip(websocket)

    # Verify API key before accepting connection
    role = _verify_api_key_with_settings(api_key, settings.api_key_admin, settings.api_key_monitor)

    if role is None:
        # Log failed auth attempt (key_prefix only, never full key)
        key_info = f"{api_key[:8]}..." if api_key else "none"
        logger.warning(
            "websocket_auth_failed",
            client_ip=client_ip,
            key_prefix=key_info,
            reason="invalid_key",
        )
        # Accept then close with error code (WebSocket protocol requirement)
        await websocket.accept()
        await websocket.close(code=4001, reason="Unauthorized: Invalid API key")
        return

    if role != "admin":
        # Valid key but wrong role
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
