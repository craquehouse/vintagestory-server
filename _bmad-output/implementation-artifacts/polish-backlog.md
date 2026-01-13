# Polish Backlog

Tracks small-to-medium improvements discovered during development and testing that don't belong to a specific epic. Items are organized by category and prioritized within each section.

## Status Legend

| Status        | Meaning                    |
| ------------- | -------------------------- |
| `backlog`     | Identified but not started |
| `in-progress` | Currently being worked on  |
| `done`        | Completed                  |

## Priority Legend

| Priority | Meaning                                         |
| -------- | ----------------------------------------------- |
| `high`   | Impacts usability or correctness; address soon  |
| `medium` | Noticeable improvement; address when convenient |
| `low`    | Nice-to-have; address opportunistically         |

## Effort Legend

| Effort | Meaning                  |
| ------ | ------------------------ |
| `S`    | Small - less than 1 hour |
| `M`    | Medium - 1-4 hours       |
| `L`    | Large - 4+ hours         |

---

## UI

<!-- Items related to the web frontend -->

| ID     | Description                                                                                                                            | Priority | Effort | Status  | Related                 | Notes                                                        |
| ------ | -------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------ | ------- | ----------------------- | ------------------------------------------------------------ |
| UI-006 | Better detection and handling of the state where the frontend has lost connection to the API                                           | medium   | M      | backlog | -                       | -                                                            |
| UI-008 | Mod preview card parse HTML                                                                                                            | low      | S      | backlog | -                       | -                                                            |
| UI-009 | Mod preview card doesn't explain what "Both" means - presumeably client and server. use badges for each?                               | low      | S      | backlog | Block client only mods? | -                                                            |
| UI-011 | Installed mods table should be sortable, and sort order should stay consistent                                                         | low      | S      | backlog | -                       | -                                                            |
| UI-013 | Migrate mod list from cards to TanStack Table for sorting, filtering, search (5+ mods gets unwieldy)                                   | medium   | M      | backlog | UI-011                  | Architecture decision: use TanStack Table for all data lists |
| UI-014 | When mod is not_verified/incompatible, show the most recent compatible game version in mod card/list                                   | low      | M      | backlog | -                       | Helps users understand which game version the mod supports   |
| UI-015 | Move the server install/start/stop functionality to the gameserver tab. the card on the dashboard should just show status              | low      | M      | backlog | -                       | -                                                            |
| UI-016 | Add a font size selector to the console viewer                                                                                         | low      | M      | backlog | -                       | -                                                            |
| UI-018 | Make better use of horizontal space on the server settings cards when in desktop mode. It's too wide.                                  | low      | M      | backlog | -                       | -                                                            |
| UI-020 | Mod List refresh and server version refresh duration should accept human readable strings, not seconds. Mod refresh default to 4 hours | low      | M      | backlog | -                       | -                                                            |
| UI-021 | Server commands entered by the user should have a different color when output in the console. Prefixed by \[CMD]                       | low      | s      | done    | Story-9.5               | Implemented via ANSI cyan color codes                        |
| UI-023 | Implement json colorization in file viewer                                                                                             | low      | s      | backlog | -                       |                                                              |
| UI-024 | Filebrowser show all the directories in /data/serverdata, including but not limited to ModConfigs, Macros, Playerdata                  | low      | s      | done    | Story-9.7               | Implemented via Story 9.7                                    |
| UI-029 | File browser breadcrumb navigation - clickable path segments instead of back button                                                     | low      | S      | backlog | Story-9.7               | Deferred from review - current back button is functional     |
| UI-030 | File browser E2E tests - directory navigation, new directory appears on refresh                                                         | low      | M      | backlog | Story-9.7               | AC3 validation via Playwright                                |
| UI-025 | Implement file editing capability in filebrowser. Require server to be stopped in order to edit file                                   | low      | s      | backlog | -                       |                                                              |
| UI-027 | Server Status card should display api manager and game server memory and possibly CPU                                                  | low      | s      | backlog | API-026                 |                                                              |
| UI-028 | Add debug logging toggle to Settings tab - enable/disable verbose logging at runtime via /api/v1alpha1/debug endpoints                 | low      | S      | backlog | Story-9.4               | API endpoints already implemented; needs UI toggle component |
| UI-031 | Add scroll position restoration for mod detail back navigation | low | S | backlog | - | - |
| UI-032 | Theme consistency audit - verify CSS variables defined and applied consistently | low | M | backlog | Epic-11 | Check --success --warning etc. |
| UI-033 | Consider table view instead of card view for version list | medium | S | backlog | - | Story 13.3 UX feedback - card view may be overkill for small version list |


