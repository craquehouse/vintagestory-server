# Story 9.4: Debug Logging Infrastructure

Status: complete

## Story

As a **developer or operator**,
I want **comprehensive debug logging throughout the API**,
So that **I can troubleshoot issues with detailed request tracing**.

## Acceptance Criteria

1. **Given** `VS_DEBUG=true` is set
   **When** API requests are processed
   **Then** debug-level logs are emitted for each service layer (router → service → repository)
   *(Covers FR47)*

2. **Given** `VS_DEBUG` is changed at runtime
   **When** the environment variable is updated
   **Then** debug logging is enabled/disabled without server restart
   *(Covers FR48)*

3. **Given** debug logging is enabled
   **When** a request is processed
   **Then** all log entries include a correlation ID (`request_id`) for tracing
   **And** the correlation ID is consistent across all logs for that request
   *(Covers FR49)*

4. **Given** debug logging is disabled (default)
   **When** requests are processed
   **Then** only info, warning, and error logs are emitted

## Tasks / Subtasks

- [x] Task 1: Implement request ID middleware + tests (AC: 3)
  - [x] Subtask 1.1: Create `middleware/request_context.py` with middleware that generates UUID request_id
  - [x] Subtask 1.2: Use `structlog.contextvars.bind_contextvars()` to bind request_id per-request
  - [x] Subtask 1.3: Add `structlog.contextvars.clear_contextvars()` at request start
  - [x] Subtask 1.4: Write tests verifying request_id appears in all log entries for a request

 - [x] Task 2: Update configure_logging with merge_contextvars + tests (AC: 3)
  - [x] Subtask 2.1: Add `structlog.contextvars.merge_contextvars` as first processor
  - [x] Subtask 2.2: Update config.py to include merge_contextvars in processor chain
  - [x] Subtask 2.3: Write tests verifying context vars are merged into log output

- [x] Task 3: Add debug logging to key services + tests (AC: 1, 4)
  - [x] Subtask 3.1: Add debug logs to `ModService` methods (install, enable, disable, remove)
  - [x] Subtask 3.2: Add debug logs to `ServerService` methods (start, stop, restart, install)
  - [x] Subtask 3.3: Add debug logs to `ConsoleService` methods (command execution, buffer operations)
  - [x] Subtask 3.4: Verify DEBUG level logs only appear when VS_DEBUG=true

- [x] Task 4: Implement runtime log level check + tests (AC: 2)
  - [x] Subtask 4.1: Research structlog runtime reconfiguration options
  - [x] Subtask 4.2: Implement periodic or per-request check of VS_DEBUG env var
  - [x] Subtask 4.3: Document approach in Technical Notes (hot-reload vs periodic check)
  - [x] Subtask 4.4: Write tests for runtime debug toggle behavior

- [x] Task 5: Review Follow-ups (AI-Review)
  - [x] [HIGH Priority]: Add debug logs to router layer endpoints
  - [x] [MEDIUM Priority]: Update File List to include all changed files
  - [x] [MEDIUM Priority]: Standardize test fixtures in test_config.py to use consistent structlog configuration

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Never log sensitive data (API keys, passwords, tokens) in debug logs
- Mask or truncate sensitive fields when logging request context
- Log key prefixes only: `api_key[:8] + "..."`

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint-api` - Run linter on API code

### Architecture & Patterns

**Existing Logging Configuration (from config.py:192-244):**
- `configure_logging(debug, log_level)` - Configures structlog processors
- Dev mode: `ConsoleRenderer()` - colorful, human-readable
- Prod mode: `JSONRenderer()` - machine-parseable JSON
- Common processors: `TimeStamper(fmt="iso")`, `add_log_level`

**Adding Request Context (structlog.contextvars pattern):**
```python
# In middleware (runs first for each request)
import structlog
from structlog.contextvars import clear_contextvars, bind_contextvars

async def request_context_middleware(request, call_next):
    clear_contextvars()  # Clear any stale context
    request_id = str(uuid.uuid4())
    bind_contextvars(request_id=request_id)  # Available to all loggers in this request
    return await call_next(request)

