# Story 6.0: Epic 6 Technical Preparation

Status: in-progress

## Story

As a **developer**,
I want **to research VintageStory console commands and create configuration infrastructure**,
So that **subsequent stories have a solid foundation for config management**.

## Acceptance Criteria

1. **Given** we need to understand console command behavior, **When** I research the `/serverconfig` command, **Then** I document which settings support live update vs require restart, **And** I verify that console changes persist to serverconfig.json automatically.

2. **Given** we need a reference configuration template, **When** I analyze DarkMatterProductions and VintageStory defaults, **Then** I create `serverconfig-template.json` with sensible defaults, **And** the template includes all common settings.

3. **Given** we need to support VS_CFG_* environment variables, **When** I define the environment variable mapping, **Then** I document the complete ENV_VAR_MAP (VS_CFG_SERVER_NAME → ServerName, etc.), **And** I verify the mapping covers all settings from the reference implementation.

4. **Given** we need TanStack Table for data lists, **When** I add the dependency, **Then** `@tanstack/react-table` is added to web/package.json, **And** a basic table component pattern is documented.

## Tasks / Subtasks

- [x] Task 1: Research `/serverconfig` command + tests (AC: 1)
  - [x] Subtask 1.1: Document available `/serverconfig` subcommands from VintageStory wiki/forums
  - [x] Subtask 1.2: Create reference document for console command syntax
  - [x] Subtask 1.3: Identify which settings are console-commandable vs file-only
  - [x] Subtask 1.4: Document which settings take effect immediately vs require restart
  - [x] Subtask 1.5: Add findings to architecture.md under Epic 6 section

- [x] Task 2: Create `serverconfig-template.json` + validation (AC: 2)
  - [x] Subtask 2.1: Analyze DarkMatterProductions generate-config.py for setting patterns
  - [x] Subtask 2.2: Analyze VintageStory default serverconfig.json structure
  - [x] Subtask 2.3: Create `api/src/vintagestory_api/templates/serverconfig-template.json`
  - [x] Subtask 2.4: Include all common settings with sensible defaults
  - [x] Subtask 2.5: Write unit tests validating template is valid JSON and contains expected keys

- [x] Task 3: Define VS_CFG_* → serverconfig.json mapping + tests (AC: 3)
  - [x] Subtask 3.1: Create complete ENV_VAR_MAP in code or config file
  - [x] Subtask 3.2: Include type coercion rules (string → int, string → bool)
  - [x] Subtask 3.3: Document mapping in architecture.md
  - [x] Subtask 3.4: Write unit tests for type coercion (int, bool, string)

- [x] Task 4: Add TanStack Table dependency + tests (AC: 4)
  - [x] Subtask 4.1: Run `bun add @tanstack/react-table` in web directory
  - [x] Subtask 4.2: Document table component pattern in architecture.md (already partially done)
  - [x] Subtask 4.3: Verify web project builds successfully with new dependency
  - [x] Subtask 4.4: Write basic integration test for table component usage

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

### Architecture & Patterns

**Epic 6 Architectural Pivot:** This prep story establishes the foundation for a console-command-based configuration approach, NOT file editing.

- **Console commands for live updates:** VintageStory supports `/serverconfig` for runtime changes
- **File updates for restart-required settings:** Some settings (Port, world seed) need restart
- **VS_CFG_* environment variables:** First-run config generation from container env vars
- **Two config domains:**
  - `/config/game` - Game server settings (serverconfig.json)
  - `/config/api` - API operational settings (api-settings.json)

