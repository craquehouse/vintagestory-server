# Story 6.1: ConfigInitService and Template

Status: done

## Story

As an **administrator**,
I want **the server to automatically generate an initial configuration from environment variables**,
So that **I can deploy with custom settings without manual file creation**.

## Acceptance Criteria

1. **Given** the game server is installed but no serverconfig.json exists, **When** the server start is requested, **Then** ConfigInitService generates serverconfig.json from the template, **And** any VS_CFG_* environment variables override template defaults.

2. **Given** VS_CFG_SERVER_NAME is set to "My Custom Server", **When** ConfigInitService generates the config, **Then** serverconfig.json contains `"ServerName": "My Custom Server"`.

3. **Given** VS_CFG_MAX_CLIENTS is set to "32", **When** ConfigInitService generates the config, **Then** serverconfig.json contains `"MaxClients": 32` (integer, not string).

4. **Given** serverconfig.json already exists, **When** the server start is requested, **Then** ConfigInitService does NOT overwrite the existing config, **And** the existing config is used as-is.

5. **Given** an invalid VS_CFG_* value is provided (e.g., VS_CFG_MAX_CLIENTS="abc"), **When** ConfigInitService processes environment variables, **Then** the invalid value is logged as a warning, **And** the template default is used instead.

## Tasks / Subtasks

- [x] Task 1: Create ConfigInitService class + tests (AC: 1, 4, 5)
  - [x] Subtask 1.1: Create `api/src/vintagestory_api/services/config_init_service.py` with ConfigInitService class
  - [x] Subtask 1.2: Implement `needs_initialization()` method - checks if serverconfig.json exists at `data_dir / "serverdata" / "serverconfig.json"`
  - [x] Subtask 1.3: Implement `initialize_config()` method - loads template, applies overrides, writes atomically
  - [x] Subtask 1.4: Write tests for needs_initialization() - file exists vs not exists
  - [x] Subtask 1.5: Write tests for idempotency - existing config NOT overwritten

- [x] Task 2: Implement environment variable override application + tests (AC: 2, 3, 5)
  - [x] Subtask 2.1: Implement `_collect_env_overrides()` - collect all VS_CFG_* from os.environ
  - [x] Subtask 2.2: Implement `_apply_overrides()` - use `parse_env_value()` from config_init.py for type coercion
  - [x] Subtask 2.3: Handle nested keys (e.g., "WorldConfig.AllowCreativeMode") using `get_config_key_path()`
  - [x] Subtask 2.4: Implement graceful error handling - log warning on invalid value, use template default
  - [x] Subtask 2.5: Write tests for type coercion - string, int, bool, float values
  - [x] Subtask 2.6: Write tests for nested key application
  - [x] Subtask 2.7: Write tests for invalid value handling

- [x] Task 3: Integrate with ServerService.start() + tests (AC: 1)
  - [x] Subtask 3.1: Add ConfigInitService as dependency to ServerService
  - [x] Subtask 3.2: Call `config_init.needs_initialization()` before server launch
  - [x] Subtask 3.3: Call `config_init.initialize_config()` if needed
  - [x] Subtask 3.4: Log initialization event with structured logging
  - [x] Subtask 3.5: Write integration test verifying config is created before server start
  - [x] Subtask 3.6: Write integration test verifying existing config is not overwritten

### Review Follow-ups (AI)

- [x] [AI-Review][MEDIUM] Git commit message format violation - Single commit `feat(story-6.1): implement ConfigInitService` instead of expected 3 task-level commits with `/task-N` suffixes (per project-context.md Git Workflow section)
  - **Resolution**: Acknowledged. The commit was already pushed before review. For future stories, will follow the task-level commit pattern: `feat(story-X.Y/task-N): description`. The code implementation is correct; only the commit granularity deviated from process.

- [x] [AI-Review][MEDIUM] Story File List discrepancy - `api/src/vintagestory_api/services/__init__.py` listed in "Files to modify" but not actually modified (exports not needed since direct import paths used)
  - **Resolution**: Intentionally not modified. Python's direct import paths (`from vintagestory_api.services.config_init_service import ConfigInitService`) work without `__init__.py` exports. Adding exports would be redundant and create maintenance overhead. The story template was overly prescriptive; actual implementation is correct.

