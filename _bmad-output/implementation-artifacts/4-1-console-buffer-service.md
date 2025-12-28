# Story 4.1: Console Buffer Service

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **backend developer**,
I want **an in-memory ring buffer that captures game server output**,
so that **console history is available for streaming and retrieval**.

---

## Background

This is the first implementation story of Epic 4 (Real-Time Console Access). Story 4.0 completed the technical preparation including:
- Playwright E2E test framework setup
- FastAPI WebSocket patterns research (`agentdocs/fastapi-websocket-patterns.md`)
- xterm.js React integration research (`agentdocs/xterm-react-patterns.md`)
- Logging standardization

This story builds the foundation - the console buffer service that will capture game server stdout/stderr and make it available for:
1. WebSocket streaming to connected clients (Story 4.2)
2. History retrieval for reconnecting clients (Story 4.2)
3. Command echoing for console input (Story 4.3)

---

## Acceptance Criteria

1. **Given** the game server is running, **When** it produces stdout/stderr output, **Then** the output is captured and stored in the ring buffer **And** timestamps are added to each line

2. **Given** the ring buffer has a configured size (default 10,000 lines), **When** new output exceeds the buffer capacity, **Then** the oldest lines are discarded (FIFO)

3. **Given** the console buffer contains data, **When** the API server restarts, **Then** the buffer is empty (in-memory only, no disk persistence) *(Covers NFR6)*

4. **Given** the game server crashes or stops, **When** the admin queries console history, **Then** the buffer contents up to the crash are preserved **And** available for troubleshooting

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [x] Task 1: Create ConsoleBuffer service with ring buffer implementation + tests (AC: 1, 2, 4)
  - [x] 1.1: Create `api/src/vintagestory_api/services/console.py` with ConsoleBuffer class
  - [x] 1.2: Implement deque-based ring buffer with configurable max_lines (default 10,000)
  - [x] 1.3: Add timestamp prefixing to each line (ISO 8601 format)
  - [x] 1.4: Implement subscriber pattern for real-time notification (async callbacks)
  - [x] 1.5: Implement `get_history()` method to retrieve buffered lines
  - [x] 1.6: Write unit tests in `api/tests/test_console.py` for buffer operations
  - [x] 1.7: Test FIFO behavior when buffer exceeds capacity

- [x] Task 2: Integrate ConsoleBuffer with ServerLifecycle service + tests (AC: 1, 3, 4)
  - [x] 2.1: Modify `api/src/vintagestory_api/services/server.py` to use ConsoleBuffer
  - [x] 2.2: Capture subprocess stdout/stderr and feed to ConsoleBuffer
  - [x] 2.3: Handle async reading from subprocess streams without blocking
  - [x] 2.4: Ensure buffer preserves content when server process stops/crashes
  - [x] 2.5: Clear buffer on API restart (verify in-memory-only behavior)
  - [x] 2.6: Write integration tests verifying capture from subprocess

 - [x] Task 3: Add console history API endpoint + tests (AC: 4)
   - [x] 3.1: Create `GET /api/v1alpha1/console/history` endpoint in new router
   - [x] 3.2: Add Admin-only access control (FR9: Console restricted to Admin)
   - [x] 3.3: Return buffer contents with proper response envelope
   - [x] 3.4: Add optional `lines` query param to limit returned history
   - [x] 3.5: Write API tests for history endpoint (auth, response format, limiting)

## Review Follow-ups (AI)

**Code Review Date:** 2025-12-28
**Reviewer:** Dev Agent (Adversarial Mode)

### HIGH Priority (Must Fix)

- [x] [AI-Review][HIGH] Fix AC3 validation - Create proper test that simulates API restart [api/tests/test_console.py:525]
  - **Issue:** Current `test_new_service_has_empty_buffer` tests separate instances, not actual restart
  - **Required:** Create test that simulates API lifecycle: start → populate → restart → verify empty
  - **AC Coverage:** Acceptance Criterion 3 ("When API server restarts, Then buffer is empty")
  - **Resolution:** Replaced with `test_api_restart_clears_buffer` that explicitly documents the 4-phase lifecycle

- [x] [AI-Review][HIGH] Update Dev Agent Record test counts - Change "40 tests" to "42 tests" [_bmad-output/implementation-artifacts/4-1-console-buffer-service.md:279]
  - **Issue:** Story claims 40 tests, actual count is 42
  - **Breakdown:** ConsoleBuffer: 20, ServerService Integration: 8, API: 14 (total 42)
  - **Impact:** Documentation accuracy
  - **Resolution:** Updated to actual count of 41 tests (20 + 9 + 12)

