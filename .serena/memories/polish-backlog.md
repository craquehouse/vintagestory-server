# Polish Backlog Summary

Tracks improvements discovered during development that don't belong to specific epics.

## Categories Overview

### UI (8 items)
- UI-005: Stream/tail logfiles in Console tab (low)
- UI-006: Better API connection loss handling (medium)
- UI-008: Mod preview card HTML parsing (low)
- UI-009: Explain "Both" in mod side field (low)
- UI-010: No restart toast when server not running (low)
- UI-011: Sortable mod table with consistent order (low)
- UI-013: Migrate mod list to TanStack Table (medium)
- UI-014: Show compatible game version for not_verified mods (low)

### API (13 items - API-003 to API-023)
- **High Priority:**
  - API-005: WebSocket token in URL is insecure
  - API-006: Stream/tail logfiles API
  - API-007: Auto-create expected directories
  - API-008: Track available disk space
  - API-023: VintageStory game server metrics

- **Medium Priority:**
  - API-009: Mod cache cleanup strategy (LRU/TTL)
  - API-010: Extensive debug logging
  - API-011: Scheduled restarts, cleanup, log rotation
  - API-012: Parse serverconfig.json into object
  - API-017: Mod list pagination
  - API-021: Player whitelist management
  - API-022: Prometheus metrics endpoint

### Infrastructure (1 item)
- INFRA-001: Auto-start installed server on API init (low)

### Tools (3 items)
- TOOLS-001: Test commit reminders in dev-story
- TOOLS-002: Semgrep justfile recipes
- TOOLS-003: Worktree dev experience (port conflicts, missing keys)

### CI/CD (5 items)
- CICD-001 to CICD-005: Semgrep, linting, testing, Renovate, release action

## Completed Items (9)
UI-001, UI-002, UI-003, UI-004, UI-007, UI-012, API-001, API-002, API-004