**Reference Implementation:** [DarkMatterProductions generate-config.py](https://raw.githubusercontent.com/DarkMatterProductions/vintagestory/refs/heads/main/generate-config.py)

### Project Structure Notes

**New files to create:**
- `api/src/vintagestory_api/templates/serverconfig-template.json` - Reference config template
- Consider `api/src/vintagestory_api/services/config_init.py` placeholder for Story 6.1

**Configuration mapping location options:**
1. In `config_init.py` as class constant (simpler)
2. In separate `config/mappings.py` file (if mapping grows complex)

### Epic 5 Retrospective Learnings

From `epic-5-retro-2025-12-30.md`:

1. **Testing discipline is paramount** - No exceptions without explicit user approval
2. **Commit early, commit often** - Task-level commits enable verification
3. **Branch per story with PRs** - Use `story/6-0-epic-6-technical-preparation` branch
4. **Prep stories work** - Continue the pattern established in Epic 4/5

### Git Workflow for This Story

```bash
# Create feature branch
git checkout -b story/6-0-epic-6-technical-preparation

# Task-level commits
git commit -m "feat(story-6.0/task-1): document /serverconfig commands"
git commit -m "feat(story-6.0/task-2): create serverconfig-template.json"
git commit -m "feat(story-6.0/task-3): define VS_CFG_* env var mapping"
git commit -m "feat(story-6.0/task-4): add TanStack Table dependency"

# Push and create PR
git push -u origin story/6-0-epic-6-technical-preparation
gh pr create --title "Story 6.0: Epic 6 Technical Preparation" --body "..."
```

### Known Console Commands (Research Starting Point)

From VintageStory documentation and community sources:

| Command | Description |
|---------|-------------|
| `/serverconfig` | Base command for server configuration |
| `/serverconfig list` | List available settings |
| `/serverconfig Name "value"` | Set server name |
| `/serverconfig MaxClients N` | Set max player count |

**Research needed:** Complete list of `/serverconfig` subcommands, which are live-update vs restart-required.

### References

- `project-context.md` - Critical implementation rules and patterns
- `_bmad-output/planning-artifacts/architecture.md#epic-6-game-configuration-management-architecture` - Full architecture details
- `_bmad-output/implementation-artifacts/epic-5-retro-2025-12-30.md` - Retrospective learnings
- `agentdocs/vs-server-troubleshooting.md` - VintageStory server quirks
- [DarkMatterProductions generate-config.py](https://raw.githubusercontent.com/DarkMatterProductions/vintagestory/refs/heads/main/generate-config.py) - Reference implementation

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- **Task 1 (2025-12-30):** Researched VintageStory /serverconfig commands from wiki. Created `agentdocs/vs-serverconfig-commands.md` with complete command reference. Documented 22+ console-commandable settings with immediate effect vs 10+ restart-required settings. Updated architecture.md Epic 6 section with complete findings. Key insight: console commands automatically persist to serverconfig.json.

- **Task 2 (2025-12-30):** Created `serverconfig-template.json` with sensible defaults based on VintageStory default config and DarkMatterProductions patterns. Includes 4 roles (visitor, player, creative, admin), all standard settings. Created 47 tests validating JSON validity, required keys, default values, role structure, world config, and mod paths. All tests pass.

- **Task 3 (2025-12-30):** Created `config_init.py` with complete ENV_VAR_MAP (40+ mappings) covering server identity, network, gameplay, whitelist, performance, security, hosted mode, world settings, and safety settings. Implemented `parse_env_value()` with type coercion for string/int/bool/float. Updated architecture.md with complete mapping documentation. Created 53 tests for ENV_VAR_MAP structure and type coercion. All tests pass.

- **Task 4 (2025-12-30):** Added @tanstack/react-table v8.21.3 to web dependencies. Verified build succeeds. Table component pattern already documented in architecture.md. Created 6 integration tests verifying TanStack Table import, column helper usage, row model functions, and type safety. All tests pass.

- **Post-completion (2025-12-30):** Migrated development tool permissions (`just` commands, `mise exec`, `docker compose`, etc.) from `.claude/settings.local.json` to shared `.claude/settings.json` so they're available to all contributors.

### File List

- `agentdocs/vs-serverconfig-commands.md` (new) - Complete /serverconfig command reference
- `_bmad-output/planning-artifacts/architecture.md` (modified) - Updated Epic 6 console commands section, ENV_VAR_MAP
- `api/src/vintagestory_api/templates/serverconfig-template.json` (new) - Reference config template
- `api/tests/test_serverconfig_template.py` (new) - 47 tests for template validation
- `api/src/vintagestory_api/services/config_init.py` (new) - ENV_VAR_MAP and type coercion
- `api/tests/test_config_init.py` (new) - 58 tests for config init
- `web/package.json` (modified) - Added @tanstack/react-table dependency
- `web/bun.lock` (modified) - Updated lockfile (note: file is named bun.lock, not bun.lockb)
- `web/src/lib/tanstack-table.test.ts` (new) - 12 integration tests for TanStack Table

### Review Follow-ups (AI)

Issues found during code review on 2025-12-30:

#### High Priority Issues

- [x] [AI-Review][HIGH] Fix template file path in Dev Notes (line 93): Change `data/serverconfig-template.json` to `templates/serverconfig-template.json` to match actual implementation
- [x] [AI-Review][HIGH] Add symlink path to ModPaths template (line 153): Update `["Mods"]` to `["Mods", "/data/serverdata/Mods"]` to match architecture.md symlink strategy
- [x] [AI-Review][HIGH] Fix bool type coercion case handling (config_init.py lines 100-108): Added `normalized` variable for clarity in bool coercion
- [x] [AI-Review][HIGH] Add real TanStack Table integration tests (tanstack-table.test.ts): Added 6 useReactTable tests verifying table creation, headers, cell values, sorting, filtering, and flexRender

#### Medium Priority Issues

- [x] [AI-Review][MEDIUM] Fix file extension in File List (line 176): Updated to `bun.lock` to match actual filename
- [x] [AI-Review][MEDIUM] Add EntitySpawning to ENV_VAR_MAP (config_init.py): Added `"VS_CFG_ENTITY_SPAWNING": ("EntitySpawning", "bool")`
- [x] [AI-Review][MEDIUM] Implement nested key application or clarify scope: Clarified in docstring that full nested key application is implemented in ConfigInitService._apply_overrides() (Story 6.1)
- [x] [AI-Review][MEDIUM] Add end-to-end config generation test: Added 5 tests in TestEndToEndConfigGeneration class validating template + env vars → valid config
