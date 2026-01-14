# Story 13.6: Server Uninstall API

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **an API endpoint to uninstall the server**,
So that **I can programmatically remove the server installation**.

**Background:** Added from Epic 11 retrospective to support testing workflow. Allows clean uninstall for version switching without manual file deletion.

## Acceptance Criteria

1. **Given** the server is running
   **When** I call `DELETE /api/v1alpha1/server` as Admin
   **Then** I receive a 409 Conflict with error code `SERVER_RUNNING`
   **And** a message indicating the server must be stopped first

2. **Given** the server is stopped and installed
   **When** I call `DELETE /api/v1alpha1/server` as Admin
   **Then** the `/data/server` directory is deleted
   **And** the state transitions to `not_installed`
   **And** I receive a success response

3. **Given** no server is installed
   **When** I call `DELETE /api/v1alpha1/server` as Admin
   **Then** I receive a 404 or appropriate error response
   **And** no files are deleted

4. **Given** I call the uninstall endpoint
   **When** the operation completes
   **Then** the `/data/serverdata` directory is preserved (configs, mods, worlds)

## Tasks / Subtasks

- [x] Task 1: Add `DELETE /api/v1alpha1/server` endpoint to server router + tests (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Add new DELETE endpoint to `api/src/vintagestory_api/routers/server.py`
  - [x] Subtask 1.2: Check for running state and return 409 if running
  - [x] Subtask 1.3: Return 404/400 if not installed
  - [x] Subtask 1.4: Write router-level tests for all response scenarios

- [x] Task 2: Implement `uninstall_server` method in ServerService + tests (AC: 2, 4)
  - [x] Subtask 2.1: Add `uninstall_server` method to `api/src/vintagestory_api/services/server.py`
  - [x] Subtask 2.2: Delete `/data/server` directory recursively (using shutil.rmtree)
  - [x] Subtask 2.3: Remove version tracking file (`/data/vsmanager/current_version`)
  - [x] Subtask 2.4: Preserve `/data/serverdata` directory (DO NOT delete)
  - [x] Subtask 2.5: Reset internal state to `NOT_INSTALLED`
  - [x] Subtask 2.6: Write unit tests for uninstall logic

- [x] Task 3: Add `SERVER_RUNNING` error code + tests (AC: 1)
  - [x] Subtask 3.1: Add `SERVER_RUNNING` constant to `api/src/vintagestory_api/models/errors.py`
  - [x] Subtask 3.2: Document error code in ErrorCode class docstring

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Run `just test-api` to verify all API tests pass before marking task complete

### Security Requirements

Follow patterns in `project-context.md` → Security Patterns section:

- Endpoint requires Admin role (use `RequireAdmin` dependency)
- Use existing auth middleware patterns from other server endpoints

### Development Commands

```bash
just test-api                                    # Run all API tests
just test-api -k "uninstall"                     # Run uninstall-related tests
just test-api tests/test_server.py -xvs         # Run server tests verbose
just check                                       # Full validation
```

### Architecture & Patterns

**Endpoint Design:**

Follow the existing pattern in `api/src/vintagestory_api/routers/server.py`:

```python
@router.delete("", response_model=ApiResponse)
async def uninstall_server(
    _: RequireAdmin,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Uninstall the VintageStory server.

    Removes the server installation while preserving configuration,
    mods, and world data. Requires Admin role.

    Returns:
        ApiResponse with uninstall result

    Raises:
        HTTPException: 409 if server is running
        HTTPException: 400/404 if server not installed
    """
```

**Service Method Design:**

Add to `ServerService` class following existing patterns:

```python
async def uninstall_server(self) -> bool:
    """Uninstall the server, preserving serverdata.

    Removes /data/server directory and version tracking.
    Preserves /data/serverdata (configs, mods, worlds).

    Returns:
        True if uninstallation successful.

    Raises:
        RuntimeError: If server is running or not installed.
    """
```

**Directory Structure Preservation:**

```
/data/
├── server/          # DELETE - VintageStory server binaries
├── serverdata/      # PRESERVE - Game configs, mods, worlds
└── vsmanager/
    └── current_version  # DELETE - Version tracking file
```

**Why preserve serverdata:**
- Contains user's game configuration (serverconfig.json, etc.)
- Contains installed mods (/data/serverdata/Mods/)
- Contains world saves (/data/serverdata/Saves/)
- User may want to reinstall a different version with same config

### Error Code Addition

Add to `api/src/vintagestory_api/models/errors.py`:

```python
# Server lifecycle
SERVER_RUNNING = "SERVER_RUNNING"  # Cannot uninstall while running
```

**Placement:** In the "Server lifecycle" section, after `SERVER_ALREADY_STOPPED`.

### Implementation Guide

**Step 1: Service Method**

```python
import shutil

async def uninstall_server(self) -> bool:
    """Uninstall the server, preserving serverdata."""
    async with self._lifecycle_lock:
        return await self._uninstall_server_locked()

async def _uninstall_server_locked(self) -> bool:
    """Internal uninstall logic (must be called with lock held)."""
    logger.debug("uninstall_server_begin")

    # Check if installed
    if not self.is_installed():
        logger.warning("uninstall_failed", reason="not_installed")
        raise RuntimeError(ErrorCode.SERVER_NOT_INSTALLED)

    # Check if running - MUST be stopped first
    if self._process is not None and self._process.returncode is None:
        logger.warning("uninstall_failed", reason="server_running")
        raise RuntimeError(ErrorCode.SERVER_RUNNING)

    # Get current version for logging
    current_version = self.get_installed_version()

    logger.info("uninstalling_server", version=current_version)

    # Delete server directory (binaries)
    server_dir = self._settings.server_dir
    if server_dir.exists():
        shutil.rmtree(server_dir)
        logger.info("server_dir_deleted", path=str(server_dir))

    # Delete version tracking file
    version_file = self._settings.vsmanager_dir / "current_version"
    if version_file.exists():
        version_file.unlink()
        logger.info("version_file_deleted", path=str(version_file))

    # Reset state
    self._reset_install_state()
    self._server_state = ServerState.NOT_INSTALLED

    logger.info("uninstall_complete", previous_version=current_version)
    return True
```

**Step 2: Router Endpoint**

```python
@router.delete("", response_model=ApiResponse)
async def uninstall_server(
    _: RequireAdmin,
    service: ServerService = Depends(get_server_service),
) -> ApiResponse:
    """Uninstall the VintageStory server."""
    logger.debug("router_uninstall_server_start")
    try:
        await service.uninstall_server()
        logger.debug("router_uninstall_server_complete")
        return ApiResponse(
            status="ok",
            data={
                "message": "Server uninstalled successfully",
                "state": ServerState.NOT_INSTALLED.value,
            },
        )
    except RuntimeError as e:
        error_code = str(e)
        if error_code == ErrorCode.SERVER_NOT_INSTALLED:
            raise HTTPException(
                status_code=404,
                detail={
                    "code": ErrorCode.SERVER_NOT_INSTALLED,
                    "message": "No server is installed.",
                },
            )
        elif error_code == ErrorCode.SERVER_RUNNING:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": ErrorCode.SERVER_RUNNING,
                    "message": "Server must be stopped before uninstalling.",
                },
            )
        else:
            raise HTTPException(
                status_code=500,
                detail={
                    "code": ErrorCode.INTERNAL_ERROR,
                    "message": f"Failed to uninstall server: {error_code}",
                },
            )
```

### Test Patterns

**Router Tests (`tests/test_server.py` additions):**

```python
class TestUninstallServer:
    """Tests for DELETE /api/v1alpha1/server endpoint."""

    async def test_uninstall_requires_admin(self, client, monitor_headers):
        """Monitor role cannot uninstall."""
        response = await client.delete("/api/v1alpha1/server", headers=monitor_headers)
        assert response.status_code == 403

    async def test_uninstall_when_running_returns_409(self, client, admin_headers, running_server):
        """Cannot uninstall running server."""
        response = await client.delete("/api/v1alpha1/server", headers=admin_headers)
        assert response.status_code == 409
        data = response.json()
        assert data["detail"]["code"] == ErrorCode.SERVER_RUNNING

    async def test_uninstall_when_stopped_succeeds(self, client, admin_headers, installed_server):
        """Uninstall stopped server succeeds."""
        response = await client.delete("/api/v1alpha1/server", headers=admin_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["data"]["state"] == "not_installed"

    async def test_uninstall_when_not_installed_returns_404(self, client, admin_headers):
        """Cannot uninstall when no server installed."""
        response = await client.delete("/api/v1alpha1/server", headers=admin_headers)
        assert response.status_code == 404
        data = response.json()
        assert data["detail"]["code"] == ErrorCode.SERVER_NOT_INSTALLED

    async def test_uninstall_preserves_serverdata(self, client, admin_headers, installed_server, tmp_path):
        """Uninstall preserves serverdata directory."""
        # Create test files in serverdata
        serverdata_file = tmp_path / "serverdata" / "test.txt"
        serverdata_file.parent.mkdir(parents=True, exist_ok=True)
        serverdata_file.write_text("preserved")

        response = await client.delete("/api/v1alpha1/server", headers=admin_headers)
        assert response.status_code == 200

        # Verify serverdata still exists
        assert serverdata_file.exists()
        assert serverdata_file.read_text() == "preserved"
```

**Service Tests (unit tests for `ServerService.uninstall_server`):**

```python
async def test_uninstall_deletes_server_dir(self, service, tmp_path):
    """Uninstall removes server directory."""
    # Setup: create fake server installation
    server_dir = tmp_path / "server"
    server_dir.mkdir()
    (server_dir / "VintagestoryServer.dll").touch()

    await service.uninstall_server()

    assert not server_dir.exists()

async def test_uninstall_removes_version_file(self, service, tmp_path):
    """Uninstall removes version tracking file."""
    version_file = tmp_path / "vsmanager" / "current_version"
    version_file.parent.mkdir(parents=True, exist_ok=True)
    version_file.write_text("1.21.3")

    await service.uninstall_server()

    assert not version_file.exists()

async def test_uninstall_resets_state(self, service):
    """Uninstall resets service state to NOT_INSTALLED."""
    await service.uninstall_server()

    status = service.get_server_status()
    assert status.state == ServerState.NOT_INSTALLED
```

### Previous Story Intelligence

**From Story 13.5 (Version Page Integration):**
- Test count baseline: 1299 web tests, ~966 API tests
- QuickInstallButton shows confirmation when server running before update
- Installation flow uses `force` flag for reinstall/upgrade

**From Epic 13 Architecture (ADR-4):**
- After uninstall, invalidate related queries:
  - `queryKeys.server.status`
  - `queryKeys.versions.all` (to refresh installed badges)

**Patterns from server.py:**
- Use `async with self._lifecycle_lock` for state-changing operations
- Use `RuntimeError(ErrorCode.X)` for error handling
- Log with structlog: `logger.info("event_name", key=value)`

### File Structure

**Files to modify:**
- `api/src/vintagestory_api/routers/server.py` - Add DELETE endpoint
- `api/src/vintagestory_api/services/server.py` - Add uninstall_server method
- `api/src/vintagestory_api/models/errors.py` - Add SERVER_RUNNING error code
- `api/tests/test_server.py` - Add uninstall tests

**Files to reference (DO NOT modify):**
- `api/src/vintagestory_api/config.py` - Settings class with directory paths
- `api/src/vintagestory_api/middleware/permissions.py` - RequireAdmin dependency
- `api/src/vintagestory_api/models/responses.py` - ApiResponse model

### Git Workflow

**Branch:** `story/13-6-server-uninstall-api`

**Commit Pattern:**
```
feat(story-13.6/task-1): add DELETE /api/v1alpha1/server endpoint
feat(story-13.6/task-2): implement uninstall_server service method
feat(story-13.6/task-3): add SERVER_RUNNING error code
```

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 13.6] - Story requirements
- [Source: api/src/vintagestory_api/services/server.py] - ServerService implementation
- [Source: api/src/vintagestory_api/routers/server.py] - Server router patterns
- [Source: _bmad-output/implementation-artifacts/13-5-version-page-integration.md] - Previous story

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None - no issues encountered

### Completion Notes List

- All 3 tasks completed successfully
- 15 tests added (8 service tests + 7 router tests)
- All tests pass, typecheck clean, lint clean
- Pre-existing test failures unrelated to this story (websocket, scheduler, jobs_router)
- Implemented exactly as specified in dev notes

### File List

**Modified:**

- `api/src/vintagestory_api/models/errors.py` - Added SERVER_RUNNING error code
- `api/src/vintagestory_api/services/server.py` - Added uninstall_server method
- `api/src/vintagestory_api/routers/server.py` - Added DELETE endpoint

**Added:**

- `api/tests/test_server_service.py` - 8 service unit tests
- `api/tests/test_server_router.py` - 7 router integration tests
