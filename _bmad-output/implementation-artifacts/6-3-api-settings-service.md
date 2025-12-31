# Story 6.3: API Settings Service

Status: complete

## Story

As an **administrator**,
I want **to view and update API operational settings**,
So that **I can configure auto-start, refresh intervals, and environment handling**.

## Acceptance Criteria

1. **Given** I call `GET /api/v1alpha1/config/api` as Admin, **When** api-settings.json exists (or defaults are used), **Then** I receive current API settings: auto_start_server, block_env_managed_settings, refresh intervals.

2. **Given** I call `POST /api/v1alpha1/config/api/settings/auto_start_server` with `{"value": true}`, **When** the request is valid, **Then** the setting is saved to api-settings.json, **And** the response confirms the update.

3. **Given** I update mod_list_refresh_interval, **When** the scheduler is running (Epic 7+), **Then** the job is rescheduled with the new interval. *(Note: Scheduler integration is Epic 7 - stub the interface for now)*

4. **Given** I am authenticated as Monitor, **When** I call GET /api/v1alpha1/config/api, **Then** I receive a 403 Forbidden (API settings are Admin-only).

## Tasks / Subtasks

- [x] Task 1: Create ApiSettingsService + tests (AC: 1, 2)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/services/api_settings.py` with ApiSettingsService class
  - [x] Subtask 1.2: Define `ApiSettings` Pydantic model with defaults matching architecture spec
  - [x] Subtask 1.3: Implement `get_settings()` method - reads api-settings.json or returns defaults
  - [x] Subtask 1.4: Implement `update_setting()` method - validates, persists, and returns result
  - [x] Subtask 1.5: Implement atomic file writes (temp file + rename pattern)
  - [x] Subtask 1.6: Add setting validation (e.g., intervals must be positive integers)
  - [x] Subtask 1.7: Write tests for get_settings() - returns defaults when file missing
  - [x] Subtask 1.8: Write tests for get_settings() - reads existing file correctly
  - [x] Subtask 1.9: Write tests for update_setting() - validates and persists setting
  - [x] Subtask 1.10: Write tests for validation errors (negative intervals, unknown keys)

- [x] Task 2: Add /config/api router + tests (AC: 1, 2, 4)
  - [x] Subtask 2.1: Add `/config/api` GET endpoint to existing `routers/config.py`
  - [x] Subtask 2.2: Add `POST /config/api/settings/{key}` endpoint for setting updates
  - [x] Subtask 2.3: Add Admin-only authorization (require_admin dependency)
  - [x] Subtask 2.4: Write integration tests for GET endpoint
  - [x] Subtask 2.5: Write integration tests for POST endpoint
  - [x] Subtask 2.6: Write integration tests for RBAC (Monitor blocked from all API settings endpoints)

- [x] Task 3: Add API settings error codes + tests (AC: 2)
  - [x] Subtask 3.1: Add API_SETTING_UNKNOWN, API_SETTING_INVALID to ErrorCode class if not present
  - [x] Subtask 3.2: Write tests verifying error codes in error responses

- [x] Task 4: Add scheduler interface stub (AC: 3)
  - [x] Subtask 4.1: Add optional scheduler_callback parameter to ApiSettingsService
  - [x] Subtask 4.2: Call callback when refresh interval settings change (stub for Epic 7)
   - [x] Subtask 4.3: Add test verifying callback is invoked on interval change

### Review Follow-ups (AI)
- [x] [AI-Review][MEDIUM] Fix typo in ApiSettings model docstring: "refreshes" → "refreshes" (api_settings.py:43) - **No action needed**: Review finding appears to be false positive (both words identical)
- [x] [AI-Review][MEDIUM] Test timing documentation discrepancy: Update completion notes to reflect actual new test count (39: 24 service + 15 router)
- [x] [AI-Review][MEDIUM] Document scheduler integration pattern for Epic 7: Add TODO comment in config.py explaining how to wire scheduler callback when Epic 7 is implemented
- [x] [AI-Review][LOW-MEDIUM] Refactor error codes section: Add docstring in errors.py explaining SETTING_* vs API_SETTING_* scope
- [x] [AI-Review][LOW-MEDIUM] Enhance logging context: Add old_value and source fields to api_setting_updated log
- [x] [AI-Review][LOW-MEDIUM] Add error handling to _save_settings(): Wrap write operations in try/except OSError
- [x] [AI-Review][LOW] Rename test class: TestApiSettingsResponseFormat → TestConfigResponseFormat or split into TestGameSettingsResponseFormat and TestApiSettingsResponseFormat - **Renamed TestConfigAPIResponseFormat → TestGameSettingsResponseFormat for clarity**
- [x] [AI-Review][LOW] Add docstring to get_api_settings_service(): Match pattern of get_game_config_service()
- [x] [AI-Review][LOW] Document graceful degradation strategy: Add comment explaining why get_settings() returns defaults on JSON/ValidationError
- [x] [AI-Review][LOW] Add edge case comment: Document why validated_value is safe for scheduler callback (validation happens before callback)

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- API settings endpoints are Admin-only (no Monitor access)
- Use `RequireAdmin` dependency from `middleware/permissions.py`
- Never log sensitive data in plaintext
- RBAC patterns for endpoint protection

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api -k "api_settings"` - Run API settings tests specifically
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**API Settings File Location:**
- File path: `settings.data_dir / "state" / "api-settings.json"` (same pattern as state.json)
- Use `settings.data_dir` from `vintagestory_api.config.Settings`

