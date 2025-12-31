# Story 6.2: Game Settings API

Status: done

## Story

As an **administrator**,
I want **to view and update game server settings through the API**,
So that **I can configure the server using console commands for live updates**.

## Acceptance Criteria

1. **Given** I call `GET /api/v1alpha1/config/game` as Admin or Monitor, **When** serverconfig.json exists, **Then** I receive settings with metadata (key, value, type, live_update, env_managed), **And** the response includes source_file and last_modified.

2. **Given** I call `POST /api/v1alpha1/config/game/settings/ServerName` with `{"value": "New Name"}`, **When** the game server is running, **Then** the API executes `/serverconfig Name "New Name"` via console, **And** the response includes `method: "console_command"` and `pending_restart: false`.

3. **Given** I call `POST /api/v1alpha1/config/game/settings/Port` with `{"value": 42421}`, **When** the game server is running, **Then** the setting is written to serverconfig.json (Port requires restart), **And** the response includes `method: "file_update"` and `pending_restart: true`.

4. **Given** I attempt to update a setting managed by VS_CFG_* environment variable, **When** block_env_managed_settings is true (default), **Then** I receive a 400 error with code SETTING_ENV_MANAGED, **And** the error message identifies the controlling environment variable.

5. **Given** I am authenticated as Monitor, **When** I attempt to POST a setting update, **Then** I receive a 403 Forbidden.

## Tasks / Subtasks

- [x] Task 1: Create GameConfigService + tests (AC: 1, 2, 3, 4)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/services/game_config.py` with GameConfigService class
  - [x] Subtask 1.2: Implement `LIVE_SETTINGS` dict with ServerSetting model (key, value_type, console_command, requires_restart)
  - [x] Subtask 1.3: Implement `get_settings()` method - reads serverconfig.json and enriches with metadata
  - [x] Subtask 1.4: Implement `update_setting()` method - console command for live settings, file update for restart-required
  - [x] Subtask 1.5: Implement `_execute_console_command()` - uses ServerService.send_command()
  - [x] Subtask 1.6: Implement `_update_config_file()` - atomic write for file-based updates
  - [x] Subtask 1.7: Write tests for get_settings() - returns enriched settings with metadata
  - [x] Subtask 1.8: Write tests for update_setting() with live update path
  - [x] Subtask 1.9: Write tests for update_setting() with file update path
  - [x] Subtask 1.10: Write tests for env-managed setting blocking

- [x] Task 2: Add /config/game router + tests (AC: 1, 2, 3, 4, 5)
  - [x] Subtask 2.1: Create `api/src/vintagestory_api/routers/config.py` with config router
  - [x] Subtask 2.2: Implement `GET /config/game` endpoint - returns settings with metadata
  - [x] Subtask 2.3: Implement `POST /config/game/settings/{key}` endpoint - updates setting
  - [x] Subtask 2.4: Add Monitor + Admin auth for GET (read-only)
  - [x] Subtask 2.5: Add Admin-only auth for POST (write operations)
  - [x] Subtask 2.6: Register router in main.py
  - [x] Subtask 2.7: Write integration tests for GET endpoint
  - [x] Subtask 2.8: Write integration tests for POST endpoint with live update
  - [x] Subtask 2.9: Write integration tests for POST endpoint with file update
  - [x] Subtask 2.10: Write integration tests for RBAC (Monitor blocked from POST)

- [x] Task 3: Add Epic 6 error codes + tests (AC: 4)
  - [x] Subtask 3.1: Add SETTING_UNKNOWN, SETTING_ENV_MANAGED, SETTING_UPDATE_FAILED to ErrorCode class
  - [x] Subtask 3.2: Write tests verifying error codes in error responses

- [x] Task 4: Integrate pending restart state + tests (AC: 3)
  - [x] Subtask 4.1: Inject PendingRestartState into GameConfigService
  - [x] Subtask 4.2: Call require_restart() when file-based update occurs
  - [x] Subtask 4.3: Write tests verifying pending restart flag is set for restart-required settings

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
- Never log sensitive data in plaintext (especially Password setting)
- Proxy-aware client IP logging
- RBAC patterns for endpoint protection

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api -k "game_config"` - Run game config tests specifically
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Epic 6 Architectural Pivot:** This story implements the Game Settings API using console commands for live updates.

