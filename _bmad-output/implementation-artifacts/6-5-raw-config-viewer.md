# Story 6.5: Raw Config Viewer

Status: ready-for-dev

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator or monitor**,
I want **read-only access to raw configuration files**,
So that **I can troubleshoot configuration issues**.

## Acceptance Criteria

1. **Given** I call `GET /api/v1alpha1/config/files` as Admin or Monitor, **When** config files exist in the data directory, **Then** I receive a list of configuration file names.

2. **Given** I call `GET /api/v1alpha1/config/files/serverconfig.json`, **When** the file exists, **Then** I receive the raw JSON content.

3. **Given** I request a file with path traversal (e.g., `../secrets.json`), **When** the API validates the path, **Then** I receive a 400 error and the request is rejected.

## Tasks / Subtasks

<!--
CRITICAL TASK STRUCTURE RULES:
1. Each functional task MUST include "+ tests" in its name
2. Do NOT create separate "Write tests" tasks at the end
3. A task is NOT complete until its tests pass
4. Tests verify the specific AC listed for that task

CORRECT PATTERN:
- [ ] Task 1: Implement user login endpoint + tests (AC: 1, 2)
  - [ ] Create login route handler
  - [ ] Add input validation
  - [ ] Write tests for success/failure cases

WRONG PATTERN (tests batched at end):
- [ ] Task 1: Implement user login endpoint (AC: 1, 2)
- [ ] Task 2: Implement logout endpoint (AC: 3)
- [ ] Task 3: Write all tests  <- NEVER DO THIS
-->

- [x] Task 1: Create ConfigFilesService with list and read methods + tests (AC: 1, 2, 3)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/services/config_files.py`
  - [x] Subtask 1.2: Implement `list_files()` method - scan `serverdata_dir` for JSON files
  - [x] Subtask 1.3: Implement `read_file(filename)` method - return raw file content
  - [x] Subtask 1.4: Implement path traversal validation using `_safe_path()` pattern from ServerService
  - [x] Subtask 1.5: Write comprehensive tests including path traversal attack vectors

- [ ] Task 2: Add error codes for config files + tests (AC: 3)
  - [ ] Subtask 2.1: Add `CONFIG_FILE_NOT_FOUND` to `api/src/vintagestory_api/models/errors.py`
  - [ ] Subtask 2.2: Add `CONFIG_PATH_INVALID` for path traversal attempts
  - [ ] Subtask 2.3: Verify error codes are consistent with existing patterns

- [ ] Task 3: Create /config/files router endpoints + tests (AC: 1, 2, 3)
  - [ ] Subtask 3.1: Add list endpoint: `GET /api/v1alpha1/config/files`
  - [ ] Subtask 3.2: Add read endpoint: `GET /api/v1alpha1/config/files/{filename}`
  - [ ] Subtask 3.3: Ensure both Admin and Monitor roles can access (read-only)
  - [ ] Subtask 3.4: Write router tests for success, 404, and path traversal cases

- [ ] Task 4: Run full test suite and verify + tests (AC: 1, 2, 3)
  - [ ] Subtask 4.1: Run `just check` to verify lint, typecheck, and all tests pass
  - [ ] Subtask 4.2: Manual test: GET /config/files returns list
  - [ ] Subtask 4.3: Manual test: GET /config/files/serverconfig.json returns content
  - [ ] Subtask 4.4: Manual test: GET /config/files/../../etc/passwd returns 400

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

**PATH TRAVERSAL PREVENTION IS THE CORE SECURITY REQUIREMENT FOR THIS STORY.**

The existing `_safe_path()` pattern from ServerService MUST be reused:

```python
def _safe_path(self, base_dir: Path, filename: str) -> Path:
    """Create a safe file path, preventing path traversal attacks.

    Uses Path.resolve() to detect path traversal attempts including:
    - ../etc/passwd (simple parent traversal)
    - subdir/../../etc/passwd (nested traversal)
    - /absolute/path (absolute paths)
    """
    base_resolved = base_dir.resolve()
    target = (base_dir / filename).resolve()

    try:
        target.relative_to(base_resolved)
    except ValueError:
        raise ValueError(f"Path traversal detected: {filename} escapes {base_dir}") from None

    return target
```

**Source:** [api/src/vintagestory_api/services/server.py:489-514]

**Security test cases to implement:**
- `../secrets.json` - simple parent traversal
- `subdir/../../secrets.json` - nested traversal
- `/etc/passwd` - absolute path
- `%2e%2e%2fsecrets.json` - URL-encoded traversal
- `....//secrets.json` - double-dot variations

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api` - Run API tests only
- `just test-api -k "config_files"` - Run specific pattern
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Config Files Location:** `settings.serverdata_dir` (`/data/serverdata/`)

This is where VintageStory stores its configuration:
- `serverconfig.json` - Main server configuration
- Other JSON files the game server may create

**Response Format (from architecture.md):**

List endpoint:
```json
{
  "status": "ok",
  "data": {
    "files": ["serverconfig.json", "other-config.json"]
  }
}
```

Read endpoint:
```json
{
  "status": "ok",
  "data": {
    "filename": "serverconfig.json",
    "content": { /* raw JSON from file */ }
  }
}
```

**Router Pattern (from existing config.py):**
- Use `RequireAuth` type alias for both Admin and Monitor access
- Use consistent error response format with ErrorCode
- Follow existing dependency injection patterns

### Previous Story Intelligence (Story 6.4)

**Key learnings from 6.4:**

1. **API Response consistency** - Use `ApiResponse(status="ok", data=...)` pattern
2. **Error handling pattern** - Catch service exceptions, convert to HTTPException
3. **Router organization** - Add to existing `config.py` router with new endpoints
4. **Testing approach** - Test both success cases and error cases (400, 404)

**Files modified in Story 6.4:**
- `api/src/vintagestory_api/routers/config.py` - Add new endpoints here
- `web/src/features/settings/SettingsPage.tsx` - Has File Manager stub

### Git Intelligence (Recent Commits)

Recent relevant commits:
- `ee1df49` - docs: fix WebSocket path in CLAUDE.md (API-016)
- `2fd4ec7` - Merge story/6-4-settings-ui
- `7f3b93b` - feat(api): implement auto_start_server functionality
- `d53e183` - fix(story-6.4): address code review feedback

**Pattern from recent commits:**
- Feature commits use: `feat(story-X.Y/task-N): description`
- Fix commits use: `fix(story-X.Y/review): description`

### Project Structure Notes

**New files to create:**
- `api/src/vintagestory_api/services/config_files.py` - Service class
- `api/tests/test_config_files.py` - Service and router tests

**Files to modify:**
- `api/src/vintagestory_api/routers/config.py` - Add `/config/files` endpoints
- `api/src/vintagestory_api/models/errors.py` - Add new error codes

**Existing code to reuse:**
- `ServerService._safe_path()` pattern [server.py:489-514]
- `ModStateService._is_safe_zip_path()` pattern [mod_state.py:236-259]
- Router tests pattern from `api/tests/test_config.py`

### File List Reference

**serverdata_dir contains:**
- `serverconfig.json` - Primary game server configuration
- Potentially other JSON files depending on server state

**Only return JSON files** - Filter to `*.json` extension in list method.

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md#raw-config-files-config-files` - API design
- `_bmad-output/implementation-artifacts/6-4-settings-ui.md` - Previous story patterns
- `api/src/vintagestory_api/services/server.py` - Path validation pattern
- `api/tests/server/test_validation.py` - Path traversal test examples

## Dev Agent Record

### Agent Model Used

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