**ApiSettings Model (from architecture.md):**

```python
from pydantic import BaseModel, Field

class ApiSettings(BaseModel):
    """API server operational settings."""

    auto_start_server: bool = Field(
        default=False,
        description="Start game server automatically when API launches"
    )
    block_env_managed_settings: bool = Field(
        default=True,
        description="Reject UI changes to settings controlled by VS_CFG_* env vars"
    )
    enforce_env_on_restart: bool = Field(
        default=False,
        description="Re-apply VS_CFG_* values on each game server restart (backlog)"
    )
    mod_list_refresh_interval: int = Field(
        default=3600,
        ge=0,
        description="Seconds between mod API cache refreshes (0 = disabled)"
    )
    server_versions_refresh_interval: int = Field(
        default=86400,
        ge=0,
        description="Seconds between checking for new VS versions (0 = disabled)"
    )
```

**Scheduler Integration Pattern (Epic 7):**

For now, stub the scheduler interface with a callback:

```python
from typing import Callable, Optional

class ApiSettingsService:
    def __init__(
        self,
        settings: Settings,
        scheduler_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self._settings = settings
        self._scheduler_callback = scheduler_callback

    async def update_setting(self, key: str, value: Any) -> dict:
        # ... validation and persistence ...

        # Notify scheduler if refresh interval changed
        if key in ("mod_list_refresh_interval", "server_versions_refresh_interval"):
            if self._scheduler_callback:
                self._scheduler_callback(key, value)

        return result
```

### API Response Format

**GET /api/v1alpha1/config/api:**

```json
{
  "status": "ok",
  "data": {
    "settings": {
      "auto_start_server": false,
      "block_env_managed_settings": true,
      "enforce_env_on_restart": false,
      "mod_list_refresh_interval": 3600,
      "server_versions_refresh_interval": 86400
    }
  }
}
```

**POST /api/v1alpha1/config/api/settings/{key}:**

Request:
```json
{
  "value": true
}
```

Response (success):
```json
{
  "status": "ok",
  "data": {
    "key": "auto_start_server",
    "value": true
  }
}
```

Response (unknown setting):
```json
{
  "status": "error",
  "detail": {
    "code": "API_SETTING_UNKNOWN",
    "message": "Unknown API setting: 'invalid_key'"
  }
}
```

Response (invalid value):
```json
{
  "status": "error",
  "detail": {
    "code": "API_SETTING_INVALID",
    "message": "Invalid value for 'mod_list_refresh_interval': must be a non-negative integer"
  }
}
```

### Previous Story Intelligence (Story 6.2)

From `6-2-game-settings-api.md`:

