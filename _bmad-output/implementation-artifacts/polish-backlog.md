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
| UI-001  | The sidebar is much wider than it needs to be.                                                             | low        | S        | backlog  | -         | -       |
| UI-002  | "VS Server" in the upper lefthand corner should read "VS Server Manager"                                   | low        | S        | backlog  | -         | -       |
| UI-003  | Vertical order, top to bottom, of sidebar items should be "Dashboard", "Console", "Mods", "Config"         | low        | S        | backlog  | -         | -       |

---

## API

<!-- Items related to the FastAPI backend -->

| ID      | Description                                                                                                | Priority   | Effort   |  Status  | Related   | Notes   |
| ------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------- | -------- | --------- | ------- |
| API-001 | /docs endpoint shows inconsistent capitalization (Health, Authentication, console, Server, test, default)  | low        | S        | backlog  | -         | -       |  
| API-002 | /healthz endpoint returns data.game_server but the value doesn't seem to report actual server status       | low        | S        | backlog  | -         | -       |  
| API-003 | /healthz endpoint should report data.(game_server_version|game_server_uptime|game_server_pending_restart)  | low        | S        | backlog  | -         | -       |  
| API-004 | /readyz endpoint should report data.checks.game_server                                                     | low        | S        | backlog  | -         | -       |  

---

## Infrastructure

<!-- Items related to Docker, deployment, configuration -->

| ID        | Description                                                                                                | Priority   | Effort   |  Status  | Related   | Notes   |
| --------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------- | -------- | --------- | ------- |
| INFRA-001 | _Example: Optimize container image size_ | low | M | backlog | - | - |

---

## Tools

<!-- Items related to development tooling, scripts, justfile -->

| ID      | Description                                                                                                | Priority   | Effort   |  Status  | Related   | Notes   |
| ------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------- | -------- | --------- | ------- |
| TOOLS-001 | _Example: Add just recipe for database migrations_ | low | S | backlog | - | - |

---

## CI/CD

<!-- Items related to continuous integration and deployment -->

| ID      | Description                                                                                                | Priority   | Effort   |  Status  | Related   | Notes   |
| ------- | ---------------------------------------------------------------------------------------------------------- | ---------- | -------- | -------- | --------- | ------- |
| CICD-001 | _Example: Add test coverage reporting_ | medium | M | backlog | - | - |

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
| - | - | - | - |
