# Story 3.3: Server Status API

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator or monitor**,
I want **to view the current server status**,
so that **I can see if the server is running and its version**.

---

## Acceptance Criteria

1. **Given** the API is running, **When** I call `GET /api/v1alpha1/server/status` as Admin, **Then** I receive server status including: state (not_installed/stopped/starting/running/stopping), version, uptime (if running) *(Covers FR1)*

2. **Given** the API is running, **When** I call `GET /api/v1alpha1/server/status` as Monitor, **Then** I receive the same status information (read-only access permitted) *(Covers FR5)*

3. **Given** the server is running, **When** I query status, **Then** uptime is calculated from process start time **And** version is read from the installed server

4. **Given** the server is not installed, **When** I query status, **Then** state is "not_installed" **And** version and uptime are null

---

## Tasks / Subtasks

<!--
🚨 CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task
-->

- [ ] Task 1: Create GET /status endpoint + tests (AC: 1, 2, 3, 4)
  - [ ] 1.1: Add `GET /api/v1alpha1/server/status` endpoint to `routers/server.py`
  - [ ] 1.2: Allow both Admin AND Monitor roles to access (read-only endpoint)
  - [ ] 1.3: Return `ServerStatus` wrapped in `ApiResponse` envelope
  - [ ] 1.4: Write tests for Admin access to status endpoint
  - [ ] 1.5: Write tests for Monitor access to status endpoint
  - [ ] 1.6: Write tests for various server states (not_installed, installed/stopped, running)
  - [ ] 1.7: Write test for unauthenticated request returns 401

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

- Role-based access: Both Admin AND Monitor can access status (read-only endpoint)
- Use `get_current_user` dependency for authentication (not `require_admin`)
- Log authentication failures appropriately

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api -k "status"` - Run status-related tests only
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**This is a SIMPLE story - leverage existing infrastructure:**

The `ServerService.get_server_status()` method already exists (Story 3.2) and returns a `ServerStatus` model. This story ONLY needs to:
1. Add a GET endpoint that exposes this method via the API
2. Allow both Admin and Monitor roles (unlike lifecycle endpoints which are Admin-only)

**Existing Code to Reuse:**

```python
# Already exists in api/src/vintagestory_api/services/server.py:624
def get_server_status(self) -> ServerStatus:
    """Get current server runtime status.

    Returns:
        ServerStatus with current state, version, uptime, and exit code.
    """
```

**ServerStatus Model (already exists):**

```python
# api/src/vintagestory_api/models/server.py:86
class ServerStatus(BaseModel):
    """Current server status information."""
    state: ServerState
    version: str | None = None
    uptime_seconds: int | None = None  # If running
    last_exit_code: int | None = None  # If stopped after running
```

**ServerState Values (already exists):**

```python
class ServerState(str, Enum):
    NOT_INSTALLED = "not_installed"
    INSTALLING = "installing"
    INSTALLED = "installed"  # Server installed but stopped
    STARTING = "starting"
    RUNNING = "running"
    STOPPING = "stopping"
    ERROR = "error"
```

**Endpoint Pattern to Follow:**

```python
# Add to api/src/vintagestory_api/routers/server.py
from vintagestory_api.middleware.auth import get_current_user

@router.get("/status", response_model=ApiResponse)
async def get_server_status(
    _: str = Depends(get_current_user),  # Both Admin and Monitor
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Get current server status.

    Returns server state, version, uptime (if running), and last exit code.
    Available to both Admin and Monitor roles.

    Returns:
        ApiResponse with ServerStatus data
    """
    status = service.get_server_status()
    return ApiResponse(status="ok", data=status.model_dump())
```

**Role Access Pattern:**

- Use `get_current_user` for endpoints accessible to both roles
- Use `require_admin` for write-only endpoints (already used by start/stop/restart)

See `api/src/vintagestory_api/middleware/auth.py` for the `get_current_user` dependency.

### Previous Story Intelligence (3.2)

**Patterns established in Story 3.2:**
- Lifecycle endpoints use `RequireAdmin` dependency
- Singleton pattern via `get_server_service()` function
- `ApiResponse` envelope with `status="ok"` and `data` field
- Import `ServerState` from `models.server` (not from service)

**Test patterns from Story 3.2:**
- Use `test_client` fixture with `respx_mock`
- Set headers with `{"X-API-Key": settings.api_key_admin}` or `api_key_monitor`
- Check response JSON structure: `response.json()["data"]["state"]`

### Git Intelligence

**Recent commits:**
- `519fa76` - fix(api): Resolve test code type annotation issues (Story 3.2)
- `7fafb49` - feat(api): Add server lifecycle control API (Story 3.2)

**Files modified in Story 3.2 (context for this story):**
- `api/src/vintagestory_api/routers/server.py` - Add new endpoint here
- `api/tests/test_server.py` - Add new tests here

### Project Structure Notes

**Files to modify (ONLY):**

| File | Change |
|------|--------|
| `api/src/vintagestory_api/routers/server.py` | Add GET /status endpoint |
| `api/tests/test_server.py` | Add status endpoint tests |

**DO NOT create new files** - this is a single endpoint addition.

**Import to add:**
```python
from vintagestory_api.middleware.auth import get_current_user
```

### API Response Format

```json
// GET /api/v1alpha1/server/status (success - running)
{
  "status": "ok",
  "data": {
    "state": "running",
    "version": "1.21.3",
    "uptime_seconds": 3600,
    "last_exit_code": null
  }
}

// GET /api/v1alpha1/server/status (success - not installed)
{
  "status": "ok",
  "data": {
    "state": "not_installed",
    "version": null,
    "uptime_seconds": null,
    "last_exit_code": null
  }
}

// GET /api/v1alpha1/server/status (401 - unauthenticated)
{
  "detail": {
    "code": "UNAUTHORIZED",
    "message": "API key required"
  }
}
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/architecture.md#Authentication & Security]
- [Source: _bmad-output/planning-artifacts/epics.md#Story 3.3]
- `api/src/vintagestory_api/services/server.py:624` - Existing `get_server_status()` method
- `api/src/vintagestory_api/models/server.py:86` - Existing `ServerStatus` model
- `api/src/vintagestory_api/middleware/auth.py` - `get_current_user` dependency

---

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List