1. **GameConfigService pattern** - Use same structure for ApiSettingsService
2. **Router pattern** - Add to existing `routers/config.py` (don't create new file)
3. **Atomic writes** - Use temp file + rename pattern (same as game config)
4. **Error handling** - Follow pattern from game_config.py with custom exception classes
5. **Type validation** - Use `parse_env_value` from config_init.py for consistency
6. **RBAC** - Use `RequireAdmin` dependency for all endpoints

**Key difference from Story 6.2:**
- API settings are Admin-only (Monitor cannot read)
- No console command integration (direct file persistence)
- Simpler update logic (no live vs restart-required distinction)

### Existing Code to Reuse

**File: `api/src/vintagestory_api/services/game_config.py`**
- Pattern for service structure
- Error exception class pattern
- Atomic file write implementation

**File: `api/src/vintagestory_api/routers/config.py`**
- Existing router to extend with /config/api endpoints
- Pattern for SettingUpdateRequest model

**File: `api/src/vintagestory_api/middleware/permissions.py`**
- `RequireAdmin` dependency for Admin-only endpoints

**File: `api/src/vintagestory_api/config.py`**
- `Settings` class with `data_dir` property

### Project Structure Notes

**New files to create:**
- `api/src/vintagestory_api/services/api_settings.py` - ApiSettingsService class
- `api/tests/test_api_settings.py` - Service tests

**Files to modify:**
- `api/src/vintagestory_api/routers/config.py` - Add /config/api endpoints
- `api/src/vintagestory_api/models/errors.py` - Add API settings error codes (if needed)
- `api/tests/test_routers_config.py` - Add API settings router tests

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/6-3-api-settings-service

# Task-level commits
git commit -m "feat(story-6.3/task-1): create ApiSettingsService with settings model"
git commit -m "feat(story-6.3/task-2): add /config/api router endpoints"
git commit -m "feat(story-6.3/task-3): add API settings error codes"
git commit -m "feat(story-6.3/task-4): add scheduler interface stub"

# Push and create PR
git push -u origin story/6-3-api-settings-service
gh pr create --title "Story 6.3: API Settings Service" --body "..."
```

### Service Implementation Pattern

```python
"""API settings service for management API configuration.

Story 6.3: API Settings Service
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable, Optional

import structlog

from vintagestory_api.config import Settings
from pydantic import BaseModel, Field, ValidationError

logger = structlog.get_logger()


class ApiSettings(BaseModel):
    """API server operational settings."""

    auto_start_server: bool = Field(default=False)
    block_env_managed_settings: bool = Field(default=True)
    enforce_env_on_restart: bool = Field(default=False)
    mod_list_refresh_interval: int = Field(default=3600, ge=0)
    server_versions_refresh_interval: int = Field(default=86400, ge=0)


class ApiSettingUnknownError(Exception):
    """Raised when an unknown API setting key is requested."""
    pass


class ApiSettingInvalidError(Exception):
    """Raised when an invalid value is provided for an API setting."""
    pass


class ApiSettingsService:
    """Service for managing API operational settings."""

    def __init__(
        self,
        settings: Settings,
        scheduler_callback: Optional[Callable[[str, int], None]] = None,
    ):
        self._settings = settings
        self._scheduler_callback = scheduler_callback
        self._settings_file = self._settings.data_dir / "state" / "api-settings.json"

    def get_settings(self) -> ApiSettings:
        """Get current API settings (from file or defaults)."""
        if not self._settings_file.exists():
            return ApiSettings()

        try:
            content = self._settings_file.read_text()
            data = json.loads(content)
            return ApiSettings(**data)
        except (json.JSONDecodeError, ValidationError) as e:
            logger.warning("api_settings_load_failed", error=str(e))
            return ApiSettings()

    async def update_setting(self, key: str, value: Any) -> dict:
        """Update a single API setting."""
        # Validate key exists
        if key not in ApiSettings.model_fields:
            raise ApiSettingUnknownError(f"Unknown API setting: '{key}'")

        # Get current settings
        current = self.get_settings()

        # Validate and update
        try:
            setattr(current, key, value)
            # Re-validate with Pydantic
            current = ApiSettings(**current.model_dump())
        except ValidationError as e:
            raise ApiSettingInvalidError(str(e))

        # Persist with atomic write
        self._save_settings(current)

        # Notify scheduler if interval changed
        if key in ("mod_list_refresh_interval", "server_versions_refresh_interval"):
            if self._scheduler_callback:
                self._scheduler_callback(key, value)

        return {"key": key, "value": getattr(current, key)}

    def _save_settings(self, settings: ApiSettings) -> None:
        """Save settings with atomic write pattern."""
        # Ensure directory exists
        self._settings_file.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write: temp file then rename
        temp_file = self._settings_file.with_suffix(".tmp")
        temp_file.write_text(json.dumps(settings.model_dump(), indent=2))
        temp_file.rename(self._settings_file)

        logger.info("api_settings_saved")
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md#epic-6-game-configuration-management-architecture` - Full architecture details
- `_bmad-output/implementation-artifacts/6-2-game-settings-api.md` - Previous story patterns
- `api/src/vintagestory_api/services/game_config.py` - GameConfigService patterns to follow
- `api/src/vintagestory_api/routers/config.py` - Existing config router to extend

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Implementation completed without issues.

### Completion Notes List

- ✅ Created ApiSettingsService with full Pydantic model validation
- ✅ Implemented get_settings() with defaults when file missing
- ✅ Implemented update_setting() with type coercion and validation
- ✅ Added atomic file writes using temp file + rename pattern
- ✅ Added scheduler_callback stub for Epic 7 integration
- ✅ Added GET /config/api endpoint (Admin only)
- ✅ Added POST /config/api/settings/{key} endpoint (Admin only)
- ✅ Added API_SETTING_UNKNOWN and API_SETTING_INVALID error codes
- ✅ All 4 acceptance criteria satisfied
- ✅ All tests pass (39 new tests: 24 service + 15 router)

### Change Log

- 2025-12-31: Story implementation complete (Opus 4.5)
- 2025-12-31: Code review completed - Found 10 issues (0 Critical, 6 Medium, 4 Low). All acceptance criteria implemented, 41 tests passing. Status changed to in-progress pending action items.
- 2025-12-31: All 10 review follow-up items addressed (Opus 4.5). Status changed to complete.

### File List

**New Files:**
- `api/src/vintagestory_api/services/api_settings.py` - ApiSettingsService class
- `api/tests/test_api_settings.py` - 24 service unit tests

**Modified Files:**
- `api/src/vintagestory_api/routers/config.py` - Added /config/api endpoints
- `api/src/vintagestory_api/models/errors.py` - Added API settings error codes
- `api/tests/test_routers_config.py` - Added 15 API settings router tests
- `_bmad-output/implementation-artifacts/sprint-status.yaml` - Updated story status
