# Polish Backlog

Tracks small-to-medium improvements discovered during development and testing that don't belong to a specific epic. Items are organized by category and prioritized within each section.

## Status Legend

| Status | Meaning |
|--------|---------|
| `backlog` | Identified but not started |
| `in-progress` | Currently being worked on |
| `done` | Completed |

## Priority Legend

| Priority | Meaning |
|----------|---------|
| `high` | Impacts usability or correctness; address soon |
| `medium` | Noticeable improvement; address when convenient |
| `low` | Nice-to-have; address opportunistically |

## Effort Legend

| Effort | Meaning |
|--------|---------|
| `S` | Small - less than 1 hour |
| `M` | Medium - 1-4 hours |
| `L` | Large - 4+ hours |

---

## UI

<!-- Items related to the web frontend -->

| ID      | Description                                                                                                | Priority   | Effort   |  Status  | Related   | Notes   |
| ------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------- | -------- | --------- | ------- |
| ~~UI-001~~  | ~~The sidebar is much wider than it needs to be.~~                                                     | ~~low~~    | ~~S~~    | done     | -         | Reduced from 240px to 160px |
| ~~UI-002~~  | ~~"VS Server" in the upper lefthand corner should be replaced with assets/vintagestory-logobanner.png~~        | ~~low~~        | ~~S~~        | done  | -         | WebP format (3.3KB + 8.4KB 2x retina), srcset for resolution switching |
| UI-003  | Vertical order, top to bottom, of sidebar items should be "Dashboard", "GameServer", "Mods", "Settings"    | low        | S        | backlog  | Epic-6    | Renamed per Epic 6 architecture: Console→GameServer, added Settings tab |
| UI-004  | Toasts for server starting and server stopping exist, but not server started and server stopped            | low        | S        | backlog  | -         | -       |
| UI-005  | The server console tab should have ways to also "tail" *.log logfiles in serverdata/Logs                   | low        | S        | backlog  | -         | -       |
| UI-006  | Better detection and handling of the state where the frontend has lost connection to the API               | medium     | M        | backlog  | -         | -       |
| ~~UI-007~~  | ~~Mod preview card should display mod image~~                                                          | ~~low~~    | ~~S~~    | done     | -         | Added logo_url to ModLookupResponse and display in card |
| UI-008  | Mod preview card parse HTML                                                                                | low        | S        | backlog  | -         | -       |
| UI-009  | Mod preview card doesn't explain what "Both" means - presumeably client and server. use badges for each?   | low        | S        | backlog  | -         | -       |
| UI-010  | Mods installed when server is not running should not generate "server may need to be restarted" toast      | low        | S        | backlog  | -         | -       |
| UI-011  | Installed mods table should be sortable, and sort order should stay consistent                             | low        | S        | backlog  | -         | -       |
| UI-013  | Migrate mod list from cards to TanStack Table for sorting, filtering, search (5+ mods gets unwieldy)       | medium     | M        | backlog  | UI-011    | Architecture decision: use TanStack Table for all data lists |
| UI-014  | When mod is not_verified/incompatible, show the most recent compatible game version in mod card/list       | low        | M        | backlog  | -         | Helps users understand which game version the mod supports |

---

## API

<!-- Items related to the FastAPI backend -->

