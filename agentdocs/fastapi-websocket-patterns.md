# FastAPI WebSocket Patterns for Console Streaming

This document contains research findings and patterns for implementing WebSocket-based console streaming in Epic 4.

## Authentication via Query Parameters

WebSockets cannot use HTTP headers for authentication in the browser (no `Authorization` header support). The standard pattern is query parameter authentication.

### Pattern: Query Parameter API Key Validation

```python
from fastapi import WebSocket, Query
from starlette.websockets import WebSocketDisconnect

from vintagestory_api.middleware.auth import verify_admin_key

@app.websocket("/api/v1alpha1/console")
async def console_websocket(
    websocket: WebSocket,
    api_key: str = Query(..., description="Admin API key for authentication")
):
    """WebSocket endpoint for console streaming."""
    # Validate BEFORE accepting - more efficient
    if not verify_admin_key(api_key):
        # Accept first to send close frame with reason
        await websocket.accept()
        await websocket.close(code=4003, reason="Forbidden: Invalid API key")
        return

    await websocket.accept()
    try:
        # Connection handling loop
        while True:
            data = await websocket.receive_text()
            # Process command...
    except WebSocketDisconnect:
        # Clean up connection
        pass
```

### WebSocket Close Codes

| Code | Meaning | Use Case |
|------|---------|----------|
| 1000 | Normal closure | Clean disconnect |
| 1008 | Policy violation | Auth/permission error |
| 4003 | Custom: Forbidden | Invalid API key (matches HTTP 403) |
| 4004 | Custom: Not Found | Resource not found |
| 4429 | Custom: Too Many | Rate limiting |

**Note:** Codes 4000-4999 are reserved for application use.

## Connection Lifecycle Management

### Pattern: Connection Manager for Broadcasting

```python
from typing import Set
from fastapi import WebSocket

class ConnectionManager:
    """Manages active WebSocket connections for broadcasting."""

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        """Accept and register a new connection."""
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        """Remove a connection from the active set."""
        self.active_connections.discard(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket) -> None:
        """Send a message to a specific client."""
        await websocket.send_text(message)

    async def broadcast(self, message: str) -> None:
        """Broadcast a message to all connected clients."""
        # Copy set to avoid modification during iteration
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception:
                # Client disconnected, remove from set
                self.active_connections.discard(connection)

# Global manager instance
manager = ConnectionManager()
```

### Pattern: WebSocket Endpoint with Manager

```python
@app.websocket("/api/v1alpha1/console")
async def console_websocket(
    websocket: WebSocket,
    api_key: str = Query(...)
):
    # Authentication
    if not verify_admin_key(api_key):
        await websocket.accept()
        await websocket.close(code=4003, reason="Forbidden")
        return

    await manager.connect(websocket)
    try:
        while True:
            # Receive commands from client
            data = await websocket.receive_text()
            # Process and optionally broadcast
            await manager.broadcast(f"[{timestamp}] {data}")
    except WebSocketDisconnect:
        manager.disconnect(websocket)
```

## Integration with Console Buffer Service

### Pattern: Async Ring Buffer Consumer

The console buffer service will maintain an in-memory ring buffer of console output. WebSocket clients need to:
1. Receive historical buffer content on connect
2. Receive real-time updates as they occur

```python
import asyncio
from collections import deque
from typing import Callable, Awaitable

class ConsoleBuffer:
    """Ring buffer for console output with subscriber support."""

    def __init__(self, max_lines: int = 10000):
        self.buffer: deque[str] = deque(maxlen=max_lines)
        self.subscribers: Set[Callable[[str], Awaitable[None]]] = set()

    async def append(self, line: str) -> None:
        """Add a line and notify all subscribers."""
        timestamped = f"[{datetime.now().isoformat()}] {line}"
        self.buffer.append(timestamped)

        # Notify subscribers
        for callback in list(self.subscribers):
            try:
                await callback(timestamped)
            except Exception:
                self.subscribers.discard(callback)

    def get_history(self) -> list[str]:
        """Get all buffered lines."""
        return list(self.buffer)

    def subscribe(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Subscribe to new lines."""
        self.subscribers.add(callback)

    def unsubscribe(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Unsubscribe from new lines."""
        self.subscribers.discard(callback)

# Global buffer instance
console_buffer = ConsoleBuffer()
```

### Pattern: WebSocket with Buffer Integration

```python
@app.websocket("/api/v1alpha1/console")
async def console_websocket(
    websocket: WebSocket,
    api_key: str = Query(...)
):
    if not verify_admin_key(api_key):
        await websocket.accept()
        await websocket.close(code=4003, reason="Forbidden")
        return

    await websocket.accept()

    # Send historical buffer content first
    for line in console_buffer.get_history():
        await websocket.send_text(line)

    # Create callback for new lines
    async def on_new_line(line: str):
        await websocket.send_text(line)

    console_buffer.subscribe(on_new_line)
    try:
        while True:
            # Receive commands from client
            command = await websocket.receive_text()
            # Send command to game server (via RCON or stdin)
            await send_command_to_server(command)
    except WebSocketDisconnect:
        console_buffer.unsubscribe(on_new_line)
```