---

## API

<!-- Items related to the FastAPI backend -->

| ID      | Description                                                                                                                            | Priority | Effort | Status  | Related   | Notes                                                                                                        |
| ------- | -------------------------------------------------------------------------------------------------------------------------------------- | -------- | ------ | ------- | --------- | ------------------------------------------------------------------------------------------------------------ |
| API-003 | /healthz endpoint should report game_server_version, game_server_uptime, game_server_pending_restart                                   | low      | S      | done    | -         | -                                                                                                            |
| API-005 | Passing the api token in the URL to authorize the websocket is insecure. | high | M | done | - | Implement self-signed wss:// ? |
| API-007 | API should create expected directories under data/vsmanager like cache and state if they don't exist | high | M | done | - | - |
| API-008 | API should track available space on data volume, and we should have a config var for warning threshold                                 | high     | M      | done    | -         | /healthz returns disk_space with warning when < max(1GB, 10% of total)                                       |
| API-009 | Mod cache cleanup strategy - cached mod files grow indefinitely with no eviction (LRU, TTL, or size-based)                             | medium   | M      | backlog | Story-5.2 | Risk of disk space exhaustion in production                                                                  |
| API-010 | We need extensive debug logging. Most functions should generate debug logs. disk is cheap.                                             | medium   | M      | backlog | -         | -                                                                                                            |
| API-011 | This might need to be an entire story, but, scheduled restarts along with disk cleanup and log rotation                                | medium   | L      | backlog | -         | -                                                                                                            |
| API-012 | Parse serverconfig.json into internal object, validate paths (ModPaths, SaveFileLocation), expose via API                              | medium   | M      | backlog | Story-5.4 | Would enable detecting misconfigured paths and provide config visibility                                     |
| API-017 | Add pagination to GET /mods endpoint for large mod lists (50+ mods could violate <500ms NFR3)                                          | medium   | M      | backlog | Story-5.5 | Deferred post-MVP per PRD                                                                                    |
| API-018 | Success responses include null `error` field - consider exclude_none or document as design choice                                      | low      | S      | backlog | Story-5.5 | Project-wide design decision                                                                                 |
| API-019 | Add edge case tests for mod list: corrupted state.json, disk I/O errors, malformed mod zips                                            | low      | M      | backlog | Story-5.5 | Improve test coverage beyond happy paths                                                                     |
| API-020 | Extract common test fixtures (temp_data_dir, restart_state, auth_headers) to api/tests/conftest.py                                     | low      | S      | backlog | Story-5.5 | DRY principle - fixtures duplicated across test classes                                                      |
| API-021 | Player whitelist management - API to view/add/remove whitelisted players, UI component in Settings tab                                 | medium   | M      | backlog | FR25-26   | Moved from Epic 9; covers whitelist enable/disable toggle + player list CRUD                                 |
| API-022 | Add Prometheus metrics endpoint (/metrics) with CPU, memory, and process stats using psutil and prometheus-fastapi-instrumentator      | medium   | M      | backlog | -         | Expose CPU%, memory (RSS/VMS), thread count for APM integration                                              |
| API-023 | Extend /metrics to include VintageStory game server metrics: concurrent players, game server process CPU/memory, uptime                | high     | M      | backlog | API-022   | Requires process discovery (find VintageStory.exe), game server API integration for player count             |
| API-024 | There is double timestamping visible in console logs. I think the server already timetamps. | high | M | done | API-022 | Requires process discovery (find VintageStory.exe), game server API integration for player count |
| API-025 | Investigate DI pattern for service access to reduce deferred imports and avoid circular dependencies                                   | low      | M      | backlog | Epic-7    | Current pattern uses global singletons with getter functions; deferred imports work but feel like workaround |
| API-026 | ServerStatus should track the memory usage of both the API server and the game server. bonus points if it can track CPU usage as well. | low      | M      | backlog | -         | -                                                                                                            |
| API-027 | Structlog type stubs incomplete - processors parameter type mismatch requires type: ignore comments                                     | low      | S      | backlog | Story-9.2 | See test_config.py:184,221 - custom processors don't match Processor type; upstream issue                    |
| API-028 | Browse endpoint: Add game version pre-filtering (`?version=1.21`) to filter mods by compatible game version                             | medium   | M      | backlog | Story-10.1 | Epic requires pre-filtering but deferred - requires server version detection + release tag matching          |
| API-029 | Browse endpoint: Add `sort=name` option for alphabetical sorting (Epic specifies 5 sort options, implemented 3)                         | low      | S      | backlog | Story-10.1 | Simple addition; deferred as downloads/trending/recent cover primary use cases                               |
| API-030 | Documentation: Align Epic-10 and Story-10.1 parameter naming (`per_page` vs `page_size`) and sort options                               | low      | S      | backlog | Story-10.1 | Update Epic to use `page_size` and document final 3 sort options as intentional scope                        |
| API-031 | Documentation: Update Story-10.1 AC1 to enumerate all 11 response fields (currently lists 7)                                            | low      | S      | backlog | Story-10.1 | Add: follows, trending_points, side, mod_type, last_released                                                 |