- [x] [AI-Review][LOW] Complete manual tests in PR test plan - 2 unchecked manual tests: verify template+overrides applied on first run, verify existing config not overwritten
  - **Resolution**: Manual tests completed successfully:
    1. First run: Config generated from template with env var overrides ✓
    2. Existing config: Not overwritten on subsequent starts ✓
  - **Bug found during manual testing**: Quoted env var values (e.g., `VS_CFG_SERVER_NAME="My Server"`) included literal quotes. Fixed by adding `_strip_surrounding_quotes()` helper.

## Dev Notes

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

- Each task that adds functionality must include its tests before marking complete
- A task is NOT complete until tests pass
- Do not batch tests into a separate "Write tests" task at the end
- Run `just test` to verify all tests pass before marking task complete

### Security Requirements

**Follow patterns in `project-context.md` → Security Patterns section:**

- Never log sensitive data in plaintext (VS_CFG_SERVER_PASSWORD should not be logged)
- Use atomic file writes (temp file + rename pattern) for config persistence

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-api -k "config_init"` - Run config init tests specifically
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

**Epic 6 Architectural Pivot:** This story implements the ConfigInitService for first-run configuration generation using the console-command-based architecture established in Story 6.0.

**Key Architecture Decisions:**
- Config file location: `/data/serverdata/serverconfig.json` (VintageStory's --dataPath)
- Template location: `api/src/vintagestory_api/templates/serverconfig-template.json` (already created in 6.0)
- Environment variable mapping: Use `ENV_VAR_MAP` from `config_init.py` (already created in 6.0)
- Type coercion: Use `parse_env_value()` from `config_init.py` (already created in 6.0)
- Nested key handling: Use `get_config_key_path()` from `config_init.py` (already created in 6.0)

**Atomic Write Pattern (MANDATORY):**
```python
# All config writes MUST use this pattern
temp = path.with_suffix('.tmp')
temp.write_text(json.dumps(config, indent=2))
temp.rename(path)  # atomic on POSIX
```

**Reference:** See `_bmad-output/planning-artifacts/architecture.md#epic-6-game-configuration-management-architecture` for full architecture.

### Previous Story Intelligence (Story 6.0)

From `6-0-epic-6-technical-preparation.md`:

1. **ENV_VAR_MAP already exists** in `api/src/vintagestory_api/services/config_init.py` with 40+ mappings
2. **Type coercion already implemented** via `parse_env_value()` function
3. **Nested key helper already exists** via `get_config_key_path()` function
4. **serverconfig-template.json already exists** at `api/src/vintagestory_api/templates/`
5. **Tests for mapping/coercion exist** in `api/tests/test_config_init.py` (58 tests)

**CRITICAL: DO NOT recreate these - extend the existing implementation!**

### Existing Code to Reuse

**File: `api/src/vintagestory_api/services/config_init.py` (Story 6.0)**
```python
# Already provides:
ENV_VAR_MAP: dict[str, tuple[str, Literal["string", "int", "bool", "float"]]]
parse_env_value(value: str, value_type: str) -> Any
get_config_key_path(key: str) -> list[str]
```

**File: `api/src/vintagestory_api/templates/serverconfig-template.json` (Story 6.0)**
- Complete template with all settings
- ModPaths already includes symlink path: `["Mods", "/data/serverdata/Mods"]`
- 4 roles defined (suvisitor, suplayer, crplayer, admin)

**Pattern from ServerService (server.py lines 447-452):**
```python
# Atomic write pattern - USE THIS for config file writes
temp_file = version_file.with_suffix(".tmp")
temp_file.write_text(version)
temp_file.rename(version_file)
```

### Config File Path Resolution

**CRITICAL PATH:** The config file lives at `/data/serverdata/serverconfig.json`

This is because:
- VintageStory uses `--dataPath serverdata` when started
- VintageStory expects serverconfig.json in the data path
- Settings object provides `serverdata_dir` property which resolves to this path

Use `settings.serverdata_dir / "serverconfig.json"` NOT `settings.data_dir / "config" / "serverconfig.json"`

### Integration Point with ServerService

The ConfigInitService should be called from `ServerService._start_server_locked()` BEFORE launching the process:

