# Story 3.2: Server Lifecycle Control API

Status: ready-for-review

---

## Story

As an **administrator**,
I want **to start, stop, and restart the game server via API**,
so that **I can control the server without container access**.

---

## Acceptance Criteria

1. **Given** a server is installed and stopped, **When** I call `POST /api/v1alpha1/server/start`, **Then** the game server process starts, **And** the response confirms the action was initiated *(Covers FR2)*

2. **Given** a server is running, **When** I call `POST /api/v1alpha1/server/stop`, **Then** the game server receives a graceful shutdown signal, **And** the process terminates cleanly, **And** the response confirms the action was initiated *(Covers FR3)*

3. **Given** a server is running, **When** I call `POST /api/v1alpha1/server/restart`, **Then** the server stops gracefully and starts again, **And** the response confirms the restart was initiated *(Covers FR4)*

4. **Given** no server is installed, **When** I attempt to start/stop/restart, **Then** I receive a 400 Bad Request indicating no server is installed

5. **Given** the server process crashes unexpectedly, **When** the API detects the crash, **Then** the server status updates to "stopped" with exit code information, **And** the API remains available and responsive *(Covers NFR8, NFR9)*

---

## Tasks / Subtasks

- [x] Task 1: Extend ServerService with process management + tests (AC: 1, 2, 5)
  - [x] 1.1: Add `asyncio.subprocess` management to `ServerService` class
  - [x] 1.2: Implement `start_server()` - spawns dotnet process as background subprocess
  - [x] 1.3: Implement `stop_server()` - sends SIGTERM for graceful shutdown, SIGKILL after timeout
  - [x] 1.4: Implement process monitoring task that detects crashes and updates state
  - [x] 1.5: Add server state enum values: `starting`, `running`, `stopping`
  - [x] 1.6: Write tests for start, stop, and crash detection with mocked subprocess

- [x] Task 2: Implement server restart functionality + tests (AC: 3)
  - [x] 2.1: Implement `restart_server()` that calls stop then start in sequence
  - [x] 2.2: Add timeout handling for graceful shutdown (10s default, then SIGKILL)
  - [x] 2.3: Write tests for restart including partial failure scenarios

- [x] Task 3: Create lifecycle control API endpoints + tests (AC: 1-4)
  - [x] 3.1: Add `POST /api/v1alpha1/server/start` endpoint
  - [x] 3.2: Add `POST /api/v1alpha1/server/stop` endpoint
  - [x] 3.3: Add `POST /api/v1alpha1/server/restart` endpoint
  - [x] 3.4: Add proper error responses (400 for not installed, 409 for already in target state)
  - [x] 3.5: Add Admin role requirement for all control endpoints
  - [x] 3.6: Write integration tests for all endpoints

- [x] Task 4: Implement exit code tracking and crash recovery + tests (AC: 5)
  - [x] 4.1: Store last exit code when process terminates
  - [x] 4.2: Add exit code to status response when server is stopped
  - [x] 4.3: Ensure API remains responsive when game server crashes
   - [x] 4.4: Write tests for crash scenarios and API resilience

  ### Review Follow-ups (AI)

   Action items from code review (2025-12-27):

   - [x] [AI-Review][HIGH] Add comprehensive error handling to /restart endpoint - handle SERVER_NOT_RUNNING, SERVER_ALREADY_RUNNING, SERVER_START_FAILED, SERVER_STOP_FAILED [api/src/vintagestory_api/routers/server.py:285-302]
   - [x] [AI-Review][HIGH] Add tests for restart partial failure scenarios - restart when stop fails, restart when start fails after stop, restart during transitional states [api/tests/test_server.py]
   - [x] [AI-Review][MEDIUM] Add test for restart when server in STARTING state - verify graceful handling [api/tests/test_server.py]
   - [x] [AI-Review][MEDIUM] Add test for restart with graceful shutdown timeout - verify SIGKILL behavior in restart context [api/tests/test_server.py]
   - [x] [AI-Review][LOW] Update /restart endpoint docstring to match actual error behavior - document 409 and 500 cases [api/src/vintagestory_api/routers/server.py:258-273]
   - [x] [AI-Review][LOW] Add test for restart when server in ERROR state - verify behavior after failed operation [api/tests/test_server.py]
   - [x] [AI-Review][LOW] Improve type annotation for _process state tracking - added documentation for process state invariants [api/src/vintagestory_api/services/server.py:68]

  ---

  ## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- DEBUG mode gating for test/dev endpoints
- Timing-safe comparison for sensitive data (API keys, passwords)
- Never log sensitive data in plaintext
- Proxy-aware client IP logging
- RBAC patterns for endpoint protection

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Extend Existing ServerService:**

The `ServerService` class already exists at `api/src/vintagestory_api/services/server.py` with:
- Installation logic (download, extract, verify)
- Version tracking via `current_version` file
- State management with `ServerState` enum (NOT_INSTALLED, INSTALLING, INSTALLED, ERROR)
- HTTP client for VintageStory API calls

**Add New Responsibilities:**
- Process spawning and lifecycle management
- Background process monitoring
- Graceful shutdown with timeout