# In configure_logging - add merge_contextvars as FIRST processor
structlog.configure(
    processors=[
        structlog.contextvars.merge_contextvars,  # MUST be first
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        # ... rest of processors
    ],
)
```

**Debug Log Placement Guidelines:**
- Router layer: Log request entry/exit with request_id
- Service layer: Log method entry with parameters, exit with result summary
- Error handling: Log exception type and message (not full stack trace in debug)
- External calls: Log before/after httpx calls with timing

**Runtime Debug Toggle Options:**
1. **Per-request check** - Check `os.environ.get("VS_DEBUG")` in middleware (simple, slight overhead)
2. **Periodic reconfigure** - Background task reconfigures structlog every N seconds (complex)
3. **Signal handler** - SIGUSR1 triggers reconfiguration (Linux only)
4. **Endpoint** - `POST /api/v1alpha1/debug` to toggle (requires auth, most flexible)

Recommendation: Per-request check in middleware is simplest and sufficient for dev/debug use cases.

### Previous Story Intelligence (9-3)

**Code Review Findings Applied:**
- [x] Ensure log event tests verify actual log content (add TestLogging pattern)
- [x] Don't defer APScheduler type suppressions - document inline if adding new ones

**Pattern Established:**
- Use `logger = structlog.get_logger()` at module level
- Log events with snake_case names: `cache_evicted`, `request_started`
- Include relevant context as key=value pairs

### Project Structure Notes

**Files to Create/Modify:**
- **NEW:** `api/src/vintagestory_api/middleware/request_context.py` - Request ID middleware
- **MODIFY:** `api/src/vintagestory_api/config.py` - Add merge_contextvars processor
- **MODIFY:** `api/src/vintagestory_api/main.py` - Register middleware
- **MODIFY:** `api/src/vintagestory_api/services/mods.py` - Add debug logs
- **MODIFY:** `api/src/vintagestory_api/services/server.py` - Add debug logs
- **MODIFY:** `api/src/vintagestory_api/services/console.py` - Add debug logs
- **NEW:** `api/tests/test_request_context.py` - Middleware tests
- **MODIFY:** `api/tests/test_config.py` - Logging configuration tests

**Alignment with Existing Patterns:**
- Middleware goes in `middleware/` directory (existing: `auth.py`, `permissions.py`)
- Service logging pattern established in `cache_eviction.py`
- Test files in `api/tests/` with `test_` prefix

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Logging framework decision (structlog)
- `api/src/vintagestory_api/config.py:192-244` - Current configure_logging implementation
- `api/src/vintagestory_api/services/cache_eviction.py` - Example of structured logging
- [Source: epics.md#Story-9.4] - Story requirements (FR47, FR48, FR49)

### Technical Constraints

**FR48 Implementation Note:**
"Debug logging enabled/disabled without server restart" requires runtime environment checking.
Structlog's `cache_logger_on_first_use=True` (current setting) caches logger configuration.
For true runtime toggle:
- Either set `cache_logger_on_first_use=False` (slight performance impact)
- Or implement periodic reconfiguration
- Or check env var in a custom processor

Document the chosen approach in completion notes.

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created RequestContextMiddleware that generates UUID4 request_id per request, binds to structlog contextvars, and clears context at request start. Registered middleware in main.py. Added 5 tests verifying request_id generation, consistency across logs, uniqueness per request, and context isolation.
- Task 2: Added merge_contextvars as first processor in configure_logging() for both debug and production modes. This ensures all context vars (request_id, etc.) appear in every log entry. Added 5 tests for context var merging behavior.
- Task 3: Added entry-level debug logs to ModService (enable, disable, remove, install), ServerService (start, stop, restart, install), and ConsoleBuffer (append, get_history). Added test suite verifying debug logs are gated by debug mode setting.
- Task 4: Implemented runtime debug toggle (FR48). Initial approach used per-request env check in middleware, but this was refactored to a cleaner internal state design:
  - Added `_debug_enabled` and `_debug_initialized` internal state variables
  - `initialize_debug_state()` reads VS_DEBUG once at startup
  - `is_debug_enabled()` returns current debug state
  - `set_debug_enabled(bool)` allows runtime toggle via API
  - Created `/api/v1alpha1/debug` endpoints (GET status, POST enable/disable)
  - Removed per-request env check from middleware (performance improvement)
  - Changed `cache_logger_on_first_use=False` to allow runtime reconfiguration
  - Added 28 tests total: 11 for config state functions, 12 for debug API endpoints, 5 for request context

### File List

**Middleware & Configuration:**
- `api/src/vintagestory_api/middleware/request_context.py` (NEW) - Request ID middleware
- `api/src/vintagestory_api/middleware/__init__.py` (MODIFIED) - Export middleware
- `api/src/vintagestory_api/config.py` (MODIFIED) - Debug state management, merge_contextvars

**Routers:**
- `api/src/vintagestory_api/routers/debug.py` (NEW) - Debug toggle API endpoints
- `api/src/vintagestory_api/routers/mods.py` (MODIFIED) - Added router-level debug logs
- `api/src/vintagestory_api/routers/server.py` (MODIFIED) - Added router-level debug logs

**Services:**
- `api/src/vintagestory_api/services/mods.py` (MODIFIED) - Added service-level debug logs
- `api/src/vintagestory_api/services/server.py` (MODIFIED) - Added service-level debug logs
- `api/src/vintagestory_api/services/console.py` (MODIFIED) - Added service-level debug logs

**Main Application:**
- `api/src/vintagestory_api/main.py` (MODIFIED) - Initialize debug state, register debug router

**Tests:**
- `api/tests/test_request_context.py` (NEW) - Request context middleware tests
- `api/tests/test_config.py` (MODIFIED) - Debug state function tests
- `api/tests/test_debug_api.py` (NEW) - Debug API endpoint tests
- `api/tests/test_debug_logging.py` (NEW) - Debug log gating tests
- `api/tests/test_runtime_debug_toggle.py` (NEW) - Runtime toggle tests
- `api/tests/conftest.py` (MODIFIED) - Test fixtures for debug state
- `api/tests/test_jobs_registration.py` (MODIFIED) - Updated for debug state

### Change Log

- 2026-01-04: Refactored FR48 runtime debug toggle from per-request env check to internal state variable with API endpoints. Added `initialize_debug_state()`, `is_debug_enabled()`, `set_debug_enabled()` functions. Created `/api/v1alpha1/debug` router with GET/POST endpoints for admin-only debug toggle. Removed env check overhead from middleware. Added UI-028 to polish backlog for UI toggle component.
- 2026-01-04: Code review follow-up - Added router-level debug logs to mods.py and server.py routers with consistent `router_{action}_start/complete` pattern. Updated File List with organized sections and all changed files.
- 2026-01-04: Code review follow-up - Standardized test fixtures in test_config.py to use `captured_logs` fixture from conftest.py instead of inline `structlog.configure()` calls. Removed unused `Any` import.