**Two Update Methods:**
1. **Console command (live update):** When server is running and setting supports live update, execute `/serverconfig` command via `ServerService.send_command()`
2. **File update (restart required):** When server is stopped OR setting requires restart, edit `serverconfig.json` atomically and set pending restart flag

**Key Architectural Decisions:**
- Frontend NEVER sees console commands - only sends key/value pairs
- API determines update method based on server state and setting type
- Console commands auto-persist to serverconfig.json (VintageStory behavior)
- Env-managed settings (VS_CFG_*) are blocked by default

**LIVE_SETTINGS Map (from architecture.md):**

```python
LIVE_SETTINGS = {
    "ServerName": ServerSetting(
        key="ServerName",
        value_type="string",
        console_command='/serverconfig name "{value}"',
        live_update=True
    ),
    "ServerDescription": ServerSetting(
        key="ServerDescription",
        value_type="string",
        console_command='/serverconfig description "{value}"',
        live_update=True
    ),
    "WelcomeMessage": ServerSetting(
        key="WelcomeMessage",
        value_type="string",
        console_command='/serverconfig motd "{value}"',
        live_update=True
    ),
    "MaxClients": ServerSetting(
        key="MaxClients",
        value_type="int",
        console_command='/serverconfig maxclients {value}',
        live_update=True
    ),
    "MaxChunkRadius": ServerSetting(
        key="MaxChunkRadius",
        value_type="int",
        console_command='/serverconfig maxchunkradius {value}',
        live_update=True
    ),
    "Password": ServerSetting(
        key="Password",
        value_type="string",
        console_command='/serverconfig password "{value}"',
        live_update=True
    ),
    "AllowPvP": ServerSetting(
        key="AllowPvP",
        value_type="bool",
        console_command='/serverconfig allowpvp {value}',
        live_update=True
    ),
    "AllowFireSpread": ServerSetting(
        key="AllowFireSpread",
        value_type="bool",
        console_command='/serverconfig allowfirespread {value}',
        live_update=True
    ),
    "AllowFallingBlocks": ServerSetting(
        key="AllowFallingBlocks",
        value_type="bool",
        console_command='/serverconfig allowfallingblocks {value}',
        live_update=True
    ),
    "EntitySpawning": ServerSetting(
        key="EntitySpawning",
        value_type="bool",
        console_command='/serverconfig entityspawning {value}',
        live_update=True
    ),
    "PassTimeWhenEmpty": ServerSetting(
        key="PassTimeWhenEmpty",
        value_type="bool",
        console_command='/serverconfig passtimewhenempty {value}',
        live_update=True
    ),
    "Upnp": ServerSetting(
        key="Upnp",
        value_type="bool",
        console_command='/serverconfig upnp {value}',  # uses 0/1
        live_update=True
    ),
    "AdvertiseServer": ServerSetting(
        key="AdvertiseServer",
        value_type="bool",
        console_command='/serverconfig advertise {value}',  # uses 0/1
        live_update=True
    ),
    # Restart-required settings (no console_command)
    "Port": ServerSetting(
        key="Port",
        value_type="int",
        console_command=None,
        requires_restart=True,
        live_update=False
    ),
    "Ip": ServerSetting(
        key="Ip",
        value_type="string",
        console_command=None,
        requires_restart=True,
        live_update=False
    ),
    # ... more settings
}
```

**Boolean Syntax Variations:** The API must normalize boolean values to correct command syntax:
- `true/false` for: allowpvp, allowfirespread, allowfallingblocks, entityspawning, passtimewhenempty
- `0/1` for: upnp, advertise, temporaryipblocklist, loginfloodprotection

### Previous Story Intelligence (Story 6.1)

From `6-1-config-init-service-and-template.md`:

1. **ConfigInitService already exists** at `api/src/vintagestory_api/services/config_init_service.py`
2. **ENV_VAR_MAP exists** at `api/src/vintagestory_api/services/config_init.py` with 40+ mappings
3. **Config path:** `settings.serverdata_dir / "serverconfig.json"` (NOT `settings.data_dir / "config"`)
4. **Atomic write pattern:** Use temp file + rename for all config file updates
5. **Quote stripping:** Env var values may have surrounding quotes from docker-compose

