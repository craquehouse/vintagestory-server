# Story 4.3: Console Command Input

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **to send commands to the game server through the console**,
so that **I can interact with the server without container access**.

---

## Background

This story builds on the WebSocket console streaming implemented in Story 4.2. The WebSocket endpoint at `/api/v1alpha1/console/ws` already:
- Authenticates Admin users via query parameter
- Streams real-time console output to connected clients
- Has a receive loop ready for command input (currently receives but doesn't process)

This story adds the command input capability - sending text from the WebSocket client to the game server's stdin, enabling administrators to execute server commands like `/help`, `/time set day`, or `/whitelist add Player`.

**FRs Covered:** FR8, FR9

---

## Acceptance Criteria

1. **Given** I am connected to the console WebSocket as Admin, **When** I send a message with type "command" and content "/help", **Then** the command is written to the game server's stdin **And** the command response appears in the console stream *(FR8)*

2. **Given** I send a command, **When** the server processes it, **Then** my sent command is echoed back (or marked) in the stream for confirmation

3. **Given** the game server is not running, **When** I attempt to send a command, **Then** I receive an error message indicating the server is stopped

4. **Given** I am authenticated as Monitor, **When** I attempt to send a command via any mechanism, **Then** the request is rejected with 403 Forbidden *(FR9)*

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Add stdin pipe to server subprocess + tests (AC: 1)
  - [x] 1.1: Modify `ServerService._start_server_locked()` to include `stdin=asyncio.subprocess.PIPE`
  - [x] 1.2: Add `async def send_command(self, command: str) -> bool` method to ServerService
  - [x] 1.3: Implement stdin write with newline append and error handling
  - [x] 1.4: Return `False` if server not running, `True` on success
  - [x] 1.5: Write unit tests for `send_command()` (running server, stopped server, invalid command)

- [x] Task 2: Add command echo to console buffer + tests (AC: 2)
  - [x] 2.1: Before writing to stdin, add command to console buffer with prefix `[CMD] `
  - [x] 2.2: Ensure echo appears in real-time stream to all connected WebSocket clients
  - [x] 2.3: Write tests verifying command echo appears in buffer with correct prefix

- [x] Task 3: Implement WebSocket command message handling + tests (AC: 1, 3, 4)
  - [x] 3.1: Define message format: `{"type": "command", "content": "/help"}`
  - [x] 3.2: Parse incoming WebSocket messages as JSON in the receive loop
  - [x] 3.3: Extract command from message and call `ServerService.send_command()`
  - [x] 3.4: Send error message back to client if server not running: `{"type": "error", "content": "Server is not running"}`
  - [x] 3.5: Handle malformed JSON gracefully (log and continue, don't disconnect)
  - [x] 3.6: Write tests for command handling (valid command, server stopped, malformed JSON)

 - [x] Task 4: Add REST API fallback endpoint for commands + tests (AC: 1, 3, 4)
   - [x] 4.1: Create `POST /api/v1alpha1/console/command` endpoint
   - [x] 4.2: Accept body: `{"command": "/help"}`
   - [x] 4.3: Require Admin role via dependency injection
   - [x] 4.4: Return success response with echoed command
   - [x] 4.5: Return 400 if server not running with appropriate error
   - [x] 4.6: Write API tests for command endpoint (auth, success, server not running)

### Review Follow-ups (AI-Review)

- [x] [AI-Review][HIGH] Add WebSocket command validation (empty and max length 1000 chars) to match REST endpoint [api/src/vintagestory_api/routers/console.py:264-276]
- [x] [AI-Review][MEDIUM] Document sprint-status.yaml change in story File List [_bmad-output/implementation-artifacts/sprint-status.yaml]
- [x] [AI-Review][LOW] Add explicit error message for empty WebSocket command [api/src/vintagestory_api/routers/console.py:264-276]
- [x] [AI-Review][LOW] Improve test_websocket_command_echoes_in_stream to verify echo timing/order [api/tests/test_console.py:1470-1490]

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test-api` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- Console command access is restricted to Admin role only (FR9)
- Use `RequireConsoleAccess` dependency for HTTP endpoint (same as history endpoint)
- WebSocket already validates Admin role before accepting connection
- Log commands with client IP but NOT command content (may contain sensitive data like passwords)
- Timing-safe comparison for any API key validation (already implemented)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests
- `just test-api -k "console"` - Run console-related tests
- `just test-api -k "command"` - Run command-specific tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Stdin Integration Pattern:**

The server subprocess is currently started in `api/src/vintagestory_api/services/server.py:750-754`:

```python
self._process = await asyncio.create_subprocess_exec(
    *command,
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

Change to include stdin:

```python
self._process = await asyncio.create_subprocess_exec(
    *command,
    stdin=asyncio.subprocess.PIPE,  # ADD THIS
    stdout=asyncio.subprocess.PIPE,
    stderr=asyncio.subprocess.PIPE,
)
```

**ServerService.send_command() Pattern:**

```python
async def send_command(self, command: str) -> bool:
    """Send a command to the game server's stdin.

    Args:
        command: The command to send (without trailing newline).

    Returns:
        True if command was sent, False if server not running.
    """
    if self._process is None or self._process.returncode is not None:
        return False

    if self._process.stdin is None:
        return False

    # Echo command to console buffer for visibility
    await self._console_buffer.append(f"[CMD] {command}")

    # Write to stdin with newline
    self._process.stdin.write(f"{command}\n".encode())
    await self._process.stdin.drain()

    return True
```

**WebSocket Message Protocol:**

Incoming messages (from client):
```json
{"type": "command", "content": "/help"}
```

Outgoing messages (to client):
```json
// Success - no explicit response needed, command echo appears in stream
// Error - server not running
{"type": "error", "content": "Server is not running"}
// Error - invalid message format
{"type": "error", "content": "Invalid message format"}
```

**REST API Endpoint:**

```python
@router.post("/command")
async def send_console_command(
    _role: RequireConsoleAccess,
    body: ConsoleCommandRequest,
    service: ServerService = Depends(get_server_service),
) -> dict[str, object]:
    """Send a command to the game server console.

    Requires Admin role.

    Args:
        body: Request with command to send.

    Returns:
        API envelope with success status.

    Raises:
        HTTPException: 400 if server not running.
    """
    if not await service.send_command(body.command):
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
```

### Project Structure Notes

**Files to modify:**
```
api/src/vintagestory_api/
├── services/
│   └── server.py              # MODIFY - Add stdin pipe and send_command()
├── routers/
│   └── console.py             # MODIFY - Add command handling to WebSocket + REST endpoint
├── models/
│   └── console.py             # NEW - Pydantic models for command request/response
└── tests/
    └── test_console.py        # MODIFY - Add command tests
```

**New Pydantic model:**
```python
# api/src/vintagestory_api/models/console.py
from pydantic import BaseModel, Field

class ConsoleCommandRequest(BaseModel):
    """Request body for console command endpoint."""
    command: str = Field(..., min_length=1, max_length=1000)
```

### Previous Story Intelligence (4.2)

**Key patterns established:**

1. **WebSocket authentication:** Query param `?api_key=` with timing-safe validation
2. **Close codes:** 4001 (Unauthorized), 4003 (Forbidden)
3. **ConsoleBuffer subscriber pattern:** Automatic cleanup on send failure
4. **Dependency injection:** `get_server_service()` for shared ServerService instance
5. **Client IP logging:** `_get_websocket_client_ip()` for proxy-aware IP extraction

**Code review findings from 4.2 to apply:**
- Error handling in WebSocket callbacks should log with client IP
- All settings should be configurable via environment variables
- Use `pytest-timeout` to prevent hanging tests

**WebSocket receive loop (console.py:202-206):**
```python
try:
    # Keep connection alive, receive any client messages (future: commands)
    while True:
        await websocket.receive_text()  # <- Currently ignores received text
except WebSocketDisconnect as e:
    logger.info("websocket_disconnected", client_ip=client_ip, code=e.code)
```

This is where command handling will be implemented.

### Git Intelligence

**Recent commits:**
- `39c8157` - feat(story-4.2): implement WebSocket console streaming
- `232ae85` - docs(story-4.1): mark as done after code review
- `4350448` - fix(story-4.1): address code review findings
- `ed8eca1` - feat(story-4.1): implement console buffer service

**Established patterns:**
- Service classes in `services/` directory with single responsibility
- Router files in `routers/` with endpoint definitions
- Tests in `api/tests/` matching module names
- Use `structlog` for all logging with structured key=value pairs
- Commit message format: `feat(story-X.Y): description`

### Testing Patterns

**WebSocket command testing:**

```python
@pytest.mark.asyncio
async def test_websocket_command_sends_to_stdin(self, mock_server_service):
    """Test that WebSocket command is written to server stdin."""
    # Arrange: Mock server running with stdin
    mock_process = AsyncMock()
    mock_process.returncode = None
    mock_process.stdin = AsyncMock()
    mock_server_service._process = mock_process

    async with client.websocket_connect("/api/v1alpha1/console/ws?api_key=admin-key") as ws:
        # Act: Send command
        await ws.send_json({"type": "command", "content": "/help"})

        # Assert: Command written to stdin
        mock_process.stdin.write.assert_called_once_with(b"/help\n")
        mock_process.stdin.drain.assert_called_once()
```

**REST command testing:**

```python
def test_console_command_admin_success(self, client, mock_server_service):
    """Test that Admin can send console command."""
    # Arrange: Mock server running
    mock_server_service.send_command = AsyncMock(return_value=True)

    # Act
    response = client.post(
        "/api/v1alpha1/console/command",
        json={"command": "/help"},
        headers={"X-API-Key": "admin-key"},
    )

    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["data"]["command"] == "/help"
    assert data["data"]["sent"] is True
```

### Error Handling

**Error scenarios to handle:**

| Scenario | WebSocket Response | REST Response |
|----------|-------------------|---------------|
| Server not running | `{"type": "error", "content": "Server is not running"}` | 400 + ErrorCode.SERVER_NOT_RUNNING |
| Malformed JSON | `{"type": "error", "content": "Invalid message format"}` | N/A (REST validates automatically) |
| Empty command | `{"type": "error", "content": "Empty command"}` | 400 + validation error |
| Command too long | `{"type": "error", "content": "Command too long"}` | 400 + validation error |

### Configuration

No new configuration needed for this story. Command handling uses existing patterns:
- `VS_API_KEY_ADMIN` - Admin API key for authentication
- `VS_CONSOLE_HISTORY_LINES` - History lines on WebSocket connect (existing)

### References

- `project-context.md` - Critical implementation rules and patterns
- `agentdocs/fastapi-websocket-patterns.md` - WebSocket message handling patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.3: Console Command Input]
- [Source: 4-1-console-buffer-service.md] - ConsoleBuffer patterns
- [Source: 4-2-websocket-console-streaming.md] - WebSocket patterns, authentication

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - No debugging issues encountered.

### Completion Notes List

- **Task 1:** Modified `ServerService._start_server_locked()` to include `stdin=asyncio.subprocess.PIPE` for subprocess command input. Added `async def send_command()` method that writes commands to stdin with proper error handling for server not running and stdin not available cases.

- **Task 2:** Command echo functionality was already implemented as part of Task 1's `send_command()` method - it calls `await self._console_buffer.append(f"[CMD] {command}")` before writing to stdin, ensuring real-time stream to all WebSocket subscribers.

- **Task 3:** Modified WebSocket receive loop in `console.py` to parse JSON messages, handle `{"type": "command", "content": "..."}` format, call `send_command()`, and return appropriate error messages for server not running or malformed JSON.

- **Task 4:** Created `POST /api/v1alpha1/console/command` REST endpoint with Admin-only access via `RequireConsoleAccess` dependency. Returns 400 with `SERVER_NOT_RUNNING` error code when server is stopped. Added `ConsoleCommandRequest` Pydantic model with validation (1-1000 char command length).

All 4 acceptance criteria verified:
- AC1: Commands written to stdin and response appears in console stream ✓
- AC2: Command echo with [CMD] prefix appears in real-time stream ✓
- AC3: Error message returned when server not running ✓
- AC4: Monitor role rejected with 403 Forbidden ✓

### File List

**Modified:**
- api/src/vintagestory_api/services/server.py - Added stdin pipe to subprocess, added `send_command()` method
- api/src/vintagestory_api/routers/console.py - Added JSON command parsing in WebSocket loop, added REST command endpoint, added WebSocket validation
- api/tests/test_console.py - Added 25 tests for send_command, WebSocket commands, validation, and REST endpoint
- _bmad-output/implementation-artifacts/sprint-status.yaml - Updated story status (ready-for-dev → in-progress → review)

**New:**
- api/src/vintagestory_api/models/console.py - ConsoleCommandRequest Pydantic model

