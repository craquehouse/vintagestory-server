# Story 5.4: Mod Enable/Disable and Remove API

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **to enable, disable, and remove installed mods**,
So that **I can manage which mods are active without deleting files**.

---

## Background

This story implements the mod lifecycle management API endpoints for enabling, disabling, and removing mods. It builds directly on the foundation established in Stories 5.1-5.3:

- **Story 5.1:** ModService, ModStateManager, PendingRestartState, file suffix approach (`.disabled`), state persistence
- **Story 5.2:** ModApiClient, install_mod(), atomic file operations, mod file management
- **Story 5.3:** Mod lookup API, compatibility checking, error handling patterns

The enable/disable functionality uses the file suffix approach (`.zip` ↔ `.zip.disabled`) established in Story 5.1.

**FRs Covered:** FR14 (Admin enables mod), FR15 (Admin disables mod), FR16 (Admin removes mod)

**NFRs Addressed:** NFR11 (graceful failures), NFR16 (sufficient error context)

---

## Acceptance Criteria

1. **Given** a mod is installed and enabled **When** I call `POST /api/v1alpha1/mods/{slug}/disable` **Then** the mod is marked as disabled in state **And** the mod file is renamed with `.disabled` suffix (e.g., `mod.zip` → `mod.zip.disabled`) **And** a pending restart flag is set if server is running *(Covers FR15)*

2. **Given** a mod is installed and disabled **When** I call `POST /api/v1alpha1/mods/{slug}/enable` **Then** the mod is marked as enabled in state **And** the mod file is restored to active status (`.disabled` suffix removed) **And** a pending restart flag is set if server is running *(Covers FR14)*

3. **Given** a mod is installed **When** I call `DELETE /api/v1alpha1/mods/{slug}` **Then** the mod file is deleted from `/data/serverdata/Mods/` **And** the mod is removed from state **And** a pending restart flag is set if server is running *(Covers FR16)*

4. **Given** the mod slug doesn't exist in installed mods **When** I attempt enable/disable/remove **Then** I receive a 404 error with message "Mod not installed"

5. **Given** a mod is already enabled **When** I call enable **Then** I receive a 200 OK (idempotent) **And** no state change occurs

6. **Given** a mod is already disabled **When** I call disable **Then** I receive a 200 OK (idempotent) **And** no state change occurs

7. **Given** I am authenticated as Monitor **When** I attempt enable/disable/remove **Then** I receive a 403 Forbidden (Admin-only operations)

---

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

CORRECT PATTERN:
- [ ] Task 1: Implement feature A + tests (AC: 1, 2)
  - [ ] Create implementation
  - [ ] Write tests for success/failure cases

WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement feature A (AC: 1, 2)
- [ ] Task 2: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Extend ModService with remove_mod method + tests (AC: 3, 4)
  - [x] 1.1: Add `remove_mod(slug: str) -> RemoveResult` to ModService in `api/src/vintagestory_api/services/mods.py`:
    - Validate mod exists in state index
    - Get mod file path from state (handle both enabled and disabled filenames)
    - Delete mod file from disk using `Path.unlink()`
    - Remove mod from state index via `ModStateManager.remove_mod(slug)`
    - Set pending_restart if server is running
    - Return `RemoveResult(slug, pending_restart)`
  - [x] 1.2: Create `RemoveResult` model in `api/src/vintagestory_api/models/mods.py`:
    - `slug: str`
    - `pending_restart: bool`
  - [x] 1.3: Handle errors: mod not found (raise `ModNotInstalledError`), file already deleted
  - [x] 1.4: Add cleanup of cached metadata in `state/mods/<slug>/` directory
  - [x] 1.5: Write tests in `api/tests/test_mod_service.py`:
    - Test successful removal of enabled mod
    - Test successful removal of disabled mod
    - Test removal sets pending_restart when server running
    - Test removal of non-existent mod returns error
    - Test cleanup of cached metadata directory
  - [x] 1.6: Run `just test-api tests/test_mod_service.py` - verify tests pass