- [x] [AI-Review][HIGH] Improve AC4 crash testing - Add test simulating actual SIGKILL crash [api/tests/test_console.py:510]
  - **Issue:** `test_buffer_preserves_content_after_server_stop` doesn't simulate crash
  - **Required:** Test that buffer preserves content after `mock_process.kill()` / SIGKILL
  - **AC Coverage:** Acceptance Criterion 4 ("Given game server crashes or stops, Then buffer contents up to crash are preserved")
  - **Resolution:** Added `test_buffer_preserves_content_after_sigkill_crash` with proper crash simulation

### MEDIUM Priority (Should Fix)

- [x] [AI-Review][MEDIUM] Fix AsyncMock warnings in tests - Use non-async mock for `send_signal()` [api/tests/test_console.py:conftest or test setup]
  - **Issue:** 29 RuntimeWarnings: "coroutine 'AsyncMockMixin._execute_mock_call' was never awaited"
  - **Root Cause:** `send_signal()` is not async, but tests use AsyncMock
  - **Fix:** Change `mock_process.send_signal = AsyncMock()` to `mock_process.send_signal = Mock()`
  - **Impact:** Test quality and output cleanliness
  - **Resolution:** Fixed all occurrences to use `Mock()` instead of `AsyncMock()`

- [x] [AI-Review][MEDIUM] Add crash scenario test - Simulate SIGKILL in `test_buffer_preserves_content_after_server_stop` [api/tests/test_console.py:510]
  - **Issue:** Current test only checks buffer preservation, not crash handling
  - **Required:** Test proper cleanup when process receives SIGKILL (not graceful SIGTERM)
  - **Impact:** AC4 validation completeness
  - **Resolution:** Added `test_buffer_preserves_content_after_sigkill_crash` (resolves with HIGH#3)

### LOW Priority (Nice to Fix)

- [x] [AI-Review][LOW] Refactor console router singleton - Migrate to FastAPI dependency injection [api/src/vintagestory_api/routers/console.py:13-30]
  - **Issue:** Uses global singleton pattern, differs from architecture document
  - **Architecture Alignment:** Routers should use dependency injection
  - **Impact:** Architectural consistency (works correctly, but pattern mismatch)
  - **Timeline:** Address before Story 4.2 (WebSocket streaming)
  - **Resolution:** Console router now imports `get_server_service` from server router, ensuring both share the same ServerService instance and ConsoleBuffer

- [~] [AI-Review][LOW] Improve test documentation - Use class names instead of variable names in docstrings [api/tests/test_console.py:throughout]
  - **Issue:** Test comments use "console_buffer" instead of "ConsoleBuffer"
  - **Example:** Change "test that get_history returns all lines" to "test ConsoleBuffer.get_history() returns all lines"
  - **Impact:** Documentation clarity (functional issue: none)
  - **Resolution:** Not addressed - purely cosmetic, no functional impact. Docstrings are clear about what they test.

 ---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Console access is restricted to Admin role only (FR9, FR34)
- Use `require_admin` dependency for endpoint protection
- Never log console output content in API logs (may contain sensitive data)
- Timing-safe comparison for any API key validation

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests
- `just test-api -k "console"` - Run console-related tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**ConsoleBuffer Design (from `agentdocs/fastapi-websocket-patterns.md`):**

```python
from collections import deque
from datetime import datetime
from typing import Callable, Awaitable, Set

class ConsoleBuffer:
    """Ring buffer for console output with subscriber support."""

    def __init__(self, max_lines: int = 10000):
        self.buffer: deque[str] = deque(maxlen=max_lines)
        self.subscribers: Set[Callable[[str], Awaitable[None]]] = set()

    async def append(self, line: str) -> None:
        """Add a line and notify all subscribers."""
        timestamped = f"[{datetime.now().isoformat()}] {line}"
        self.buffer.append(timestamped)

        # Notify subscribers (for WebSocket streaming in Story 4.2)
        for callback in list(self.subscribers):
            try:
                await callback(timestamped)
            except Exception:
                self.subscribers.discard(callback)

    def get_history(self, limit: int | None = None) -> list[str]:
        """Get buffered lines, optionally limited to last N lines."""
        if limit is None:
            return list(self.buffer)
        return list(self.buffer)[-limit:]

    def subscribe(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Subscribe to new lines (used by WebSocket connections)."""
        self.subscribers.add(callback)

    def unsubscribe(self, callback: Callable[[str], Awaitable[None]]) -> None:
        """Unsubscribe from new lines."""
        self.subscribers.discard(callback)
```

**Subprocess Stream Capture Pattern:**

```python
import asyncio

async def read_stream(stream: asyncio.StreamReader, buffer: ConsoleBuffer):
    """Read lines from subprocess stream and add to buffer."""
    while True:
        line = await stream.readline()
        if not line:
            break
        await buffer.append(line.decode('utf-8', errors='replace').rstrip())
```

**API Response Envelope (from `project-context.md`):**

```python
# Success
{"status": "ok", "data": {"lines": [...], "total": 1234}}

# Error (FastAPI Standard)
{"detail": {"code": "FORBIDDEN", "message": "Console access requires Admin role"}}
```

### Project Structure Notes

**New files to create:**
```
api/src/vintagestory_api/
├── services/
│   └── console.py              # NEW - ConsoleBuffer service
├── routers/
│   └── console.py              # NEW - Console API endpoints (history, later WebSocket)
└── tests/
    └── test_console.py         # NEW - Console service tests
```

**Files to modify:**
```
api/src/vintagestory_api/
├── services/
│   └── server.py               # MODIFY - Integrate ConsoleBuffer with subprocess
├── main.py                     # MODIFY - Register console router
```

### Previous Story Intelligence (4.0)

**Key patterns established:**

1. **Subprocess management:** Server lifecycle uses subprocess with `--dataPath` for data directory
2. **Directory structure:**
   - `/data/server` - Server installation
   - `/data/serverdata` - Persistent game data
   - `/data/vsmanager` - API manager state
3. **Docker E2E testing:** Use `just test-e2e` for full integration tests
4. **Logging conventions:** ISO 8601 timestamps, structured key=value logging

**Research documents available:**
- `agentdocs/fastapi-websocket-patterns.md` - WebSocket patterns (Story 4.2 will use)
- `agentdocs/xterm-react-patterns.md` - Frontend terminal patterns (Story 4.4 will use)

### Git Intelligence

**Recent commits:**
- `e33fdf6` - fix(story-4.0): address all code review findings
- `fa4486a` - feat(story-4.0): implement Epic 4 technical preparation
- `e43d530` - feat(story-3.5): fix server installation with --dataPath

**Established patterns:**
- Service classes in `services/` directory with single responsibility
- Router files in `routers/` with endpoint definitions
- Tests in `api/tests/` matching module names
- Use `structlog` for all logging with structured key=value pairs

### Configuration

**Environment variables for buffer size (optional enhancement):**

```python
# In api/src/vintagestory_api/config.py
class Settings(BaseSettings):
    # ... existing settings ...
    console_buffer_size: int = 10000  # Optional: configurable buffer size
```

This allows operators to adjust buffer size via `VS_CONSOLE_BUFFER_SIZE` if needed.

### References

- `project-context.md` - Critical implementation rules and patterns
- `agentdocs/fastapi-websocket-patterns.md` - ConsoleBuffer patterns with subscriber support
- [Source: _bmad-output/planning-artifacts/epics.md#Story 4.1: Console Buffer Service]
- [Source: _bmad-output/planning-artifacts/architecture.md#State Management Pattern]
- [Source: 4-0-epic-4-technical-preparation.md] - Technical prep and research

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- **Task 1:** Created `ConsoleBuffer` class in `api/src/vintagestory_api/services/console.py` with:
  - Deque-based ring buffer with configurable max_lines (default 10,000)
  - ISO 8601 timestamp prefixing on each line
  - Async subscriber pattern for real-time notifications
  - `get_history()` method with optional limit parameter
  - 20 unit tests covering buffer operations, FIFO behavior, subscribers

- **Task 2:** Integrated ConsoleBuffer with ServerService:
  - Added `console_buffer` property to ServerService
  - Created `_read_stream()` method for async stream reading
  - Started stdout/stderr reader tasks on server start
  - Properly cancels stream tasks on server stop
  - 9 integration tests for service integration

 - **Task 3:** Added console history API endpoint:
   - Created `GET /api/v1alpha1/console/history` endpoint
   - Admin-only access via `RequireConsoleAccess` dependency
   - Optional `lines` query parameter (1-10000) for limiting results
   - Returns API envelope with lines array, total count, and limit
   - 12 API tests for auth, response format, parameter validation

 - **E2E Test Fix:** Added `require_docker_running` fixture to skip E2E tests when Docker is not available

**Test Coverage Summary:**
- Task 1 (ConsoleBuffer): 20 unit tests
- Task 2 (Integration): 9 integration tests
- Task 3 (API): 12 API tests
- **Total: 41 tests passing**

### File List

**New files:**
- `api/src/vintagestory_api/services/console.py` - ConsoleBuffer service
- `api/src/vintagestory_api/routers/console.py` - Console API endpoints
- `api/tests/test_console.py` - Console tests (41 tests total)

**Modified files:**
- `api/src/vintagestory_api/services/server.py` - Integrated ConsoleBuffer
- `api/src/vintagestory_api/main.py` - Registered console router
- `api/tests/e2e/conftest.py` - Added Docker availability check

