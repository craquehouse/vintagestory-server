# Story 9.2: Directory Auto-Creation on Startup

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **operator**,
I want **the API server to automatically create required directories on startup**,
So that **I don't encounter errors from missing directories during first-run or after volume mounts**.

## Acceptance Criteria

1. **Given** the API server starts, **When** expected directories don't exist under `/data/vsmanager/`, **Then** the directories are created: `cache/`, `state/`, `logs/` *(Covers FR42)*

2. **Given** directories are created on startup, **When** any directory is created, **Then** a log entry is emitted: `{"event": "directory_created", "path": "..."}` *(Covers FR43)*

3. **Given** directories already exist, **When** the API server starts, **Then** no errors occur and no creation logs are emitted

4. **Given** directory creation fails (permissions issue), **When** startup encounters the error, **Then** a clear error is logged and startup fails gracefully

## Tasks / Subtasks

<!--
🚨 CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

✅ CORRECT PATTERN:
- [ ] Task 1: Implement user login endpoint + tests (AC: 1, 2)
  - [ ] Create login route handler
  - [ ] Add input validation
  - [ ] Write tests for success/failure cases

❌ WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement user login endpoint (AC: 1, 2)
- [ ] Task 2: Implement logout endpoint (AC: 3)
- [ ] Task 3: Write all tests  <- NEVER DO THIS
-->

- [ ] Task 1: Create directory initialization service + tests (AC: 1, 2, 3, 4)
  - [ ] Subtask 1.1: Create `api/src/vintagestory_api/services/directory_init_service.py` with `ensure_directories()` function
  - [ ] Subtask 1.2: Define required directory paths based on `Settings.data_dir` (cache, state, logs under `/data/vsmanager/`)
  - [ ] Subtask 1.3: Implement `pathlib.Path.mkdir(parents=True, exist_ok=True)` for directory creation
  - [ ] Subtask 1.4: Add structured logging for directory creation events with `directory_created` event name
  - [ ] Subtask 1.5: Add error handling for permission errors with clear error messages
  - [ ] Subtask 1.6: Write tests in `api/tests/test_directory_init_service.py` for creation, idempotency, permission failures

- [ ] Task 2: Integrate with FastAPI lifespan + tests (AC: 1, 2, 3, 4)
  - [ ] Subtask 2.1: Call `ensure_directories()` in `api/src/vintagestory_api/main.py` lifespan startup
  - [ ] Subtask 2.2: Add error handling - fail startup gracefully if directory creation fails
  - [ ] Subtask 2.3: Add integration test in `api/tests/test_main.py` verifying directories created on startup
  - [ ] Subtask 2.4: Add test for permission error causing startup failure
  - [ ] Subtask 2.5: Verify all tests pass with `just check`

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

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

### Directory Structure Overview

The API server uses `/data/vsmanager/` as the base directory for all application-managed files (separate from game server data at `/data/server/`):

```
/data/vsmanager/
├── cache/       # Mod downloads, server tarballs (see Story 9.3 for eviction)
├── state/       # state.json, api-settings.json
└── logs/        # Application log files (if file logging enabled)
```

**Why vsmanager/ subdirectory:**
- Keeps API-managed files separate from game server files
- Prevents conflicts with VintageStory's own directory structure
- Clean volume organization for operators

### Implementation Pattern

Use Python's `pathlib` for cross-platform path handling:

```python
from pathlib import Path
from vintagestory_api.config import Settings
import structlog

logger = structlog.get_logger(__name__)

def ensure_directories(settings: Settings) -> None:
    """Create required application directories if they don't exist.

    Raises:
        OSError: If directory creation fails (e.g., permissions)
    """
    base = Path(settings.data_dir) / "vsmanager"
    required_dirs = [
        base / "cache",
        base / "state",
        base / "logs",
    ]

    for dir_path in required_dirs:
        if not dir_path.exists():
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                logger.info("directory_created", path=str(dir_path))
            except OSError as e:
                logger.error("directory_creation_failed",
                    path=str(dir_path), error=str(e))
                raise
```