- [x] Task 2: Verify ModService enable_mod/disable_mod methods + tests (AC: 1, 2, 5, 6)
  - [x] 2.1: Review existing `enable_mod(slug)` and `disable_mod(slug)` in ModService (from 5.1)
  - [x] 2.2: Verify enable_mod:
    - Returns gracefully if already enabled (idempotent)
    - Renames file from `.zip.disabled` to `.zip`
    - Updates state index
    - Sets pending_restart if server running
    - Raises `ModNotInstalledError` if not found
  - [x] 2.3: Verify disable_mod:
    - Returns gracefully if already disabled (idempotent)
    - Renames file from `.zip` to `.zip.disabled`
    - Updates state index
    - Sets pending_restart if server running
    - Raises `ModNotInstalledError` if not found
  - [x] 2.4: Add/verify tests for idempotent behavior:
    - Test enable on already-enabled mod (should succeed, no change)
    - Test disable on already-disabled mod (should succeed, no change)
  - [x] 2.5: Add `EnableResult` and `DisableResult` models if not present:
    - `slug: str`
    - `enabled: bool`
    - `pending_restart: bool`
  - [x] 2.6: Run `just test-api tests/test_mod_service.py` - verify tests pass

- [x] Task 3: Create mod lifecycle API endpoints + tests (AC: 1, 2, 3, 4, 7)
  - [x] 3.1: Add `POST /api/v1alpha1/mods/{slug}/enable` to `routers/mods.py`:
    - Path parameter: `slug` (mod slug)
    - Requires Admin role authentication (`require_admin` dependency)
    - Returns `EnableResult` wrapped in API envelope
    - Returns 404 if mod not installed
  - [x] 3.2: Add `POST /api/v1alpha1/mods/{slug}/disable` to `routers/mods.py`:
    - Path parameter: `slug` (mod slug)
    - Requires Admin role authentication
    - Returns `DisableResult` wrapped in API envelope
    - Returns 404 if mod not installed
  - [x] 3.3: Add `DELETE /api/v1alpha1/mods/{slug}` to `routers/mods.py`:
    - Path parameter: `slug` (mod slug)
    - Requires Admin role authentication
    - Returns `RemoveResult` wrapped in API envelope
    - Returns 404 if mod not installed
  - [x] 3.4: Implement error handling:
    - 404 Not Found: `MOD_NOT_INSTALLED` error code
    - 403 Forbidden: Monitor attempting write operation
    - 500 Internal: File operation failures
  - [x] 3.5: Write API endpoint tests in `api/tests/test_mods_router.py`:
    - Test successful enable
    - Test successful disable
    - Test successful remove
    - Test enable/disable/remove on non-existent mod (404)
    - Test idempotent enable/disable
    - Test Monitor role receives 403
    - Test pending_restart flag in responses
  - [x] 3.6: Run `just test-api tests/test_mods_router.py` - verify tests pass

- [x] Task 4: Final validation + tests (AC: 1-7)
  - [x] 4.1: Run `just test-api` - verify full test suite passes (503 tests passed)
  - [x] 4.2: Run `just check` - verify lint, typecheck, and all tests pass
  - [x] 4.3: Manual test: Enable a disabled mod with server running
  - [x] 4.4: Manual test: Disable an enabled mod with server running
  - [x] 4.5: Manual test: Remove a mod and verify file deletion (including .disabled files)
  - [x] 4.6: Verify pending_restart flag is set correctly in all cases

---

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- When it comes time for manual tests, pause, and give the User guidance on how to complete them. Wait until User confirms that they are successful before continuing
- Run `just test-api` to verify tests pass before marking task complete
- Run `just check` for full validation (lint + typecheck + test) before story completion

**Test file locations:**
```
api/tests/
├── test_mod_service.py      # Tasks 1, 2: ModService tests (extend existing)
└── test_mods_router.py      # Task 3: API endpoint tests (extend existing)
```