| ID      | Description                                                                                                  | Priority   | Effort   |  Status  | Related   | Notes   |
| ------- | ------------------------------------------------------------------------------------------------------------ | ---------- | -------- | -------- | --------- | ------- |
| ~~API-001~~ | ~~/docs endpoint shows inconsistent capitalization (Health, Authentication, console, Server, test, default)~~    | ~~low~~        | ~~S~~        | ~~done~~     | ~~-~~         | ~~-~~       |  
| ~~API-002~~ | ~~/healthz endpoint returns data.game_server but the value doesn't seem to report actual server status~~ | ~~low~~ | ~~S~~ | ~~done~~ | ~~-~~ | Fixed alongside API-004 |
| API-003 | /healthz endpoint should report data.(game_server_version,game_server_uptime,game_server_pending_restart)    | low        | S        | backlog  | -         | -       |
| ~~API-004~~ | ~~/readyz endpoint should report data.checks.game_server~~ | ~~low~~ | ~~S~~ | ~~done~~ | ~~-~~ | ~~-~~ |  
| API-005 | Passing the api token in the URL to authorize the websocket is insecure.                                     | high       | M        | backlog  | -         | Implement self-signed wss:// ? |  
| API-006 | API should be able to stream/tail *.log logfiles in serverdata/Logs                                          | high       | M        | backlog  | UI-005    | -       |  
| API-007 | API should create expected directories under data/vsmanager like cache and state if they don't exist         | high       | M        | backlog  | -         | -       |  
| API-008 | API should track available space on data volume, and we should have a config var for warning threshold       | high       | M        | backlog  | -         | -       |
| API-009 | Mod cache cleanup strategy - cached mod files grow indefinitely with no eviction (LRU, TTL, or size-based)   | medium     | M        | backlog  | Story-5.2 | Risk of disk space exhaustion in production |
| API-010 | We need extensive debug logging. Most functions should generate debug logs. disk is cheap.                   | medium     | M        | backlog  | -         | -       |
| API-011 | This might need to be an entire story, but, scheduled restarts along with disk cleanup and log rotation      | medium     | L        | backlog  | -         | -       |
| API-012 | Parse serverconfig.json into internal object, validate paths (ModPaths, SaveFileLocation), expose via API    | medium     | M        | backlog  | Story-5.4 | Would enable detecting misconfigured paths and provide config visibility |
| API-013 | routers/__init__.py only exports auth, health, test_rbac - should export all routers for module completeness | low        | S        | backlog  | -         | Minor but misleading module structure |
| API-014 | Console router returns raw dict instead of ApiResponse model (console.py:34, console.py:67)                  | low        | S        | backlog  | -         | Pattern consistency - bypasses typed envelope |
| API-015 | Move get_server_service() singleton from routers/server.py to services/server.py                             | low        | S        | backlog  | -         | Layer separation - mods.py does this correctly |
| API-016 | CLAUDE.md documents WebSocket at /ws/console but actual path is /api/v1alpha1/console/ws                     | low        | S        | backlog  | -         | Documentation drift |
| API-017 | Add pagination to GET /mods endpoint for large mod lists (50+ mods could violate <500ms NFR3)                | medium     | M        | backlog  | Story-5.5 | Deferred post-MVP per PRD |
| API-018 | Success responses include null `error` field - consider exclude_none or document as design choice            | low        | S        | backlog  | Story-5.5 | Project-wide design decision |
| API-019 | Add edge case tests for mod list: corrupted state.json, disk I/O errors, malformed mod zips                 | low        | M        | backlog  | Story-5.5 | Improve test coverage beyond happy paths |
| API-020 | Extract common test fixtures (temp_data_dir, restart_state, auth_headers) to api/tests/conftest.py          | low        | S        | backlog  | Story-5.5 | DRY principle - fixtures duplicated across test classes |
 | API-021 | Player whitelist management - API to view/add/remove whitelisted players, UI component in Settings tab      | medium     | M        | backlog  | FR25-26   | Moved from Epic 9; covers whitelist enable/disable toggle + player list CRUD |
 | API-022 | Add Prometheus metrics endpoint (/metrics) with CPU, memory, and process stats using psutil and prometheus-fastapi-instrumentator | medium     | M        | backlog  | -         | Expose CPU%, memory (RSS/VMS), thread count for APM integration |
 | API-023 | Extend /metrics to include VintageStory game server metrics: concurrent players, game server process CPU/memory, uptime | high       | M        | backlog  | API-022    | Requires process discovery (find VintageStory.exe), game server API integration for player count |

---

## Infrastructure

<!-- Items related to Docker, deployment, configuration -->

| ID        | Description                                                                                                | Priority   | Effort   |  Status  | Related   | Notes   |
| --------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------- | -------- | --------- | ------- |
| INFRA-001 | If a server is installed, the api should autostart it when initializing, unless overriden by env variable  | low        | S        | backlog  | -         | -       |

---

## Tools

<!-- Items related to development tooling, scripts, justfile -->

| ID        | Description                                                                                                  | Priority   | Effort   |  Status  | Related   | Notes   |
| --------- | ------------------------------------------------------------------------------------------------------------ | ---------- | -------- | -------- | --------- | ------- |
| TOOLS-001 | Add incremental test commit reminders to dev-story workflow to prevent test batching (Epic 1 retro lesson 2) | medium     | S        | backlog  | Epic-5.1  | Tests should be committed alongside implementation, not batched at the end |
| TOOLS-002 | Add semgrep justfile recipies. Need to decide if add to existing test-api, test-web in addition.             | medium     | S        | backlog  |           | semgrep scan --verbose --error ./api |

---

## CI/CD

<!-- Items related to continuous integration and deployment -->

| ID       | Description                                                                                                | Priority   | Effort   |  Status  | Related   | Notes   |
| -------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------- | -------- | --------- | ------- |
| CICD-001 | Integrate semgrep into pipeline                                                                            | medium     | M        | backlog  | -         | -       |
| CICD-002 | Integrate linting into pipeline                                                                            | medium     | M        | backlog  | -         | -       |
| CICD-003 | Integrate testing into pipeline                                                                            | medium     | M        | backlog  | -         | -       |
| CICD-004 | Integrate Renovate into repository                                                                         | medium     | M        | backlog  | -         | -       |
| CICD-005 | Add release action                                                                                         | medium     | M        | backlog  | -         | -       |

---

## Item Template

When adding new items, copy this template:

```markdown
| XX-NNN | Description of the improvement | priority | effort | backlog | Epic-N.N or - | Optional notes |
```

- **ID**: Category prefix + 3-digit number (e.g., `API-002`)
- **Description**: Clear, actionable description of the change
- **Priority**: `high`, `medium`, or `low`
- **Effort**: `S`, `M`, or `L`
- **Status**: `backlog`, `in-progress`, or `done`
- **Related**: Link to related epic/story (e.g., `Epic-5.1`) or `-` if standalone
- **Notes**: Any additional context, blockers, or implementation hints

---

## Completed Items Archive

When items are marked `done`, optionally move them here for historical reference:

| ID | Description | Completed | Notes |
|----|-------------|-----------|-------|
| UI-002 | Replace "VS Server" text with Vintage Story logo banner | 2025-12-31 | WebP logo (3.3KB + 8.4KB 2x) + icon for collapsed state (742B + 1.6KB 2x) |
| UI-012 | Installed mods in table should have clickable link to VintageStory mods page | 2025-12-31 | Mod name is now a clickable external link |