---

## Infrastructure

<!-- Items related to Docker, deployment, configuration -->

| ID        | Description                                                                                               | Priority | Effort | Status  | Related | Notes |
| --------- | --------------------------------------------------------------------------------------------------------- | -------- | ------ | ------- | ------- | ----- |
| INFRA-001 | If a server is installed, the api should autostart it when initializing, unless overriden by env variable | low      | S      | backlog | -       | -     |

---

## Tools

<!-- Items related to development tooling, scripts, justfile -->

| ID        | Description                                                                                                  | Priority | Effort | Status  | Related  | Notes                                                                      |
| --------- | ------------------------------------------------------------------------------------------------------------ | -------- | ------ | ------- | -------- | -------------------------------------------------------------------------- |
| TOOLS-001 | Add incremental test commit reminders to dev-story workflow to prevent test batching (Epic 1 retro lesson 2) | medium   | S      | backlog | Epic-5.1 | Tests should be committed alongside implementation, not batched at the end |
| TOOLS-002 | Add semgrep justfile recipies. Need to decide if add to existing test-api, test-web in addition.             | medium   | S      | backlog |          | semgrep scan --verbose --error ./api                                       |
| TOOLS-003 | worktree dev experience is poor. conflicting ports on web and ui servers, missing API keys make tests fail   | medium   | S      | backlog |          |                                                                            |

---

## CI/CD

<!-- Items related to continuous integration and deployment -->

| ID       | Description                        | Priority | Effort | Status  | Related | Notes |
| -------- | ---------------------------------- | -------- | ------ | ------- | ------- | ----- |
| CICD-001 | Integrate semgrep into pipeline    | medium   | M      | backlog | -       | -     |
| CICD-002 | Integrate linting into pipeline    | medium   | M      | backlog | -       | -     |
| CICD-003 | Integrate testing into pipeline    | medium   | M      | backlog | -       | -     |
| CICD-004 | Integrate Renovate into repository | medium   | M      | backlog | -       | -     |
| CICD-005 | Add release action                 | medium   | M      | backlog | -       | -     |

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
Add the PR link to the item's ID.