**Test mocking pattern:**
ModService tests use fixture-based mocking with temporary directories (established pattern):
```python
@pytest.fixture
def mod_service(tmp_path):
    """Create ModService with temporary directories."""
    mods_dir = tmp_path / "mods"
    mods_dir.mkdir()
    state_dir = tmp_path / "state"
    state_dir.mkdir()
    return ModService(mods_dir=mods_dir, state_dir=state_dir)
```

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Admin-only endpoints: Use `require_admin` dependency (not `get_current_user`)
- Validate slug format before file operations (use existing `validate_slug()`)
- Path traversal protection: Validate mod file path stays within mods directory
- Atomic file operations where applicable

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests
- `just test-api tests/test_mod_service.py` - Run specific test file
- `just test-api -k "enable"` - Run tests matching pattern
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just lint-api --fix` - Lint with auto-fix

### Architecture & Patterns

**From architecture.md → Epic 5: Mod Management Architecture:**

**Enable/Disable Pattern (from Story 5.1):**
```python
async def disable_mod(self, slug: str) -> DisableResult:
    """Disable a mod by renaming file with .disabled suffix."""
    mod = self._get_mod_state(slug)
    if not mod:
        raise ModNotInstalledError(slug)

    if not mod.enabled:
        # Already disabled - idempotent
        return DisableResult(slug=slug, enabled=False, pending_restart=False)

    # Rename file
    old_path = self.mods_dir / mod.filename
    new_path = old_path.with_suffix('.zip.disabled')
    old_path.rename(new_path)

    # Update state
    mod.enabled = False
    mod.filename = new_path.name
    self._save_state()

    # Set pending restart if server running
    pending_restart = self._maybe_require_restart(f"Disabled mod: {slug}")

    return DisableResult(slug=slug, enabled=False, pending_restart=pending_restart)
```

**Remove Pattern:**
```python
async def remove_mod(self, slug: str) -> RemoveResult:
    """Remove a mod by deleting file and state."""
    mod = self._get_mod_state(slug)
    if not mod:
        raise ModNotInstalledError(slug)

    # Delete file (handle both enabled and disabled)
    file_path = self.mods_dir / mod.filename
    if file_path.exists():
        file_path.unlink()

    # Remove from state
    self._state_manager.remove_mod(slug)

    # Clean up cached metadata
    cache_dir = self.state_dir / "mods" / slug
    if cache_dir.exists():
        shutil.rmtree(cache_dir)

    # Set pending restart if server running
    pending_restart = self._maybe_require_restart(f"Removed mod: {slug}")

    return RemoveResult(slug=slug, pending_restart=pending_restart)
```

**Pending Restart Integration (established in 5.1):**
```python
def _maybe_require_restart(self, reason: str) -> bool:
    """Set pending restart if server is running."""
    if self._server_running:
        self._pending_restart.require_restart(reason)
        return True
    return False
```

**Response envelope pattern:**
```python
# Success response
{"status": "ok", "data": {"slug": "smithingplus", "enabled": false, "pending_restart": true}}

# Error response (FastAPI standard)
{"detail": {"code": "MOD_NOT_INSTALLED", "message": "Mod 'xyz' is not installed"}}
```

### Project Structure Notes

**Files to modify:**
```
api/src/vintagestory_api/
├── models/mods.py           # Add EnableResult, DisableResult, RemoveResult
├── services/mods.py         # Add remove_mod, verify enable_mod/disable_mod
└── routers/mods.py          # Add POST /enable, POST /disable, DELETE endpoints
```

**Files to extend (tests):**
```
api/tests/
├── test_mod_service.py      # Add remove_mod tests, idempotent tests
└── test_mods_router.py      # Add enable/disable/remove endpoint tests
```

### Previous Story Intelligence (5.1, 5.2, 5.3)

**Key patterns established:**
- `enable_mod()` and `disable_mod()` already exist in ModService (5.1) - verify and extend
- File suffix approach (`.zip.disabled`) for disable state
- `ModStateManager.remove_mod(slug)` exists for state removal
- `PendingRestartState` integration via `_maybe_require_restart()` pattern
- `ModNotInstalledError` exception class (5.2) - use for 404 responses
- `require_admin` dependency for write operations (established in Epic 2)

**From 5.1 Code Review:**
- Implemented `_is_safe_zip_path()` for path validation
- Server-mod integration via `set_server_running()` and `clear_restart()`
- Atomic write patterns for state persistence

**From 5.2 Code Review:**
- HTTP client cleanup via `close_mod_service()` in lifespan
- Atomic file copy pattern (temp file + rename)
- Enhanced slug validation with Windows reserved name rejection

**From 5.3 Code Review:**
- Logging for lookup operations - apply same pattern to enable/disable/remove
- Both Admin and Monitor can access read-only operations; writes are Admin-only

### Git Intelligence

**Recent commits establishing patterns:**
- `2af4b55` - docs(story-5.3): mark story as done after code review
- `3e47026` - fix(story-5.3): address code review findings
- `d5a1ae4` - feat(story-5.3): implement mod compatibility validation API

**Commit message format:** `type(scope): description`
- `feat(mods)`: for new functionality
- `fix(mods)`: for bug fixes
- `test(mods)`: for test-only changes

### Error Handling

**Use error codes from models/errors.py:**
```python
from vintagestory_api.models.errors import ErrorCode