**DO NOT recreate existing functionality - reuse ConfigInitService patterns.**

### ServerService Integration

**Key methods to use from ServerService:**

```python
# Check if server is running (use _get_runtime_state)
from vintagestory_api.models.responses import ServerState

# In GameConfigService:
def _is_server_running(self) -> bool:
    """Check if game server is currently running."""
    state = self._server_service._get_runtime_state()
    return state == ServerState.RUNNING

# Send console command
await self._server_service.send_command('/serverconfig name "New Name"')
```

**Console output:** Commands echo to console buffer with `[CMD]` prefix (see server.py:1133-1167)

### API Response Format

**GET /api/v1alpha1/config/game:**

```json
{
  "status": "ok",
  "data": {
    "settings": [
      {
        "key": "ServerName",
        "value": "My Server",
        "type": "string",
        "live_update": true,
        "env_managed": false
      },
      {
        "key": "Port",
        "value": 42420,
        "type": "int",
        "live_update": false,
        "requires_restart": true,
        "env_managed": false
      },
      {
        "key": "MaxClients",
        "value": 16,
        "type": "int",
        "live_update": true,
        "env_managed": true,
        "env_var": "VS_CFG_MAX_CLIENTS"
      }
    ],
    "source_file": "serverconfig.json",
    "last_modified": "2025-12-30T10:00:00Z"
  }
}
```

**POST /api/v1alpha1/config/game/settings/{key}:**

Request:
```json
{
  "value": "New Server Name"
}
```

Response (live update):
```json
{
  "status": "ok",
  "data": {
    "key": "ServerName",
    "value": "New Server Name",
    "method": "console_command",
    "pending_restart": false
  }
}
```

Response (file update - restart required):
```json
{
  "status": "ok",
  "data": {
    "key": "Port",
    "value": 42421,
    "method": "file_update",
    "pending_restart": true
  }
}
```

Response (env managed - blocked):
```json
{
  "status": "error",
  "error": {
    "code": "SETTING_ENV_MANAGED",
    "message": "Setting 'MaxClients' is managed by environment variable VS_CFG_MAX_CLIENTS"
  }
}
```

### Existing Code to Reuse

**File: `api/src/vintagestory_api/services/config_init.py`**
```python
# Already provides:
ENV_VAR_MAP: dict[str, tuple[str, Literal["string", "int", "bool", "float"]]]
parse_env_value(value: str, value_type: str) -> Any
get_config_key_path(key: str) -> list[str]
```

**File: `api/src/vintagestory_api/services/pending_restart.py`**
```python
# Already provides:
class PendingRestartState:
    pending_restart: bool
    pending_changes: list[str]
    def require_restart(self, reason: str) -> None
    def clear_restart(self) -> None
```

**File: `api/src/vintagestory_api/services/server.py`**
```python
# Already provides:
async def send_command(self, command: str) -> bool  # line 1133
def _get_runtime_state(self) -> ServerState  # line 824
def is_installed(self) -> bool  # line 435
```

### Project Structure Notes

**New files to create:**
- `api/src/vintagestory_api/services/game_config.py` - GameConfigService class
- `api/src/vintagestory_api/routers/config.py` - Config router
- `api/tests/test_game_config.py` - Service tests
- `api/tests/test_routers_config.py` - Router integration tests

**Files to modify:**
- `api/src/vintagestory_api/models/errors.py` - Add Epic 6 error codes
- `api/src/vintagestory_api/main.py` - Register config router

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/6-2-game-settings-api

# Task-level commits
git commit -m "feat(story-6.2/task-1): create GameConfigService with LIVE_SETTINGS"
git commit -m "feat(story-6.2/task-2): add /config/game router endpoints"
git commit -m "feat(story-6.2/task-3): add Epic 6 error codes"
git commit -m "feat(story-6.2/task-4): integrate pending restart state"

# Push and create PR
git push -u origin story/6-2-game-settings-api
gh pr create --title "Story 6.2: Game Settings API" --body "..."
```

### ServerSetting Model Definition

```python
from typing import Literal, Optional
from pydantic import BaseModel