**Key points:**
- `parents=True` creates parent directories if needed
- `exist_ok=True` prevents errors if directory already exists
- Only log when directory is actually created (check `not dir_path.exists()` first)
- Let exceptions propagate to fail startup gracefully

### Lifespan Integration

Add to `main.py` lifespan function:

```python
from contextlib import asynccontextmanager
from vintagestory_api.services.directory_init_service import ensure_directories

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("api_starting")

    # Ensure directories exist before other services start
    settings = get_settings()
    ensure_directories(settings)

    # ... existing startup code (scheduler, etc.)

    yield

    # Shutdown
    # ... existing shutdown code
```

**Placement:** Directory creation should happen FIRST in startup, before any other services that might need these directories (caching, state management, etc.).

### Architecture & Patterns

- **Fail-fast on startup:** If directories can't be created, fail startup with clear error
- **Idempotent:** Multiple startups don't cause errors (exist_ok=True)
- **Structured logging:** Use event names (directory_created, directory_creation_failed) not string interpolation
- **Path handling:** Use pathlib.Path for cross-platform compatibility
- **Settings integration:** Read data_dir from Settings (defaults to /data)

### Project Structure Notes

**Files to CREATE:**
- `api/src/vintagestory_api/services/directory_init_service.py` - Directory initialization service
- `api/tests/test_directory_init_service.py` - Unit tests for directory creation

**Files to MODIFY:**
- `api/src/vintagestory_api/main.py` - Add ensure_directories() call in lifespan startup
- `api/tests/test_main.py` - Add integration test for startup directory creation

**Directory paths align with:**
- Epic 1 architecture: Single volume mount at `/data/`
- Epic 5-8 implementations: State files in `/data/vsmanager/state/`
- Future caching (Story 9.3): Cache files in `/data/vsmanager/cache/`

### Previous Story Intelligence

**From Story 9.1 (Secure WebSocket Authentication):**
- **Test baseline:** 1041 API tests + 735 web tests = 1776 total tests (Story 9.2 should maintain or increase)
- **Service pattern:** Singleton services with dependency injection (e.g., `get_ws_token_service()`)
- **Lifespan integration:** Services initialized in `main.py` lifespan function, clean startup/shutdown
- **Async patterns:** Services use async/await with asyncio.Lock for thread-safety where needed
- **Error handling:** Clear error messages with structured logging, fail gracefully on startup errors
- **Test organization:** Unit tests in `tests/` with same path structure as `src/`, integration tests in `tests/test_main.py`

**From Previous Epic 8.3:**
- **Settings pattern:** Use `Settings.data_dir` for base path, all app files under `/data/vsmanager/`
- **Structured logging:** Event-driven logging (e.g., `logger.info("event_name", key=value)`) not string interpolation

**Key Learnings for Story 9.2:**
- Keep it simple: This is a small story (2 tasks) - don't over-engineer
- Directory creation is synchronous (no async needed) but called from async lifespan
- Test both success and failure cases (permissions, existing dirs)
- Follow logging conventions: `directory_created`, `directory_creation_failed` event names

### References

- `project-context.md` → Logging Conventions - Structured logging with event names
- `project-context.md` → Critical Implementation Rules #6 - Atomic File Writes (pattern for state persistence)
- `_bmad-output/planning-artifacts/epics.md#Story 9.2` - Story requirements and acceptance criteria
- `_bmad-output/planning-artifacts/architecture.md` → Infrastructure - Volume mounts and directory structure
- `api/src/vintagestory_api/config.py` - Settings with data_dir configuration
- `api/src/vintagestory_api/main.py` - Lifespan function for startup initialization
- Story 9.1 completion notes - Service patterns, test organization, error handling
- Story 9.3 (next): Mod cache eviction strategy will use `/data/vsmanager/cache/`

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