# May need to add if not present
ErrorCode.MOD_NOT_INSTALLED = "MOD_NOT_INSTALLED"  # Different from MOD_NOT_FOUND (API lookup)
```

**HTTP exception pattern:**
```python
from fastapi import HTTPException

# 404 Not Found - mod not installed locally
raise HTTPException(
    status_code=404,
    detail={
        "code": ErrorCode.MOD_NOT_INSTALLED,
        "message": f"Mod '{slug}' is not installed",
    }
)

# 403 Forbidden - Monitor attempting write
raise HTTPException(
    status_code=403,
    detail={
        "code": ErrorCode.FORBIDDEN,
        "message": "Admin role required for this operation",
    }
)
```

**Error code distinction:**
- `MOD_NOT_FOUND`: Remote mod doesn't exist in VintageStory database (5.3 lookup)
- `MOD_NOT_INSTALLED`: Mod not present in local installation (this story)

### Idempotency Requirements

Enable/disable operations should be idempotent:
- `enable_mod()` on already-enabled mod: Return success, no state change
- `disable_mod()` on already-disabled mod: Return success, no state change

This prevents errors from duplicate API calls and simplifies frontend logic.

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md` - Full architecture (Epic 5 section)
- `_bmad-output/implementation-artifacts/5-1-mod-service-and-state-management.md` - enable/disable patterns
- `_bmad-output/implementation-artifacts/5-2-mod-installation-api.md` - file operation patterns
- `_bmad-output/implementation-artifacts/5-3-mod-compatibility-validation.md` - error handling patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 5.4: Mod Enable/Disable and Remove API]

---

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

- VintageStory path issue diagnosed via `server-main.log` grep for "Not found"
- API startup logging enhanced to show command, cwd, and path configuration

### Completion Notes List

- All three endpoints implemented: enable, disable, remove
- Idempotent behavior verified for enable/disable
- Remove correctly handles both `.zip` and `.zip.disabled` files
- During manual testing, discovered VintageStory ignores `--dataPath` after first run in favor of `serverconfig.json` values
- Created `agentdocs/vs-server-troubleshooting.md` documenting this behavior
- Added polish backlog item API-012 for serverconfig.json parsing/validation

### File List

- `api/src/vintagestory_api/models/mods.py` - Added EnableResult, DisableResult, RemoveResult
- `api/src/vintagestory_api/services/mods.py` - Updated enable_mod, disable_mod; added remove_mod
- `api/src/vintagestory_api/routers/mods.py` - Added enable, disable, remove endpoints
- `api/src/vintagestory_api/services/server.py` - Enhanced startup logging
- `api/tests/test_mod_service.py` - Added remove_mod tests, idempotent behavior tests
- `api/tests/test_mods_router.py` - Added endpoint tests for enable/disable/remove
- `agentdocs/vs-server-troubleshooting.md` - New troubleshooting documentation
- `project-context.md` - Added reference to troubleshooting doc
- `_bmad-output/implementation-artifacts/polish-backlog.md` - Added API-012