class ServerSetting(BaseModel):
    """Definition of a server setting with update behavior."""
    key: str
    value_type: Literal["string", "int", "bool", "float"]
    console_command: Optional[str] = None  # Template with {value} placeholder
    requires_restart: bool = False
    live_update: bool = True  # False if no console command
    env_var_override: Optional[str] = None  # VS_CFG_* env var name if managed
```

### Env-Managed Setting Detection

To determine if a setting is env-managed, check `ENV_VAR_MAP` for any mapping that targets this setting key:

```python
from vintagestory_api.services.config_init import ENV_VAR_MAP
import os

def get_env_var_for_setting(key: str) -> Optional[str]:
    """Get env var name that manages this setting, if any."""
    for env_var, (config_key, _) in ENV_VAR_MAP.items():
        if config_key == key and env_var in os.environ:
            return env_var
    return None
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md#epic-6-game-configuration-management-architecture` - Full architecture details
- `agentdocs/vs-serverconfig-commands.md` - Console command reference
- `api/src/vintagestory_api/services/config_init.py` - ENV_VAR_MAP and helper functions
- `api/src/vintagestory_api/services/config_init_service.py` - ConfigInitService for patterns
- `api/src/vintagestory_api/services/pending_restart.py` - PendingRestartState
- `api/src/vintagestory_api/services/server.py` - ServerService for console/state integration

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A

### Completion Notes List

- Task 1: Created GameConfigService with LIVE_SETTINGS dict containing 15 settings (13 live, 2 restart-required). Service supports console command updates for running server, file updates for stopped server or restart-required settings.
- Task 2: Created config router with GET /config/game and POST /config/game/settings/{key} endpoints. GET returns all settings with metadata, POST updates via console or file.
- Task 3: Added SETTING_UNKNOWN, SETTING_ENV_MANAGED, SETTING_UPDATE_FAILED error codes to ErrorCode class.
- Task 4: PendingRestartState injected into service, require_restart() called for restart-required settings.

### File List

New files:
- api/src/vintagestory_api/services/game_config.py
- api/src/vintagestory_api/routers/config.py
- api/tests/test_game_config.py
- api/tests/test_routers_config.py

Modified files:
- api/src/vintagestory_api/models/errors.py (added Epic 6 error codes)
- api/src/vintagestory_api/main.py (registered config router)

### Change Log

- 2025-12-30: Story 6.2 implementation complete - Game Settings API with console commands for live updates

### Review Follow-ups (AI)

Issues found during code review on 2025-12-30:

#### High Priority Issues

- [x] [AI-Review][HIGH] Fix command injection vulnerability: String values in console commands aren't sanitized, allowing potential injection via quotes (e.g., value: 'Test"; malicious command'). Add input sanitization in _execute_console_command() at game_config.py:547.
- [x] [AI-Review][HIGH] Add type validation for API input: UpdateRequest accepts any value without validating it matches expected type (int/bool/string). Use or create validation based on LIVE_SETTINGS value_type at game_config.py:463 and routers_config.py:37.

#### Medium Priority Issues

- [x] [AI-Review][MEDIUM] Add test for password redaction: No test verifies password values are properly redacted in logs. Add test case verifying logger receives "***" instead of actual password at game_config.py:551-552, 608-614.
- [x] [AI-Review][MEDIUM] Add tests for invalid type input: No test verifies error handling when wrong type is sent (e.g., string for int setting like MaxClients). Add test cases that expect 400 or validation errors.
- [x] [AI-Review][MEDIUM] Integrate type validation layer: parse_env_value() exists in config_init.py with proper type coercion but isn't used for API input validation. Import and leverage this function for consistency.
- [x] [AI-Review][MEDIUM] Add security test for command injection: No test verifies that malicious input with quotes/semicolons is properly rejected or escaped. Add test case with malicious string input.
- [x] [AI-Review][MEDIUM] Verify test timing: Per Epic 5 retro lesson, confirm tests were written alongside implementation (not batched at end). Git commit history shows 2 commits - review if tests were included in task-1 commit.

#### Low Priority Issues

- [x] [AI-Review][LOW] Import parse_env_value for consistency: Utility function exists in config_init.py but isn't imported/used in game_config.py. Import for future type validation work.