**Server Process State Machine:**

```
        ┌─────────────────┐
        │    INSTALLED    │◀────────────────────┐
        │    (stopped)    │                     │
        └───────┬─────────┘                     │
                │ start()                       │
                ▼                               │
        ┌─────────────────┐                     │
        │    STARTING     │                     │
        └───────┬─────────┘                     │
                │ process ready                 │
                ▼                               │
        ┌─────────────────┐                     │
        │    RUNNING      │                     │
        └───────┬─────────┘                     │
                │ stop() or crash               │
                ▼                               │
        ┌─────────────────┐                     │
        │    STOPPING     │─────────────────────┘
        └─────────────────┘
```

**VintageStory Server Execution:**

```python
# Command to run server (per agentdocs/server-installation.md)
command = [
    "dotnet",
    str(settings.server_dir / "VintagestoryServer.dll"),
    "--dataPath", str(settings.data_dir),
]
```

**Subprocess Management Pattern:**

```python
import asyncio
import signal

class ServerService:
    _process: asyncio.subprocess.Process | None = None
    _monitor_task: asyncio.Task | None = None

    async def start_server(self) -> None:
        """Start the game server subprocess."""
        self._process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        # Start background monitoring
        self._monitor_task = asyncio.create_task(self._monitor_process())

    async def stop_server(self, timeout: float = 10.0) -> None:
        """Stop server gracefully, force kill after timeout."""
        if self._process is None:
            return

        self._process.send_signal(signal.SIGTERM)
        try:
            await asyncio.wait_for(self._process.wait(), timeout=timeout)
        except asyncio.TimeoutError:
            self._process.kill()
            await self._process.wait()

    async def _monitor_process(self) -> None:
        """Background task to detect crashes."""
        if self._process:
            returncode = await self._process.wait()
            self._last_exit_code = returncode
            self._server_status = ServerState.STOPPED
```

**Graceful Shutdown Timeout:**

- Default: 10 seconds
- Send SIGTERM first (allows VintageStory to save world state)
- SIGKILL after timeout if process doesn't exit

**Exit Code Handling:**

```python
# Common exit codes
EXIT_SUCCESS = 0
EXIT_SIGTERM = -15  # Killed by SIGTERM
EXIT_SIGKILL = -9   # Killed by SIGKILL
# Any other non-zero = crash/error
```

### Pydantic Models to Extend

```python
# api/src/vintagestory_api/models/server.py

class ServerState(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"  # Server installed but stopped
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"

class LifecycleAction(str, Enum):
    START = "start"
    STOP = "stop"
    RESTART = "restart"

class LifecycleResponse(BaseModel):
    status: str  # "ok" or "error"
    action: LifecycleAction
    previous_state: ServerState
    new_state: ServerState
    message: str | None = None

class ServerStatus(BaseModel):
    state: ServerState
    version: str | None = None
    uptime_seconds: int | None = None  # If running
    last_exit_code: int | None = None  # If stopped after running
```

### Error Codes to Add

```python
# api/src/vintagestory_api/models/errors.py
class ErrorCode:
    # ... existing codes from Story 3.1 ...
    SERVER_NOT_INSTALLED = "SERVER_NOT_INSTALLED"
    SERVER_ALREADY_RUNNING = "SERVER_ALREADY_RUNNING"
    SERVER_NOT_RUNNING = "SERVER_NOT_RUNNING"
    SERVER_START_FAILED = "SERVER_START_FAILED"
    SERVER_STOP_FAILED = "SERVER_STOP_FAILED"
```

### API Endpoints to Add

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| POST | `/api/v1alpha1/server/start` | Admin | Start the game server |
| POST | `/api/v1alpha1/server/stop` | Admin | Stop the game server gracefully |
| POST | `/api/v1alpha1/server/restart` | Admin | Restart the game server |

**Response Format:**

```json
// POST /api/v1alpha1/server/start (success)
{
  "status": "ok",
  "data": {
    "action": "start",
    "previous_state": "installed",
    "new_state": "starting",
    "message": "Server start initiated"
  }
}

// POST /api/v1alpha1/server/start (error - not installed)
{
  "detail": {
    "code": "SERVER_NOT_INSTALLED",
    "message": "No server is installed. Install a server version first."
  }
}
```

### Project Structure Notes

**Files to modify:**

- `api/src/vintagestory_api/services/server.py` - Add lifecycle methods
- `api/src/vintagestory_api/routers/server.py` - Add lifecycle endpoints
- `api/src/vintagestory_api/models/server.py` - Add lifecycle models
- `api/src/vintagestory_api/models/errors.py` - Add lifecycle error codes
- `api/tests/test_server.py` - Add lifecycle tests

**DO NOT create new files** - extend existing server module.

### Previous Story Intelligence

**From Story 3.1 (Server Installation Service):**
- `ServerService` class exists with installation logic
- `ServerState` enum has: NOT_INSTALLED, INSTALLING, INSTALLED, ERROR
- Version tracking via `current_version` file at `/data/server/current_version`
- `is_installed()` checks for VintagestoryServer.dll and VintagestoryLib.dll
- Uses `asyncio.Lock` for race condition protection (pattern to reuse)
- Tests use `respx` for mocking HTTP and temp directories for file operations
- Error tracking: Added `error_code` field for machine-readable errors in async operations