```python
# In ServerService._start_server_locked() - add BEFORE process creation
if self._config_init_service.needs_initialization():
    self._config_init_service.initialize_config()
    logger.info("config_initialized", source="template+env")

# Then proceed with existing subprocess creation...
```

### Project Structure Notes

**New files to create:**
- `api/src/vintagestory_api/services/config_init_service.py` - The main service class

**Files to modify:**
- `api/src/vintagestory_api/services/server.py` - Add ConfigInitService integration
- `api/src/vintagestory_api/services/__init__.py` - Export ConfigInitService

**Test file to create:**
- `api/tests/test_config_init_service.py` - Service-level tests (separate from existing test_config_init.py which tests mapping/coercion)

### Error Handling Strategy

**Invalid ENV values should NOT crash the server start:**
1. Log a structured warning with the env var name and invalid value
2. Skip that override (use template default)
3. Continue processing other env vars
4. Continue with server start

```python
try:
    parsed_value = parse_env_value(raw_value, value_type)
except ValueError as e:
    logger.warning(
        "env_var_parse_error",
        env_var=env_var,
        value=raw_value,
        expected_type=value_type,
        error=str(e),
    )
    continue  # Skip this override, use template default
```

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/6-1-config-init-service-and-template

# Task-level commits
git commit -m "feat(story-6.1/task-1): create ConfigInitService class"
git commit -m "feat(story-6.1/task-2): implement env var override application"
git commit -m "feat(story-6.1/task-3): integrate ConfigInitService with ServerService"

# Push and create PR
git push -u origin story/6-1-config-init-service-and-template
gh pr create --title "Story 6.1: ConfigInitService and Template" --body "..."
```

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md#epic-6-game-configuration-management-architecture` - Full Epic 6 architecture
- `api/src/vintagestory_api/services/config_init.py` - Existing ENV_VAR_MAP and helper functions (Story 6.0)
- `api/src/vintagestory_api/templates/serverconfig-template.json` - Config template (Story 6.0)
- `api/tests/test_config_init.py` - Existing tests for mapping/coercion (58 tests)
- `api/src/vintagestory_api/services/server.py` - ServerService for integration point
- `agentdocs/vs-serverconfig-commands.md` - Console command reference (for future stories)

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

None

### Completion Notes List

- **Task 1**: Created ConfigInitService class in `api/src/vintagestory_api/services/config_init_service.py` with:
  - `needs_initialization()` - checks if serverconfig.json exists
  - `initialize_config()` - loads template, applies VS_CFG_* env overrides, writes atomically
  - Uses temp-file-then-rename pattern for atomic writes (prevents corruption)
  - Tests cover file existence check, idempotency, atomic write behavior

- **Task 2**: Implemented environment variable override application:
  - `_collect_env_overrides()` collects VS_CFG_* env vars matching ENV_VAR_MAP
  - `_apply_overrides()` applies type coercion using `parse_env_value()` from config_init.py
  - `_set_nested_value()` handles dotted keys like "WorldConfig.AllowCreativeMode"
  - Graceful error handling: invalid values logged as warning, template default used
  - Tests cover string/int/bool/float coercion, nested keys, invalid value handling

- **Task 3**: Integrated ConfigInitService with ServerService:
  - Added `config_init_service` property to ServerService for dependency injection
  - Called `needs_initialization()` and `initialize_config()` in `_start_server_locked()`
  - Added structured logging for config initialization events
  - Integration tests verify config creation before server start and idempotency

### Change Log

- 2025-12-30: Implemented Story 6.1 - ConfigInitService and Template
  - Created ConfigInitService class with atomic write pattern
  - Implemented env var override application with type coercion
  - Integrated with ServerService.start() lifecycle
  - Added 26 tests covering all acceptance criteria
  - Fixed: Strip surrounding quotes from env var values (docker-compose UX issue)
  - Added 5 tests for quote-stripping behavior (31 total tests)
  - Manual tests completed: first run config generation ✓, idempotency ✓

### File List

**New Files:**
- `api/src/vintagestory_api/services/config_init_service.py` - ConfigInitService class
- `api/tests/test_config_init_service.py` - Test suite (26 tests)

**Modified Files:**
- `api/src/vintagestory_api/services/server.py` - Added ConfigInitService dependency and integration
- `docker-compose.dev.yaml` - Added VS_CFG_SERVER_NAME variable for testing