| ID                                                                    | Description                                                                                                                                                                                      | Completed  | Notes                                                                     |
| --------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------- | ------------------------------------------------------------------------- |
| [UI-004](https://github.com/craquehouse/vintagestory-server/pull/10)  | Toasts for server starting and server stopping exist, but not server started and server stopped                                                                                                  | 2025-12-31 | Added useServerStateToasts hook to detect state transitions               |
| [UI-001](https://github.com/craquehouse/vintagestory-server/pull/4)   | The sidebar is much wider than it needs to be                                                                                                                                                    | 2025-12-31 | Reduced from 240px to 160px                                               |
| [UI-003](https://github.com/craquehouse/vintagestory-server/pull/11)  | Vertical order, top to bottom, of sidebar items should be "Dashboard", "GameServer", "Mods", "Settings"                                                                                          | 2025-12-31 | Reordered nav items, renamed Console→GameServer, Config→Settings          |
| [UI-007](https://github.com/craquehouse/vintagestory-server/pull/6)   | Mod preview card should display mod image                                                                                                                                                        | 2025-12-31 | Added logo_url to ModLookupResponse and display in card                   |
| [API-001](https://github.com/craquehouse/vintagestory-server/pull/5)  | /docs endpoint shows inconsistent capitalization                                                                                                                                                 | 2025-12-31 | -                                                                         |
| [API-002](https://github.com/craquehouse/vintagestory-server/pull/7)  | /healthz endpoint returns data.game_server but the value doesn't seem to report actual server status                                                                                             | 2025-12-31 | Fixed alongside API-004                                                   |
| [API-004](https://github.com/craquehouse/vintagestory-server/pull/7)  | /readyz endpoint should report data.checks.game_server                                                                                                                                           | 2025-12-31 | -                                                                         |
| [UI-002](https://github.com/craquehouse/vintagestory-server/pull/8)   | Replace "VS Server" text with Vintage Story logo banner                                                                                                                                          | 2025-12-31 | WebP logo (3.3KB + 8.4KB 2x) + icon for collapsed state (742B + 1.6KB 2x) |
| [UI-012](https://github.com/craquehouse/vintagestory-server/pull/9)   | Installed mods in table should have clickable link to VintageStory mods page                                                                                                                     | 2025-12-31 | Mod name is now a clickable external link                                 |
| [UI-010](https://github.com/craquehouse/vintagestory-server/pull/13)  | Mods installed when server is not running should not generate "server may need to be restarted" toast                                                                                            | 2025-12-31 | Only show restart toast when server is running                            |
| [API-003](https://github.com/craquehouse/vintagestory-server/pull/16) | /healthz endpoint should report game_server_version, game_server_uptime, game_server_pending_restart                                                                                             | 2026-01-01 | Added 3 fields with error handling and OpenAPI docs                       |
| [API-016](https://github.com/craquehouse/vintagestory-server/pull/14) | CLAUDE.md documents WebSocket at /ws/console but actual path is /api/v1alpha1/console/ws                                                                                                         | 2025-12-31 | Documentation drift - fixed in CLAUDE.md                                  |
| [API-015](https://github.com/craquehouse/vintagestory-server/pull/21) | Move get_server_service() singleton from routers/server.py to services/server.py                                                                                                                 | 2026-01-01 | Layer separation - follows mods.py pattern                                |
| [UI-005](https://github.com/craquehouse/vintagestory-server/pull/21)  | The server console tab should have ways to also "tail" *.log logfiles in serverdata/Logs                                                                                                         | 2026-01-01 | Added source selector dropdown in ConsolePanel, streaming via WebSocket   |
| [API-006](https://github.com/craquehouse/vintagestory-server/pull/21) | API should be able to stream/tail *.log logfiles in serverdata/Logs                                                                                                                              | 2026-01-01 | Added GET /console/logs + WebSocket /console/logs/ws                      |
| [UI-022](https://github.com/craquehouse/vintagestory-server/pull/25)  | Implement word wrap in file viewer                                                                                                                                                               | 2026-01-02 | Added toggle button in FileViewer toolbar                                 |
| [API-014](https://github.com/craquehouse/vintagestory-server/pull/24) | Console router returns raw dict instead of ApiResponse model (console.py:34, console.py:67)                                                                                                      | 2026-01-02 | Updated to use ApiResponse model for pattern consistency                  |
| [UI-017](https://github.com/craquehouse/vintagestory-server/pull/26)  | User preferences such as light/dark mode (if overridden), console font size, etc. should be stored as a cookie                                                                                   | 2026-01-02 | Added cookie-based preferences system                                     |
| [API-013](https://github.com/craquehouse/vintagestory-server/pull/23) | routers/__init__.py only exports auth, health, test_rbac - should export all routers for module completeness                                                                                     | 2026-01-02 | Export all routers from __init__.py                                       |
| [UI-019](https://github.com/craquehouse/vintagestory-server/pull/27)  | "VintageStory Server" placeholder at the top of the screen should be updated with the server name                                                                                                | 2026-01-02 | Display server name from game config in header                            |
| [UI-026](https://github.com/craquehouse/vintagestory-server/pull/28)  | When updating the servername in the game server panel, the name is getting wrapped in quotes. Also the field reverts until the api polls the game server again. It should happen immediatelyish. | 2026-01-02 | Fixed quote wrapping and immediate optimistic update                      |
| [UI-021](https://github.com/craquehouse/vintagestory-server/pull/45)  | Server commands entered by the user should have a different color when output in the console. Prefixed by \[CMD]                                                                                 | 2026-01-04 | ANSI cyan color codes via Story 9.5                                       |