**Key learnings from 3.1:**
- Pydantic returns 422 for validation errors (not 400)
- Background tasks can't raise HTTPException - use error_code field for status polling
- Use `filter="tar"` for tarfile extraction (security pattern)
- Path traversal protection via `_safe_path()` method

**Established patterns to follow:**
- Atomic writes for state persistence
- Structured logging with structlog
- Error responses use FastAPI's `detail` pattern

### Testing Patterns

**Mock subprocess for lifecycle tests:**

```python
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

@pytest.fixture
def mock_subprocess():
    """Mock asyncio.subprocess for testing."""
    with patch("asyncio.create_subprocess_exec") as mock:
        process = AsyncMock()
        process.pid = 12345
        process.returncode = None
        process.wait = AsyncMock(return_value=0)
        process.send_signal = MagicMock()
        process.kill = MagicMock()
        mock.return_value = process
        yield mock, process

async def test_start_server_spawns_process(server_service, mock_subprocess):
    mock_exec, mock_process = mock_subprocess
    await server_service.start_server()

    mock_exec.assert_called_once()
    assert "dotnet" in mock_exec.call_args[0]
    assert "VintagestoryServer.dll" in str(mock_exec.call_args[0])
```

**Test crash detection:**

```python
async def test_crash_detected_and_state_updated(server_service, mock_subprocess):
    mock_exec, mock_process = mock_subprocess
    mock_process.wait = AsyncMock(return_value=1)  # Non-zero = crash

    await server_service.start_server()
    # Let monitor task run
    await asyncio.sleep(0.1)

    status = server_service.get_status()
    assert status.state == ServerState.INSTALLED  # Stopped after crash
    assert status.last_exit_code == 1
```

### NFR Compliance Notes

**NFR8 (API survives crashes):**
- Game server runs as subprocess, not in main process
- API continues to handle requests if game crashes
- Monitor task updates state on process exit

**NFR9 (Graceful crash recovery):**
- Detect unexpected process termination
- Update state to reflect stopped status
- Store exit code for debugging
- Allow restart after crash

### References

- `project-context.md` - Critical implementation rules and patterns
- `agentdocs/server-installation.md` - Server execution command (`dotnet VintagestoryServer.dll`)
- [Source: _bmad-output/planning-artifacts/architecture.md#Container Strategy Decision]
- [Source: _bmad-output/planning-artifacts/architecture.md#Service Boundaries]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.2]
- `api/src/vintagestory_api/services/server.py` - Existing ServerService class (Story 3.1)

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Extended `ServerState` enum with `STARTING`, `RUNNING`, `STOPPING` values
- Added `LifecycleAction`, `LifecycleResponse`, and `ServerStatus` Pydantic models
- Added new error codes: `SERVER_START_FAILED`, `SERVER_STOP_FAILED`, `SERVER_ALREADY_STOPPED`
- Implemented `ServerService` lifecycle methods:
  - `start_server()` - spawns dotnet subprocess, starts background monitor
  - `stop_server()` - SIGTERM with 10s timeout, then SIGKILL
  - `restart_server()` - stop then start in sequence
  - `get_server_status()` - returns current state, version, uptime, exit code
  - `_monitor_process()` - background task for crash detection
- Added `asyncio.Lock` (`_lifecycle_lock`) for thread-safe lifecycle operations
- Created three new API endpoints:
  - `POST /api/v1alpha1/server/start` - Admin role required
  - `POST /api/v1alpha1/server/stop` - Admin role required
  - `POST /api/v1alpha1/server/restart` - Admin role required
- All endpoints return proper error responses (400, 409, 500) for edge cases
- 227 tests pass (added 49 new lifecycle tests total)
- All type checks and linting pass

**Review Follow-up Work (2025-12-27):**
- Added comprehensive error handling to /restart endpoint for SERVER_STOP_FAILED and SERVER_START_FAILED
- Added 7 new tests for restart partial failure scenarios:
  - test_restart_fails_when_stop_fails
  - test_restart_fails_when_start_fails_after_stop
  - test_restart_from_starting_state
  - test_restart_with_graceful_shutdown_timeout
  - test_restart_from_error_state
  - test_restart_stop_failed_returns_500 (API endpoint test)
  - test_restart_start_failed_returns_500 (API endpoint test)
- Updated /restart endpoint docstring to document 500 error cases
- Added documentation for process state invariants in ServerService.__init__

### File List

- `api/src/vintagestory_api/models/server.py` - Added ServerState enum values, LifecycleAction, LifecycleResponse, ServerStatus models
- `api/src/vintagestory_api/models/errors.py` - Added SERVER_START_FAILED, SERVER_STOP_FAILED, SERVER_ALREADY_STOPPED error codes
- `api/src/vintagestory_api/services/server.py` - Extended ServerService with process lifecycle management
- `api/src/vintagestory_api/routers/server.py` - Added start, stop, restart API endpoints
- `api/tests/test_server.py` - Added lifecycle tests (42 new tests)