## Error Handling and Graceful Disconnection

### Pattern: Robust Connection Handling

```python
from starlette.websockets import WebSocketDisconnect, WebSocketState
import structlog

logger = structlog.get_logger()

@app.websocket("/api/v1alpha1/console")
async def console_websocket(websocket: WebSocket, api_key: str = Query(...)):
    client_ip = websocket.client.host if websocket.client else "unknown"

    # Auth check
    if not verify_admin_key(api_key):
        logger.warning("WebSocket auth failed", client_ip=client_ip, key_prefix=api_key[:8])
        await websocket.accept()
        await websocket.close(code=4003, reason="Forbidden")
        return

    logger.info("WebSocket connected", client_ip=client_ip)
    await manager.connect(websocket)

    try:
        while True:
            try:
                data = await asyncio.wait_for(
                    websocket.receive_text(),
                    timeout=60.0  # Heartbeat timeout
                )
                # Process data...
            except asyncio.TimeoutError:
                # Send ping to check if client is alive
                if websocket.application_state == WebSocketState.CONNECTED:
                    await websocket.send_text('{"type": "ping"}')

    except WebSocketDisconnect as e:
        logger.info("WebSocket disconnected", client_ip=client_ip, code=e.code)
    except Exception as e:
        logger.error("WebSocket error", client_ip=client_ip, error=str(e))
    finally:
        manager.disconnect(websocket)
        logger.info("WebSocket cleanup complete", client_ip=client_ip)
```

## Security Considerations

### 1. Rate Limiting Commands

```python
from datetime import datetime, timedelta

class RateLimiter:
    """Simple per-connection rate limiter."""

    def __init__(self, max_commands: int = 10, window_seconds: int = 1):
        self.max_commands = max_commands
        self.window = timedelta(seconds=window_seconds)
        self.command_times: deque[datetime] = deque()

    def is_allowed(self) -> bool:
        now = datetime.now()
        # Remove old entries
        while self.command_times and (now - self.command_times[0]) > self.window:
            self.command_times.popleft()

        if len(self.command_times) >= self.max_commands:
            return False

        self.command_times.append(now)
        return True
```

### 2. Input Validation

```python
import re

# Maximum command length
MAX_COMMAND_LENGTH = 1000

# Dangerous command patterns to block
BLOCKED_PATTERNS = [
    r"^/op\s+",       # Operator commands
    r"^/deop\s+",
    r"^/stop$",       # Server stop (use API instead)
]

def validate_command(command: str) -> tuple[bool, str]:
    """Validate a console command before execution."""
    if len(command) > MAX_COMMAND_LENGTH:
        return False, "Command too long"

    for pattern in BLOCKED_PATTERNS:
        if re.match(pattern, command, re.IGNORECASE):
            return False, f"Command blocked by security policy"

    return True, ""
```

### 3. Never Log Sensitive Data

```python
# WRONG - logs the API key
logger.warning(f"Auth failed with key: {api_key}")

# CORRECT - logs only prefix
logger.warning("Auth failed", key_prefix=api_key[:8] + "...")
```

## Testing WebSocket Endpoints

### Pattern: pytest-asyncio with httpx

```python
import pytest
from httpx import AsyncClient, ASGITransport
from httpx_ws import aconnect_ws

from vintagestory_api.main import app

@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client

@pytest.mark.asyncio
async def test_websocket_auth_required(client):
    """Test that WebSocket requires authentication."""
    async with aconnect_ws("ws://test/api/v1alpha1/console", client) as ws:
        # Should receive close frame immediately
        message = await ws.receive()
        assert message.type == "websocket.close"
        assert message.code == 4003

@pytest.mark.asyncio
async def test_websocket_echo(client):
    """Test WebSocket with valid auth."""
    async with aconnect_ws(
        "ws://test/api/v1alpha1/console?api_key=valid-admin-key",
        client
    ) as ws:
        await ws.send_text("test command")
        response = await ws.receive_text()
        assert "test command" in response
```

## Frontend Reconnection Pattern

See `xterm-react-patterns.md` for the client-side reconnection implementation.

**Server Consideration:** The server should:
1. Not maintain connection state that requires the same client to reconnect
2. Send full buffer history on each new connection
3. Use stateless command processing

## References

- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)
- [Starlette WebSocket Reference](https://www.starlette.io/websockets/)
- [RFC 6455 - WebSocket Protocol](https://tools.ietf.org/html/rfc6455)
- Project Architecture: `_bmad-output/planning-artifacts/architecture.md`
