---
stepsCompleted: [1, 2, 3, 4]
inputDocuments:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/ux-design-specification.md'
lastUpdated: '2026-11-27'
updates:
  - date: '2026-11-27'
    description: 'Added Epic 28 (5 stories) for Mods From Outside the Mod Database; FR354-FR366, scope named by the maintainer (VSS-guzf)'
  - date: '2026-11-20'
    description: 'Added Epic 25 (4 stories) for Server Config Read Correctly; FR344-FR353, with the maintainer''s four answers of the same day (VSS-7ap, VSS-egi)'
  - date: '2026-11-20'
    description: 'Added Epic 24 (8 stories) for Mod Management Follow-ups; FR327-FR343, with the maintainer''s five answers of the same day (VSS-2bp, VSS-uhek and VSS-koo1 folded in)'
  - date: '2026-11-19'
    description: 'Added Epic 23 (7 stories) for Config File Editing; FR309-FR326, with the maintainer''s eight answers of the same day (VSS-o8s and VSS-7z3 pulled in)'
  - date: '2026-11-19'
    description: 'Epic 22: the Product changes line and Story 22.6 (fourth criterion, tasks, FR305 row) now name only backup_keep_count, after the maintainer''s "Backups only + docs" decision dropped the two log-archive settings (Story 22.4)'
  - date: '2026-11-19'
    description: 'Added Story 22.8 (stopping the container saves the world first) to Epic 22 with FR308, on the maintainer''s thirteenth answer after Story 22.7''s throwaway run (found in the epic; no bead)'
  - date: '2026-11-18'
    description: 'Added Epic 22 (6 stories) for Server Operations and Metrics; FR287-FR305, with the maintainer''s eleven answers of the same day (VSS-zws pulled in); revised the same day: FR306 (one pending-restart state) pulled into Story 22.2 during its validation, and Story 22.7 with FR307 (VSS-zws fixed, after Story 22.3 confirmed it; maintainer''s twelfth answer)'
  - date: '2026-11-17'
    description: 'Added Epic 21 (8 stories) for Maintainer Decisions and Web Polish; FR260-FR286 (revised the same day with the maintainer''s answers: every default confirmed, VSS-q38r pulled into Story 21.4 with FR286)'
  - date: '2026-11-17'
    description: 'Added Epic 20 (7 stories) for Tooling and Test Health; FR234-FR259 (revised the same day with the maintainer''s answers: a mod database address setting, three beads pulled in)'
  - date: '2026-11-17'
    description: 'Added Epic 19 (7 stories) for API Security and Mod File Safety; FR205-FR233 (revised twice the same day: follow-ups folded in, VSS-9wv split out, start-up mod state sync added as Story 19.5)'
  - date: '2026-11-16'
    description: 'Added Epic 18 (4 stories) for Mod Media and Fixes; FR194-FR204'
  - date: '2026-11-15'
    description: 'Added Epic 17 (8 stories) for Mod Data Correctness and Fixes; FR177-FR193'
  - date: '2026-11-13'
    description: 'Added Story 16.8 (Name sort and empty settings) to Epic 16; FR175-FR176'
  - date: '2026-11-13'
    description: 'Added Epic 16 (8 stories) for UI Polish'
  - date: '2026-11-10'
    description: 'Added Epic 15 (7 stories) for Release Engineering'
  - date: '2026-11-09'
    description: 'Added Epic 14 (7 stories) for Mod Updates'
  - date: '2026-01-10'
    description: 'Added Epic 11 (6 stories), Epic 12 (6 stories), Epic 13 (6 stories) for Navigation Refactor, Enhanced Dashboard, and Version Browser'
  - date: '2026-01-03'
    description: 'Added Epic 9 (7 stories) and Epic 10 (8 stories) for QoL Polish and Advanced Mod Browser'
---

# vintagestory-server - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for vintagestory-server, decomposing the requirements from the PRD, UX Design, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

**Server Lifecycle Management (FR1-5):**

- FR1: Admin can view current server status (running/stopped, uptime, game version)
- FR2: Admin can start the game server
- FR3: Admin can stop the game server gracefully
- FR4: Admin can restart the game server
- FR5: Monitor can view current server status (running/stopped, uptime, game version)

**Console Access (FR6-9):**

- FR6: Admin can view real-time game server console output via WebSocket stream
- FR7: Admin can scroll back through console history buffer
- FR8: Admin can send commands to the game server console
- FR9: Console access is restricted to Admin role only (sensitive data)

**Mod Management (FR10-17):**

- FR10: Admin can view list of installed mods with version and compatibility status
- FR11: Admin can install a mod by entering its slug
- FR12: System validates mod compatibility against current game version before installation
- FR13: System displays warning when mod is not explicitly compatible with current game version
- FR14: Admin can enable an installed mod
- FR15: Admin can disable an installed mod
- FR16: Admin can remove an installed mod
- FR17: Monitor can view list of installed mods (read-only)

**Game Configuration (FR18-22):**

- FR18: Admin can view list of game configuration files
- FR19: Admin can read contents of a game configuration file
- FR20: Admin can edit and save game configuration files
- FR21: Monitor can view list of game configuration files (read-only)
- FR22: Monitor can read contents of game configuration files (read-only)

**Settings Management (FR23-26):**

- FR23: Admin can view server management settings (server name, whitelist mode, etc.)
- FR24: Admin can update server management settings
- FR25: Admin can view player whitelist
- FR26: Admin can add/remove players from whitelist

**Health & Observability (FR27-30):**

- FR27: System exposes health check endpoint (`/healthz`) without authentication
- FR28: System exposes readiness check endpoint (`/readyz`) without authentication
- FR29: Health endpoints report game server process status (running/stopped)
- FR30: System exposes metrics endpoint (`/metrics`) without authentication (POST-MVP)

**Authentication & Authorization (FR31-37):**

- FR31: Protected API endpoints require valid API key via `X-API-Key` header
- FR32: System supports Monitor API keys with read-only access to non-sensitive data
- FR33: System supports Admin API keys with full access including console and write operations
- FR34: Console stream and history are restricted to Admin role (sensitive data protection)
- FR35: Write operations are restricted to Admin role
- FR36: System returns 401 Unauthorized for missing or invalid API key
- FR37: System returns 403 Forbidden when key lacks permission for requested operation

**Deployment & Setup (FR38-39):**

- FR38: System can be deployed via docker-compose with minimal configuration
- FR39: System configuration is provided via environment variables

### NonFunctional Requirements

**Performance (NFR1-3):**

- NFR1: Console output appears in web UI within 1 second of being generated by game server
- NFR2: WebSocket preferred for real-time streaming; polling at 1-second intervals is acceptable fallback
- NFR3: API endpoints under local control respond within 500ms; external API calls may take longer with progress indication

**Security (NFR4-7):**

- NFR4: API keys are stored securely and never logged in plaintext
- NFR5: TLS termination is out of scope for MVP; users requiring HTTPS must provide a reverse proxy
- NFR6: Console history buffer does not persist to disk (sensitive data protection)
- NFR7: Failed authentication attempts are logged for security monitoring

**Reliability (NFR8-10):**

- NFR8: Management API remains available when game server is stopped or crashed
- NFR9: System recovers gracefully from game server process crashes without requiring restart
- NFR10: WebSocket disconnections reconnect automatically without losing significant console history

**Integration (NFR11-13):**

- NFR11: System gracefully handles VintageStory mod API unavailability (cached data, clear error messages)
- NFR12: Mod installation failures due to network issues are reported clearly to user
- NFR13: System does not require external network access for core functionality (mod management requires it)

**Observability (NFR14-16):**

- NFR14: API server logs are structured (JSON) for easy parsing; game server logs remain in their native format
- NFR15: Health endpoints differentiate between "API healthy" and "game server healthy"
- NFR16: Errors include sufficient context for debugging without exposing sensitive data

### Additional Requirements

**From Architecture - Starter Template:**

- Project uses mise for development environment (Python 3.13, uv, Bun)
- Backend: uv + FastAPI pattern with httpx, pydantic-settings, structlog
- Frontend: Vite + React 19.2 + TypeScript + shadcn/ui + Tailwind CSS v4
- Project initialization should be the first implementation story

**From Architecture - Infrastructure:**

- Single container deployment (API + game server in same container) for simplified deployment
- Base image: `mcr.microsoft.com/dotnet/runtime:8.0.22-noble-amd64` (Ubuntu Noble + .NET 8 + Python 3.12)
- Single volume mount at `/data` for all persistence
- Atomic file writes for state persistence (temp file + rename pattern)
- Docker registry: `ghcr.io/craquehouse/vintagestory-server`

**From Architecture - State Management:**

- In-memory state with JSON file sync (`data/state/state.json`)
- WebSocket reconnection with exponential backoff (max 30s, 10 retries)

**From Architecture - API Patterns:**

- API versioning: `/api/v1alpha1`
- Response envelope: `{"status": "ok|error", "data": {...}}`
- JSON field naming: snake_case in API, camelCase in frontend (transform at boundary)
- Error codes centralized in `models/errors.py`

**From Architecture - Frontend Patterns:**

- TanStack Query v5 for server state
- React Context for UI state only (theme, sidebar)
- React Router v7 for navigation
- xterm.js for terminal (Console + Shell modes)
- Catppuccin Mocha/Latte theming via JSON config files

**From UX Design - Server Lifecycle:**

- Server can be in "Not Installed" state with Install button and version input
- Installation progress stages: Downloading → Extracting → Verifying → Complete
- Version mismatch alert when installed differs from configured
- Server states: Not Installed, Installing, Installed (Stopped), Installed (Running), Upgrading, Error

**From UX Design - Pending Restart Pattern:**

- Changes requiring restart tracked server-side (`pendingRestart` state)
- Persistent header banner: "⟳ Restart required · N pending changes · [Restart Now]"
- Two workflows: immediate restart or batch changes

**From UX Design - Components:**

- ServerStatusBadge (6 states with icons)
- CompatibilityBadge (Compatible/Not verified/Incompatible)
- ModLookupInput (accepts slugs or URLs, debounced lookup)
- PendingRestartBanner (header component)
- TerminalView (xterm.js wrapper with Console/Shell tabs)
- ServerInstallCard (empty state for no server)
- InstallProgress (progress bar with stage labels)

**From UX Design - Accessibility:**

- WCAG 2.1 Level AA compliance
- Minimum 44x44px touch targets
- Keyboard navigation via Radix primitives
- ARIA live regions for dynamic content
- Respect `prefers-reduced-motion`

### FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR1 | Epic 3 | Admin views server status |
| FR2 | Epic 3 | Admin starts server |
| FR3 | Epic 3 | Admin stops server |
| FR4 | Epic 3 | Admin restarts server |
| FR5 | Epic 3 | Monitor views server status |
| FR6 | Epic 4 | Admin views console stream |
| FR7 | Epic 4 | Admin scrolls console history |
| FR8 | Epic 4 | Admin sends console commands |
| FR9 | Epic 4 | Console restricted to Admin |
| FR10 | Epic 5 | Admin views mod list |
| FR11 | Epic 5 | Admin installs mod by slug |
| FR12 | Epic 5 | System validates compatibility |
| FR13 | Epic 5 | System shows compatibility warnings |
| FR14 | Epic 5 | Admin enables mod |
| FR15 | Epic 5 | Admin disables mod |
| FR16 | Epic 5 | Admin removes mod |
| FR17 | Epic 5 | Monitor views mod list |
| FR18 | Epic 6 | Admin views config file list |
| FR19 | Epic 6 | Admin reads config file |
| FR20 | Epic 6 | Admin edits config file |
| FR21 | Epic 6 | Monitor views config file list |
| FR22 | Epic 6 | Monitor reads config file |
| FR23 | Epic 7 | Admin views settings |
| FR24 | Epic 7 | Admin updates settings |
| FR25 | Epic 7 | Admin views whitelist |
| FR26 | Epic 7 | Admin manages whitelist |
| FR27 | Epic 1 | Health endpoint exposed |
| FR28 | Epic 1 | Readiness endpoint exposed |
| FR29 | Epic 1 | Health reports game server status |
| FR31 | Epic 2 | API key authentication |
| FR32 | Epic 2 | Monitor role support |
| FR33 | Epic 2 | Admin role support |
| FR34 | Epic 2 | Console restricted to Admin |
| FR35 | Epic 2 | Writes restricted to Admin |
| FR36 | Epic 2 | 401 for invalid key |
| FR37 | Epic 2 | 403 for insufficient role |
| FR38 | Epic 1 | docker-compose deployment |
| FR39 | Epic 1 | Environment variable config |

**Note:** FR30 (Metrics endpoint) is marked POST-MVP in PRD, not included in MVP epics.

### Post-MVP FR Coverage Map

| FR | Epic | Description |
|----|------|-------------|
| FR40 | Epic 9 | Secure WebSocket token auth |
| FR41 | Epic 9 | Short-lived token validation |
| FR42 | Epic 9 | Auto-create directories on startup |
| FR43 | Epic 9 | Log directory creation |
| FR44 | Epic 9 | Cache eviction strategy |
| FR45 | Epic 9 | Configurable cache limits |
| FR46 | Epic 9 | Log cache eviction events |
| FR47 | Epic 9 | Debug logging throughout services |
| FR48 | Epic 9 | Toggle debug via env var |
| FR49 | Epic 9 | Correlation IDs in debug logs |
| FR50 | Epic 9 | Distinct color for user commands |
| FR51 | Epic 9 | [CMD] prefix for commands |
| FR52 | Epic 9 | JSON syntax colorization |
| FR53 | Epic 9 | Distinct colors for JSON types |
| FR54 | Epic 9 | Show all directories in browser |
| FR55 | Epic 9 | Dynamic directory listing |
| FR56 | Epic 10 | Split Mods into tabs |
| FR57 | Epic 10 | Installed tab functionality |
| FR58 | Epic 10 | Browse tab experience |
| FR59 | Epic 10 | Default newest mods |
| FR60 | Epic 10 | Pre-filter compatible mods |
| FR61 | Epic 10 | Immediate content load |
| FR62 | Epic 10 | Keyword search |
| FR63 | Epic 10 | Debounced search |
| FR64 | Epic 10 | Maintain filters during search |
| FR65 | Epic 10 | Filter by side |
| FR66 | Epic 10 | Filter by tags |
| FR67 | Epic 10 | Filter by game version |
| FR68 | Epic 10 | Filter by mod type |
| FR69 | Epic 10 | Combined filters (AND) |
| FR70 | Epic 10 | Display/remove active filters |
| FR71 | Epic 10 | Sort options |
| FR72 | Epic 10 | Default sort: newest |
| FR73 | Epic 10 | Persist sort selection |
| FR74 | Epic 10 | Card display format |
| FR75 | Epic 10 | Compatibility badges on cards |
| FR76 | Epic 10 | Clickable cards to details |
| FR77 | Epic 10 | Full mod detail view |
| FR78 | Epic 10 | Install with version selection |
| FR79 | Epic 10 | Show installed status in detail |
| FR80 | Epic 10 | Pagination support |
| FR81 | Epic 10 | Infinite scroll or pages |
| FR82 | Epic 10 | Maintain position on return |
| FR83 | Epic 10 | Install from browse/detail |
| FR84 | Epic 10 | Show compatibility before install |
| FR85 | Epic 10 | Update UI after install |
| FR86 | Epic 11 | Expandable Game Server sub-navigation |
| FR87 | Epic 11 | Sub-nav order: Version, Settings, Mods, Console |
| FR88 | Epic 11 | Persist expanded/collapsed state |
| FR89 | Epic 11 | Dynamic Installation/Version label |
| FR90 | Epic 11 | Rename Settings to VSManager |
| FR91 | Epic 11 | Mods under Game Server nav |
| FR92 | Epic 11 | Dedicated Console page |
| FR93 | Epic 11 | Dedicated Settings page |
| FR94 | Epic 11 | Version/Installation page |
| FR95 | Epic 11 | Mods at /game-server/mods with redirects |
| FR96 | Epic 11 | Empty state when server not installed |
| FR97 | Epic 11 | Remove install from Dashboard |
| FR98 | Epic 11 | Dashboard link to Version page |
| FR99 | Epic 11 | Default redirect /game-server → /game-server/version |
| FR100 | Epic 12 | Collect API server metrics |
| FR101 | Epic 12 | Collect game server process metrics |
| FR102 | Epic 12 | Configurable metrics interval |
| FR103 | Epic 12 | Historical metrics storage |
| FR104 | Epic 12 | Current metrics API |
| FR105 | Epic 12 | Historical metrics API with time filter |
| FR106 | Epic 12 | Admin-only metrics access |
| FR107 | Epic 12 | Dashboard stat cards |
| FR108 | Epic 12 | Memory card with API/Game breakdown |
| FR109 | Epic 12 | Time-series memory chart |
| FR110 | Epic 12 | Selectable chart time ranges |
| FR111 | Epic 12 | Quick links to Game Server pages |
| FR112 | Epic 12 | Disabled quick links when no server |
| FR113 | Epic 13 | Version list from stable/unstable |
| FR114 | Epic 13 | Channel filter for versions |
| FR115 | Epic 13 | Version card display |
| FR116 | Epic 13 | Version data caching |
| FR117 | Epic 13 | Version cards like mod browser |
| FR118 | Epic 13 | Installed version indicator |
| FR119 | Epic 13 | Latest version badge |
| FR120 | Epic 13 | Version sort by newest |
| FR121 | Epic 13 | Install from version card |
| FR122 | Epic 13 | Install confirmation dialog |
| FR123 | Epic 13 | Upgrade version comparison |
| FR124 | Epic 13 | Downgrade warning |
| FR125 | Epic 13 | Server-running warning |
| FR126 | Epic 13 | Installation progress display |
| FR127 | Epic 13 | Install Latest Stable quick action |
| FR128 | Epic 13 | Update to Latest quick action |
| FR129 | Epic 14 | Detect newer releases by release order |
| FR130 | Epic 14 | Offer newest compatible release |
| FR131 | Epic 14 | No offer when only incompatible releases are newer |
| FR132 | Epic 14 | Unknown status for unlisted mods or versions |
| FR133 | Epic 14 | View mod update status |
| FR134 | Epic 14 | On-demand update check |
| FR135 | Epic 14 | One-click mod update |
| FR136 | Epic 14 | Warning before not-verified update |
| FR137 | Epic 14 | Failed update leaves mod unchanged |
| FR138 | Epic 14 | Preserve enabled state across version change |
| FR139 | Epic 14 | Pending restart on version change |
| FR140 | Epic 14 | Switch to any listed release |
| FR141 | Epic 14 | Warnings when switching versions |
| FR142 | Epic 14 | Reuse cached release, otherwise download |
| FR143 | Epic 14 | Update all compatible mods |
| FR144 | Epic 14 | Update all skips and reports not-verified mods |
| FR145 | Epic 14 | Per-mod results, failures isolated |
| FR146 | Epic 14 | Scheduled update checks |
| FR147 | Epic 14 | Update status survives API restart |
| FR148 | Epic 14 | Update count on Dashboard and navigation |
| FR149 | Epic 14 | Admin-only webhook URL treated as a secret |
| FR150 | Epic 14 | One webhook alert per new update |
| FR151 | Epic 14 | Webhook failures isolated from checks |
| FR152 | Epic 15 | One version across API, web and image |
| FR153 | Epic 15 | API reports its version |
| FR154 | Epic 15 | Web UI shows the running version |
| FR155 | Epic 15 | Changelog from conventional commits |
| FR156 | Epic 15 | Planning scopes omitted from changelog |
| FR157 | Epic 15 | Preview unreleased changelog |
| FR158 | Epic 15 | One-command release |
| FR159 | Epic 15 | Release preconditions |
| FR160 | Epic 15 | Release dry run |
| FR161 | Epic 15 | GitHub release with notes on tag push |
| FR162 | Epic 15 | GHCR image tags, pre-release handling |
| FR163 | Epic 15 | Tag and version mismatch blocks publishing |
| FR164 | Epic 15 | SBOM and signed provenance |
| FR165 | Epic 15 | Runtime web API key, none in the image |
| FR166 | Epic 15 | Release and install documentation |
| FR167 | Epic 16 | Mod browser keeps search, filters and sort |
| FR168 | Epic 16 | Page and scroll restored with browse state |
| FR169 | Epic 16 | Installed mod recognized by any mod ID |
| FR170 | Epic 16 | Latest supported game version for incompatible mods |
| FR171 | Epic 16 | Withdrawn (lookup preview removed in VSS-195); Story 16.4 delivers the shared description sanitizer and safe links |
| FR172 | Epic 16 | Installed mods as cards on phones |
| FR173 | Epic 16 | Settings use desktop width |
| FR174 | Epic 16 | File browser breadcrumbs |
| FR175 | Epic 16 | Name (A-Z) sort works, server-side and paged |
| FR176 | Epic 16 | Empty settings shown and saved as empty; Password masked |
| FR177 | Epic 17 | Nulls in mod database data cannot fail a request |
| FR178 | Epic 17 | Back to Browse on the mod detail error state |
| FR179 | Epic 17 | Install considers only the requested mod ID |
| FR180 | Epic 17 | Install picks the newest stable release |
| FR181 | Epic 17 | "(Latest)" matches what install picks |
| FR182 | Epic 17 | One operation per mod at a time, 409 otherwise |
| FR183 | Epic 17 | Case-insensitive `modinfo.json` keys on import |
| FR184 | Epic 17 | Browse cards recognize any installed mod ID |
| FR185 | Epic 17 | Update status for a newly installed mod |
| FR186 | Epic 17 | Monitor keys never receive the server password |
| FR187 | Epic 17 | Interval settings reschedule their jobs |
| FR188 | Epic 17 | Unset boolean settings show the game default |
| FR189 | Epic 17 | Mods tabs work on a mod detail page |
| FR190 | Epic 17 | Out-of-range browse page is clamped |
| FR191 | Epic 17 | Installed mods fit tablet widths |
| FR192 | Epic 17 | Settings tabs fit phones |
| FR193 | Epic 17 | Game Settings title row aligned with the panel |
| FR194 | Epic 18 | Screenshot gallery on the mod detail page |
| FR195 | Epic 18 | Gallery keyboard, touch, alt text, lazy loading, phones |
| FR196 | Epic 18 | Trailer link, no embedded player |
| FR197 | Epic 18 | Only allow-listed media URLs leave the API |
| FR198 | Epic 18 | Description links marked as opening in a new tab |
| FR199 | Epic 18 | Install refuses a file-name collision with 409 |
| FR200 | Epic 18 | Update record stored after a version change |
| FR201 | Epic 18 | Game version indicator on browse cards, no per-card request |
| FR202 | Epic 18 | No indicator when the version or data is unknown |
| FR203 | Epic 18 | Sort control for installed mod cards |
| FR204 | Epic 18 | Installed mods table fits at 1024px with a long name |
| FR205 | Epic 19 | Config file viewer serves `.json` files only |
| FR206 | Epic 19 | Other config file requests refused with an error code, never 500 |
| FR207 | Epic 19 | Recursive secret redaction for roles other than Admin |
| FR208 | Epic 19 | Roles other than Admin see the root files and `ModConfig` only |
| FR209 | Epic 19 | `VS_GAME_VERSION` removed |
| FR210 | Epic 19 | No key for the web UI when `VS_API_KEY` is unset; set-up message |
| FR211 | Epic 19 | Start-up warnings for the Admin key as web key and for no web key |
| FR212 | Epic 19 | `VS_API_KEY` documentation, compose defaults, breaking release note |
| FR213 | Epic 19 | Enforced Content-Security-Policy on the web UI's pages |
| FR214 | Epic 19 | Every page works under the policy |
| FR215 | Epic 19 | `VS_CSP_MODE` and the other page headers |
| FR216 | Epic 19 | Blocked description images replaced by text |
| FR217 | Epic 19 | API documentation pages only in debug mode |
| FR218 | Epic 19 | Enable and disable refuse a taken file name with 409 |
| FR219 | Epic 19 | Version change file-name refusal is 409, not 500 |
| FR220 | Epic 19 | File-name collisions ignore letter case |
| FR221 | Epic 19 | Download cache keyed by file ID |
| FR222 | Epic 19 | Missing mod file on enable or disable is 409 `MOD_FILE_MISSING` |
| FR223 | Epic 19 | Start-up recovery of interrupted mod file operations |
| FR224 | Epic 19 | Logo URL allow-list and no referrer |
| FR225 | Epic 19 | Homepage and source URLs checked |
| FR226 | Epic 19 | Malformed mod database bodies are 502 |
| FR227 | Epic 19 | One shared request for the listing and for the game version list |
| FR228 | Epic 19 | E2E job in CI against the built image with a seeded `serverconfig.json` |
| FR229 | Epic 19 | E2E tags for tests CI leaves out; settings specs run in CI |
| FR230 | Epic 19 | One `/config.js` key helper, no `localStorage` key scripts |
| FR231 | Epic 19 | Mod state reconciled with the mods directory at start-up |
| FR232 | Epic 19 | The start-up sync skips what is not a readable mod archive and never fails start-up |
| FR233 | Epic 19 | Note in the file browser for roles other than Admin |
| FR234 | Epic 20 | The API is formatted by one commit |
| FR235 | Epic 20 | `just lint-api` and CI check the API's format |
| FR236 | Epic 20 | The format commit is in `.git-blame-ignore-revs` |
| FR237 | Epic 20 | Pyright reports 0 warnings |
| FR238 | Epic 20 | No skipped web tests |
| FR239 | Epic 20 | Web tests run in the `vmThreads` pool |
| FR240 | Epic 20 | E2E specs are type-checked |
| FR241 | Epic 20 | ShellCheck covers every script |
| FR242 | Epic 20 | Recipes pass quoted arguments intact |
| FR243 | Epic 20 | Playwright output is not tracked |
| FR244 | Epic 20 | `just semgrep`: pinned version, six packs, source only |
| FR245 | Epic 20 | Pull requests fail only on findings they add; `main` is scanned in full |
| FR246 | Epic 20 | SARIF to code scanning from a job with its own permission |
| FR247 | Epic 20 | No open finding; the `nosemgrep` exception |
| FR248 | Epic 20 | Seeded directories; file browser navigation tests in CI |
| FR249 | Epic 20 | A new directory appears after a reload |
| FR250 | Epic 20 | Playwright browsers cached in CI |
| FR251 | Epic 20 | The connection reset in the E2E stub is explained or recorded |
| FR252 | Epic 20 | Mod database tests run in CI on recorded answers, through the address setting |
| FR253 | Epic 20 | Recordings with a manifest and a refresh command |
| FR254 | Epic 20 | Live-only tests are tagged and stay local |
| FR255 | Epic 20 | Dockerfile images pinned by digest; uv matches `.mise.toml` |
| FR256 | Epic 20 | Renovate moves the pins |
| FR257 | Epic 20 | Story numbering rule matches practice |
| FR258 | Epic 20 | `VS_MOD_DB_URL`: the mod database's address is an optional setting |
| FR259 | Epic 20 | The address is validated at start-up; `http` only with `VS_DEBUG=true` |
| FR260 | Epic 21 | The web is formatted by one commit |
| FR261 | Epic 21 | Prettier pinned, with a committed configuration and ignore file |
| FR262 | Epic 21 | `just lint-web` and CI check the web's format |
| FR263 | Epic 21 | The web format commit is in `.git-blame-ignore-revs` |
| FR264 | Epic 21 | The uv update keeps the preset's hold; the red first day is documented |
| FR265 | Epic 21 | Image digest refreshes are `chore(container)` |
| FR266 | Epic 21 | `VS_LOG_LEVEL` sets the log level at start-up |
| FR267 | Epic 21 | An invalid `VS_LOG_LEVEL` stops start-up; the debug switch still gives DEBUG |
| FR268 | Epic 21 | Discord `ptb.` and `canary.` webhook URLs are redacted |
| FR269 | Epic 21 | Config listings show nothing that leaves the data directory |
| FR270 | Epic 21 | 403 for a forbidden directory even when the data directory is missing |
| FR271 | Epic 21 | The remove dialog stays open until the removal succeeds |
| FR272 | Epic 21 | A failed removal: one message, dialog stays open |
| FR273 | Epic 21 | The remove dialog's running state belongs to one mod |
| FR274 | Epic 21 | One error message per failed action |
| FR275 | Epic 21 | Versions sort by Semantic Versioning precedence |
| FR276 | Epic 21 | Sortable headers expose `aria-sort` |
| FR277 | Epic 21 | Dialog and sheet close buttons are 44px |
| FR278 | Epic 21 | Every new-tab link says so |
| FR279 | Epic 21 | The mod detail page fits phones |
| FR280 | Epic 21 | Mod descriptions are typeset |
| FR281 | Epic 21 | Tab buttons are 44px tall below 1024px |
| FR282 | Epic 21 | Settings tabs answer arrow keys at once, or the cause is recorded |
| FR283 | Epic 21 | Jobs and Version tables fit phones; every page measured |
| FR284 | Epic 21 | The sidebar follows the width until the user chooses |
| FR285 | Epic 21 | 1280px maximum content width, console excepted |
| FR286 | Epic 21 | Mod data is refreshed when the installed game version changes |
| FR287 | Epic 22 | Players online are counted from the game's join and leave lines |
| FR288 | Epic 22 | `playersOnline` in the JSON metrics and a dashboard Players card |
| FR289 | Epic 22 | An open Prometheus `/metrics` with the game server's metrics |
| FR290 | Epic 22 | `/metrics` is read live; absent series when the game is stopped |
| FR291 | Epic 22 | The README documents `/metrics` with a scrape example |
| FR292 | Epic 22 | `scheduled_restart_times`: daily `HH:MM` times in `TZ` |
| FR293 | Epic 22 | A scheduled restart restarts a running game, never starts a stopped one |
| FR294 | Epic 22 | Warnings at 15, 5 and 1 minutes before a scheduled restart |
| FR295 | Epic 22 | Restart times apply at once and are listed in Scheduled Jobs |
| FR296 | Epic 22 | Stop time measured; `VSS-zws` verified |
| FR297 | Epic 22 | Daily cleanup job at 03:00; log archives left to the game (it keeps 5) |
| FR298 | Epic 22 | Backups kept to a count only when set; nothing else deleted |
| FR299 | Epic 22 | Cleanup logged; the README says who rotates which logs |
| FR300 | Epic 22 | An On switch per interval field |
| FR301 | Epic 22 | A Metrics Collection field |
| FR302 | Epic 22 | Interval bounds and fallbacks match the API |
| FR303 | Epic 22 | No API Settings tab for a Monitor key |
| FR304 | Epic 22 | Restart times edited in the API Settings tab |
| FR305 | Epic 22 | Backup limit edited in the API Settings tab |
| FR306 | Epic 22 | A restart-required game setting is a pending restart, cleared by a restart |
| FR307 | Epic 22 | A restart-required change made while the game runs survives a live change |
| FR308 | Epic 22 | Stopping the container stops the game through the normal stop first, so the world is saved |
| FR309 | Epic 23 | The config viewer reads JSON5 |
| FR310 | Epic 23 | An unparseable file shows its error with line and column |
| FR311 | Epic 23 | Admin's read returns the text and a version |
| FR312 | Epic 23 | The file browser carries paths as lists of names |
| FR313 | Epic 23 | Game Settings are read-only for keys that are not Admin |
| FR314 | Epic 23 | Admin saves an existing config file's text as sent |
| FR315 | Epic 23 | A save is refused while the game server is not stopped |
| FR316 | Epic 23 | A save with a stale version is refused |
| FR317 | Epic 23 | A text can be checked without saving |
| FR318 | Epic 23 | A serverconfig.json save drops the pending edits it changes |
| FR319 | Epic 23 | Config files are edited in the file browser |
| FR320 | Epic 23 | Admin sees config text with comments |
| FR321 | Epic 23 | Each save keeps the replaced text as a revision |
| FR322 | Epic 23 | Two API settings limit the history |
| FR323 | Epic 23 | Revisions can be listed, read and restored through the API |
| FR324 | Epic 23 | History, comparison and restore in the file browser |
| FR325 | Epic 23 | History limits edited in the API Settings tab |
| FR326 | Epic 23 | The README documents editing and history |
| FR327 | Epic 24 | API tests run without a `.env` file |
| FR328 | Epic 24 | The Vintage Story icon is the favicon |
| FR329 | Epic 24 | Missing static files answer 404 |
| FR330 | Epic 24 | `/assets` carries the security headers |
| FR331 | Epic 24 | A version change with the mod's file missing is 409 |
| FR332 | Epic 24 | Cache eviction covers every file type |
| FR333 | Epic 24 | A removed mod's modinfo cache is removed |
| FR334 | Epic 24 | The update check fills in a missing asset ID |
| FR335 | Epic 24 | Mods unknown to the mod database are local mods |
| FR336 | Epic 24 | Admin can rescan the mods folder |
| FR337 | Epic 24 | Unused files in the mods folder are listed |
| FR338 | Epic 24 | Admin can delete a listed unused file |
| FR339 | Epic 24 | The Installed tab shows unused files |
| FR340 | Epic 24 | `.cs` files, folders and mod files are never listed |
| FR341 | Epic 24 | Installed mods can be filtered |
| FR342 | Epic 24 | Installed filters are kept in the URL |
| FR343 | Epic 24 | Blocked description media shows a note |
| FR344 | Epic 25 | serverconfig.json is read through one typed model |
| FR345 | Epic 25 | A malformed serverconfig.json reports line and column |
| FR346 | Epic 25 | Mod and save paths are checked |
| FR347 | Epic 25 | A mods folder missing from ModPaths is reported |
| FR348 | Epic 25 | Game Settings warns about a wrong path |
| FR349 | Epic 25 | Entity Spawning shows the running game's value |
| FR350 | Epic 25 | Entity Spawning shows the last value seen while stopped |
| FR351 | Epic 25 | Entity Spawning is changed through the console only |
| FR352 | Epic 25 | VS_CFG_ENTITY_SPAWNING is applied after each start |
| FR353 | Epic 25 | A console change to Entity Spawning is reflected |
| FR354 | Epic 28 | Each mod records its source |
| FR355 | Epic 28 | Uploaded and linked mods are not looked up in the mod database |
| FR356 | Epic 28 | Admin can upload a mod file |
| FR357 | Epic 28 | Uploads and downloads have a size limit |
| FR358 | Epic 28 | A file without a valid modinfo.json is refused |
| FR359 | Epic 28 | An installed mod is replaced only when asked |
| FR360 | Epic 28 | Admin can install a mod from a link |
| FR361 | Epic 28 | A link install never reaches internal addresses |
| FR362 | Epic 28 | A link install has time and size limits |
| FR363 | Epic 28 | The Installed tab adds a mod from a file or a link |
| FR364 | Epic 28 | The dialog offers a replace |
| FR365 | Epic 28 | Release mods are checked for updates |
| FR366 | Epic 28 | Release mods can be updated |

## Epic List

### Epic 1: Project Foundation & Health Monitoring

Developers can set up the project using the defined starter template, and operations teams can verify the system is running via health endpoints. This epic establishes the scaffolding for all future development and provides the first deployable artifact.

**FRs covered:** FR27, FR28, FR29, FR38, FR39

**MVP Scope:**

- Project initialization per Architecture starter template (mise, uv, Bun)
- Backend scaffolding (FastAPI + dependencies)
- Frontend scaffolding (Vite + React + shadcn/ui)
- Health endpoints (`/healthz`, `/readyz`) without authentication
- docker-compose configuration
- Environment variable configuration pattern

---

### Epic 2: Authentication & API Security

API consumers can authenticate with appropriate role-based access, and the system enforces security boundaries between Admin and Monitor roles.

**FRs covered:** FR31, FR32, FR33, FR34, FR35, FR36, FR37

**MVP Scope:**

- API key authentication via `X-API-Key` header
- Admin role with full access
- Monitor role with read-only access to non-sensitive data
- Console access restricted to Admin only
- Proper 401/403 responses
- Security logging for failed auth attempts

---

### Epic 3: Server Lifecycle Management

Admins can install the VintageStory server by version number and control it (start, stop, restart) from the web UI. This is the first "real user value" epic.

**FRs covered:** FR1, FR2, FR3, FR4, FR5

**MVP Scope:**

- Server installation by version number (download tarball, extract, post-install setup)
- Download progress indication
- Server start/stop/restart controls
- Server status display (running/stopped, version, uptime)
- Dashboard with server controls
- ServerStatusBadge component
- ServerInstallCard for empty state

**Post-MVP (deferred):**

- Version switching/upgrade
- Rollback to previous version

---

### Epic 4: Real-Time Console Access

Admins can monitor game server output in real-time and send commands, enabling troubleshooting without container access.

**FRs covered:** FR6, FR7, FR8, FR9

**MVP Scope:**

- WebSocket console streaming
- Console history buffer (in-memory ring buffer)
- Command input to game server
- Admin-only access enforcement
- TerminalView component with xterm.js (Console mode)
- Auto-reconnection with exponential backoff

**Post-MVP (deferred):**

- Shell tab (PTY access)
- Console search

---

### Epic 5: Mod Management

Admins can install, enable/disable, and remove mods via the web UI with automatic compatibility validation. This is the "slug to success" experience - the defining user journey.

**FRs covered:** FR10, FR11, FR12, FR13, FR14, FR15, FR16, FR17

**MVP Scope:**

- Mod list with version and compatibility status
- Install mod by slug (or URL - parsed to slug)
- Compatibility validation against game version
- Compatibility warnings for unverified mods
- Enable/disable mods
- Remove mods
- Monitor read-only access to mod list
- ModLookupInput component
- CompatibilityBadge component
- Pending restart indication

**Post-MVP (delivered by Epic 14):**

- Mod update detection
- One-click updates
- Version switching/rollback

---

### Epic 6: Game Configuration Management

Admins can view and edit game server configuration files through the web UI, completing the "no terminal needed" promise.

**FRs covered:** FR18, FR19, FR20, FR21, FR22

**MVP Scope:**

- List game configuration files
- Read configuration file contents
- Edit and save configuration files (JSON)
- Monitor read-only access
- Config editor component
- Pending restart pattern for config changes

---

### Epic 7: Server Settings & Whitelist Management

Admins can manage server-level settings and control player access via whitelist.

**FRs covered:** FR23, FR24, FR25, FR26

**MVP Scope:**

- View server management settings
- Update settings (server name, whitelist mode, etc.)
- View player whitelist
- Add/remove players from whitelist
- Settings UI page

---

## Epic Summary

| Epic | Title | FRs | User Value |
|------|-------|-----|------------|
| 1 | Project Foundation & Health Monitoring | 5 | Deployable system with health checks |
| 2 | Authentication & API Security | 7 | Secure role-based API access |
| 3 | Server Lifecycle Management | 5 | Install and control game server |
| 4 | Real-Time Console Access | 4 | Monitor and command server in browser |
| 5 | Mod Management | 8 | Install mods by slug with compatibility |
| 6 | Game Configuration Management | 5 | Edit configs without file access |
| 7 | Server Settings & Whitelist | 4 | Manage settings and player access |
| **Total** | | **38** | |

## Dependency Flow

```
Epic 1 (Foundation)
    ↓
Epic 2 (Auth) ←── Required by all protected endpoints
    ↓
Epic 3 (Server Lifecycle) ←── First user value
    ↓
Epic 4 (Console) ←── Requires server to monitor
    ↓
Epic 5 (Mods) ←── Uses console for verification, server for restarts
    ↓
Epic 6 (Config) ←── Uses pending restart pattern
    ↓
Epic 7 (Settings) ←── Final admin capabilities
```

Each epic is standalone once complete and enables future epics without requiring them.

---

## Epic 1: Project Foundation & Health Monitoring

Developers can set up the project using the defined starter template, and operations teams can verify the system is running via health endpoints.

### Story 1.1: Initialize Development Environment and Project Structure

As a **developer**,
I want **a properly configured development environment with project scaffolding**,
So that **I can begin implementing features with consistent tooling across the team**.

**Acceptance Criteria:**

**Given** a fresh clone of the repository
**When** I run `mise trust && mise install`
**Then** Python 3.13, uv, and Bun are installed at the pinned versions
**And** a `.mise.toml` file exists at the project root with tool versions specified

**Given** the development environment is set up
**When** I navigate to the `api/` directory
**Then** a `pyproject.toml` exists with project name `vintagestory-api`
**And** dependencies include `fastapi[standard]`, `httpx`, `pydantic-settings`, `structlog`
**And** dev dependencies include `pytest`, `pytest-asyncio`, `ruff`, `respx`

**Given** the development environment is set up
**When** I navigate to the `web/` directory
**Then** a `package.json` exists with React 19.2 and TypeScript configured
**And** Tailwind CSS v4 is installed and configured
**And** shadcn/ui is initialized with the project's component configuration

**Given** the project structure is initialized
**When** I examine the repository root
**Then** the directory structure matches the Architecture specification
**And** `.gitignore` excludes appropriate files (node_modules, .venv, **pycache**, data/)

---

### Story 1.2: Backend API Skeleton with Health Endpoints

As an **operations engineer**,
I want **health check endpoints that report system status**,
So that **I can configure Kubernetes probes and monitoring systems**.

**Acceptance Criteria:**

**Given** the API server is running
**When** I send a GET request to `/healthz`
**Then** I receive a 200 status code
**And** the response follows the envelope format `{"status": "ok", "data": {...}}`
**And** no authentication is required
*(Covers FR27)*

**Given** the API server is running
**When** I send a GET request to `/readyz`
**Then** I receive a 200 status code when the API is ready to serve requests
**And** the response includes readiness information
**And** no authentication is required
*(Covers FR28)*

**Given** the API server is running
**When** I query the health endpoints
**Then** the response includes game server process status (running/stopped/not_installed)
**And** the API health is reported separately from game server health
*(Covers FR29, NFR15)*

**Given** the API server is running
**When** the game server process is not running
**Then** the API still responds to health checks (API healthy, game stopped)
*(Covers NFR8)*

**Given** any API request is made
**When** the server processes the request
**Then** structured JSON logs are emitted (in production mode)
**And** human-readable logs are emitted (in development mode)
*(Covers NFR14)*

---

### Story 1.3: Frontend Application Shell

As an **administrator**,
I want **a web interface with navigation and theming**,
So that **I can access server management features through a consistent UI**.

**Acceptance Criteria:**

**Given** I navigate to the web application
**When** the page loads
**Then** I see a sidebar with navigation items (Dashboard, Mods, Config, Terminal)
**And** I see a header displaying the server name placeholder
**And** the application uses Catppuccin Mocha theme by default (dark mode)

**Given** I am viewing the application
**When** I click the theme toggle in the header
**Then** the theme switches between Mocha (dark) and Latte (light)
**And** my preference is persisted in localStorage

**Given** I am viewing the application
**When** my system has `prefers-color-scheme: dark` or `light`
**Then** the initial theme respects my system preference (if no stored preference)

**Given** I am on any page
**When** I click a navigation item in the sidebar
**Then** the URL updates to reflect the selected section
**And** the main content area displays the corresponding view
**And** the active navigation item is visually highlighted

**Given** I am viewing the sidebar
**When** I click the collapse button
**Then** the sidebar collapses to icon-only mode (64px)
**And** my collapse preference is persisted in localStorage

**Given** I resize my browser to mobile width (<768px)
**When** the viewport is narrow
**Then** the sidebar is hidden by default
**And** a hamburger menu button appears to toggle the sidebar overlay

---

### Story 1.4: Docker Deployment Configuration

As a **server administrator**,
I want **to deploy the application using docker-compose**,
So that **I can run VintageStory Server Manager with minimal configuration**.

**Acceptance Criteria:**

**Given** I have Docker and docker-compose installed
**When** I run `docker compose up -d` with `docker-compose.yaml`
**Then** the container starts successfully
**And** the web UI is accessible on port 8080
**And** the health endpoints respond correctly
*(Covers FR38)*

**Given** the container is running
**When** I check the container logs
**Then** I see structured startup messages
**And** no errors are present for a clean start

**Given** I set environment variables (`VS_API_KEY_ADMIN`, etc.)
**When** the container starts
**Then** the application reads configuration from environment variables
**And** default values are used for optional unset variables
*(Covers FR39)*

**Given** a `docker-compose.dev.yaml` file exists
**When** I run `docker compose -f docker-compose.dev.yaml up --build`
**Then** the image builds from local source
**And** development defaults are applied (e.g., `VS_DEBUG=true`)

**Given** the container is running
**When** I examine the volume mounts
**Then** `/data` is mounted for persistent storage
**And** the directory structure matches Architecture specification (`/data/server/`, `/data/mods/`, `/data/state/`, etc.)

**Given** I have a `.env.example` file
**When** I review it
**Then** all configurable environment variables are documented with descriptions

---

## Epic 2: Authentication & API Security

API consumers can authenticate with appropriate role-based access, and the system enforces security boundaries between Admin and Monitor roles.

### Story 2.1: API Key Authentication Middleware

As an **API consumer**,
I want **to authenticate using an API key in the request header**,
So that **I can access protected endpoints securely**.

**Acceptance Criteria:**

**Given** I have a valid Admin API key
**When** I send a request with `X-API-Key: <valid-admin-key>` header
**Then** the request is authenticated successfully
**And** my role is identified as Admin
*(Covers FR31, FR33)*

**Given** I have a valid Monitor API key
**When** I send a request with `X-API-Key: <valid-monitor-key>` header
**Then** the request is authenticated successfully
**And** my role is identified as Monitor
*(Covers FR31, FR32)*

**Given** I send a request without an API key
**When** the endpoint requires authentication
**Then** I receive a 401 Unauthorized response
**And** the response body contains `{"status": "error", "error": {"code": "UNAUTHORIZED", "message": "..."}}`
*(Covers FR36)*

**Given** I send a request with an invalid API key
**When** the endpoint requires authentication
**Then** I receive a 401 Unauthorized response
**And** the failed attempt is logged with request context (but not the key value)
*(Covers FR36, NFR7)*

**Given** any authentication attempt occurs
**When** the system processes the request
**Then** API keys are never logged in plaintext
*(Covers NFR4)*

**Given** health endpoints (`/healthz`, `/readyz`)
**When** I send a request without authentication
**Then** the request succeeds (health endpoints remain unauthenticated)

---

### Story 2.2: Role-Based Access Control for API Endpoints

As a **system administrator**,
I want **different API keys to have different permission levels**,
So that **I can grant read-only access to monitoring systems while reserving write access for admins**.

**Acceptance Criteria:**

**Given** I am authenticated as Admin
**When** I attempt any API operation (read or write)
**Then** the operation is permitted
*(Covers FR33)*

**Given** I am authenticated as Monitor
**When** I attempt a read operation on non-sensitive endpoints
**Then** the operation is permitted
*(Covers FR32)*

**Given** I am authenticated as Monitor
**When** I attempt a write operation (POST, PUT, DELETE on protected resources)
**Then** I receive a 403 Forbidden response
**And** the response body contains `{"status": "error", "error": {"code": "FORBIDDEN", "message": "..."}}`
*(Covers FR35, FR37)*

**Given** I am authenticated as Monitor
**When** I attempt to access console endpoints (stream or history)
**Then** I receive a 403 Forbidden response
**And** the error message indicates console access requires Admin role
*(Covers FR34)*

**Given** role permissions are checked
**When** a 403 response is returned
**Then** the response clearly indicates the required role for the operation

---

### Story 2.3: Frontend API Client with Authentication

As a **frontend developer**,
I want **an API client that handles authentication and key transformation**,
So that **all API calls are properly authenticated and response data is correctly formatted**.

**Acceptance Criteria:**

**Given** the frontend application is configured
**When** API calls are made
**Then** the `X-API-Key` header is automatically included from configuration

**Given** the API returns a response with snake_case fields
**When** the API client processes the response
**Then** fields are transformed to camelCase for frontend consumption

**Given** the API returns a 401 Unauthorized response
**When** the frontend receives the error
**Then** an appropriate error state is displayed to the user
**And** the user is informed that authentication failed

**Given** the API returns a 403 Forbidden response
**When** the frontend receives the error
**Then** an appropriate error state is displayed
**And** the user is informed they lack permission for the operation

**Given** TanStack Query is configured
**When** API calls are made
**Then** server state is managed through TanStack Query hooks
**And** client-only state (theme, sidebar) uses React Context

---

## Epic 3: Server Lifecycle Management

Admins can install the VintageStory server by version number and control it (start, stop, restart) from the web UI.

### Story 3.1: Server Installation Service

As an **administrator**,
I want **to install the VintageStory server by providing a version number**,
So that **I can get a game server running without manual file management**.

**Acceptance Criteria:**

**Given** no server is installed
**When** I call `POST /api/v1alpha1/server/install` with `{"version": "1.21.3"}`
**Then** the system downloads the server tarball from the VintageStory CDN
**And** extracts it to `/data/server/`
**And** creates a symlink from `/data/server/Mods` to `/data/mods/`
**And** copies default config if none exists

**Given** a server installation is in progress
**When** I query `GET /api/v1alpha1/server/install/status`
**Then** I receive progress information (stage: downloading/extracting/configuring, percentage if available)

**Given** the download fails (network error, invalid version)
**When** the installation process encounters the error
**Then** the error is reported clearly with actionable message
**And** the system returns to "not installed" state

**Given** the version format is invalid
**When** I attempt installation
**Then** I receive a 400 Bad Request with validation error details

**Given** a server is already installed
**When** I attempt to install again
**Then** I receive an error indicating server already exists (version switching is post-MVP)

---

### Story 3.2: Server Lifecycle Control API

As an **administrator**,
I want **to start, stop, and restart the game server via API**,
So that **I can control the server without container access**.

**Acceptance Criteria:**

**Given** a server is installed and stopped
**When** I call `POST /api/v1alpha1/server/start`
**Then** the game server process starts
**And** the response confirms the action was initiated
*(Covers FR2)*

**Given** a server is running
**When** I call `POST /api/v1alpha1/server/stop`
**Then** the game server receives a graceful shutdown signal
**And** the process terminates cleanly
**And** the response confirms the action was initiated
*(Covers FR3)*

**Given** a server is running
**When** I call `POST /api/v1alpha1/server/restart`
**Then** the server stops gracefully and starts again
**And** the response confirms the restart was initiated
*(Covers FR4)*

**Given** no server is installed
**When** I attempt to start/stop/restart
**Then** I receive a 400 Bad Request indicating no server is installed

**Given** the server process crashes unexpectedly
**When** the API detects the crash
**Then** the server status updates to "stopped" with exit code information
**And** the API remains available and responsive
*(Covers NFR8, NFR9)*

---

### Story 3.3: Server Status API

As an **administrator or monitor**,
I want **to view the current server status**,
So that **I can see if the server is running and its version**.

**Acceptance Criteria:**

**Given** the API is running
**When** I call `GET /api/v1alpha1/server/status` as Admin
**Then** I receive server status including: state (not_installed/stopped/starting/running/stopping), version, uptime (if running)
*(Covers FR1)*

**Given** the API is running
**When** I call `GET /api/v1alpha1/server/status` as Monitor
**Then** I receive the same status information (read-only access permitted)
*(Covers FR5)*

**Given** the server is running
**When** I query status
**Then** uptime is calculated from process start time
**And** version is read from the installed server

**Given** the server is not installed
**When** I query status
**Then** state is "not_installed"
**And** version and uptime are null

---

### Story 3.4: Dashboard with Server Controls UI

As an **administrator**,
I want **a dashboard showing server status with control buttons**,
So that **I can monitor and control the server from the web interface**.

**Acceptance Criteria:**

**Given** no server is installed
**When** I view the Dashboard
**Then** I see the ServerInstallCard with version input and "Install Server" button
**And** server control buttons (Start/Stop/Restart) are not visible

**Given** a server installation is in progress
**When** I view the Dashboard
**Then** I see a progress indicator with current stage and percentage
**And** the install button is disabled

**Given** a server is installed and stopped
**When** I view the Dashboard
**Then** I see the ServerStatusBadge showing "Stopped" (red)
**And** server version is displayed
**And** "Start" button is enabled
**And** "Stop" and "Restart" buttons are disabled

**Given** a server is running
**When** I view the Dashboard
**Then** I see the ServerStatusBadge showing "Running" (green)
**And** server version and uptime are displayed
**And** "Stop" and "Restart" buttons are enabled
**And** "Start" button is disabled

**Given** I click a server control button
**When** the action is in progress
**Then** the button shows a loading state
**And** a toast notification appears on success or failure

**Given** the server state changes
**When** the Dashboard is open
**Then** the status updates automatically without page refresh (TanStack Query polling or refetch)

---

## Epic 4: Real-Time Console Access

Admins can monitor game server output in real-time and send commands, enabling troubleshooting without container access.

### Story 4.1: Console Buffer Service

As a **backend developer**,
I want **an in-memory ring buffer that captures game server output**,
So that **console history is available for streaming and retrieval**.

**Acceptance Criteria:**

**Given** the game server is running
**When** it produces stdout/stderr output
**Then** the output is captured and stored in the ring buffer
**And** timestamps are added to each line

**Given** the ring buffer has a configured size (default 10,000 lines)
**When** new output exceeds the buffer capacity
**Then** the oldest lines are discarded (FIFO)

**Given** the console buffer contains data
**When** the API server restarts
**Then** the buffer is empty (in-memory only, no disk persistence)
*(Covers NFR6)*

**Given** the game server crashes or stops
**When** the admin queries console history
**Then** the buffer contents up to the crash are preserved
**And** available for troubleshooting

---

### Story 4.2: WebSocket Console Streaming

As an **administrator**,
I want **to receive real-time console output via WebSocket**,
So that **I can monitor server activity as it happens**.

**Acceptance Criteria:**

**Given** I am authenticated as Admin
**When** I connect to `ws://host/api/v1alpha1/console` with `?api_key=<admin-key>`
**Then** the WebSocket connection is established
**And** I begin receiving console output in real-time
*(Covers FR6)*

**Given** I am connected to the console WebSocket
**When** the game server produces output
**Then** I receive the output within 1 second
*(Covers NFR1)*

**Given** I connect to the console WebSocket
**When** the connection is established
**Then** I receive the recent buffer history (configurable, e.g., last 100 lines)
*(Covers FR7)*

**Given** I am authenticated as Monitor
**When** I attempt to connect to the console WebSocket
**Then** the connection is rejected with 403 Forbidden
*(Covers FR9)*

**Given** I have no API key or an invalid key
**When** I attempt to connect to the console WebSocket
**Then** the connection is rejected with 401 Unauthorized

**Given** the WebSocket connection is lost
**When** the client reconnects
**Then** recent buffer history is sent to fill the gap

---

### Story 4.3: Console Command Input

As an **administrator**,
I want **to send commands to the game server through the console**,
So that **I can interact with the server without container access**.

**Acceptance Criteria:**

**Given** I am connected to the console WebSocket as Admin
**When** I send a message with type "command" and content "/help"
**Then** the command is written to the game server's stdin
**And** the command response appears in the console stream
*(Covers FR8)*

**Given** I send a command
**When** the server processes it
**Then** my sent command is echoed back (or marked) in the stream for confirmation

**Given** the game server is not running
**When** I attempt to send a command
**Then** I receive an error message indicating the server is stopped

**Given** I am authenticated as Monitor
**When** I attempt to send a command via any mechanism
**Then** the request is rejected with 403 Forbidden
*(Covers FR9)*

---

### Story 4.4: Terminal View Component

As an **administrator**,
I want **a terminal interface in the web UI showing console output**,
So that **I can view and interact with the server console visually**.

**Acceptance Criteria:**

**Given** I navigate to the Terminal page as Admin
**When** the page loads
**Then** I see an xterm.js terminal component
**And** it connects to the console WebSocket automatically
**And** displays incoming console output with Catppuccin theming

**Given** the terminal is connected
**When** new console output arrives
**Then** it appears in the terminal view immediately
**And** the terminal auto-scrolls to show new content

**Given** I am viewing the terminal
**When** I scroll up in the terminal
**Then** I can view console history from the buffer
*(Covers FR7)*

**Given** I type in the terminal and press Enter
**When** the command is submitted
**Then** it is sent via the WebSocket command mechanism
**And** I see the command and its response in the terminal
*(Covers FR8)*

**Given** the WebSocket connection is lost
**When** the terminal detects disconnection
**Then** a "Disconnected" indicator is shown
**And** the terminal attempts to reconnect with exponential backoff (max 30s, 10 retries)
*(Covers NFR10)*

**Given** reconnection succeeds
**When** the terminal reconnects
**Then** recent history is loaded to fill the gap
**And** the "Disconnected" indicator is removed

**Given** I am authenticated as Monitor
**When** I navigate to the Terminal page
**Then** I see a message indicating console access requires Admin role
**And** no terminal is displayed

---

## Epic 5: Mod Management

Admins can install, enable/disable, and remove mods via the web UI with automatic compatibility validation.

### Story 5.0: Epic 5 Technical Preparation

As a **development team**,
I want **to complete technical preparation for Epic 5 (Mod Management)**,
So that **we have updated architecture docs, caching patterns, and refactored tests before implementing mod features**.

**Background:** This preparatory story was defined during the Epic 4 retrospective. Epic 5 introduces external API dependencies and new UI patterns that benefit from upfront research and infrastructure improvements.

**Acceptance Criteria:**

**Given** the architecture documentation is reviewed
**When** I read the architecture.md file
**Then** it reflects current implementation state and any needed updates for Epic 5

**Given** a manual test checklist exists
**When** I review `docs/manual-test-checklist.md`
**Then** it contains smoke tests for Epics 1-4 functionality and placeholders for Epic 5

**Given** the mod API patterns are verified
**When** I review `agentdocs/modstoryapi.md`
**Then** it contains current API patterns with working examples verified against the live API

**Given** pending restart pattern research is complete
**When** I review the research findings
**Then** it documents the UI pattern for tracking changes requiring server restart

**Given** caching strategy research is complete
**When** I review the caching documentation
**Then** it covers artifact caching (server tarballs) and API response caching (mod data, TTL-based)

**Given** large test files are refactored
**When** I examine `api/tests/`
**Then** `test_console.py` and `test_server.py` are split into focused modules

**Tasks:**

- [ ] Task 1: Architecture doc review and update
- [ ] Task 2: Manual test checklist creation (`docs/manual-test-checklist.md`)
- [ ] Task 3: Mod API integration patterns verification
- [ ] Task 4: Pending restart pattern research
- [ ] Task 5: Caching strategy research (artifacts + API responses)
- [ ] Task 6: Refactor large test files into focused modules

---

### Story 5.1: Mod Service and State Management

As a **backend developer**,
I want **a service that tracks installed mods and their state**,
So that **mod information is persisted and available to the API**.

**Acceptance Criteria:**

**Given** mods are installed in `/data/mods/`
**When** the API starts or rescans
**Then** the mod service discovers all `.zip` files in the mods directory
**And** extracts mod metadata (modid, version, name) from `modinfo.json`

**Given** a mod's enabled/disabled state changes
**When** the state is updated
**Then** the change is persisted to `/data/state/state.json` (atomic write)
**And** a pending restart flag is set if the server is running

**Given** state persistence fails
**When** an atomic write is attempted
**Then** the temp file is written first, then renamed (prevents corruption)

---

### Story 5.2: Mod Installation API

As an **administrator**,
I want **to install a mod by entering its slug**,
So that **I don't need to manually download and copy mod files**.

**Acceptance Criteria:**

**Given** I call `POST /api/v1alpha1/mods` with `{"slug": "smithingplus"}`
**When** the mod exists on mods.vintagestory.at
**Then** the latest release is downloaded to `/data/mods/`
**And** the mod appears in the installed mods list
*(Covers FR11)*

**Given** I provide a full URL instead of a slug
**When** I call the install endpoint with `{"slug": "https://mods.vintagestory.at/smithingplus"}`
**Then** the slug is extracted from the URL and installation proceeds

**Given** the mod slug does not exist
**When** I attempt installation
**Then** I receive a 404 error with message "Mod not found"

**Given** the VintageStory mod API is unavailable
**When** I attempt installation
**Then** I receive a 502 error with clear message about external API failure
*(Covers NFR11)*

**Given** the download fails mid-transfer
**When** the error occurs
**Then** partial files are cleaned up
**And** a clear error message is returned
*(Covers NFR12)*

---

### Story 5.3: Mod Compatibility Validation

As an **administrator**,
I want **to see mod compatibility before installation**,
So that **I can make informed decisions about installing mods**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/mods/lookup/{slug}`
**When** the mod exists
**Then** I receive mod details including: name, description, latest version, and compatibility status

**Given** the installed game server version is 1.21.3
**When** I look up a mod with release tagged for "1.21.3"
**Then** compatibility status is "compatible"
*(Covers FR12)*

**Given** the installed game server version is 1.21.3
**When** I look up a mod with latest release tagged for "1.21.0"
**Then** compatibility status is "not_verified"
**And** a warning message indicates the mod wasn't explicitly tested for this version
*(Covers FR13)*

**Given** the installed game server version is 1.21.3
**When** I look up a mod with release tagged for "1.20.x" only
**Then** compatibility status is "incompatible"
**And** a warning message indicates version mismatch

**Given** I install a mod with "not_verified" or "incompatible" status
**When** the installation completes
**Then** the mod is installed (user made informed choice)
**And** the compatibility status is stored with the mod record

---

### Story 5.4: Mod Enable/Disable and Remove API

As an **administrator**,
I want **to enable, disable, and remove installed mods**,
So that **I can manage which mods are active without deleting files**.

**Acceptance Criteria:**

**Given** a mod is installed and enabled
**When** I call `POST /api/v1alpha1/mods/{slug}/disable`
**Then** the mod is marked as disabled in state
**And** the mod file is moved/renamed to indicate disabled status (e.g., `.disabled` suffix)
**And** a pending restart flag is set
*(Covers FR15)*

**Given** a mod is installed and disabled
**When** I call `POST /api/v1alpha1/mods/{slug}/enable`
**Then** the mod is marked as enabled in state
**And** the mod file is restored to active status
**And** a pending restart flag is set
*(Covers FR14)*

**Given** a mod is installed
**When** I call `DELETE /api/v1alpha1/mods/{slug}`
**Then** the mod file is deleted from `/data/mods/`
**And** the mod is removed from state
**And** a pending restart flag is set
*(Covers FR16)*

**Given** the mod slug doesn't exist in installed mods
**When** I attempt enable/disable/remove
**Then** I receive a 404 error

---

### Story 5.5: Mod List API

As an **administrator or monitor**,
I want **to view a list of installed mods with their status**,
So that **I can see what mods are installed and their compatibility**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/mods` as Admin
**When** mods are installed
**Then** I receive a list of installed mods with: slug, name, version, enabled status, compatibility status
*(Covers FR10)*

**Given** I call `GET /api/v1alpha1/mods` as Monitor
**When** mods are installed
**Then** I receive the same list (read-only access permitted)
*(Covers FR17)*

**Given** no mods are installed
**When** I query the mod list
**Then** I receive an empty array

**Given** the pending restart flag is set
**When** I query the mod list
**Then** the response includes `pending_restart: true` indicator

---

### Story 5.6: Mod Management UI

As an **administrator**,
I want **a web interface for managing mods**,
So that **I can install, view, and manage mods visually**.

**Acceptance Criteria:**

**Given** I navigate to the Mods page
**When** the page loads
**Then** I see a ModLookupInput field with placeholder "Enter mod slug or paste URL"
**And** I see a table of installed mods (or empty state if none)

**Given** I type a mod slug in the input
**When** I stop typing (300ms debounce)
**Then** a lookup request is made
**And** mod details appear in a preview card below the input

**Given** the mod lookup returns results
**When** I view the preview card
**Then** I see mod name, description, and CompatibilityBadge (green/yellow/red)
**And** an "Install" button is available

**Given** I click "Install" on a compatible mod
**When** installation completes
**Then** a success toast appears
**And** the mod appears in the installed mods table
**And** the pending restart banner appears in the header

**Given** I click "Install" on an incompatible mod
**When** I click the button
**Then** a warning dialog appears asking for confirmation
**And** I can choose to proceed or cancel

**Given** the mods table is displayed
**When** I view an installed mod row
**Then** I see: mod name, installed version, compatibility badge, enabled/disabled toggle, remove button

**Given** I toggle a mod's enabled state
**When** the toggle is clicked
**Then** the state updates optimistically
**And** a toast confirms success or shows error
**And** pending restart indicator updates

**Given** I click the remove button on a mod
**When** the confirmation dialog appears and I confirm
**Then** the mod is removed from the list
**And** a success toast appears

---

## Epic 6: Game Configuration Management

Admins can configure game server settings through the web UI using console commands for live updates. The Console tab is renamed to GameServer and includes both console output and a configuration panel side-by-side. API operational settings are managed separately in a new Settings tab.

**Architectural Pivot (2025-12-30):** Original file-editing approach replaced with console command pattern. VintageStory server handles JSON persistence automatically when settings are changed via `/serverconfig` commands.

**Key Decisions:**
- `/config/game` - Game server settings (console commands for live update)
- `/config/api` - API operational settings (auto_start, refresh intervals)
- ConfigInitService - First-run config generation from template + VS_CFG_* env vars
- Console tab → GameServer tab with responsive split layout
- TanStack Table for data lists, Zod + custom hooks for field validation

---

### Story 6.0: Epic 6 Technical Preparation

As a **developer**,
I want **to research VintageStory console commands and create configuration infrastructure**,
So that **subsequent stories have a solid foundation for config management**.

**Acceptance Criteria:**

**Given** we need to understand console command behavior
**When** I research the `/serverconfig` command
**Then** I document which settings support live update vs require restart
**And** I verify that console changes persist to serverconfig.json automatically

**Given** we need a reference configuration template
**When** I analyze DarkMatterProductions and VintageStory defaults
**Then** I create `serverconfig-template.json` with sensible defaults
**And** the template includes all common settings with documentation comments removed

**Given** we need to support VS_CFG_* environment variables
**When** I define the environment variable mapping
**Then** I document the complete ENV_VAR_MAP (VS_CFG_SERVER_NAME → ServerName, etc.)
**And** I verify the mapping covers all settings from the reference implementation

**Given** we need TanStack Table for data lists
**When** I add the dependency
**Then** `@tanstack/react-table` is added to web/package.json
**And** a basic table component pattern is documented

**Tasks:**
- [ ] Research `/serverconfig` command - document supported settings
- [ ] Test console command persistence - verify JSON auto-save
- [ ] Create `serverconfig-template.json` from DarkMatterProductions reference
- [ ] Define complete VS_CFG_* → serverconfig.json key mapping
- [ ] Add TanStack Table dependency to web project
- [ ] Update architecture.md with research findings

---

### Story 6.1: ConfigInitService and Template

As an **administrator**,
I want **the server to automatically generate an initial configuration from environment variables**,
So that **I can deploy with custom settings without manual file creation**.

**Acceptance Criteria:**

**Given** the game server is installed but no serverconfig.json exists
**When** the server start is requested
**Then** ConfigInitService generates serverconfig.json from the template
**And** any VS_CFG_* environment variables override template defaults

**Given** VS_CFG_SERVER_NAME is set to "My Custom Server"
**When** ConfigInitService generates the config
**Then** serverconfig.json contains `"ServerName": "My Custom Server"`

**Given** VS_CFG_MAX_CLIENTS is set to "32"
**When** ConfigInitService generates the config
**Then** serverconfig.json contains `"MaxClients": 32` (integer, not string)

**Given** serverconfig.json already exists
**When** the server start is requested
**Then** ConfigInitService does NOT overwrite the existing config
**And** the existing config is used as-is

**Given** an invalid VS_CFG_* value is provided (e.g., VS_CFG_MAX_CLIENTS="abc")
**When** ConfigInitService processes environment variables
**Then** the invalid value is logged as a warning
**And** the template default is used instead

**Tasks:**
- [ ] Create ConfigInitService class with needs_initialization() and initialize_config()
- [ ] Implement ENV_VAR_MAP with type coercion (string, int, bool)
- [ ] Ship serverconfig-template.json in api package
- [ ] Integrate with ServerService.start() - call before server launch
- [ ] Add comprehensive tests for env var processing
- [ ] Test atomic write pattern (temp file + rename)

---

### Story 6.2: Game Settings API

As an **administrator**,
I want **to view and update game server settings through the API**,
So that **I can configure the server using console commands for live updates**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/config/game` as Admin or Monitor
**When** serverconfig.json exists
**Then** I receive settings with metadata (key, value, type, live_update, env_managed)
**And** the response includes source_file and last_modified

**Given** I call `POST /api/v1alpha1/config/game/settings/ServerName` with `{"value": "New Name"}`
**When** the game server is running
**Then** the API executes `/serverconfig Name "New Name"` via console
**And** the response includes `method: "console_command"` and `pending_restart: false`

**Given** I call `POST /api/v1alpha1/config/game/settings/Port` with `{"value": 42421}`
**When** the game server is running
**Then** the setting is written to serverconfig.json (Port requires restart)
**And** the response includes `method: "file_update"` and `pending_restart: true`

**Given** I attempt to update a setting managed by VS_CFG_* environment variable
**When** block_env_managed_settings is true (default)
**Then** I receive a 400 error with code SETTING_ENV_MANAGED
**And** the error message identifies the controlling environment variable

**Given** I am authenticated as Monitor
**When** I attempt to POST a setting update
**Then** I receive a 403 Forbidden

**Tasks:**
- [ ] Create GameConfigService with get_settings() and update_setting()
- [ ] Implement LIVE_SETTINGS map with console command templates
- [ ] Add /config/game router with GET and POST endpoints
- [ ] Integrate with ConsoleService for command execution
- [ ] Add pending restart state integration
- [ ] Comprehensive tests for live vs restart-required settings

---

### Story 6.3: API Settings Service

As an **administrator**,
I want **to view and update API operational settings**,
So that **I can configure auto-start, refresh intervals, and environment handling**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/config/api` as Admin
**When** api-settings.json exists (or defaults are used)
**Then** I receive current API settings: auto_start_server, block_env_managed_settings, refresh intervals

**Given** I call `POST /api/v1alpha1/config/api/settings/auto_start_server` with `{"value": true}`
**When** the request is valid
**Then** the setting is saved to api-settings.json
**And** the response confirms the update

**Given** I update mod_list_refresh_interval
**When** the scheduler is running (Epic 7+)
**Then** the job is rescheduled with the new interval

**Given** I am authenticated as Monitor
**When** I call GET /api/v1alpha1/config/api
**Then** I receive a 403 Forbidden (API settings are Admin-only)

**Tasks:**
- [ ] Create ApiSettingsService with get_settings() and update_setting()
- [ ] Define ApiSettings Pydantic model with defaults
- [ ] Implement api-settings.json persistence with atomic writes
- [ ] Add /config/api router with GET and POST endpoints
- [ ] Add setting validation (e.g., intervals must be positive)

---

### Story 6.4: Settings UI

As an **administrator**,
I want **a web interface for managing game and API settings**,
So that **I can configure the server visually and see console command feedback**.

**Acceptance Criteria:**

**Given** I navigate to the GameServer tab as Admin
**When** the page loads on desktop (≥1024px)
**Then** I see Game Config panel on left and Console on right (split view)

**Given** I navigate to the GameServer tab on mobile (<1024px)
**When** the page loads
**Then** I see Console on top and Game Config below (stacked, scrollable)

**Given** I change the ServerName field in Game Config
**When** I blur the field (auto-save)
**Then** the API is called and I see the `/serverconfig` command execute in Console
**And** a success toast appears

**Given** I change a restart-required setting (e.g., Port)
**When** the save completes
**Then** the PendingRestartBanner appears (consistent with mod changes)

**Given** a setting is managed by VS_CFG_* environment variable
**When** I view the setting
**Then** it shows an "Env: VS_CFG_*" badge and the input is disabled

**Given** I navigate to the Settings tab
**When** the page loads
**Then** I see tabs for "API Settings" and "File Manager"
**And** API Settings shows auto_start, env handling, and refresh intervals
**And** File Manager shows a "coming soon" stub

**Tasks:**
- [ ] Rename Console → GameServer in navigation
- [ ] Create GameServerPage with responsive split layout
- [ ] Create GameConfigPanel with SettingGroup and SettingField components
- [ ] Implement useSettingField hook with Zod validation
- [ ] Create SettingsPage with API Settings and File Manager tabs
- [ ] Create ApiSettingsPanel component
- [ ] Add File Manager stub component

---

### Story 6.5: Raw Config Viewer

As an **administrator or monitor**,
I want **read-only access to raw configuration files**,
So that **I can troubleshoot configuration issues**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/config/files` as Admin or Monitor
**When** config files exist in the data directory
**Then** I receive a list of configuration file names

**Given** I call `GET /api/v1alpha1/config/files/serverconfig.json`
**When** the file exists
**Then** I receive the raw JSON content

**Given** I request a file with path traversal (e.g., `../secrets.json`)
**When** the API validates the path
**Then** I receive a 400 error and the request is rejected

**Note:** This story provides the backend for the File Manager UI (stub in 6.4). Full File Manager UI is deferred to a future epic.

**Tasks:**
- [ ] Create /config/files router with list and read endpoints
- [ ] Implement path validation to prevent traversal attacks
- [ ] Add Monitor + Admin role access
- [ ] Add tests for path traversal prevention

---

## Epic 7: APScheduler Integration

The API server can execute periodic background tasks using APScheduler, enabling features like cache refresh and version checking.

**Added (2025-12-30):** New epic for background task scheduling infrastructure.

**Key Decisions:**
- APScheduler with AsyncIOScheduler and MemoryJobStore
- No external dependencies (in-memory job store)
- SchedulerService pattern with lifespan integration
- Job management API for visibility

---

### Story 7.0: Epic 7 Preparation

As a **developer**,
I want **to research APScheduler patterns and async integration**,
So that **subsequent stories have a solid foundation for scheduling**.

**Acceptance Criteria:**

**Given** we need to understand APScheduler async patterns
**When** I research the library
**Then** I document AsyncIOScheduler configuration best practices
**And** I verify compatibility with our FastAPI lifespan pattern

**Given** we need to add APScheduler
**When** I add the dependency
**Then** `apscheduler` is added to api/pyproject.toml
**And** version is pinned appropriately

**Tasks:**
- [ ] Research APScheduler AsyncIOScheduler patterns
- [ ] Add apscheduler dependency to pyproject.toml
- [ ] Document job defaults (coalesce, max_instances, misfire_grace_time)

---

### Story 7.1: SchedulerService

As a **developer**,
I want **a scheduler service that manages periodic background tasks**,
So that **jobs can be added, removed, and monitored**.

**Acceptance Criteria:**

**Given** the API server starts
**When** the lifespan context initializes
**Then** the SchedulerService starts the AsyncIOScheduler
**And** a log entry confirms "scheduler_started"

**Given** the API server shuts down
**When** the lifespan context exits
**Then** the SchedulerService stops the scheduler gracefully
**And** running jobs complete before shutdown

**Given** I need to add an interval job
**When** I call scheduler.add_interval_job(func, seconds, job_id)
**Then** the job is registered and will execute at the specified interval

**Given** I need to add a cron job
**When** I call scheduler.add_cron_job(func, cron_expression, job_id)
**Then** the job is registered with the cron schedule

**Tasks:**
- [ ] Create SchedulerService class with start/shutdown methods
- [ ] Implement add_interval_job and add_cron_job methods
- [ ] Integrate with FastAPI lifespan in main.py
- [ ] Add structured logging for scheduler events
- [ ] Add tests for scheduler lifecycle

---

### Story 7.2: Job Management API

As an **administrator**,
I want **to view and manage scheduled jobs through the API**,
So that **I can monitor background task status**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/jobs` as Admin
**When** jobs are registered
**Then** I receive a list of jobs with: id, next_run_time, interval/cron, last_run_status

**Given** I call `DELETE /api/v1alpha1/jobs/{job_id}` as Admin
**When** the job exists
**Then** the job is removed from the scheduler
**And** the response confirms deletion

**Given** I am authenticated as Monitor
**When** I call GET /api/v1alpha1/jobs
**Then** I receive a 403 Forbidden (job management is Admin-only)

**Tasks:**
- [ ] Create /jobs router with list and delete endpoints
- [ ] Implement job serialization (id, schedule, status)
- [ ] Add Admin-only authorization
- [ ] Add tests for job API

---

### Story 7.3: Scheduler Health

As an **operator**,
I want **scheduler status included in health checks**,
So that **I can monitor the background task system**.

**Acceptance Criteria:**

**Given** I call `GET /healthz`
**When** the scheduler is running
**Then** the response includes `scheduler: { status: "running", job_count: N }`

**Given** the scheduler has failed to start
**When** I call /healthz
**Then** the response includes `scheduler: { status: "stopped" }`

**Tasks:**
- [ ] Add scheduler status to health endpoint
- [ ] Include job count in health response
- [ ] Add tests for scheduler health reporting

---

## Epic 8: Periodic Task Patterns

Initial periodic jobs are implemented using the APScheduler infrastructure, enabling automated cache refresh and version checking.

**Added (2025-12-30):** New epic for implementing periodic jobs.

---

### Story 8.0: Epic 8 Preparation

As a **developer**,
I want **to define job patterns and error handling strategy**,
So that **periodic tasks are implemented consistently**.

**Acceptance Criteria:**

**Given** we need a standard job pattern
**When** I define the template
**Then** jobs follow a consistent structure: try/except, structured logging, no re-raise

**Given** we need job registration patterns
**When** I define the approach
**Then** jobs are registered in a central register_default_jobs() function
**And** registration respects API settings (interval values)

**Tasks:**
- [ ] Define standard job template in architecture
- [ ] Create jobs/ directory structure
- [ ] Implement register_default_jobs() function

---

### Story 8.1: Mod Cache Refresh Job

As an **administrator**,
I want **the mod API cache to refresh automatically**,
So that **mod information stays current without manual intervention**.

**Acceptance Criteria:**

**Given** mod_list_refresh_interval is set to 3600 (1 hour)
**When** the scheduler runs
**Then** the mod cache refresh job executes every hour

**Given** the mod API is unreachable during refresh
**When** the job executes
**Then** the error is logged but the job continues on schedule
**And** stale cache data is preserved

**Given** mod_list_refresh_interval is set to 0
**When** the scheduler starts
**Then** the mod cache refresh job is NOT registered

**Tasks:**
- [ ] Create refresh_mod_cache job function
- [ ] Register job in register_default_jobs()
- [ ] Add error handling and logging
- [ ] Add tests for job execution

---

### Story 8.2: Server Versions Check Job

As an **administrator**,
I want **automatic checks for new VintageStory versions**,
So that **I'm notified when updates are available**.

**Acceptance Criteria:**

**Given** server_versions_refresh_interval is set to 86400 (24 hours)
**When** the scheduler runs
**Then** the version check job executes daily

**Given** a new version is available
**When** the job detects it
**Then** the new version is logged
**And** the version info is available via status API

**Tasks:**
- [ ] Create check_server_versions job function
- [ ] Register job in register_default_jobs()
- [ ] Store latest version info for status API
- [ ] Add tests for version checking

---

### Story 8.3: Job Configuration UI

As an **administrator**,
I want **to view scheduled jobs in the Settings UI**,
So that **I can monitor background task status**.

**Acceptance Criteria:**

**Given** I navigate to the Settings page
**When** the page loads
**Then** I see a "Scheduled Jobs" section showing registered jobs

**Given** jobs are displayed
**When** I view a job
**Then** I see: job name, interval/schedule, next run time, last status

**Tasks:**
- [ ] Add jobs section to SettingsPage
- [ ] Create JobsTable component using TanStack Table
- [ ] Add useJobs query hook
- [ ] Style with badges for status (running, scheduled, failed)

---

## Story Summary

| Epic | Stories | Total |
|------|---------|-------|
| Epic 1: Project Foundation & Health Monitoring | 1.1, 1.2, 1.3, 1.4 | 4 |
| Epic 2: Authentication & API Security | 2.1, 2.2, 2.3 | 3 |
| Epic 3: Server Lifecycle Management | 3.1, 3.2, 3.3, 3.4, 3.5 | 5 |
| Epic 4: Real-Time Console Access | 4.0, 4.1, 4.2, 4.3, 4.4 | 5 |
| Epic 5: Mod Management | 5.0, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6 | 7 |
| Epic 6: Game Configuration Management | 6.0, 6.1, 6.2, 6.3, 6.4, 6.5 | 6 |
| Epic 7: APScheduler Integration | 7.0, 7.1, 7.2, 7.3 | 4 |
| Epic 8: Periodic Task Patterns | 8.0, 8.1, 8.2, 8.3 | 4 |
| Epic 9: Quality of Life Polish Pass | 9.1, 9.2, 9.3, 9.4, 9.5, 9.6, 9.7 | 7 |
| Epic 10: Advanced Mod Browser | 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8 | 8 |
| Epic 11: GameServer Navigation Refactor | 11.1, 11.2, 11.3, 11.4, 11.5, 11.6 | 6 |
| Epic 12: Enhanced Dashboard with Server Metrics | 12.1, 12.2, 12.3, 12.4, 12.5, 12.6 | 6 |
| Epic 13: Server Version Browser | 13.0, 13.1, 13.2, 13.3, 13.4, 13.5 | 6 |
| Epic 14: Mod Updates | 14.0, 14.1, 14.2, 14.3, 14.4, 14.5, 14.6 | 7 |
| Epic 15: Release Engineering | 15.0, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6 | 7 |
| Epic 16: UI Polish | 16.0, 16.1, 16.2, 16.3, 16.4, 16.5, 16.6, 16.7, 16.8 | 9 |
| Epic 17: Mod Data Correctness and Fixes | 17.1, 17.2, 17.3, 17.4, 17.5, 17.6, 17.7, 17.8 | 8 |
| Epic 18: Mod Media and Fixes | 18.1, 18.2, 18.3, 18.4 | 4 |
| Epic 19: API Security and Mod File Safety | 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7 | 7 |
| Epic 20: Tooling and Test Health | 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7 | 7 |
| Epic 21: Maintainer Decisions and Web Polish | 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8 | 8 |
| Epic 22: Server Operations and Metrics | 22.1, 22.2, 22.3, 22.4, 22.5, 22.6, 22.7, 22.8 | 8 |
| Epic 23: Config File Editing | 23.1, 23.2, 23.3, 23.4, 23.5, 23.6, 23.7 | 7 |
| Epic 24: Mod Management Follow-ups | 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7, 24.8 | 8 |
| Epic 25: Server Config Read Correctly | 25.1, 25.2, 25.3, 25.4 | 4 |
| Epic 28: Mods From Outside the Mod Database | 28.1, 28.2, 28.3, 28.4, 28.5 | 5 |
| **Total** | | **160** |

---

## Epic 9: Quality of Life Polish Pass

Admins benefit from security improvements, better debugging capabilities, and enhanced UI features that improve daily operations and troubleshooting.

**FRs covered:** FR40, FR41, FR42, FR43, FR44, FR45, FR46, FR47, FR48, FR49, FR50, FR51, FR52, FR53, FR54, FR55

**MVP Scope:**

- Secure WebSocket token authentication (replaces API key in URL)
- Directory auto-creation on startup
- Mod cache eviction strategy
- Debug logging with correlation IDs
- Console command highlighting with [CMD] prefix
- JSON syntax colorization in file viewer
- Dynamic directory listing in file browser

---

### Story 9.1: Secure WebSocket Authentication

As an **administrator**,
I want **WebSocket connections to use secure token authentication**,
So that **my API key is not exposed in URL query parameters**.

**Acceptance Criteria:**

**Given** I need to connect to the console WebSocket
**When** I request a connection token via `POST /api/v1alpha1/auth/ws-token`
**Then** I receive a short-lived token (e.g., 30 second TTL)
**And** the response includes `{"token": "<jwt-or-opaque-token>", "expires_in": 30}`
*(Covers FR40)*

**Given** I have a valid WebSocket token
**When** I connect to `ws://host/api/v1alpha1/console?token=<token>`
**Then** the connection is established successfully
**And** the token is validated server-side
*(Covers FR41)*

**Given** I attempt to connect with an expired token
**When** the token TTL has passed
**Then** the WebSocket connection is rejected with 401

**Given** the frontend needs to connect to the console
**When** the Terminal component mounts
**Then** it first requests a token, then connects with that token
**And** token refresh is handled automatically before expiry

---

### Story 9.2: Directory Auto-Creation on Startup

As an **operator**,
I want **the API server to create required directories on startup**,
So that **I don't encounter errors from missing directories**.

**Acceptance Criteria:**

**Given** the API server starts
**When** expected directories don't exist under `/data/vsmanager/`
**Then** the directories are created: `cache/`, `state/`, `logs/`
*(Covers FR42)*

**Given** directories are created on startup
**When** any directory is created
**Then** a log entry is emitted: `{"event": "directory_created", "path": "..."}`
*(Covers FR43)*

**Given** directories already exist
**When** the API server starts
**Then** no errors occur and no creation logs are emitted

**Given** directory creation fails (permissions issue)
**When** startup encounters the error
**Then** a clear error is logged and startup fails gracefully

---

### Story 9.3: Mod Cache Eviction Strategy

As an **administrator**,
I want **the mod cache to automatically clean up old files**,
So that **disk space is managed without manual intervention**.

**Acceptance Criteria:**

**Given** the mod cache directory exists
**When** total cache size exceeds the configured limit (default 500MB)
**Then** the oldest accessed files are evicted until under limit (LRU strategy)
*(Covers FR44)*

**Given** I set `VS_MOD_CACHE_MAX_SIZE` environment variable
**When** the API server starts
**Then** the cache limit is set to the configured value
*(Covers FR45)*

**Given** cache eviction occurs
**When** files are removed
**Then** log entries are emitted: `{"event": "cache_evicted", "file": "...", "reason": "size_limit"}`
*(Covers FR46)*

**Given** the cache is under the size limit
**When** eviction check runs
**Then** no files are removed

---

### Story 9.4: Debug Logging Infrastructure

As a **developer or operator**,
I want **comprehensive debug logging throughout the API**,
So that **I can troubleshoot issues with detailed request tracing**.

**Acceptance Criteria:**

**Given** `VS_DEBUG=true` is set
**When** API requests are processed
**Then** debug-level logs are emitted for each service layer (router → service → repository)
*(Covers FR47)*

**Given** `VS_DEBUG` is changed at runtime
**When** the environment variable is updated
**Then** debug logging is enabled/disabled without server restart
*(Covers FR48)*

**Given** debug logging is enabled
**When** a request is processed
**Then** all log entries include a correlation ID (`request_id`) for tracing
**And** the correlation ID is consistent across all logs for that request
*(Covers FR49)*

**Given** debug logging is disabled (default)
**When** requests are processed
**Then** only info, warning, and error logs are emitted

---

### Story 9.5: Console Command Highlighting

As an **administrator**,
I want **my commands to be visually distinct in the console**,
So that **I can easily identify what I typed vs server output**.

**Acceptance Criteria:**

**Given** I send a command via the console
**When** the command is echoed in the terminal
**Then** it is displayed in a distinct color (e.g., cyan or yellow)
*(Covers FR50)*

**Given** I send a command via the console
**When** the command appears in the output
**Then** it is prefixed with `[CMD]` marker
*(Covers FR51)*

**Given** server output arrives
**When** it is displayed in the terminal
**Then** it uses the default console color (not the command color)

---

### Story 9.6: JSON Syntax Colorization

As an **administrator**,
I want **JSON files to be syntax-highlighted in the file viewer**,
So that **configuration files are easier to read and understand**.

**Acceptance Criteria:**

**Given** I open a `.json` file in the file viewer
**When** the content is rendered
**Then** syntax colorization is applied
*(Covers FR52)*

**Given** JSON content is displayed
**When** I view the highlighted content
**Then** keys, strings, numbers, booleans, and null values each have distinct colors
*(Covers FR53)*

**Given** I open a non-JSON file
**When** the content is rendered
**Then** no JSON colorization is applied (plain text)

**Given** the JSON file contains invalid JSON
**When** the file is displayed
**Then** it renders as plain text with no colorization errors

---

### Story 9.7: Dynamic File Browser

As an **administrator**,
I want **the file browser to show all directories dynamically**,
So that **I can access ModConfigs, Macros, Playerdata, and other directories**.

**Acceptance Criteria:**

**Given** I open the file browser
**When** the directory listing loads
**Then** all directories under `/data/serverdata/` are displayed
**And** this includes ModConfigs, Macros, Playerdata, and any others present
*(Covers FR54)*

**Given** the file browser lists directories
**When** the list is generated
**Then** it is dynamically discovered from the filesystem (not hardcoded)
*(Covers FR55)*

**Given** a new directory is created in `/data/serverdata/`
**When** I refresh the file browser
**Then** the new directory appears in the listing

---

## Epic 10: Advanced Mod Browser

Admins can discover and install mods through a full-featured browser with search, filters, and sorting - matching the experience of mods.vintagestory.at directly within the management UI.

**FRs covered:** FR56, FR57, FR58, FR59, FR60, FR61, FR62, FR63, FR64, FR65, FR66, FR67, FR68, FR69, FR70, FR71, FR72, FR73, FR74, FR75, FR76, FR77, FR78, FR79, FR80, FR81, FR82, FR83, FR84, FR85

**MVP Scope:**

- Split Mods view into Installed/Browse tabs
- Smart landing page with newest mods, pre-filtered to game version
- Keyword search with debounce
- Filters: side, tags, game version, mod type
- Sorting: recent, downloads, trending, name
- Card display with thumbnails and compatibility badges
- Mod detail view with install/update actions
- Pagination for large result sets
- Direct install from browse results

---

### Story 10.1: Mod Browse API

As a **frontend developer**,
I want **an API endpoint that searches and filters the mod database**,
So that **the browse UI can display mods with all filtering and sorting options**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/mods/browse`
**When** no parameters are provided
**Then** I receive the newest mods, pre-filtered to the current game server version
**And** the response includes pagination metadata (total, page, page_size)
*(Covers FR59, FR60, FR61)*

**Given** I call `GET /api/v1alpha1/mods/browse?q=magic`
**When** the search parameter is provided
**Then** results are filtered to mods matching "magic" in name or description
*(Covers FR62)*

**Given** I call with filter parameters
**When** I include `side=server`, `tags=qol,utility`, `version=1.21`, `type=code`
**Then** results are filtered by all specified criteria (AND logic)
*(Covers FR65, FR66, FR67, FR68, FR69)*

**Given** I call with sort parameter
**When** I include `sort=downloads` (or `trending`, `recent`, `name`)
**Then** results are sorted accordingly
*(Covers FR71, FR72, FR73)*

**Given** I call with pagination parameters
**When** I include `page=2&page_size=20`
**Then** I receive the second page of 20 results
**And** response includes `total_count` for pagination UI
*(Covers FR80)*

**Given** the VintageStory mod API is unavailable
**When** I attempt to browse mods
**Then** I receive cached data if available, or a clear error message
*(Covers NFR11)*

---

### Story 10.2: Mods Tab Restructure

As an **administrator**,
I want **the Mods page split into Installed and Browse tabs**,
So that **I can manage installed mods separately from discovering new ones**.

**Acceptance Criteria:**

**Given** I navigate to the Mods page
**When** the page loads
**Then** I see two tabs: "Installed" and "Browse"
**And** "Installed" is the default active tab
*(Covers FR56)*

**Given** I click the "Installed" tab
**When** the tab activates
**Then** I see the existing mod management UI (list, enable, disable, remove, update)
*(Covers FR57)*

**Given** I click the "Browse" tab
**When** the tab activates
**Then** I see the new mod discovery interface
*(Covers FR58)*

**Given** I am on either tab
**When** I switch tabs
**Then** the URL updates to reflect the active tab (e.g., `/mods/installed`, `/mods/browse`)
**And** browser back/forward navigation works correctly

---

### Story 10.3: Browse Landing Page & Search

As an **administrator**,
I want **the Browse tab to show newest mods immediately with search capability**,
So that **I can discover mods without having to search first**.

**Acceptance Criteria:**

**Given** I navigate to the Browse tab
**When** the page loads
**Then** newest mods are displayed immediately (no user action required)
**And** results are pre-filtered to my game server version
*(Covers FR59, FR60, FR61)*

**Given** I see the Browse interface
**When** I look at the top of the page
**Then** I see a search input field

**Given** I type in the search field
**When** I stop typing (300ms debounce)
**Then** search results update automatically
*(Covers FR62, FR63)*

**Given** I have filters or sort applied
**When** I perform a search
**Then** the search respects existing filter and sort selections
*(Covers FR64)*

**Given** the search field has text
**When** I click a clear button or press Escape
**Then** the search is cleared and results return to default (newest)

---

### Story 10.4: Filter & Sort Controls

As an **administrator**,
I want **to filter and sort mod results**,
So that **I can find specific types of mods quickly**.

**Acceptance Criteria:**

**Given** I am on the Browse tab
**When** I view the filter controls
**Then** I see filter options for: Side, Tags, Game Version, Mod Type

**Given** I select a Side filter
**When** I choose "Server-only"
**Then** results update to show only server-side mods
*(Covers FR65)*

**Given** I select Tags
**When** I choose multiple tags (e.g., "QoL", "Utility")
**Then** results show mods matching ANY selected tag
*(Covers FR66)*

**Given** I select a Game Version filter
**When** I choose a specific version
**Then** results show mods compatible with that version
*(Covers FR67)*

**Given** I select a Mod Type filter
**When** I choose "Code Mod"
**Then** results show only code mods
*(Covers FR68)*

**Given** I have multiple filters active
**When** results are displayed
**Then** all filters are applied together (AND logic)
*(Covers FR69)*

**Given** filters are active
**When** I view the filter area
**Then** active filters are displayed as chips/badges that can be individually removed
*(Covers FR70)*

**Given** I view the sort dropdown
**When** I select a sort option (Newest, Downloads, Updated, Trending, Name)
**Then** results are re-sorted accordingly
*(Covers FR71)*

**Given** I haven't changed the sort
**When** browsing mods
**Then** the default sort is "Newest"
*(Covers FR72)*

**Given** I change the sort option
**When** I navigate within the browse experience
**Then** my sort selection persists
*(Covers FR73)*

---

### Story 10.5: Mod Card Display

As an **administrator**,
I want **mods displayed as informative cards**,
So that **I can quickly scan and evaluate mods**.

**Acceptance Criteria:**

**Given** browse results are displayed
**When** I view the mod grid/list
**Then** each mod shows: thumbnail image (or placeholder), name, author, download count, short description
*(Covers FR74)*

**Given** a mod card is displayed
**When** I view the compatibility indicator
**Then** I see a badge showing compatibility with my game server version (Compatible/Not verified/Incompatible)
*(Covers FR75)*

**Given** I see a mod card
**When** I click anywhere on the card
**Then** I navigate to the mod detail view
*(Covers FR76)*

**Given** mods have no thumbnail
**When** the card is rendered
**Then** a placeholder image is displayed

---

### Story 10.6: Mod Detail View

As an **administrator**,
I want **a detailed view of any mod**,
So that **I can read full information before installing**.

**Acceptance Criteria:**

**Given** I click a mod card
**When** the detail view opens
**Then** I see: full description (rendered markdown), all releases, dependencies, compatibility information
*(Covers FR77)*

**Given** I am viewing mod details
**When** I look at the install section
**Then** I see an "Install" button with a version dropdown to select which release
*(Covers FR78)*

**Given** the mod is already installed
**When** I view the detail page
**Then** I see "Installed: v1.2.3" indicator
**And** if an update is available, I see an "Update to v1.3.0" button
*(Covers FR79)*

**Given** I am on the detail view
**When** I click the back button or breadcrumb
**Then** I return to the browse results at the same position

---

### Story 10.7: Pagination

As an **administrator**,
I want **pagination for large result sets**,
So that **I can browse through thousands of mods efficiently**.

**Acceptance Criteria:**

**Given** browse results exceed one page
**When** results are displayed
**Then** pagination controls are visible (page numbers or "Load more" button)
*(Covers FR80)*

**Given** the UI implements infinite scroll
**When** I scroll to the bottom of the results
**Then** the next page of results loads automatically
*(Covers FR81 - Option A)*

**Given** the UI implements page controls
**When** I click page 2
**Then** page 2 results are displayed
*(Covers FR81 - Option B)*

**Given** I am on page 3 of results
**When** I click a mod card, view details, then go back
**Then** I return to page 3 at approximately the same scroll position
*(Covers FR82)*

---

### Story 10.8: Browse Install Integration

As an **administrator**,
I want **to install mods directly from the browser**,
So that **discovery and installation is a seamless experience**.

**Acceptance Criteria:**

**Given** I am viewing a mod card or detail view
**When** I click "Install"
**Then** an install confirmation dialog appears
*(Covers FR83)*

**Given** the install dialog is open
**When** I view the dialog
**Then** I see the compatibility check result (Compatible/Not verified/Incompatible)
**And** a warning is shown if not verified or incompatible
*(Covers FR84)*

**Given** I confirm installation
**When** the install completes successfully
**Then** a success toast appears
**And** the mod card/detail updates to show "Installed"
**And** the mod appears in the Installed tab
*(Covers FR85)*

**Given** I install a mod from the browse view
**When** I switch to the Installed tab
**Then** the newly installed mod is visible in the list

**Given** installation fails
**When** the error occurs
**Then** a clear error message is displayed
**And** the install button returns to its original state

---

## Epic 11: GameServer Navigation Refactor

Admins can navigate game server functionality through an organized sub-navigation structure, with dedicated pages for version management, settings, mods, and console access.

**Goal:** Split the current combined GameServer page into distinct sections with proper sub-navigation, improving organization and discoverability. Move Mods under Game Server as a logical grouping.

### Current State

- Single `/game-server` route with split-view layout (Console + Settings)
- Server installation lives on Dashboard (ServerInstallCard)
- Mods is a top-level navigation item
- No sub-navigation under Game Server

### Target State

```
Sidebar Navigation:
├── Dashboard (server stats at-a-glance)
├── Game Server (expandable)
│   ├── Installation / Version (dynamic label based on install state)
│   ├── Settings (game configuration)
│   ├── Mods (mod management + browser)
│   └── Console (full-page console view)
└── VSManager (app settings - formerly "Settings")
```

**Dynamic Label:** "Installation" when no server installed → "Version" once installed

**Rationale:**
- Mods are part of the game server, not a separate top-level concept
- Clear distinction: "Game Server → Settings" = game config vs "VSManager" = application settings
- Logical flow: Version → Settings → Mods → Console

---

### Story 11.1: Sub-Navigation Infrastructure

As a **frontend developer**,
I want **an expandable sub-navigation component in the sidebar**,
So that **Game Server can have nested navigation items**.

**Acceptance Criteria:**

**Given** I view the sidebar
**When** I click on "Game Server"
**Then** the section expands to show sub-items: Version/Installation, Settings, Mods, Console
**And** the expanded/collapsed state is persisted in localStorage

**Given** the Game Server section is expanded
**When** I click on "Game Server" again
**Then** the section collapses to hide sub-items

**Given** I am on a Game Server sub-page (e.g., `/game-server/console`)
**When** I view the sidebar
**Then** the Game Server section is automatically expanded
**And** the active sub-item is highlighted

**Given** no server is installed
**When** I view the sidebar
**Then** the first sub-item shows "Installation"

**Given** a server is installed
**When** I view the sidebar
**Then** the first sub-item shows "Version"

**Given** the sidebar is in collapsed mode (icons only)
**When** I hover over the Game Server icon
**Then** a tooltip/flyout shows the sub-navigation items

**Tasks:**
- [ ] Create ExpandableNavItem component with expand/collapse behavior
- [ ] Add sub-navigation items to Sidebar.tsx
- [ ] Update routes in App.tsx for nested routing
- [ ] Implement localStorage persistence for expanded state
- [ ] Add dynamic label logic based on server install state
- [ ] Handle collapsed sidebar hover behavior
- [ ] Update tests for new navigation structure

---

### Story 11.2: Version/Installation Page

As an **administrator**,
I want **a dedicated page for server version management**,
So that **I can see and manage which server version is installed**.

**Acceptance Criteria:**

**Given** no server is installed
**When** I navigate to `/game-server/version`
**Then** I see the installation interface (version input + install button)
**And** the page title is "Server Installation"

**Given** a server is installed
**When** I navigate to `/game-server/version`
**Then** I see the current installed version prominently displayed
**And** I see server state (running/stopped)
**And** the page title is "Server Version"

**Given** server installation is in progress
**When** I view the page
**Then** I see installation progress (stage + percentage)
**And** the install button is disabled

**Given** a newer version is available
**When** I view the page (server installed)
**Then** I see an "Update Available" indicator
**And** I can see the new version number

**Given** I am on the version page
**When** the page loads
**Then** the ServerInstallCard logic from Dashboard is reused/moved here

**Tasks:**
- [ ] Create `/features/game-server/VersionPage.tsx`
- [ ] Move ServerInstallCard logic from Dashboard
- [ ] Add installed version display with status
- [ ] Add update available indicator
- [ ] Add route `/game-server/version`
- [ ] Add tests for version page states

---

### Story 11.3: Settings Page Extraction

As an **administrator**,
I want **a dedicated full-page view for game server settings**,
So that **I have more space to view and edit configuration**.

**Acceptance Criteria:**

**Given** I navigate to `/game-server/settings`
**When** the page loads
**Then** I see the GameConfigPanel in a full-width layout
**And** server status is shown in the page header

**Given** no server is installed
**When** I navigate to `/game-server/settings`
**Then** I see a message indicating server must be installed first
**And** a link to the Installation page is provided

**Given** I am on the settings page
**When** I edit a setting
**Then** the existing auto-save behavior works as before
**And** toast notifications appear for success/error

**Given** the settings page is displayed
**When** I view the layout
**Then** setting groups have better horizontal space utilization than the previous split-view

**Tasks:**
- [ ] Create `/features/game-server/SettingsPage.tsx`
- [ ] Extract GameConfigPanel into full-page layout
- [ ] Add server status header component
- [ ] Add empty state for no server installed
- [ ] Add route `/game-server/settings`
- [ ] Improve layout for wider screens
- [ ] Add tests for settings page

---

### Story 11.4: Mods Page Migration

As an **administrator**,
I want **Mods accessible under Game Server navigation**,
So that **mod management is logically grouped with other server functions**.

**Acceptance Criteria:**

**Given** I navigate to `/game-server/mods`
**When** the page loads
**Then** I see the existing Mods interface (Installed/Browse tabs)
**And** all existing mod functionality works as before

**Given** I navigate to the old `/mods` URL
**When** the page loads
**Then** I am redirected to `/game-server/mods`

**Given** I am on the mod detail page
**When** I view the URL
**Then** it is `/game-server/mods/browse/:slug`

**Given** no server is installed
**When** I navigate to `/game-server/mods`
**Then** I see a message indicating server must be installed first
**And** compatibility checking is disabled (no game version to check against)

**Tasks:**
- [ ] Move mods feature routes under `/game-server/mods`
- [ ] Update all internal links to mods pages
- [ ] Add redirect from old `/mods` routes
- [ ] Update breadcrumbs in mod detail page
- [ ] Add empty state for no server installed
- [ ] Update tests for new routes

---

### Story 11.5: Console Page Extraction

As an **administrator**,
I want **a dedicated full-page console view**,
So that **I have maximum space for monitoring server output**.

**Acceptance Criteria:**

**Given** I navigate to `/game-server/console`
**When** the page loads
**Then** I see the ConsolePanel in a full-width, full-height layout
**And** server status is shown in the page header

**Given** no server is installed
**When** I navigate to `/game-server/console`
**Then** I see a message indicating server must be installed first
**And** the console is not displayed

**Given** the server is stopped
**When** I view the console page
**Then** I can still view console history
**And** command input is disabled with explanation

**Given** I am on the console page
**When** I select a different log source (dropdown)
**Then** the log streaming switches as before

**Tasks:**
- [ ] Create `/features/game-server/ConsolePage.tsx`
- [ ] Extract ConsolePanel into full-page layout
- [ ] Add server status header component
- [ ] Add empty state for no server installed
- [ ] Add route `/game-server/console`
- [ ] Maximize vertical space usage
- [ ] Add tests for console page

---

### Story 11.6: Dashboard & Navigation Cleanup

As an **administrator**,
I want **a simplified Dashboard focused on status**,
So that **it serves as a quick overview without duplicate functionality**.

**Acceptance Criteria:**

**Given** I navigate to Dashboard
**When** the page loads
**Then** ServerInstallCard is NOT displayed (moved to Version page)
**And** Server status card remains with basic info

**Given** no server is installed
**When** I view the Dashboard
**Then** I see a card indicating "No server installed"
**And** a button/link takes me to `/game-server/version`

**Given** the sidebar navigation is updated
**When** I view the sidebar
**Then** "Settings" is renamed to "VSManager"
**And** "Mods" is no longer a top-level item

**Given** the default route for `/game-server`
**When** I navigate to `/game-server` without a sub-path
**Then** I am redirected to `/game-server/version`

**Tasks:**
- [ ] Remove ServerInstallCard from Dashboard
- [ ] Add "No server installed" card with link to version page
- [ ] Rename "Settings" to "VSManager" in sidebar
- [ ] Remove top-level "Mods" from sidebar
- [ ] Set default redirect for `/game-server` → `/game-server/version`
- [ ] Update any remaining internal navigation links
- [ ] Add tests for navigation changes

---

## Epic 12: Enhanced Dashboard with Server Metrics

Admins can monitor server health and performance through a comprehensive dashboard with real-time metrics, historical charts, and quick actions.

**Goal:** Transform Dashboard from a basic status card into a monitoring hub with CPU, memory, player count, and time-series visualizations.

### Current State

- Dashboard shows: server state badge, version, uptime, disk space, controls
- No historical data, no player info, no resource metrics
- Single polling interval (5 seconds)
- Basic status card layout

### Target State

- Real-time metrics: Memory (API + Game), CPU, player count
- Time-series charts for key metrics (1h, 6h, 24h views)
- Server health indicators with thresholds
- Quick links to other sections
- Responsive card-based layout

---

### Story 12.1: Epic 12 Technical Preparation

As a **developer**,
I want **to research metrics collection and visualization approaches**,
So that **subsequent stories have a solid technical foundation**.

**Acceptance Criteria:**

**Given** we need to collect process metrics
**When** I research approaches
**Then** I document how to use psutil for API server metrics
**And** I document how to find and monitor the VintageStory game server process

**Given** we need to display charts
**When** I evaluate charting libraries
**Then** I recommend a library (recharts, visx, or lightweight alternative)
**And** I document bundle size and feature trade-offs

**Given** we need to store historical metrics
**When** I design the storage approach
**Then** I document in-memory ring buffer design with configurable retention
**And** I specify data structure for metrics snapshots

**Given** we may want player information
**When** I research VintageStory server capabilities
**Then** I document how to get player count (console parsing, RCON, or API)
**And** I note any limitations

**Tasks:**
- [ ] Research psutil for process metrics collection
- [ ] Document game server process discovery (by name or PID file)
- [ ] Evaluate charting libraries (recharts vs alternatives)
- [ ] Design MetricsSnapshot data model
- [ ] Design in-memory ring buffer with retention policy
- [ ] Research player count extraction methods
- [ ] Update architecture.md with findings

---

### Story 12.2: Metrics Collection Service

As a **backend developer**,
I want **a service that collects server metrics periodically**,
So that **current and historical metrics are available via API**.

**Acceptance Criteria:**

**Given** the API server is running
**When** the metrics collection job executes (default every 10 seconds)
**Then** it collects: timestamp, api_memory_mb, api_cpu_percent

**Given** the game server process is running
**When** metrics are collected
**Then** it also collects: game_memory_mb, game_cpu_percent

**Given** the game server is not running
**When** metrics are collected
**Then** game_memory_mb and game_cpu_percent are null
**And** collection continues without error

**Given** metrics are collected
**When** the ring buffer is at capacity (default 1 hour at 10s intervals = 360 samples)
**Then** the oldest samples are evicted (FIFO)

**Given** the collection interval is configurable
**When** `VS_METRICS_INTERVAL` is set
**Then** metrics are collected at the specified interval

**Tasks:**
- [ ] Add psutil dependency to pyproject.toml
- [ ] Create MetricsService with collect() method
- [ ] Create MetricsSnapshot Pydantic model
- [ ] Implement ring buffer storage with configurable size
- [ ] Implement game server process discovery
- [ ] Register metrics collection background job
- [ ] Add tests for metrics collection

---

### Story 12.3: Metrics API Endpoints

As a **frontend developer**,
I want **API endpoints to retrieve current and historical metrics**,
So that **the dashboard can display real-time and chart data**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/metrics/current` as Admin
**When** metrics have been collected
**Then** I receive the latest MetricsSnapshot
**And** response includes: timestamp, api_memory_mb, api_cpu_percent, game_memory_mb, game_cpu_percent

**Given** I call `GET /api/v1alpha1/metrics/history` as Admin
**When** I don't specify parameters
**Then** I receive all available historical metrics (up to buffer size)

**Given** I call `GET /api/v1alpha1/metrics/history?minutes=60`
**When** I specify a time range
**Then** I receive metrics from the last 60 minutes only

**Given** I am authenticated as Monitor
**When** I call metrics endpoints
**Then** I receive a 403 Forbidden (metrics are Admin-only)

**Given** no metrics have been collected yet
**When** I call metrics endpoints
**Then** I receive an empty response (not an error)

**Tasks:**
- [ ] Create /metrics router with current and history endpoints
- [ ] Add time range filtering for history
- [ ] Add Admin-only authorization
- [ ] Add OpenAPI documentation
- [ ] Add tests for metrics API

---

### Story 12.4: Dashboard Stats Cards

As an **administrator**,
I want **stat cards showing current server metrics**,
So that **I can see server health at a glance**.

**Acceptance Criteria:**

**Given** I view the Dashboard
**When** the page loads
**Then** I see stat cards for: Server Status, Memory Usage, Disk Space, Uptime

**Given** the Memory Usage card is displayed
**When** metrics are available
**Then** I see API memory and Game memory separately
**And** values update in real-time (polling every 10 seconds)

**Given** the Server Status card is displayed
**When** I view it
**Then** I see status badge (running/stopped/etc.)
**And** Start/Stop/Restart buttons are available

**Given** the game server is not running
**When** I view the Memory card
**Then** Game memory shows "N/A" or "-"
**And** API memory is still displayed

**Given** I am on a mobile device
**When** I view the Dashboard
**Then** stat cards stack vertically in a responsive layout

**Tasks:**
- [ ] Create StatCard component with icon, label, value, trend
- [ ] Create useMetrics hook for polling current metrics
- [ ] Redesign Dashboard layout with card grid
- [ ] Implement Memory card with API/Game breakdown
- [ ] Implement Disk Space card (existing data)
- [ ] Implement Uptime card
- [ ] Move server controls to Status card
- [ ] Add responsive layout for mobile
- [ ] Add tests for stat cards

---

### Story 12.5: Dashboard Time-Series Charts

As an **administrator**,
I want **charts showing metrics over time**,
So that **I can identify trends and anomalies**.

**Acceptance Criteria:**

**Given** I view the Dashboard
**When** the page loads
**Then** I see a Memory Usage chart showing API and Game memory over time

**Given** the chart is displayed
**When** I view it
**Then** it shows data for the selected time range (default 1 hour)
**And** API and Game memory are shown as separate lines

**Given** I want to change the time range
**When** I click a time range selector (15m, 1h, 6h, 24h)
**Then** the chart updates to show that time period

**Given** the game server was stopped during the time range
**When** I view the chart
**Then** Game memory line has gaps where data is unavailable

**Given** I hover over a point on the chart
**When** the tooltip appears
**Then** I see the timestamp and exact values

**Tasks:**
- [ ] Add recharts (or chosen library) dependency
- [ ] Create MetricsChart component
- [ ] Create useMetricsHistory hook
- [ ] Implement time range selector
- [ ] Style chart with Catppuccin theme colors
- [ ] Add responsive sizing
- [ ] Add tests for chart component

---

## Epic 13: Server Version Browser

Admins can browse and install server versions through a visual interface similar to the mod browser, replacing the simple version input with a discoverable list of available releases.

**Goal:** Replace free-text version input with a browsable list showing available versions, release info, and one-click install/upgrade.

### Current State

- User must know exact version number (e.g., "1.21.3")
- Version input is free-text field
- No visibility into available versions or release dates
- No upgrade path visibility
- Must type version manually

### Target State

- Browse available versions with release metadata
- Filter by channel (stable/unstable)
- One-click install or upgrade
- Version comparison and warnings
- Similar UX to mod browser

---

### Story 13.0: Epic 13 Technical Preparation

As a **developer**,
I want **to research VintageStory version APIs and plan the browser implementation**,
So that **subsequent stories have accurate API documentation and design**.

**Acceptance Criteria:**

**Given** we need to fetch available versions
**When** I research the VintageStory version API
**Then** I document the response format from stable.json and unstable.json
**And** I note all available fields (version, filename, filesize, md5, etc.)

**Given** we want to show release information
**When** I research available metadata
**Then** I document what release info is available (date, changelog, etc.)
**And** I note any limitations

**Given** we need to cache version data
**When** I design the caching strategy
**Then** I document cache TTL (versions don't change frequently)
**And** I specify how to handle cache refresh

**Given** we want a similar UX to mod browser
**When** I design the UI approach
**Then** I document which patterns can be reused from Epic 10

**Tasks:**
- [ ] Document VintageStory version API response format
- [ ] Identify all available version metadata
- [ ] Design versions caching strategy (extend existing VersionsCache)
- [ ] Plan UI component reuse from mod browser
- [ ] Update architecture.md with findings

---

### Story 13.1: Server Versions API

As a **frontend developer**,
I want **an API endpoint to list available server versions**,
So that **the version browser can display all available releases**.

**Acceptance Criteria:**

**Given** I call `GET /api/v1alpha1/versions` as Admin
**When** the endpoint is called
**Then** I receive a list of available versions from both stable and unstable channels
**And** each version includes: version, channel, filename, filesize, md5, is_latest

**Given** I call `GET /api/v1alpha1/versions?channel=stable`
**When** the channel filter is applied
**Then** I receive only stable versions

**Given** I call `GET /api/v1alpha1/versions?channel=unstable`
**When** the channel filter is applied
**Then** I receive only unstable versions

**Given** the VintageStory API is unavailable
**When** I call the versions endpoint
**Then** I receive cached data if available
**And** the response includes a `cached: true` indicator

**Given** I call `GET /api/v1alpha1/versions/{version}`
**When** the version exists
**Then** I receive detailed information for that specific version

**Tasks:**
- [ ] Extend VersionsCache to store full version lists (not just latest)
- [ ] Create /versions router with list and detail endpoints
- [ ] Add channel filtering
- [ ] Add cache indicator in response
- [ ] Add background job to refresh version cache
- [ ] Add tests for versions API

---

### Story 13.2: Version Card Component

As an **administrator**,
I want **versions displayed as informative cards**,
So that **I can quickly scan and compare available versions**.

**Acceptance Criteria:**

**Given** the version list is displayed
**When** I view the version cards
**Then** each card shows: version number, channel badge (stable/unstable), file size

**Given** a version is the currently installed version
**When** I view its card
**Then** I see an "Installed" badge

**Given** a version is the latest in its channel
**When** I view its card
**Then** I see a "Latest" badge

**Given** I click on a version card
**When** the click is registered
**Then** the version detail view opens (or inline expansion)

**Tasks:**
- [ ] Create VersionCard component
- [ ] Add channel badge (stable = green, unstable = yellow)
- [ ] Add "Installed" badge logic
- [ ] Add "Latest" badge logic
- [ ] Style consistently with mod cards
- [ ] Add tests for version card

---

### Story 13.3: Version List Page

As an **administrator**,
I want **a browsable list of server versions**,
So that **I can see all available versions and choose one to install**.

**Acceptance Criteria:**

**Given** I navigate to `/game-server/version`
**When** a server is installed
**Then** I see my current version prominently at the top
**And** below I see "Available Versions" with the version list

**Given** I view the version list
**When** it loads
**Then** versions are grouped or filterable by channel (All, Stable, Unstable)
**And** default filter is "All"

**Given** I select the "Stable" filter
**When** the filter is applied
**Then** only stable versions are displayed

**Given** versions are displayed
**When** I view the list
**Then** versions are sorted by version number (newest first)

**Given** I am viewing on mobile
**When** the page loads
**Then** the layout is responsive and cards stack appropriately

**Tasks:**
- [ ] Create VersionListPage component (or update existing VersionPage)
- [ ] Add channel filter tabs/buttons
- [ ] Create useVersions hook for data fetching
- [ ] Display current version section
- [ ] Add responsive layout
- [ ] Add loading and error states
- [ ] Add tests for version list

---

### Story 13.4: Install/Upgrade Flow

As an **administrator**,
I want **a confirmation dialog when installing or upgrading versions**,
So that **I understand the implications before making changes**.

**Acceptance Criteria:**

**Given** I click "Install" on a version (no server installed)
**When** the dialog opens
**Then** I see version details and an "Install" confirmation button

**Given** I click "Upgrade" on a version (server installed, newer version)
**When** the dialog opens
**Then** I see current version → new version comparison
**And** I see a warning that the server will be stopped

**Given** I click "Downgrade" on a version (server installed, older version)
**When** the dialog opens
**Then** I see a prominent warning about downgrading
**And** I must confirm I understand the risks

**Given** the server is currently running
**When** I confirm install/upgrade
**Then** I see a warning that the server will be stopped
**And** the server is stopped before installation begins

**Given** I confirm installation
**When** the installation starts
**Then** I see progress indication (stage + percentage)
**And** I can stay on the page or navigate away

**Given** installation completes successfully
**When** the process finishes
**Then** I see a success message
**And** the version list updates to show the new installed version

**Tasks:**
- [ ] Create InstallVersionDialog component
- [ ] Add version comparison display
- [ ] Add downgrade warning
- [ ] Add server-running warning
- [ ] Integrate with existing install progress tracking
- [ ] Add success/error handling
- [ ] Add tests for install flow

---

### Story 13.5: Version Page Integration

As an **administrator**,
I want **the version browser integrated into the Version page**,
So that **version management is a cohesive experience**.

**Acceptance Criteria:**

**Given** no server is installed
**When** I view `/game-server/version`
**Then** I see the version browser with "Install" buttons
**And** page title is "Server Installation"

**Given** a server is installed
**When** I view `/game-server/version`
**Then** I see current version info at the top
**And** I see "Change Version" section with the browser below
**And** page title is "Server Version"

**Given** an update is available
**When** I view the version page
**Then** the newer version card is highlighted
**And** an "Update Available" banner is shown

**Given** I want to quickly install the latest stable
**When** I view the page
**Then** there is a prominent "Install Latest Stable" button (if not installed)
**Or** "Update to Latest" button (if installed and update available)

**Tasks:**
- [ ] Integrate version browser into VersionPage
- [ ] Add "Install Latest Stable" quick action
- [ ] Add "Update Available" banner
- [ ] Highlight newer versions
- [ ] Add page title dynamic switching
- [ ] Add tests for integrated page

---

### Story 13.6: Server Uninstall API

As a **developer**,
I want **an API endpoint to uninstall the server**,
So that **I can programmatically remove the server installation**.

**Background:** Added from Epic 11 retrospective to support testing workflow. Allows clean uninstall for version switching without manual file deletion.

**Acceptance Criteria:**

**Given** the server is running
**When** I call `DELETE /api/v1alpha1/server` as Admin
**Then** the server is stopped first
**And** the `/data/server` directory is deleted
**And** the server state becomes `not_installed`
**And** I receive a success response

**Given** the server is stopped
**When** I call `DELETE /api/v1alpha1/server` as Admin
**Then** the `/data/server` directory is deleted
**And** the server state becomes `not_installed`
**And** I receive a success response

**Given** no server is installed
**When** I call `DELETE /api/v1alpha1/server` as Admin
**Then** I receive a 404 or appropriate error response
**And** no files are deleted

**Given** I call the uninstall endpoint
**When** the operation completes
**Then** the `/data/serverdata` directory is preserved (configs, mods, worlds)

**Tasks:**
- [ ] Add `DELETE /api/v1alpha1/server` endpoint to server router
- [ ] Implement uninstall logic in ServerService (stop if running, delete /data/server)
- [ ] Add state transition to `not_installed` after successful uninstall
- [ ] Preserve `/data/serverdata` directory (configs, mods, worlds)
- [ ] Add error handling for edge cases (already not_installed, deletion failures)
- [ ] Add comprehensive tests for uninstall scenarios

---

### Story 13.7: Server Uninstall UI

As an **administrator**,
I want **a way to uninstall the server from the UI**,
So that **I can cleanly remove the installation without manual file deletion**.

**Background:** Added from Epic 11 retrospective to support testing workflow. Provides UI for the uninstall API with appropriate confirmation.

**Acceptance Criteria:**

**Given** a server is installed
**When** I view the Version page
**Then** I see a "Remove Server" button (or similar)
**And** the button is styled as a destructive action (red/warning)

**Given** the server is running
**When** I click "Remove Server"
**Then** I see a confirmation dialog explaining the server will be stopped
**And** the dialog notes that configuration and world data will be preserved

**Given** the server is stopped
**When** I click "Remove Server"
**Then** I see a confirmation dialog
**And** the dialog notes that configuration and world data will be preserved

**Given** I confirm the uninstall
**When** the operation completes
**Then** I see a success toast notification
**And** the page transitions to the "Server Installation" view
**And** the sidebar label changes from "Version" to "Installation"

**Given** I cancel the confirmation dialog
**When** I close the dialog
**Then** no action is taken
**And** the server remains installed

**Tasks:**
- [ ] Add "Remove Server" button to VersionPage (visible when installed)
- [ ] Create UninstallConfirmDialog component with appropriate warnings
- [ ] Implement useUninstallServer mutation hook
- [ ] Handle loading state during uninstall operation
- [ ] Add success toast and state transition after uninstall
- [ ] Disable button when server is in transitional states (starting, stopping, installing)
- [ ] Add tests for uninstall UI flow

---

## Epic 14: Mod Updates

**Goal:** Admins can see when installed mods have updates, apply them individually or together, switch to any listed release, and be alerted when new updates appear.

### Current State

- Mods can be installed, enabled, disabled and removed
- Installing an already-installed mod is rejected, so the detail page's Update button cannot succeed
- The mod refresh job fetches data for installed mods but discards it

### Target State

- Installed mods show their update status and offered version
- Update and version switching are one safe operation that leaves the mod unchanged on failure
- Scheduled checks drive an in-app count badge and an optional webhook alert

---

### Story 14.0: Epic 14 Technical Preparation

As a **developer**,
I want **mod release behavior verified against the live mod database**,
So that **update logic rests on confirmed behavior**.

**Acceptance Criteria:**

**Given** the live mod API
**When** releases are inspected for several mods
**Then** findings document release ordering, whether old releases remain listed, and how filenames vary between versions

**Given** a mod file is replaced while the game server is running
**When** the behavior is tested
**Then** findings document whether replacement is safe before a restart

**Given** common webhook receivers
**When** payload requirements are researched
**Then** a payload format is documented that works with Discord and generic receivers

**Tasks:**
- [ ] Verify release ordering and history against the live API
- [ ] Test replacing a mod file while the server runs
- [ ] Define the webhook payload
- [ ] Update architecture documentation with findings

---

### Story 14.1: Update Detection and Status API

As an **administrator**,
I want **to see which installed mods have updates**,
So that **I know what can be updated without checking each mod**.

**Acceptance Criteria:**

**Given** an installed mod has newer releases
**When** update status is determined
**Then** release order from the mod database identifies them, without comparing version strings (apart from the base-version check below)
**And** the offered update is the newest compatible release, or if none, the newest not-verified release

*(Covers FR129, FR130)*

**Given** a ModDB entry contains releases for several modids
**When** update status is determined
**Then** only releases with the installed mod's modid are considered
**And** the installed release is identified by both modid and version

**Given** the installed version is stable
**When** a newer release is a pre-release (its version contains `-`)
**Then** it is not offered as an update
**And** a mod already on a pre-release can be offered a newer release only if its base version (the dot-separated numeric part before any `-`) is at least the installed base version
**And** a newer release whose base version cannot be parsed is not eligible, and if the installed base version cannot be parsed, no update is offered for that mod

**Given** every newer release is incompatible with the current game version
**When** update status is determined
**Then** no update is offered

*(Covers FR131)*

**Given** a mod or its installed version is not listed in the mod database
**When** update status is determined
**Then** its status is unknown, not up to date

*(Covers FR132)*

**Given** I am an Admin or Monitor
**When** I request `GET /api/v1alpha1/mods/updates`
**Then** I receive each mod's status, offered version, compatibility and last-checked time

*(Covers FR133)*

**Given** I am an Admin
**When** I request `POST /api/v1alpha1/mods/updates/check`
**Then** status is refreshed from the mod database
**And** a Monitor receives 403

*(Covers FR134)*

**Given** update status has been stored
**When** the API restarts
**Then** the last known status is still returned

*(Covers FR147)*

**Given** the mod database is unavailable
**When** a check runs
**Then** the previous status is preserved and the failure is reported

**Tasks:**
- [ ] Implement release-order detection and offered-version selection
- [ ] Persist update status with atomic writes
- [ ] Add status and check endpoints with role enforcement
- [ ] Add tests for each status outcome and API failure
- [ ] Add tests using `api/tests/fixtures/moddb/mod_carryon.json`: a `2.0.0-pre.8` install is offered `2.0.0-rc.1` but never `1.14.3`, and a `1.14.3` install is never offered a pre-release

---

### Story 14.2: Version Change API

As an **administrator**,
I want **a mod moved safely to a chosen version**,
So that **a failed update never leaves me without a working mod**.

**Acceptance Criteria:**

**Given** an installed mod and a release listed in the mod database with the installed mod's modid
**When** I request `PUT /api/v1alpha1/mods/{slug}/version`
**Then** the release is obtained from cache if present, otherwise downloaded
**And** the installed file is replaced only after the new file is validated

*(Covers FR135, FR140, FR142)*

**Given** a download or validation failure
**When** the version change fails
**Then** the original file and state are unchanged
**And** a specific error code is returned

*(Covers FR137)*

**Given** a cached or downloaded archive whose modid or version differs from the requested release
**When** it is validated
**Then** a cached copy is replaced by a fresh download, and a downloaded copy fails the change
**And** the original file and state are unchanged

**Given** ModDB's filename for the release
**When** it is used to name a file
**Then** only its final path component is used, and empty, `.` or `..` names are rejected

**Given** the old file cannot be deleted after the swap
**When** the change completes
**Then** the new file is removed, the original remains, and the change is reported as failed

**Given** the mod is disabled
**When** its version changes
**Then** it remains disabled

*(Covers FR138)*

**Given** the server is running
**When** a version change succeeds
**Then** a restart is marked as pending

*(Covers FR139)*

**Given** a release whose modid differs from the installed mod's, even within the same mod database entry
**When** a version change to it is requested
**Then** the request is rejected and the mod is unchanged

**Given** the target release is not verified, incompatible, a pre-release while the installed version is stable, or older than the installed release (later in the mod database's release list)
**When** the request does not include explicit confirmation
**Then** the request is rejected with the compatibility details

*(Covers FR136, FR141)*

**Given** a version change is in progress for a mod
**When** another change is requested for that mod
**Then** the second request is rejected with 409

**Tasks:**
- [ ] Add a version change operation to ModService
- [ ] Reuse the download, validation and atomic replacement patterns
- [ ] Add error codes to `models/errors.py`
- [ ] Add the endpoint, Admin only
- [ ] Add tests for failure at each stage, disabled mods and concurrency
- [ ] Add tests using `api/tests/fixtures/moddb/mod_instruments.json` (version `1.0.1` under two modids) and `mod_carryon.json` (publish order differs from version order)

---

### Story 14.3: Update and Version Switching UI

As an **administrator**,
I want **to update or switch a mod's version from the UI**,
So that **I can manage versions without touching files**.

**Acceptance Criteria:**

**Given** a mod has an offered update
**When** I view the Installed tab
**Then** I see the installed and offered versions with an Update action, on desktop and mobile layouts

**Given** the offered update is compatible
**When** I click Update
**Then** the mod updates without further confirmation and I see a success toast

*(Covers FR135)*

**Given** the offered update is not verified
**When** I click Update
**Then** a warning must be confirmed first

*(Covers FR136)*

**Given** a mod's status is unknown
**When** I view the Installed tab
**Then** it is shown as unknown, not as up to date

**Given** an installed mod
**When** I open its detail page
**Then** the Update button succeeds
**And** I can select any release listed for the installed mod's modid, with warnings for not-verified, incompatible, pre-release (when the installed version is stable) or older releases

*(Covers FR79, FR140, FR141)*

**Given** an update fails
**When** the error is returned
**Then** I see an error toast and the mod is shown unchanged

**Tasks:**
- [ ] Add update status and version change hooks with query invalidation
- [ ] Add version information and the Update action to the Installed tab
- [ ] Add confirmation dialogs
- [ ] Connect the detail page Update button and version selector to the new endpoint
- [ ] Add component tests
- [ ] Manual browser verification

---

### Story 14.4: Update All

As an **administrator**,
I want **to apply all compatible updates at once**,
So that **routine updates take a single action**.

**Acceptance Criteria:**

**Given** mods have compatible updates
**When** I request `POST /api/v1alpha1/mods/updates/apply-all`
**Then** each is updated using the version change operation
**And** results are returned per mod

*(Covers FR143, FR145)*

**Given** a mod's offered update is not verified
**When** update all runs
**Then** it is skipped and reported for individual review

*(Covers FR144)*

**Given** one mod fails to update
**When** update all continues
**Then** the remaining mods are still processed

*(Covers FR145)*

**Given** I click Update All in the UI
**When** the confirmation appears
**Then** it lists what will be updated and skipped
**And** afterwards I see a per-mod summary and at most one restart prompt

**Tasks:**
- [ ] Add the apply-all endpoint, Admin only
- [ ] Re-evaluate each offered version when applying
- [ ] Add the Update All action, confirmation and summary
- [ ] Add API and component tests
- [ ] Manual browser verification

---

### Story 14.5: Scheduled Checks and Update Badges

As an **administrator**,
I want **updates found automatically and shown at a glance**,
So that **I notice them without checking**.

**Acceptance Criteria:**

**Given** `mod_list_refresh_interval` is greater than 0
**When** the refresh job runs
**Then** update status is recorded for each installed mod
**And** a failure for one mod does not affect the others

*(Covers FR146)*

**Given** `mod_list_refresh_interval` is 0
**When** the scheduler starts
**Then** no scheduled checks run
**And** on-demand checks still work

*(Covers FR146)*

**Given** updates are available
**When** I view the Dashboard or navigation
**Then** I see the count of mods with updates
**And** selecting it takes me to the Installed tab

*(Covers FR148)*

**Given** no updates are available
**When** I view the Dashboard or navigation
**Then** no count is shown

**Tasks:**
- [ ] Extend `mod_cache_refresh` to record update status
- [ ] Add the count to the Dashboard and Mods navigation
- [ ] Add job and component tests
- [ ] Manual browser verification

---

### Story 14.6: Webhook Alerts

As an **administrator**,
I want **an alert sent to my chat when updates appear**,
So that **I find out without opening the UI**.

**Acceptance Criteria:**

**Given** I am an Admin
**When** I save an http or https webhook URL in API settings
**Then** it is stored and later shown only as configured or not configured
**And** the URL is never logged or returned to a Monitor

*(Covers FR149)*

**Given** a check finds a newly available update
**When** a webhook is configured
**Then** one alert is sent for that mod and version
**And** later checks do not repeat it, including after an API restart

*(Covers FR150)*

**Given** the webhook URL is a Discord webhook
**When** an alert is sent
**Then** the payload contains only `content` and `allowed_mentions`, with mentions suppressed and `content` within 2000 characters
**And** any other receiver gets `event`, `content` and an `updates` list

**Given** webhook delivery fails or times out
**When** the job continues
**Then** a failure is logged without the URL
**And** update checks are unaffected
**And** the alert is retried on the next check

*(Covers FR151)*

**Tasks:**
- [ ] Add the webhook setting with redacted reads
- [ ] Add a settings UI field
- [ ] Send alerts without following redirects, and record what was sent
- [ ] Add tests for deduplication, redaction and failure, including replayed Discord `204` and `429` responses
- [ ] Verify delivery against a test Discord webhook during manual verification
- [ ] Manual browser verification

---

## Epic 15: Release Engineering

**Goal:** Maintainers cut a versioned release with one command, and users install a published, verifiable image whose changes are described in a changelog.

### Current State

- CI lints, tests and builds the image on pull requests and `main`, but never publishes it
- No tags, releases or changelog exist; the version is hard-coded in four places that disagree
- The web UI's API key is baked into the image at build time

### Target State

- One version, shown in the API and the UI, set by the release command
- `just changelog` previews and `just release` cuts a release; a tag push publishes the GitHub release, GHCR image tags, SBOM and provenance
- One published image works for every deployment, with no key inside it

---

### Story 15.0: Epic 15 Technical Preparation

As a **developer**,
I want **the release toolchain verified against this repository**,
So that **the release stories rest on confirmed behavior**.

**Acceptance Criteria:**

**Given** this repository's history
**When** git-cliff runs with a draft configuration
**Then** findings show generated notes for a recent range, and the filter and scope rules that make them readable

**Given** a 0.x version
**When** the next version is computed from commits
**Then** findings confirm that features bump the minor version, fixes the patch version, and breaking changes the minor version

**Given** the container image
**When** the API reads its version from package metadata
**Then** findings confirm it returns the version in `pyproject.toml`

**Given** GitHub Actions on this public organization repository
**When** publishing to GHCR with attestations is researched
**Then** findings document the required permissions, the tag rules for 0.x and pre-release versions, the SBOM and provenance approach, and the one-time package visibility step

**Tasks:**
- [ ] Draft `cliff.toml` and compare its output with recent history
- [ ] Confirm version bump rules for 0.x
- [ ] Verify reading the version from package metadata inside the image
- [ ] Research GHCR publishing, image tags and attestations
- [ ] Update architecture documentation with findings

---

### Story 15.1: Single Version Source and Version Display

As an **administrator**,
I want **to see which version of the manager I am running**,
So that **I can tell whether I am up to date and report problems accurately**.

**Acceptance Criteria:**

**Given** the version in `api/pyproject.toml`
**When** the API starts
**Then** the OpenAPI document and `/healthz` report that version
**And** no other API file hard-codes it

*(Covers FR152, FR153)*

**Given** the version in `web/package.json`
**When** the web UI is built
**Then** the sidebar footer shows that version instead of a hard-coded value

*(Covers FR154)*

**Given** both version files
**When** `just version` runs
**Then** it prints the version
**And** fails if the two files disagree, comparing pre-release versions in their PEP 440 form (`0.2.0-rc.1` = `0.2.0rc1`)

**Given** the image is started with no network access
**When** the container starts
**Then** the API comes up without installing or downloading anything, and without dev dependencies (`VSS-flj`, found in Story 15.0)

**Tasks:**
- [ ] Install the project at image build time and start without syncing (`VSS-flj`)
- [ ] Read the API version from package metadata; remove hard-coded versions
- [ ] Add `version` to the `/healthz` response
- [ ] Build the web version from `package.json` into the sidebar footer
- [ ] Set `web/package.json` to 0.1.0; add `just version`
- [ ] Tests

---

### Story 15.2: Runtime API Key for the Web UI

As an **administrator running the published image**,
I want **the web UI to get its API key from my container's configuration**,
So that **one image works for every deployment and no key is baked into it**.

**Acceptance Criteria:**

**Given** `VS_API_KEY` is set on the container
**When** the web UI loads
**Then** its requests use that key

**Given** `VS_API_KEY` is not set
**When** the web UI loads
**Then** it uses the Admin key, matching the existing compose default

**Given** an image built from the Dockerfile
**When** its build arguments, layers and web bundle are inspected
**Then** they contain no API key

*(Covers FR165)*

**Given** the web dev server with `VITE_API_KEY` in `web/.env`
**When** a developer runs `just dev-web`
**Then** the UI authenticates as before

**Tasks:**
- [ ] Serve runtime web configuration from the API, never cached
- [ ] Read the key from runtime configuration in the web client, falling back to `VITE_API_KEY`
- [ ] Remove the API key build argument from the Dockerfile and compose files
- [ ] Tests; browser verification in a container

---

### Story 15.3: Changelog Generation

As a **maintainer**,
I want **release notes generated from commit messages**,
So that **each release describes its changes without manual assembly**.

**Acceptance Criteria:**

**Given** conventional commits since the last release
**When** `just changelog` runs
**Then** it prints the unreleased notes grouped into breaking changes, features, fixes and performance improvements
**And** each entry links to its commit

*(Covers FR155, FR157)*

**Given** `docs`, `chore`, `test`, `ci`, `build`, `refactor`, `style` or review commits, merge commits, or non-conventional messages
**When** notes are generated
**Then** they are left out

*(Covers FR155)*

**Given** a commit scoped to a story, task or review (e.g. `feat(story-14.2/task-6): ...`)
**When** notes are generated
**Then** the entry shows the description without that scope

*(Covers FR156)*

**Tasks:**
- [ ] Pin git-cliff in `.mise.toml`; add `cliff.toml`
- [ ] Add `just changelog`
- [ ] Automated tests against a fixture history, run in CI

---

### Story 15.4: Release Command

As a **maintainer**,
I want **to cut a release with one command**,
So that **version, changelog, commit and tag are always consistent**.

**Acceptance Criteria:**

**Given** unreleased commits on `main`
**When** I run `just release`
**Then** the next version is computed from the commits
**And** `just release patch|minor|major` or `just release X.Y.Z[-pre]` overrides it

**Given** a version is chosen
**When** the release runs
**Then** it updates `api/pyproject.toml`, `api/uv.lock`, `web/package.json` and `CHANGELOG.md`
**And** commits them as `chore(release): vX.Y.Z` with an annotated tag `vX.Y.Z`
**And** asks for confirmation, then pushes the commit and tag together

*(Covers FR158)*

**Given** I am not on `main`, the working tree is dirty, `main` differs from its remote, the tag exists, or the version is not newer than the last release
**When** I run `just release`
**Then** it stops with a clear message and changes nothing

*(Covers FR159)*

**Given** `just release --dry-run`
**When** it runs
**Then** it shows the version and notes and changes nothing

*(Covers FR160)*

**Given** an explicit pre-release version such as `0.3.0-rc.1`
**When** the release runs
**Then** it updates the version files, commits and tags, but leaves `CHANGELOG.md` unchanged
**And** the next stable release's notes cover everything since the last stable release

**Given** no releasable commits since the last release and no explicit version
**When** I run `just release`
**Then** it reports that there is nothing to release

**Given** a step fails before the push
**When** the release stops
**Then** no release commit or tag is left behind

**Tasks:**
- [ ] `scripts/release.sh` and `just release`
- [ ] Version file updates, changelog, commit, tag, confirmed push
- [ ] Preconditions, dry run, cleanup on failure
- [ ] Automated tests with a temporary repository and remote, run in CI

---

### Story 15.5: Release Workflow

As a **user of the published image**,
I want **each release published with notes and verifiable provenance**,
So that **I can install a specific version and trust where it came from**.

**Acceptance Criteria:**

**Given** a pushed tag `vX.Y.Z`
**When** the release workflow runs
**Then** a GitHub release is published with that version's changelog section as notes

*(Covers FR161)*

**Given** a stable version
**When** the image is published
**Then** GHCR has tags `X.Y.Z`, `X.Y` and `latest`
**And** a pre-release version gets only its full tag and a GitHub pre-release

*(Covers FR162)*

**Given** a tag that does not match the repository's version
**When** the workflow runs
**Then** it fails before publishing anything

*(Covers FR163)*

**Given** a published image
**When** a user runs `gh attestation verify` against it
**Then** its signed build provenance verifies
**And** an SBOM is attested for the image and attached to the release

*(Covers FR164)*

**Given** the workflow
**When** it is reviewed
**Then** each job has least-privilege permissions, actions are pinned to commit SHAs, and the image carries OCI version, revision and source labels

*(Covers NFR17, NFR18)*

**Tasks:**
- [ ] `.github/workflows/release.yml`: verify, build and push, attest, release
- [ ] Image tags and labels; pre-release handling
- [ ] SBOM and provenance attestations with `actions/attest`; SBOM release asset
- [ ] End-to-end check with a release-candidate tag, pushed only with the maintainer's approval

---

### Story 15.6: Release Documentation and First Release

As a **new user**,
I want **installation instructions for a specific release**,
So that **I can deploy and upgrade predictably**.

**Acceptance Criteria:**

**Given** the README
**When** I follow the installation section
**Then** it installs a pinned release, explains upgrading, explains verifying the image, and states that anyone who can load the web UI receives its API key

**Given** the release guide
**When** a maintainer reads it
**Then** it explains which commits become release notes, `just changelog`, `just release`, what the workflow publishes, and the one-time package visibility step

*(Covers FR166)*

**Given** the rest of the README
**When** a reader compares it with the product
**Then** it describes delivered features rather than planned ones
**And** its tool versions and commands match `.mise.toml` and the Justfile

**Given** Stories 15.1-15.5 are merged
**When** the maintainer cuts `v0.1.0`
**Then** the GitHub release, image tags and attestations exist
**And** the image starts with `docker-compose.yaml` and the UI works

**Tasks:**
- [ ] README installation, upgrade and verification sections
- [ ] README accuracy pass: delivered features, tool versions, commands
- [ ] Release guide; `CLAUDE.md` and `AGENTS.md` commands
- [ ] `docker-compose.yaml` comment on pinning a version
- [ ] Seed `CHANGELOG.md` with a summary for `v0.1.0`
- [ ] First release, cut by the maintainer

---

## Epic 16: UI Polish

**Goal:** Admins keep their place when moving around the web UI, see accurate mod information, and get layouts that fit their screen.

### Current State

- The mod browser keeps search, filters and sort in component state, so opening a mod's detail page and coming back resets them to newest, descending, no search; page and scroll restoration from Story 10.7 is cleared whenever they change
- The mod detail page matches an installed mod only by the browse slug, so an installed mod whose ID is not the entry's first mod ID shows the install flow
- An unverified or incompatible mod gives no hint of which game version it does support
- Mod description links open in the same tab and leave the app, and the description is sanitized inline on the detail page (the lookup preview card that printed it as plain text has not been mounted since VSS-195)
- The Installed mods table scrolls horizontally on phones
- Game server settings cards stretch across the full width on desktop
- The file browser has only a Back button

### Target State

- Returning from a mod's detail page restores the browser exactly: search, filters, sort, page and scroll position
- Mod information is accurate: installed mods are recognized by any mod ID, and incompatible mods name the game version they last supported
- Mod descriptions are sanitized in one place with links that open safely in a new tab; Installed mods and settings pages read well at every screen size, and the file browser path is clickable

---

### Story 16.0: Epic 16 Technical Preparation

As a **developer**,
I want **the open questions behind the polish stories answered against the running app**,
So that **each story starts from confirmed behavior and data**.

**Acceptance Criteria:**

**Given** the mod browser with Story 10.7's scroll restoration
**When** it is exercised manually, including on a throttled network
**Then** findings record whether page and scroll restoration work today, and whether the 100 ms timeout is reliable (`VSS-901`)

**Given** the browse state that has to survive navigation
**When** URL query parameters and sessionStorage are compared
**Then** findings record the chosen mechanism and why, including browser back, refresh and shared links

**Given** the mod database API
**When** its release data is checked for incompatible mods
**Then** findings record where the most recent supported game version comes from, and whether it is available on browse cards or only from mod details

**Given** the game server settings page
**When** it is reviewed at common desktop widths
**Then** findings record the target layout for the settings cards

**Tasks:**
- [ ] Verify Story 10.7 scroll restoration manually and record the result on `VSS-901`
- [ ] Choose the browse state persistence mechanism
- [ ] Find the source of a mod's most recent supported game version
- [ ] Sketch the desktop settings layout
- [ ] Write `architecture/epic-16-ui-polish.md` with the findings and add it to the index

---

### Story 16.1: Mod Browser State Survives Mod Details

As an **administrator**,
I want **the mod browser to keep my search, filters and sort when I look at a mod and come back**,
So that **I can compare several mods without searching again each time**.

**Acceptance Criteria:**

**Given** I have entered a search term, set filters or changed the sort
**When** I open a mod's detail page and return with Back to Browse or the browser's back button
**Then** the search term, filters and sort are as I left them, and the results match them

*(Covers FR167)*

**Given** I was on a later page and scrolled down
**When** I return from a mod's detail page
**Then** the same page is shown and scrolled to the card I opened, with the search, filters and sort I had set

*(Covers FR168)*

**Given** I change the search, filters or sort after returning
**When** the results change
**Then** the browser goes back to page 1, as it does today

**Tasks:**
- [ ] Persist search, filters and sort with the mechanism chosen in Story 16.0 (`VSS-dkl`)
- [ ] Restore page and scroll position together with them; fix restoration timing if Story 16.0 found it unreliable (`VSS-901`)
- [ ] Tests, including an end-to-end test of the detail round trip

---

### Story 16.2: Installed Mods Recognized by Any Mod ID

As an **administrator**,
I want **a mod's detail page to know when I already have it installed**,
So that **I am not offered an install for a mod I have**.

**Acceptance Criteria:**

**Given** a database entry that ships several mod IDs, and I have installed one that is not its first
**When** I open the entry's detail page
**Then** it shows the installed state, version and update actions, not the install flow

*(Covers FR169)*

**Tasks:**
- [ ] Match installed mods against every mod ID in the entry's releases (`ModRelease.modidstr`) instead of the browse slug (`VSS-ywb`)
- [ ] Tests

---

### Story 16.3: Latest Supported Game Version for Incompatible Mods

As an **administrator**,
I want **to see which game version an unverified or incompatible mod last supported**,
So that **I can judge how far behind it is before installing it**.

**Acceptance Criteria:**

**Given** a mod that is not verified or is incompatible with my installed game version
**When** I view it on its detail page or in the Installed mods list
**Then** the compatibility message names the most recent game version the mod supports

*(Covers FR170)*

**Given** a mod is installed
**When** I view it in the Installed mods list
**Then** its compatibility reflects the installed release, not the newest one

**Given** I browse mods
**When** the cards are shown
**Then** they are unchanged: the version needs mod details, which browse cards do not fetch (Epic 16 ADR-2)

**Tasks:**
- [ ] Add `latest_supported_game_version` to `CompatibilityInfo`, computed per mod ID as Epic 16 ADR-2 defines (`VSS-udh`)
- [ ] Evaluate the newest release of the mod ID rather than `releases[0]`; add an optional `version` to the lookup so the Installed list evaluates the installed release
- [ ] Replace the incompatible message's tag list with the behind, ahead and gap wording from ADR-2
- [ ] Show the version beside the badge in the Installed mods list
- [ ] Tests

---

### Story 16.4: Shared Description Sanitizer and Safe Links

*(Rescoped 2026-11-13: the mod lookup preview this story first targeted has not been mounted since VSS-195 (2026-01-19), so FR171 is withdrawn and the dead component is removed. Sprint key `16-4-formatted-description-in-mod-lookup-preview` is unchanged.)*

As an **administrator**,
I want **mod descriptions to be sanitized in one place, with their links opening safely in a new tab**,
So that **a mod author's HTML cannot run code, restyle the app or navigate me away from it**.

**Acceptance Criteria:**

**Given** a mod description with scripts, event handler attributes, `javascript:` URLs or `<style>` elements
**When** the mod detail page renders it
**Then** none of them reach the DOM, and its text, formatting and images are kept

**Given** a link in a mod description
**When** the detail page renders it
**Then** it opens in a new tab with `rel="noopener noreferrer"`

**Given** the web UI
**When** any code renders mod description HTML
**Then** it uses one shared sanitizing module with one DOMPurify configuration, and the unused `ModLookupInput` preview and the code only it used are removed

*(FR171 withdrawn; `VSS-4ll`)*

**Tasks:**
- [x] Shared DOMPurify sanitizer with safe links and `<style>` stripping + tests
- [x] Detail page uses it + tests
- [x] Remove the unused lookup preview and its orphaned code

---

### Story 16.5: Installed Mods on Phones

As an **administrator**,
I want **installed mods to fit a phone screen**,
So that **I can update, enable and remove mods without scrolling sideways**.

**Acceptance Criteria:**

**Given** a screen narrower than the `md` breakpoint
**When** I open Installed mods
**Then** each mod is a card showing its version, update status and Update action, enable toggle and remove action, with no horizontal scrolling

*(Covers FR172)*

**Given** a wider screen
**When** I open Installed mods
**Then** the existing table is unchanged

**Tasks:**
- [ ] Add a card layout below `md` for the Installed tab (`VSS-rr5`)
- [ ] Tests at both breakpoints

---

### Story 16.6: Settings Layout on Desktop

As an **administrator**,
I want **game server settings to use the width of a desktop screen**,
So that **I can see more settings without scrolling past half-empty cards**.

**Acceptance Criteria:**

**Given** a desktop-width screen
**When** I open game server settings
**Then** the settings cards follow the layout chosen in Story 16.0 instead of stretching across the full width

*(Covers FR173)*

**Given** a phone-width screen
**When** I open game server settings
**Then** the cards stack in one column as they do today

**Tasks:**
- [ ] Apply the desktop layout to the settings cards (`VSS-dfx`)
- [ ] Tests

---

### Story 16.7: File Browser Breadcrumbs

As an **administrator**,
I want **to jump to any folder in the current path**,
So that **I can move up several levels in one click**.

**Acceptance Criteria:**

**Given** I am in a subdirectory of the file browser
**When** I look at the path
**Then** each segment, and the root, is a link to that directory

*(Covers FR174)*

**Given** I click a segment
**When** the directory loads
**Then** its listing is shown and the path updates

**Tasks:**
- [ ] Replace the Back button with breadcrumb segments (`VSS-8lh`)
- [ ] Tests, including the end-to-end directory navigation test from `VSS-3mr` if it is still open

---

### Story 16.8: Name Sort and Empty Settings

*(Added 2026-11-13 after Stories 16.0-16.7, for two bugs found during the epic: `VSS-stm.1` and `VSS-7ed`.)*

As an **administrator**,
I want **the Name (A-Z) sort to list mods, and empty game settings to stay empty**,
So that **I can find mods alphabetically and edit settings without saving the word "null" or showing the server password**.

**Acceptance Criteria:**

**Given** the mod browser
**When** I choose Name (A-Z)
**Then** mods are listed alphabetically by name, ignoring leading spaces, letter case and accents, across all matching mods, with page controls like the other sorts

*(Covers FR175)*

**Given** the Name (A-Z) sort with a later page, a search or filters in the URL
**When** the page loads
**Then** the results are that page of the alphabetical list of matching mods, and no request asks for more than 100 mods

*(Covers FR175)*

**Given** a game setting with no value (Description, Password or IP Address)
**When** I open game server settings
**Then** the field is empty, not the text "null"

*(Covers FR176)*

**Given** I clear Description, Password or IP Address and leave the field
**When** the setting is saved
**Then** it is stored as no value (null), never as the text "null" or "None", and the other settings never store "None"

*(Covers FR176)*

**Given** the Password setting
**When** I open game server settings
**Then** the password is masked, and I can show and hide it

*(Covers FR176)*

**Tasks:**
- [ ] Use the API's existing `sort=name` with normal page sizes and drop the client-side sort (`VSS-stm.1`)
- [ ] Accept null for the settings whose VintageStory default is null; save a cleared field as null (`VSS-7ed`)
- [ ] Render null as an empty field and mask Password with a show/hide toggle (`VSS-7ed`)
- [ ] Tests, and browser verification that restores every changed setting

---

## Epic 17: Mod Data Correctness and Fixes

**Goal:** Admins can open, install and manage any mod without the manager failing on the mod database's data or acting on the wrong release, and settings and layouts behave as shown.

**Architecture:** `architecture/epic-17-mod-data-fixes.md` (ADR-1 to ADR-5). There is no preparation story; the two open questions are settled inside Stories 17.5 and 17.6, each with a recommended default.

**Order:** Story 17.1 first: it fixes a bug seen in production, and a release candidate follows it. Stories 17.2 and 17.3 change the same install code and run back to back, 17.2 first. The others are independent.

### Current State

- A mod with one release whose file ID is null in the mod database cannot be opened: the lookup returns 500 and the detail page shows "Failed to load mod details" with no way back to the browser
- Install takes the entry's newest release whatever its mod ID or version, so installing `instruments` installs `vsinstrumentsbase`, and installing `carryon` installs a release candidate; the UI labels that release "(Latest)"
- Only version changes are serialized per mod; install, enable, disable and remove can run while one is in progress
- An archive whose `modinfo.json` uses capitalized keys imports with the version "unknown"
- Browse cards show a mod as not installed when its installed mod ID is not the entry's first, and a newly installed mod shows "Unknown" in the Available column
- A Monitor key can read the game server password from the settings API and the config file viewer
- A changed refresh interval does not apply until the API restarts, and Entity Spawning shows "Disabled" when the server config has no value for it
- On a mod detail page the Installed tab does nothing, and a browse link with a page past the end shows an empty page
- The installed mods table scrolls sideways on tablets, the Settings tab list scrolls the page sideways on phones, and the Game Settings title row is wider than the settings panel on wide screens

### Target State

- Nulls in mod database data cannot fail a lookup, a browse page or an update check, and every error state on the detail page leads back to the browser
- Install picks the newest stable release of the mod that was asked for, and "(Latest)" names that release
- Operations on the same mod cannot run into each other; the second one is refused with 409
- Installed status is the same on browse cards, the detail page and the Installed list
- Monitor keys never receive the server password
- Settings take effect as saved and show what the game actually uses
- Mods navigation and layouts work at every width

---

### Story 17.1: Mod Detail Pages Cannot Fail on Bad Data

As an **administrator**,
I want **every mod in the browser to open, whatever the mod database returns for it**,
So that **one odd release does not hide a mod I want to install**.

**Acceptance Criteria:**

**Given** a mod whose releases include one with `"fileid": null` (for example `canjewelry`)
**When** I request `GET /api/v1alpha1/mods/lookup/{slug}`
**Then** the response is 200, every release is listed, and that release has `file_id: null`

*(Covers FR177)*

**Given** a mod database entry or listing item with `null` in any field the API reads, or a `null` element inside `tags`
**When** I look the mod up, browse with each sort, filter by tag, list tags, or run an update check
**Then** each request succeeds, the field has its default value, and null list elements are dropped

*(Covers FR177)*

**Given** the mod database data enters the API
**When** it is read by lookup, browse, search, sort, install and update checks
**Then** it has passed through one normalization step (Epic 17 ADR-1), and no caller relies on `.get(key, default)` to handle a null

*(Covers FR177)*

**Given** a mod detail page that fails to load (API error, unknown mod, or incomplete response)
**When** the error is shown
**Then** it has a Back to Browse link that returns to the browse state the page was opened from, as the loaded page does

*(Covers FR178)*

**Tasks:**

- [ ] Add the mod and release normalizers and apply them where `ModApiClient` receives mod database data (`VSS-a0r`, ADR-1)
- [ ] `ModRelease.file_id: int | None`; `fileId: number | null` in the web types
- [ ] Remove the per-field defaults the normalizers replace in `services/mods.py`, `routers/mods.py` and `services/mod_api.py`; use the release normalizer in `StoredRelease.from_api`
- [ ] Add Back to Browse to `ModDetailError`, reusing `browseTarget` and `MOD_DETAIL_RETURN_STATE` (`VSS-fv7`)
- [ ] Tests: a fixture with the `canjewelry` shape and one with a null in every field, against lookup, browse, each sort, tags and the update check; `ModDetailPage.test.tsx` for the three error states
- [ ] Browser verification: C&N Jewelry opens in the mod browser

---

### Story 17.2: Install Picks the Right Release

As an **administrator**,
I want **Install to give me the newest stable release of the mod I chose**,
So that **I do not end up with a different mod or a pre-release I did not ask for**.

**Acceptance Criteria:**

**Given** a mod database entry that ships several mod IDs (for example `instruments`, `vsinstruments`, `vsinstrumentsbase`)
**When** I install one of them, with or without a version
**Then** only releases with that mod ID are considered, and the installed mod has that mod ID

*(Covers FR179)*

**Given** a mod whose newest release is a pre-release (for example `carryon` with `2.0.0-rc.1`)
**When** I install it without naming a version
**Then** the newest stable release is installed

*(Covers FR180)*

**Given** the same mod
**When** I install it naming the pre-release version
**Then** that pre-release is installed

*(Covers FR180)*

**Given** a mod ID that has only pre-releases
**When** I install it without naming a version
**Then** its newest release is installed

*(Covers FR180)*

**Given** a version that no release of that mod ID has, including one that exists only under another mod ID of the entry
**When** I install naming it
**Then** the response is 404 `MOD_VERSION_NOT_FOUND` and nothing is installed

*(Covers FR179)*

**Given** a release with no file ID
**When** releases are chosen for install
**Then** it is never picked by default, and naming it fails with an error that says the release has no downloadable file, without a download request

*(Covers FR180)*

**Given** a mod's detail page or browse card
**When** I look at the install version list and the "(Latest)" label
**Then** the list holds only the releases of the mod ID that will be installed, "(Latest)" marks the release a plain install picks, and that release is preselected

*(Covers FR181)*

**Tasks:**

- [ ] One release selection function implementing Epic 17 ADR-2, used by `ModApiClient.download_mod` (`VSS-jhf`, `VSS-43b`)
- [ ] Lookup: `latest_version` from the same function, `install_mod_id` in the response, and `_compatibility_modid` defaulting to the install mod ID
- [ ] Web: install section and installed section list and label releases per ADR-2; an install with no chosen version sends no version (check what the API does today with `ModCard`'s `'latest'` string)
- [ ] Tests with `mod_instruments.json` and `mod_carryon.json`, a pre-release-only fixture, and a release without a file ID
- [ ] Browser verification: install `carryon` from a browse card and from its detail page

---

### Story 17.3: Mod Operations Are Safe Against Each Other

As an **administrator**,
I want **two operations on the same mod never to run at the same time**,
So that **a remove or toggle during an update cannot leave the mod half changed**.

**Acceptance Criteria:**

**Given** an install or version change is running for a mod
**When** I install, enable, disable, remove or change the version of the same mod
**Then** the request returns 409 `MOD_OPERATION_IN_PROGRESS`, and the mod's file and state are exactly what the running operation leaves

*(Covers FR182)*

**Given** two install requests for the same mod arrive together
**When** both are processed
**Then** one installs the mod and the other returns 409

*(Covers FR182)*

**Given** an operation is running for one mod
**When** I change a different mod
**Then** it proceeds without waiting

*(Covers FR182)*

**Given** Update All reaches a mod that is busy
**When** its version change is refused
**Then** that mod is reported as failed and the remaining mods are still processed, as today

*(Covers FR182)*

**Given** a mod archive whose `modinfo.json` uses `ModID`, `Version` or other capitalized top-level keys
**When** it is installed, or placed by a version change
**Then** it is imported with its real mod ID and version, and its `modinfo.json` is cached, the same as an archive with lowercase keys

*(Covers FR183)*

**Tasks:**

- [ ] Replace `_version_locks` with one per-mod operation lock used by install, enable, disable, remove and version change (`VSS-8wg`, Epic 17 ADR-3)
- [ ] `ModOperationInProgressError` and `MOD_OPERATION_IN_PROGRESS` (409) on all five routes; remove `MOD_VERSION_CHANGE_IN_PROGRESS`; update Update All's error handling and the API documentation
- [ ] Share the top-level key normalization between `read_modinfo` and `import_mod` (`VSS-0jl`)
- [ ] Tests: hold the lock with a blocked download and call each operation; concurrent installs; an archive with capitalized keys through install and version change

---

### Story 17.4: Installed Status Is Right Everywhere

As an **administrator**,
I want **a mod I have installed to show as installed, with its update status, wherever I see it**,
So that **I do not install a mod twice or wonder whether a new mod is up to date**.

**Acceptance Criteria:**

**Given** a mod database entry with several mod IDs, and I have installed one that is not its first
**When** I see the entry's card in the mod browser
**Then** the card shows Installed, as its detail page does

*(Covers FR184)*

**Given** the browse API
**When** it returns a mod
**Then** the item lists every mod ID of the entry (`mod_ids`), taken from the listing data without a request per mod

*(Covers FR184)*

**Given** I have just installed a mod
**When** I open the Installed list without running an update check
**Then** its Available column shows a real status ("Up to date" or an offered update), computed from the mod database data the install already fetched

*(Covers FR185)*

**Given** a mod with no stored update data (for example one found on disk at startup)
**When** I open the Installed list
**Then** its Available column shows "Not checked yet", not "Unknown"

*(Covers FR185)*

**Tasks:**

- [ ] Add `mod_ids` to `ModBrowseItem` from the listing's `modidstrs`; match installed mods against them on browse cards, reusing `web/src/lib/mod-ids.ts` (`VSS-49n`)
- [ ] After a successful install, store that mod's update record from the lookup the install made; a failure to store it must not fail the install (`VSS-br2`)
- [ ] Label the `not_checked` reason "Not checked yet" in `ModUpdateCell`
- [ ] Tests, including the `instruments` entry on a browse card

---

### Story 17.5: Monitor Keys Cannot Read the Server Password

As a **server owner**,
I want **a Monitor key never to receive the game server password**,
So that **I can hand out read-only access without handing out the password**.

*(Open question settled in this story: redact the password for Monitor, or make the endpoints Admin-only. Recommended default, used by the criteria below: redact (Epic 17 ADR-4), because the PRD gives Monitor read access to configuration (FR21, FR22) limited to non-sensitive data (FR32).)*

**Acceptance Criteria:**

**Given** a Monitor key and a server with a password set
**When** I request `GET /api/v1alpha1/config/game`
**Then** the Password setting has `value: null`, `secret: true` and `configured: true`, and the password appears nowhere in the response

*(Covers FR186)*

**Given** a Monitor key
**When** I request `serverconfig.json` through `GET /api/v1alpha1/config/files/...`, by any path that resolves to that file
**Then** the `Password` value is replaced by `"[redacted]"` when one is set and stays null when none is

*(Covers FR186)*

**Given** an Admin key
**When** I request either endpoint
**Then** the password is returned as today

*(Covers FR186)*

**Given** a Monitor key in the web UI
**When** I open Game Settings
**Then** Password shows "Set" or "Not set" and offers no reveal control

*(Covers FR186)*

**Tasks:**

- [ ] Record the redact-or-restrict choice in the story file before implementing
- [ ] `secret` flag on `ServerSetting`; role-dependent output in `GameConfigService.get_settings` and `ConfigFilesService.read_file`, redacted unless the caller is Admin (`VSS-qed`)
- [ ] Check a server-generated `serverconfig.json` for other secret fields and add any to the list
- [ ] Web: render a secret setting without a value as "Set" or "Not set"
- [ ] Tests for both endpoints and both roles, including alternate paths to `serverconfig.json`

---

### Story 17.6: Settings Behave as Saved

As an **administrator**,
I want **a setting to do what the screen says once I have saved it**,
So that **I do not have to restart the API or guess what the game is using**.

*(Open question settled in this story: VintageStory's default for `EntitySpawning` when `serverconfig.json` has no value. Recommended default, used by the criteria below: on, as `agentdocs/vs-serverconfig-commands.md` states; the story confirms it against a freshly generated server config before relying on it.)*

**Acceptance Criteria:**

**Given** a refresh interval setting with a job running on it
**When** I save a different interval
**Then** the job's next run is one new interval from the save, without restarting the API, and Scheduled Jobs shows the new interval

*(Covers FR187)*

**Given** a refresh interval above 0
**When** I save 0
**Then** its job is removed and no longer runs

*(Covers FR187)*

**Given** a refresh interval of 0
**When** I save a value above 0
**Then** its job is registered with that interval

*(Covers FR187)*

**Given** a boolean game setting that has no value in `serverconfig.json`
**When** I open Game Settings
**Then** the switch shows the game's default for that setting and is labeled as the default (for Entity Spawning: "Enabled (default)"), not "Disabled"

*(Covers FR188)*

**Given** a boolean setting whose game default is not known to the manager
**When** it has no value
**Then** it is shown as "Not set", with neither Enabled nor Disabled implied

*(Covers FR188)*

**Given** I switch such a setting
**When** it is saved
**Then** the explicit value is written and the "default" label goes away

*(Covers FR188)*

**Tasks:**

- [ ] One function that applies an interval setting to the scheduler, used at startup and passed as `scheduler_callback` (`VSS-8bl`, Epic 17 ADR-5); covers `mod_list_refresh_interval`, `server_versions_refresh_interval` and `metrics_collection_interval`
- [ ] Confirm the game's default for each boolean setting the manager shows; return it with the setting (`default`) and render null booleans from it (`VSS-2le`)
- [ ] Tests: each interval transition for each setting; null booleans with and without a known default
- [ ] Browser verification on a config without `EntitySpawning`, restoring every changed setting

---

### Story 17.7: Mods Navigation

As an **administrator**,
I want **the Mods tabs and shared browse links to take me where they say**,
So that **I am not stuck on a detail page or looking at an empty page**.

**Acceptance Criteria:**

**Given** I am on a mod detail page
**When** I look at the Mods tabs
**Then** Browse is the active tab

*(Covers FR189)*

**Given** I am on a mod detail page
**When** I click Installed
**Then** the Installed tab opens

*(Covers FR189)*

**Given** I am on a mod detail page
**When** I click Browse
**Then** the browser opens with the state Epic 16 ADR-1 defines: the state the page was opened from, otherwise the last browse state of the session, otherwise the default

*(Covers FR189)*

**Given** a browse URL whose `page` is beyond the last page of its results
**When** the first response arrives
**Then** the URL is replaced by the last page (page 1 when there are no results) without a new history entry, and that page's mods are shown

*(Covers FR190)*

**Given** a browse URL with a valid page
**When** it loads
**Then** it is requested directly, with no extra request

*(Covers FR190)*

**Tasks:**

- [ ] `getActiveTab`: treat `/game-server/mods/browse/...` as Browse; keep the Browse tab navigating from a detail page although it is the active value (`VSS-2oz`)
- [ ] Clamp the page after the first response, with `replace` (`VSS-nhb`)
- [ ] Tests in `ModsPage.test.tsx` for both tabs on a detail page and in `BrowseTab.test.tsx` for `?page=9999`; update the detour in `web/e2e/mod-browse-state.spec.ts` to use the Installed tab

---

### Story 17.8: Layout at Tablet and Phone Widths

As an **administrator**,
I want **pages to fit the screen I am using**,
So that **I do not scroll sideways to reach a control**.

**Acceptance Criteria:**

**Given** a viewport from 768px to 1023px wide
**When** I open Installed mods, including with an update offered
**Then** nothing scrolls sideways, and each mod's version, update status and Update action, enable toggle and remove action are reachable

*(Covers FR191)*

**Given** a viewport of 1024px or wider, or narrower than 768px
**When** I open Installed mods
**Then** the table and the phone cards are unchanged

*(Covers FR191)*

**Given** a 390px wide viewport
**When** I open Settings and each of its tabs
**Then** the page does not scroll sideways and every tab can be reached

*(Covers FR192)*

**Given** a viewport of 1560px or wider
**When** I open Game Settings
**Then** the title and the server status badge sit within the same centered 1280px width as the settings panel

*(Covers FR193)*

**Tasks:**

- [ ] Installed mods between `md` and `lg`: follow the UX spec's tablet rule (fewer columns, update shown inline), choosing between hiding columns and using the cards up to `lg` (`VSS-dp1`)
- [ ] Settings `TabsList`: wrap or scroll inside itself on small screens (`VSS-uni`)
- [ ] Constrain the Game Settings header to the panel's maximum width, in all three states of `SettingsPage` (`VSS-143`)
- [ ] Tests, and browser measurements at 390px, 768px, 900px, 1024px and 1920px

---

## Epic 18: Mod Media and Fixes

**Goal:** Admins can see a mod's screenshots and trailer before installing it and tell from a browse card whether it has a release for their game version, and installing, changing versions and the Installed list behave correctly in the cases Epic 17 left open.

**Architecture:** `architecture/epic-18-mod-media-and-fixes.md` (ADR-1 to ADR-6, with the mod database facts checked on 2026-11-16). There is no preparation story. Story 18.4 measures the table's columns before it settles the Name column's width.

**Order:** Story 18.1 first, because the maintainer wants the gallery most. Then 18.2 (it holds the only bug, `VSS-z7e`, P2), 18.3 and 18.4.

**Dependencies:** No story needs another's code. Stories 18.1, 18.2 and 18.3 each edit `routers/mods.py`, `models/mods.py` and `web/src/api/types.ts` in different places, so run them one after another or expect small merge conflicts. Story 18.4 is web only and touches none of their files.

### Current State

- The mod detail page shows the logo and description only; the mod database's screenshots and trailer are dropped by the API
- Description links open in a new tab with nothing to say so
- Installing a mod whose file name another installed mod already uses replaces that mod's file, and a failed import then deletes it
- After a version change to a release newer than the last update check, the Installed list shows "Unknown" until the next check
- Browse cards say nothing about the installed game version
- Below 1024px the installed mod cards can only be re-sorted by widening the window to reach the table headers
- At 1024px a long mod name makes the installed mods table scroll inside itself, with the toggle and remove button off screen

### Target State

- A mod's screenshots and trailer link are on its detail page, from URLs the API has checked
- Description links show that they open in a new tab
- An install never overwrites another mod's file, and a version change leaves a correct update status behind
- Browse cards show whether the mod has a release for the installed game version, without a request per card
- The Installed list can be sorted and fits its container at every width

---

### Story 18.1: Mod Detail Page Media and Links

**Sprint key:** `18-1-mod-detail-media-and-links`
**Beads:** `VSS-l4x` (UI-083), `VSS-tzl` (UI-078)
**FRs:** FR194, FR195, FR196, FR197, FR198

As an **administrator**,
I want **to see a mod's screenshots and trailer on its detail page**,
So that **I can judge a mod before installing it without leaving the manager**.

**Acceptance Criteria:**

**Given** a mod with screenshots in the mod database (for example `betterruins`, 10)
**When** I request `GET /api/v1alpha1/mods/lookup/{slug}`
**Then** the response has `screenshots`, one item per screenshot in the mod database's order, each with `image_url`, `thumbnail_url` and `filename`

*(Covers FR194, FR197)*

**Given** a screenshot whose image URL is not `https` on `moddbcdn.vintagestory.at`, a null element, or a `screenshots` value that is not a list
**When** I look the mod up
**Then** the response is 200, that screenshot is left out, and a screenshot with a missing or rejected thumbnail uses its image URL as the thumbnail

*(Covers FR197)*

**Given** a mod whose trailer field is a YouTube URL in any accepted form (for example `https://www.youtube-nocookie.com/watch?v=mJHZH_sThDM`)
**When** I look the mod up
**Then** `trailer_url` is `https://www.youtube-nocookie.com/embed/<id>` (maintainer decision 2026-11-16; planned as `https://www.youtube.com/watch?v=<id>`); for an empty, null or any other URL (for example `https://apachegaming.net`) it is `null`

*(Covers FR196, FR197)*

**Given** a mod with several screenshots
**When** I open its detail page
**Then** a Screenshots section shows one image, its position ("3 of 10"), Previous and Next, and a strip of thumbnails; choosing a thumbnail or Previous/Next changes the image

*(Covers FR194)*

**Given** the Screenshots section
**When** I activate the current image
**Then** it opens larger in a dialog that I can step through and close

*(Covers FR194)*

**Given** a keyboard only
**When** I tab to the gallery
**Then** every thumbnail and control can be focused and activated, Left and Right move between images in the section and in the dialog, and Escape closes the dialog and returns focus to the gallery

*(Covers FR195)*

**Given** a 390px wide touch screen, in the light and the dark theme
**When** I open the detail page of a mod with screenshots
**Then** the page does not scroll sideways, Previous and Next are at least 44px targets, and the thumbnail strip scrolls inside itself

*(Covers FR195)*

**Given** the gallery
**When** it renders
**Then** each image has alt text built from its file name, images are lazy-loaded, only the current image's full-size file is requested, and no request carries a referrer

*(Covers FR195)*

**Given** a mod with no screenshots (for example `playercorpse`) or with one
**When** I open its detail page
**Then** with none there is no Screenshots section, and with one there are no Previous, Next or thumbnail controls

*(Covers FR194)*

**Given** a mod with a trailer
**When** I open its detail page
**Then** a "Watch trailer" link opens the video in a new tab with `rel="noopener noreferrer"`, and the page loads no iframe and nothing from YouTube

*(Covers FR196)*

**Given** a mod description with links
**When** I read it
**Then** each link shows an external-link icon, and a screen reader hears "(opens in a new tab)" after the link's own text

*(Covers FR198)*

**Tasks:**

- [ ] `SCREENSHOT_FIELDS`, `screenshots` and `trailervideourl` in `models/moddb.py` (Epic 18 ADR-1 decision 1)
- [ ] `services/mod_media.py`: the image URL allow-list and the trailer rewrite (ADR-1 decision 2, ADR-2 decision 2); `ModScreenshot`, `screenshots` and `trailer_url` on `ModLookupResponse`; web types
- [ ] Gallery component from `Dialog`, `Button` and plain `<img>`; no new dependency (ADR-2 decisions 5 and 6) (`VSS-l4x`)
- [ ] "Watch trailer" link beside the other external links (ADR-2 decisions 1 and 4)
- [ ] Mark description links in `lib/mod-description.ts` and the description's styles (`VSS-tzl`)
- [ ] Tests: normalizer and URL rules with a `betterruins`-shaped fixture and a synthetic bad-data fixture; component tests for navigation, none, one, keyboard and the dialog; `mod-description.test.ts` for the link marking
- [ ] E2E against a stubbed mod with several screenshots at desktop and 390px; browser check of `betterruins` in both themes

---

### Story 18.2: Install and Version Change Keep Files and Records Right

**Sprint key:** `18-2-install-and-version-change-keep-records-right`
**Beads:** `VSS-z7e` (API-075, bug), `VSS-do7` (API-076)
**FRs:** FR199, FR200

As an **administrator**,
I want **installing or changing one mod never to damage another mod or leave a wrong status behind**,
So that **I can trust the Installed list after every operation**.

**Acceptance Criteria:**

**Given** mod A is installed as `Foo.zip`
**When** I install mod B, whose release file is also named `Foo.zip`
**Then** the response is 409 `MOD_FILE_CONFLICT` with a message naming `Foo.zip`, A's file has the same bytes as before, A's state entry is unchanged, and no `.tmp` file is left

*(Covers FR199)*

**Given** mod A is disabled, so its file is `Foo.zip.disabled`
**When** I install mod B, whose release file is named `Foo.zip`
**Then** the response is 409 `MOD_FILE_CONFLICT` and nothing is placed

*(Covers FR199)*

**Given** a file named like the download exists in the mods directory but belongs to no known mod, or the mod state has an entry under that file name with no file
**When** I install the mod
**Then** the response is 409 `MOD_FILE_CONFLICT` and nothing is placed or removed

*(Covers FR199)*

**Given** a download whose `modinfo.json` cannot be read, with a file name another mod uses
**When** I install it
**Then** the response is 409 `MOD_FILE_CONFLICT`

*(Covers FR199)*

**Given** no file-name collision, and the import or state save fails after the file is placed
**When** the install cleans up
**Then** only the newly placed file and its own state entry are removed, as today

*(Covers FR199)*

**Given** an installed mod whose stored update record does not list a release the mod database now has
**When** I change the mod to that release from its detail page
**Then** `GET /api/v1alpha1/mods/updates` reports a real status for it ("up to date" or an offered update), not `unknown` with reason `installed_release_not_listed`, without an update check

*(Covers FR200)*

**Given** a version change through `PUT /api/v1alpha1/mods/{slug}/version`
**When** it succeeds
**Then** the response has exactly the keys `slug`, `previous_version`, `version`, `filename`, `compatibility`, `changed` and `pending_restart`, as before

*(Covers FR200)*

**Given** Update All changes several mods
**When** it finishes
**Then** each changed mod's stored record comes from its own change

*(Covers FR200)*

**Given** storing the record fails, or the version change fails or is rolled back, or the requested version is already installed
**When** the request ends
**Then** a storing failure does not fail the version change, and in the other cases the stored record is untouched

*(Covers FR200)*

**Tasks:**

- [ ] `ModFileConflictError` and the check at the start of `_place_install` (Epic 18 ADR-4) (`VSS-z7e`)
- [ ] `ErrorCode.MOD_FILE_CONFLICT`, 409 on `POST /mods`; route docstring and API documentation
- [ ] Confirm the web shows the API's message for a failed install; no other web change
- [ ] `PreparedVersionChange.releases`, the `record_releases` parameter of `change_version`, and `ModUpdateService.record_releases` with `record_install` delegating to it (ADR-5) (`VSS-do7`)
- [ ] Pass the recorder from the version change route and the Update All route
- [ ] Tests: the four collision cases with file bytes and state compared before and after; a failing import after a clean placement; the version change record cases, including the response key set

---

### Story 18.3: Game Version Badge on Browse Cards

**Sprint key:** `18-3-game-version-badge-on-browse-cards`
**Beads:** `VSS-4f3` (UI-068)
**FRs:** FR201, FR202

As an **administrator**,
I want **each mod browser card to tell me whether the mod has a release for my game version**,
So that **I do not open mod after mod to find the ones I can use**.

**Acceptance Criteria:**

**Given** a game server is installed and its version has a tag in the mod database
**When** I request `GET /api/v1alpha1/mods/browse`
**Then** the response has `game_version` set to the installed version, and every item has `has_release_for_game_version` `true` or `false`

*(Covers FR201)*

**Given** two browse requests within the cache lifetime, for any pages, sorts or filters
**When** they are served
**Then** the mod database receives at most one filtered listing request for the installed version and no request per mod

*(Covers FR201)*

**Given** a card whose flag is `true`
**When** I see it
**Then** it shows "Has a release for 1.22.7" (with the installed version), and a card whose flag is `false` shows "No release for 1.22.7"; neither uses the words "Compatible" or "Incompatible"

*(Covers FR201)*

**Given** no game server is installed, or the installed version has no tag in the mod database
**When** I browse
**Then** the response is 200 with `game_version: null` and every flag `null`, and the cards show no game version indicator

*(Covers FR202)*

**Given** the mod database fails or times out on the filtered listing
**When** I browse
**Then** the response is 200; the flags come from the last copy for that version when one exists and are `null` otherwise

*(Covers FR202)*

**Given** I install a different game server version
**When** I browse again
**Then** the flags and `game_version` are for the new version on the next request, without restarting the API

*(Covers FR201)*

**Given** I pick a game version in the browse filter
**When** I change pages
**Then** the filtered listing is served from the same cache, and the cards' flags still refer to the installed version

*(Covers FR201)*

**Tasks:**

- [ ] Cache filtered listings per tag ID in `ModApiClient`, with the `modid` set, a three-entry limit and the browse cache lifetime (Epic 18 ADR-3 decisions 1 and 2) (`VSS-4f3`)
- [ ] Browse route: resolve the installed version, fetch concurrently when cold, fall back as ADR-3 decision 5 says; `has_release_for_game_version` and `game_version` in the models
- [ ] Web types and the card indicator (ADR-3 decision 9); remove `getBrowseCardCompatibility` and its test
- [ ] Tests: route cases for true, false, no server, untagged version, failure with and without an earlier copy, and a changed version; client cache tests for lifetime and the entry limit; `ModCard` tests for the three states
- [ ] Browser check on the dev stack: `carryon` shows the badge and `playercorpse` shows "No release" on 1.22.7

---

### Story 18.4: Installed Mods List at Every Width

**Sprint key:** `18-4-installed-mods-list-at-every-width`
**Beads:** `VSS-bgu` (UI-077), `VSS-n2u` (UI-086)
**FRs:** FR203, FR204

As an **administrator**,
I want **to sort my installed mods and reach every control at any window width**,
So that **the list is as usable on a tablet or a small laptop as on a wide screen**.

**Acceptance Criteria:**

**Given** a viewport narrower than 1024px
**When** I open Installed mods
**Then** a sort control above the cards shows the current sort column (Name, Version or Status) and direction

*(Covers FR203)*

**Given** the sort control
**When** I choose another column or flip the direction
**Then** the cards reorder at once, and the choice is still there after a reload

*(Covers FR203)*

**Given** I sorted the cards by Version descending
**When** I widen the window to 1024px or more
**Then** the table is sorted by Version descending with its header showing it, and a sort made on a table header is the cards' sort when I narrow the window again

*(Covers FR203)*

**Given** a viewport of 1024px or wider
**When** I open Installed mods
**Then** there is no separate sort control; the table headers sort as today

*(Covers FR203)*

**Given** a 1024px viewport, sidebar expanded or collapsed, and a mod with a 63-character name and an offered pre-release update
**When** I open Installed mods
**Then** the table does not scroll inside its container, the page does not scroll sideways, the name wraps, and the mod's enable toggle and remove button are inside the viewport

*(Covers FR204)*

**Given** a viewport of 1440px or wider, or only mods with short names
**When** I open Installed mods
**Then** each row is on one line, as today

*(Covers FR204)*

**Given** the other tables in the app (Scheduled Jobs, Version)
**When** this story is done
**Then** their cells still do not wrap

*(Covers FR204)*

**Tasks:**

- [ ] Sort control in `ModTable` above the cards, writing `installedModsSort` through `setInstalledModsSort` (Epic 18 ADR-6, sort) (`VSS-bgu`)
- [ ] Extend `layout_widths.mjs` to record each column's width at 1024px; keep the before numbers
- [ ] Wrap the Name column through its column `meta.className`, applied to body cells too; choose the minimum width from the measurements; stack the Available cell only if the numbers require it (ADR-6, long names) (`VSS-n2u`)
- [ ] Tests: `ModTable.test.tsx` for the control and the shared preference; `layout-widths.spec.ts` now expects no scrolling element at 1024px in both sidebar states
- [ ] Record the after measurements in the story file

---

## Epic 19: API Security and Mod File Safety

**Goal:** Only the Admin role, and only someone the operator chose to give the Admin key to, can read secrets or act as Admin; every page the manager serves runs under a Content-Security-Policy; no mod operation can replace or lose a mod's file; nothing the mod database sends reaches a link, an image or a 500; and the browser tests run on every pull request.

**Architecture:** `architecture/epic-19-api-security-and-mod-file-safety.md` (ADR-1 to ADR-14, with the code facts at `048fea9` and the mod database facts checked on 2026-11-16). There is no preparation story. Story 19.3 confirms two browser behaviours before it settles the policy (ADR-6 decisions 7 and 12).

**Revised 2026-11-17** after the maintainer's review: seven follow-up beads found in planning were folded in, and `VSS-9wv` became its own story (19.2). Six stories, eighteen beads.

**Revised again 2026-11-17:** Matt decided four observations from the first revision, and each is written into a story: the mod state is reconciled with the mods directory at start-up (new Story 19.5, so the two later stories moved down one), CI seeds a `serverconfig.json` so the settings specs run (19.7), `main.py` uses one settings object and the app can be built with chosen settings in tests (19.2 and 19.3), and the file browser tells a role other than Admin that some folders are hidden (19.1). Seven stories, eighteen beads; Story 19.5 has no bead of its own.

**Order:** 19.1, 19.2, 19.3, 19.4, 19.5, 19.6, 19.7.

**Dependencies:**

- Story 19.2 needs no other story's code. It comes second so the breaking change is on `main` early and the release that carries it can be prepared.
- Story 19.3 comes after 19.2: its E2E spec loads every page with a key through the `/config.js` helper Story 19.2 adds, and both stories edit `register_frontend` in `main.py` and `config.py`.
- Story 19.3 also builds on the app construction Story 19.2 introduces (ADR-5 decision 11, ADR-7 decision 6).
- Story 19.5 comes directly after 19.4: its sync runs after 19.4's start-up recovery and relies on 19.4's working-file suffixes, and it edits the same files (`services/mod_state.py`, `services/mods.py`, the start-up in `main.py`).
- Stories 19.4 and 19.6 need no other story's code. Both edit `services/mods.py` and `services/mod_api.py` in different places, so run them one after another.
- Story 19.7 comes last: it uses Story 19.2's helper and key handling, and puts the specs of Stories 19.2 and 19.3 into CI.
- Stories 19.1 and 19.2 both edit `config.py`, `.env.example` and the compose files (`VS_GAME_VERSION` in 19.1, `VS_API_KEY` in 19.2); run them one after another.

**Breaking change:** Story 19.2 stops handing the Admin key to the web UI when `VS_API_KEY` is unset (ADR-5). Every deployment that does not set `VS_API_KEY` must set it when it upgrades, including the maintainer's cluster deployment, which is configured in another repository and is not changed by this epic.

**Size:** Story 19.4 carries six beads, all in the mod file code. Its six tasks are at the project's limit; `create-story` should not add to them. That is why the start-up sync is Story 19.5 and not a seventh task.

### Current State

- A Monitor key can ask the config file viewer for any file under the server data directory; binary files and directories answer 500
- A Monitor key receives nested passwords and secrets under other key names in config files, can list `Saves`, `Backups` and `Playerdata`, and can read the player files
- `VS_GAME_VERSION` is documented and set in the compose files and does nothing
- With `VS_API_KEY` unset, anyone who can load the web UI receives the Admin key, and nothing tells the operator
- The web UI's pages have no Content-Security-Policy, and `/docs`, `/redoc` and `/openapi.json` are served to anyone, loading scripts from a public CDN
- Enabling or disabling a mod can replace another mod's file, and is a 500 when the mod's own file is gone; a version change refuses a taken name with a 500; the install check depends on the volume's case rules
- A crash during an install or version change leaves `.tmp` or `.bak` files that nothing recovers
- Two mods whose releases share a file name share one cache file, and two such downloads at once write one temporary file
- Logo, homepage and source URLs from the mod database reach `src` and `href` unchecked
- A mod database answer that is not a JSON object makes the mod browser answer 500, and several first requests each download the whole listing
- A mod file added or deleted by hand never reaches the Installed list: `sync_state_with_disk` exists and nothing calls it
- The E2E specs run only on a developer's machine, and fifteen of them carry an init script that does nothing

### Target State

- The config file viewer serves `.json` files only, and roles other than Admin see the root files and `ModConfig` only, with secrets redacted at every depth
- `VS_GAME_VERSION` is gone from the settings and the documentation
- The web UI gets a key only when `VS_API_KEY` names one; the API warns when that key is the Admin key and when there is none
- The web UI's pages are served with an enforced Content-Security-Policy and every page works under it; the API documentation pages are served only in debug mode
- Install, enable, disable and version change refuse a taken file name with 409 `MOD_FILE_CONFLICT`, ignoring case; a missing mod file is 409 `MOD_FILE_MISSING`; start-up recovers interrupted operations; the download cache is keyed by file ID
- The Installed list matches the mods directory after every start
- Only checked `https` URLs leave the API, a malformed mod database answer is a 502, and cold caches are filled by one request
- CI starts the built image with a seeded `serverconfig.json` and runs every E2E test that needs nothing outside it, the settings specs included

---

### Story 19.1: Secrets Stay with Admin

**Sprint key:** `19-1-secrets-stay-with-admin`
**Beads:** `VSS-633` (API-077, bug), `VSS-sg1` (API-078, bug), `VSS-3hs2` (API-089), `VSS-ms0` (API-070)
**FRs:** FR205, FR206, FR207, FR208, FR209, FR233

As an **operator who gives other people Monitor access**,
I want **secrets and player data to reach only the Admin role**,
So that **read-only access stays read-only**.

**Acceptance Criteria:**

**Given** a `.json` file in the root of the server data directory or under `ModConfig`
**When** I request `GET /api/v1alpha1/config/files/{path}` with an Admin or a Monitor key
**Then** the response is 200 with its content, and `GET /config/files` lists exactly the files that can be read this way

*(Covers FR205)*

**Given** a path whose name does not end in `.json` (a log, a zip, a text file), existing or not, in a directory the key's role may read
**When** I request it with either key
**Then** the response is 400 `CONFIG_FILE_NOT_SUPPORTED` and the file is not read

*(Covers FR205, FR206)*

**Given** a directory, a directory named `x.json`, a symlink `x.json` to a file of another type, or a `.json` file that is not UTF-8 text, in a directory the key's role may read
**When** I request it with either key
**Then** the response is 400 `CONFIG_FILE_NOT_SUPPORTED`, never a 500

*(Covers FR206)*

**Given** a `.json` file larger than 2 MiB
**When** I request it with either key
**Then** the response is 413 `CONFIG_FILE_TOO_LARGE` and the file is not read into memory

*(Covers FR206)*

**Given** a `.json` file that starts with a byte order mark, and one that is UTF-8 and not valid JSON or is nested too deeply to parse
**When** I request them
**Then** the first is parsed, and the second is 200 with `_raw` and `_parse_error`, the text only for Admin

*(Covers FR206)*

**Given** a config file with `{"Other": {"Password": "x"}}`, a list of objects with `Token` or `ApiKey` keys, and a key such as `bot_token` or `WebhookUrl`
**When** I read it with a Monitor key
**Then** each of those values is `"[redacted]"` at every depth, a `null` or `""` value stays as it is, and the secret is nowhere in the raw response body

*(Covers FR207)*

**Given** `serverconfig.json` with `StartupCommands` set, and a config file with a string value that is a URL with user info or a Discord webhook URL under any key name
**When** I read them with a Monitor key
**Then** those values are `"[redacted]"`

*(Covers FR207)*

**Given** the same files
**When** I read them with the Admin key
**Then** every value is returned unchanged

*(Covers FR207)*

**Given** a Monitor key
**When** I request `GET /api/v1alpha1/config/directories` for the root of the server data directory
**Then** the response lists `ModConfig` when it exists and no other directory; with the Admin key it lists every directory, as before

*(Covers FR208)*

**Given** a Monitor key
**When** I request the listing of, the files in, or a `.json` file in `Playerdata`, `Saves`, `Backups` or any directory other than `ModConfig`, in any letter case, existing or not
**Then** the response is 403 `FORBIDDEN` with a message that the directory needs the Admin role

*(Covers FR208)*

**Given** a Monitor key
**When** I read a `.json` file in the root or anywhere under `ModConfig`, and a symlink under `ModConfig` that resolves into another directory
**Then** the first is 200 with secrets redacted, and the second is 403 `FORBIDDEN`

*(Covers FR208)*

**Given** a Monitor key in the web UI
**When** I open the file browser
**Then** it shows the note "Some folders are only shown to Admin keys.", which names no folder and gives no count; with the Admin key, or while the role is not yet known, the note is not shown

*(Covers FR233)*

**Given** a deployment that still sets `VS_GAME_VERSION`
**When** the API starts
**Then** it starts as before; the variable is no longer a setting and is not in the compose files, `.env.example` or the worktree set-up script

*(Covers FR209)*

**Tasks:**

- [ ] Config file viewer: one predicate for the listing and the read; suffix, type, size and decoding checks; `CONFIG_FILE_NOT_SUPPORTED` and `CONFIG_FILE_TOO_LARGE` (Epic 19 ADR-1) (`VSS-633`)
- [ ] Recursive redaction by key name with `UNMANAGED_SECRET_KEYS`, `SECRET_KEY_FRAGMENTS` and the two value rules; replace `test_nested_password_is_unchanged` (ADR-2) (`VSS-sg1`)
- [ ] The role's directories: `MONITOR_CONFIG_DIRECTORIES`, filtered listings and 403 on the three config file routes, checked on the resolved path (ADR-3) (`VSS-3hs2`)
- [ ] Remove `Settings.game_version` and every `VS_GAME_VERSION` line; test that setting it is harmless; committed as `fix(docker):` (ADR-4) (`VSS-ms0`)
- [ ] Web: the static note in `FileManagerPanel` for a role other than Admin, from `useAuthMe()` as `SettingsPage` does; component tests for Monitor, Admin and the loading state; confirm the file browser shows a Monitor only what the API lists (ADR-3 decision 9; Matt, 2026-11-17)
- [ ] Tests for both roles with the raw response body checked; API documentation and README (what the Monitor role can read)

---

### Story 19.2: The Web UI No Longer Gets the Admin Key

**Sprint key:** `19-2-web-ui-no-longer-gets-the-admin-key`
**Beads:** `VSS-9wv` (API-079)
**FRs:** FR210, FR211, FR212
**Breaking change.**

As an **operator whose web UI can be reached by people who are not admins**,
I want **the web UI to receive a key only when I name one**,
So that **opening the page does not hand out the Admin key**.

**Acceptance Criteria:**

**Given** `VS_API_KEY` is unset or blank
**When** the API starts
**Then** it starts, `/healthz` and `/readyz` answer as before, it logs the warning `web_api_key_not_set` without any key, and `GET /config.js` serves `{"apiKey": ""}` with the same headers as before

*(Covers FR210, FR211)*

**Given** the web UI is loaded and `/config.js` serves no key
**When** the page opens
**Then** it shows a "No API key configured" screen that names `VS_API_KEY`, the Monitor key and the Admin key, and it makes no request to `/api/` and opens no WebSocket

*(Covers FR210)*

**Given** `VS_API_KEY` equals the Admin key
**When** the API starts
**Then** `/config.js` serves the Admin key and the API logs the warning `web_api_key_is_admin_key` without the key

*(Covers FR211)*

**Given** `VS_API_KEY` equals the Monitor key, or matches neither key
**When** the API starts
**Then** with the Monitor key `/config.js` serves it and neither new warning is logged; with a key that matches no role the existing `web_api_key_matches_no_role` warning is logged, as before

*(Covers FR211)*

**Given** the README, `.env.example` and both compose files
**When** I read how to give the web UI a key
**Then** they say the web UI needs `VS_API_KEY`, recommend the Monitor key or an authenticating proxy, say that anyone who can load the page receives that key, and the production compose example does not hand out the Admin key by default

*(Covers FR212)*

**Given** the dev stack started with `just docker start` and no `VS_API_KEY` in the environment
**When** I open the web UI or run the E2E specs
**Then** the page has the Admin key as before, because the dev compose file sets `VS_API_KEY` to the Admin key itself

*(Covers FR212)*

**Given** the API tests
**When** they need the app in one of the four `VS_API_KEY` states
**Then** they build the app with those settings through the app factory, and each start-up warning is asserted both ways: logged in its state and not logged in the others

*(Covers FR211)*

**Given** the commit that removes the fallback
**When** the release notes are generated with `just changelog`
**Then** the change is listed under Breaking Changes and its line says to set `VS_API_KEY` to the Monitor or the Admin key

*(Covers FR212)*

**Tasks:**

- [ ] `main.py`: an app factory that takes the settings, with the lifespan using the cached `get_settings()` instead of a new `Settings()` (ADR-5 decision 11; Matt, 2026-11-17)
- [ ] `Settings.web_api_key` without the fallback, one function for the four start-up states, the two new warnings, `/config.js` with an empty key; committed as `feat(api)!:` with a `BREAKING CHANGE:` footer and the subject of ADR-5 "Release" (`VSS-9wv`)
- [ ] Web: the "No API key configured" screen, shown before any request (ADR-5 decision 4)
- [ ] `docker-compose.dev.yaml` default, `docker-compose.yaml` comment, `.env.example`, README (ADR-5 decisions 6 and 7)
- [ ] E2E: one `/config.js` helper in `web/e2e/` and the empty-key spec, written to run without the mod database (ADR-5 decision 8)
- [ ] API tests for `/config.js` and the start-up log in the four states, each from an app built with those settings; `just changelog` checked for the breaking entry

---

### Story 19.3: Content-Security-Policy and API Docs

**Sprint key:** `19-3-content-security-policy-and-api-docs`
**Beads:** `VSS-3qb8` (INFRA-005), `VSS-my4c` (UI-102), `VSS-5mes` (API-088)
**FRs:** FR213, FR214, FR215, FR216, FR217

As an **operator**,
I want **every page the manager serves to run under a Content-Security-Policy**,
So that **an injected script cannot run on an origin that holds an API key**.

**Acceptance Criteria:**

**Given** the published image
**When** I request `/` or any web UI path
**Then** the response has `Content-Security-Policy` with exactly the directives of Epic 19 ADR-5 decision 3, and `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`

*(Covers FR213, FR215)*

**Given** the same image
**When** I request `/api/v1alpha1/...`, `/healthz` or `/readyz`
**Then** the response has no `Content-Security-Policy` header

*(Covers FR213)*

**Given** the Docker stack with the policy enforced
**When** I open the dashboard, the console, the mod browser, a mod detail page with a gallery and a description with images, the installed list, the settings and the version page, in the light and the dark theme
**Then** each page works as before, the browser reports no `securitypolicyviolation` event and no console error, and toasts, dialogs and the terminal are styled

*(Covers FR214)*

**Given** the console page with the policy enforced
**When** it connects
**Then** the console WebSocket and the log stream connect and carry data

*(Covers FR214)*

**Given** a page of the web UI with the policy enforced
**When** an inline script is injected into it, or the page is loaded inside a frame on another origin
**Then** the script does not run and the frame does not load

*(Covers FR213)*

**Given** a mod description with an image on any `https` host
**When** I open the mod's detail page
**Then** the image loads

*(Covers FR214)*

**Given** `VS_CSP_MODE=report-only`, `VS_CSP_MODE=off`, and an unknown value
**When** the API starts
**Then** with `report-only` the same policy is sent as `Content-Security-Policy-Report-Only`, with `off` neither header is sent, and an unknown value stops start-up with a message naming the setting

*(Covers FR215)*

**Given** the Vite dev server (`just dev-web`)
**When** I develop
**Then** no policy applies and hot reload works as before

*(Covers FR214)*

**Given** a mod description with an `<img>` whose address is `http:`, relative, or anything other than `https:` or a `data:image/` URL
**When** I open the mod's detail page
**Then** the image is replaced by the text "Image not shown" with its alt text, no request is made for it, no broken-image icon is shown, and the browser reports no policy violation

*(Covers FR216)*

**Given** the image started without `VS_DEBUG=true`
**When** I request `/docs`, `/redoc` or `/openapi.json`
**Then** none of them serves the API documentation or the schema, and no response from the manager loads a script from another origin

*(Covers FR217)*

**Given** the API started with `VS_DEBUG=true`
**When** I open `/docs`
**Then** the API documentation renders as before, without the web UI's policy

*(Covers FR217)*

**Given** the API tests
**When** they check the documentation paths and the RBAC test routes
**Then** they build one app with debug on and one with debug off through the app factory and assert both, and `main.py` no longer calls `Settings()` itself

*(Covers FR217)*

**Tasks:**

- [ ] `VS_CSP_MODE` in `Settings` with validation; the policy as one constant; the headers on `serve_spa` responses (Epic 19 ADR-6 decisions 1, 3, 9 and 10) (`VSS-3qb8`)
- [ ] Browser checks first: the WebSockets under `connect-src 'self'` and the next-themes inline script (ADR-6 decisions 7 and 12); record what was seen and any hash added
- [ ] Sanitizer: replace description images that are not `https:` or `data:image/` (ADR-6 decision 14) (`VSS-my4c`)
- [ ] `docs_url`, `redoc_url` and `openapi_url` off unless debug, set in the app factory; the CORS and RBAC-router `Settings()` calls in `main.py` moved to the same settings object; adapt `test_version.py`; the commit subject names the change for the release notes (ADR-7, decision 6; Matt, 2026-11-17) (`VSS-5mes`)
- [ ] API tests: the headers in each mode and on which routes, the documentation paths with debug off and on; `mod-description.test.ts` for the image rule
- [ ] E2E spec against the Docker stack with stubbed mod data: every page in both themes with no violation, and the blocked inline script (ADR-6 decision 13); README and `.env.example`

---

### Story 19.4: Mod Files Are Never Overwritten

**Sprint key:** `19-4-mod-files-are-never-overwritten`
**Beads:** `VSS-40ja` (API-082, bug), `VSS-macf` (API-083), `VSS-52fy` (API-085), `VSS-n0qv` (API-084), `VSS-yhmt` (API-091, bug), `VSS-uoxl` (API-092; stays open until Story 19.5, which rides with it)
**FRs:** FR218, FR219, FR220, FR221, FR222, FR223

As an **administrator**,
I want **no mod operation to replace or lose a mod's file, on any volume and after a crash**,
So that **the mods directory always holds what the Installed list says**.

**Acceptance Criteria:**

**Given** mod A is disabled as `Foo.zip.disabled` and another file `Foo.zip` is in the mods directory
**When** I enable mod A
**Then** the response is 409 `MOD_FILE_CONFLICT` with a message naming `Foo.zip`, both files have the same bytes as before, the mod state is unchanged and no restart is pending

*(Covers FR218)*

**Given** mod A is enabled as `Foo.zip` and a file `Foo.zip.disabled` is in the mods directory
**When** I disable mod A
**Then** the response is 409 `MOD_FILE_CONFLICT` and nothing is changed

*(Covers FR218)*

**Given** no file is in the way
**When** I enable or disable a mod
**Then** it works as before, and enabling an enabled mod or disabling a disabled one is still a success that changes nothing

*(Covers FR218)*

**Given** an installed mod and a target release whose file name, or its `.disabled` form, is another file in the mods directory or another entry in the mod state
**When** I change the mod's version
**Then** the response is 409 `MOD_FILE_CONFLICT`, not 500 `MOD_VERSION_CHANGE_FAILED`, and the mod's file, the other file and the state are unchanged

*(Covers FR219)*

**Given** Update All, and one mod's new file name is taken
**When** the run reaches it
**Then** that mod is a `failed` item with the conflict message, and the run continues with the other mods

*(Covers FR219)*

**Given** a version change that fails to place the file or save state for another reason
**When** it is rolled back
**Then** the response is 500 `MOD_VERSION_CHANGE_FAILED`, as before

*(Covers FR219)*

**Given** a case-sensitive mods directory with `Foo.zip` installed
**When** I install, enable, disable or change to a version of another mod whose file would be `foo.zip` or `FOO.ZIP.disabled`
**Then** the response is 409 `MOD_FILE_CONFLICT`, the same answer a case-insensitive volume gives

*(Covers FR220)*

**Given** an installed mod `Foo_1.0.zip`
**When** I change it to a release whose file name differs from its own only in case
**Then** the change succeeds and exactly one file for the mod is in the directory afterwards, on a case-sensitive and on a case-insensitive volume

*(Covers FR220)*

**Given** a dangling symlink with the target name, or a mod state entry under the target name with no file
**When** I run any of the four operations
**Then** the response is 409 `MOD_FILE_CONFLICT`

*(Covers FR218, FR219, FR220)*

**Given** two mods whose releases have the same file name
**When** I download both, one after the other or at the same time
**Then** each is cached under its own file ID, neither replaces the other's copy, and each install places the archive of the mod that was asked for

*(Covers FR221)*

**Given** two downloads of the same release at the same time
**When** both finish
**Then** the cache holds one complete file and no temporary file is left

*(Covers FR221)*

**Given** a cache with files from before this story, and a temporary file left by a crash more than an hour ago
**When** the API starts and the next download finishes
**Then** the old files are removed at start and their number logged, eviction counts and evicts files in the new layout and removes emptied directories and the old temporary file

*(Covers FR221)*

**Given** an installed mod whose own file was removed from the mods directory by hand
**When** I enable or disable it
**Then** the response is 409 `MOD_FILE_MISSING` with a message naming the file and saying to remove the mod and install it again, never a 500, and the mod state is unchanged

*(Covers FR222)*

**Given** that mod
**When** I remove it through the manager
**Then** the removal succeeds

*(Covers FR222)*

**Given** a mods directory left by an interrupted install or version change: an unplaced working copy; a kept-aside original whose file is missing; a kept-aside original beside a new file that the mod state does not describe; and one beside a new file that it does
**When** the API starts
**Then** the working copy is deleted, the first two originals are put back, the last is deleted, each action is logged, and every mod's file matches its state

*(Covers FR223)*

**Given** files named `something.bak` or `something.tmp` that the manager did not create under its own suffixes
**When** the API starts
**Then** they are named in one warning and are neither deleted nor renamed

*(Covers FR223)*

**Given** a leftover working file for a name
**When** I install, enable, disable or change the version of a mod with that file name
**Then** the leftover does not cause a `MOD_FILE_CONFLICT`

*(Covers FR223)*

**Tasks:**

- [ ] The file-name helper (listing plus state, `casefold`, the mod's own file excluded) and `ModFileConflictError` with the operation in its message; use it in `_place_install` (Epic 19 ADR-8 decisions 1, 2 and 6) (`VSS-52fy`)
- [ ] `enable_mod` and `disable_mod`: the name check and the missing-file check; 409 `MOD_FILE_CONFLICT` and 409 `MOD_FILE_MISSING` on both routes (ADR-8, ADR-9 decisions 1 to 4) (`VSS-40ja`, `VSS-yhmt`)
- [ ] `_apply_version_change`: the name check, `same_file` ignoring case, 409 on the version route, `ModFileConflictError` in the Update All loop (ADR-8 decisions 4 and 7) (`VSS-macf`)
- [ ] Working files as `.vsm-tmp` and `.vsm-bak`, start-up recovery, the warning for old-style leftovers (ADR-9 decisions 5 to 8) (`VSS-uoxl`)
- [ ] Cache layout `cache/mods/<fileid>/<name>`, one path function, a temporary file per download, removal of the old layout at start, `CacheEvictionService` for the new layout (ADR-11) (`VSS-n0qv`)
- [ ] Tests for every case above with file bytes and state compared before and after, on a case-sensitive directory; confirm the web shows each message; API documentation of the changed errors

---

### Story 19.5: The Mod State Matches the Mods Directory at Start-Up

**Sprint key:** `19-5-mod-state-matches-the-mods-directory`
**Beads:** none of its own (Matt, 2026-11-17). It rides with `VSS-uoxl` (API-092), which Story 19.4 starts and this story finishes: close `VSS-uoxl` with its AAR when this story is done.
**FRs:** FR231, FR232

As an **administrator who sometimes adds or deletes mod files by hand**,
I want **the manager to bring its list of installed mods in line with the mods directory when it starts**,
So that **the Installed list shows what is really there**.

**Acceptance Criteria:**

**Given** a readable mod archive `New.zip` copied into the mods directory by hand, and another as `Off.zip.disabled`
**When** the API starts
**Then** both are in `GET /api/v1alpha1/mods` with the mod ID and version from their `modinfo.json`, the first enabled and the second disabled, and each addition is logged with its file name and mod ID

*(Covers FR231)*

**Given** a mod state entry whose file is no longer in the mods directory
**When** the API starts
**Then** the entry is gone from the Installed list and the removal is logged with its file name and mod ID

*(Covers FR231)*

**Given** a state entry whose file exists under a name that does not end in `.zip` or `.zip.disabled`
**When** the API starts
**Then** the entry stays

*(Covers FR231)*

**Given** a `.zip` in the mods directory that cannot be read or has no usable `modinfo.json`
**When** the API starts
**Then** start-up completes, the file is not added, it is not deleted, and one warning names it

*(Covers FR232)*

**Given** a `.zip` added by hand whose mod ID is already installed under another file
**When** the API starts
**Then** the existing entry stays, no second entry is added, and one warning names both files

*(Covers FR232)*

**Given** `.vsm-tmp`, `.vsm-bak`, `.tmp` and `.bak` files, a directory and a text file in the mods directory
**When** the API starts
**Then** none of them is added to the state, and none is changed by the sync

*(Covers FR232)*

**Given** an interrupted version change left a working file and a kept-aside original
**When** the API starts
**Then** Story 19.4's recovery runs first and the sync then sees the recovered file, so the mod is neither removed nor added twice

*(Covers FR231)*

**Given** the mods directory does not exist when the API starts
**When** the sync runs
**Then** no state entry is removed, and a warning says the directory was not found

*(Covers FR232)*

**Given** any start-up
**When** the sync has run
**Then** one summary line gives the numbers added, removed and skipped, also when all are zero, and the game server's auto-start comes after it

*(Covers FR231, FR232)*

**Given** the API
**When** I look for a way to run the sync again
**Then** there is no route and no button for it; it runs only at start-up

*(Covers FR231)*

**Tasks:**

- [ ] Make `sync_state_with_disk` safe: guard each import, decide removal by the entry's own file, skip a second file for an installed mod ID, one save (Epic 19 ADR-10 decisions 2 to 4 and 6)
- [ ] Logging: a line per addition, removal and skip, and the summary line (ADR-10 decision 5)
- [ ] Call it once in start-up, after the recovery of Story 19.4 and before the game server auto-start (ADR-10 decision 1)
- [ ] Tests from hand-built directories and states for every case above, including that start-up continues; README: mods added or removed by hand are picked up at the next restart

---

### Story 19.6: Mod Database Data Is Checked

**Sprint key:** `19-6-mod-database-data-is-checked`
**Beads:** `VSS-2zis` (API-081), `VSS-ce0h` (API-086), `VSS-0lkb` (API-090)
**FRs:** FR224, FR225, FR226, FR227

As an **administrator**,
I want **the manager to pass on only URLs it has checked and to treat a broken mod database answer as an upstream error**,
So that **a mod author's data or a mod database fault cannot misuse or break the pages I use**.

**Acceptance Criteria:**

**Given** a mod whose logo is an `https://moddbcdn.vintagestory.at/` URL
**When** I look it up or see it in the browse results
**Then** `logo_url` is that URL unchanged

*(Covers FR224)*

**Given** a mod whose logo is an `http:` URL, a URL on another host, a `data:` or `javascript:` URL, or not a URL
**When** I look it up or browse
**Then** the response is 200, `logo_url` is `null`, and the page shows the placeholder

*(Covers FR224)*

**Given** a mod logo on a browse card, the detail page or the install dialog
**When** the image is requested
**Then** the request carries no referrer

*(Covers FR224)*

**Given** a mod whose homepage or source URL is an `https` URL
**When** I look it up
**Then** `homepage_url` or `source_url` is that URL unchanged and the detail page shows the link

*(Covers FR225)*

**Given** a homepage or source value that is empty, an `http:`, `javascript:` or `data:` URL, has user info, has a space, control character or backslash, or is longer than 2,048 characters
**When** I look the mod up
**Then** the response is 200, the field is `null` and the detail page shows no such link; the "ModDB Page" link is unaffected

*(Covers FR225)*

**Given** the mod database answers the listing, a filtered listing, a mod lookup or the game version list with HTML, an empty body, `[]`, `"text"` or `null`
**When** a mod route needs that answer
**Then** the response is 502 `EXTERNAL_API_ERROR`, never 500, and the previous cached copy and its age are unchanged

*(Covers FR226)*

**Given** the mod database answers correctly on the next request
**When** I retry
**Then** the route works; nothing malformed was cached

*(Covers FR226)*

**Given** the game version cache is cold and several browse requests arrive together
**When** they are served
**Then** the mod database receives one `/api/gameversions` request, every request gets its result, and a failure reaches every waiting request and is not kept

*(Covers FR227)*

**Given** the mod listing cache is cold or expired and several browse requests arrive together
**When** they are served
**Then** the mod database receives one `/api/mods` request, every request gets its result, and a failure reaches every waiting request and is not kept

*(Covers FR227)*

**Given** a listing fetch is running
**When** a refresh is forced
**Then** it waits for the running fetch instead of starting a second one

*(Covers FR227)*

**Tasks:**

- [ ] `external_link_url` in `services/mod_media.py`; `mod_image_url` on `logo_url` in the lookup and the browse item; debug log without the URL (Epic 19 ADR-12 decisions 1 to 3 and 6) (`VSS-2zis`)
- [ ] Web: `referrerPolicy="no-referrer"` on the three logo images; confirm the placeholder and the missing links (ADR-12 decision 5)
- [ ] One guarded JSON fetch in `ModApiClient`, used by the four fetchers, each keeping its status rules (ADR-13 decisions 1 to 4) (`VSS-ce0h`)
- [ ] One shared in-flight fetch helper for the game version list, the full listing and the filtered listings (ADR-13 decisions 5 and 6) (`VSS-0lkb`)
- [ ] Tests: URL rules with a synthetic bad-data fixture for lookup and browse; each fetcher with the five malformed bodies and an unchanged cache; concurrent cold calls for both caches; API documentation of `null` for the three URL fields

---

### Story 19.7: E2E Runs in CI

**Sprint key:** `19-7-e2e-runs-in-ci`
**Beads:** `VSS-wenx` (TOOLS-007)
**FRs:** FR228, FR229, FR230

As a **maintainer**,
I want **the browser tests to run against the built image on every pull request**,
So that **a change that breaks the page is caught before it is merged**.

**Acceptance Criteria:**

**Given** a pull request or a push to `main`
**When** CI runs
**Then** an `e2e` job builds the image, starts a container from it with a data directory that holds only the seeded `serverconfig.json` fixture and with placeholder keys, waits for `/healthz`, runs the E2E tests that carry no tag, and fails the run when one fails

*(Covers FR228)*

**Given** the `e2e` job
**When** it starts the container
**Then** `VS_API_KEY` is set as Story 19.2 requires, no game server is installed or started, and no real key or instance data is in the workflow

*(Covers FR228)*

**Given** a failed `e2e` job
**When** I open the run
**Then** the Playwright report is attached as an artifact

*(Covers FR228)*

**Given** the E2E specs
**When** I read them
**Then** every test that needs the live mod database is tagged `@moddb`, every test that needs an installed game server `@game-server`, every test that installs or removes a real mod `@install`, and each tag is explained in one place

*(Covers FR229)*

**Given** the fixture `serverconfig.json` in the repository
**When** I read it
**Then** it holds made-up values only, and the CI job copies it to `serverdata/serverconfig.json` before the container starts

*(Covers FR228)*

**Given** the settings specs (`settings-desktop-layout`, `settings-empty-values`, `settings-as-saved`, `monitor-password-redaction`)
**When** they run against the seeded stack in CI
**Then** each test that passes there carries no tag and runs in CI, and any test that still needs an installed or running game server keeps `@game-server` with its reason

*(Covers FR229)*

**Given** the CI invocation
**When** it runs
**Then** it leaves out the three tags, includes the no-key spec of Story 19.2 and the policy spec of Story 19.3, and the same `just` recipe runs it on a developer's machine

*(Covers FR229)*

**Given** `just test-e2e-web` on a developer's machine with a game server installed
**When** it runs
**Then** it still runs every spec, tagged or not

*(Covers FR229)*

**Given** the E2E specs
**When** I search them for `localStorage.setItem('apiKey'`
**Then** there is no match, and every spec that loads a page gets its key through the helper of Story 19.2

*(Covers FR230)*

**Given** the workflow files
**When** `just lint-workflows` runs
**Then** it passes, and every action is pinned by commit like the existing jobs

*(Covers FR228)*

**Tasks:**

- [ ] Remove the dead `localStorage` init scripts from the fifteen specs and move every spec to the `/config.js` helper (Epic 19 ADR-14 decision 6) (`VSS-wenx`)
- [ ] The `serverconfig.json` fixture under `web/e2e/fixtures/` and its copy into the data directory, in the CI job and in the `just` recipe (ADR-14 decision 10; Matt, 2026-11-17)
- [ ] Tag the specs and tests (`@moddb`, `@game-server`, `@install`) after running each against the seeded stack with no game server; the settings specs lose their tag where they pass; record which tests run in CI (ADR-14 decisions 2, 3 and 10)
- [ ] A `just` recipe for the CI invocation; `api/tests/e2e/` in the same run (ADR-14 decisions 3 and 8)
- [ ] The `e2e` job in `.github/workflows/ci.yml`: cached image build, container start, health wait, Playwright install, report artifact; `just lint-workflows` (ADR-14 decisions 1 and 7)
- [ ] Documentation: how to run the CI subset locally and what the tags mean

---

## Epic 20: Tooling and Test Health

**Goal:** `just check` is green and quiet, and what it checks is everything: the API's format, the E2E specs' types and every script. A static security scan runs on every pull request. CI runs the browser tests for the file browser and the mod database, not only the ones that need nothing. The release image is built from pinned inputs. Seventeen open beads and one old epic are closed.

**Architecture:** `architecture/epic-20-tooling-and-test-health.md` (ADR-1 to ADR-11, with the facts checked at `3f1c6ea`). There is no preparation story. Story 20.6 adds its setting and proves the path to the replay in its first two tasks before it records anything (ADR-9 decision 7).

**Decided by the maintainer (Matt, 2026-11-17):** the one-time `ruff format` of the API as the first change of the epic, with the check in `just lint-api` (ADR-1); Prettier for the web is not in scope; the semgrep design: pinned version, six registry packs, pull requests fail only on findings they add, full scans of `main` report without blocking, SARIF to code scanning, source only, and the inline `nosemgrep` exception for a verified false positive (ADR-6, ADR-7). The same day he answered the proposal's open questions: the mod database's address becomes a setting, `VS_MOD_DB_URL`, and CI points it at a plain-HTTP replay of recorded answers (ADR-9, the alternative to the first draft); the recordings are trimmed real answers; the three pull-ins are approved; and every other default stands (`just semgrep` outside `just check`, no scheduled live run, the `@moddb-live` tag, the `docker exec` new-directory test, stop and ask under `vmThreads`, digests for all three images with `apt-get upgrade` kept, X.0 for preparation stories).

**Order:** 20.1, 20.2, 20.3, 20.4, 20.5, 20.6, 20.7.

**Dependencies:**

- Story 20.1 comes first and merges before any other branch of the epic is cut: it rewrites 75 API files, and every later API change (the fixtures in 20.2, the hash call in 20.4) is made on formatted code.
- Story 20.2 needs no other story's code. It comes second so that every later story starts from a `just check` with no warning and no skip.
- Story 20.3 comes before 20.4, 20.5 and 20.6: they add recipes to the `Justfile` and edit E2E specs, and from 20.3 on recipes pass arguments intact, specs are type-checked and a local E2E run leaves the tree clean.
- Story 20.4 comes after 20.1 (it edits `services/server.py`) and after 20.3 (its script is covered by the widened `just lint-scripts`). It adds a sixth job to `ci.yml` and updates the guard in `scripts/tests/test-release.sh`.
- Story 20.6 comes directly after 20.5: both edit `scripts/e2e-ci.sh`, its test, the `e2e` job and `web/e2e/README.md`.
- Story 20.7 needs no other story's code. It comes last because a digest change empties the image build cache that the `docker` and `e2e` jobs share, which would blur the timings Stories 20.5 and 20.6 record.
- Stories 20.3, 20.4, 20.5 and 20.6 all edit the `Justfile`, and 20.4, 20.5 and 20.6 all edit `ci.yml`; run them one after another.

**Beads:** seventeen in scope (the fourteen the maintainer picked and three pull-ins he approved on 2026-11-17: `VSS-eh41` in 20.2, `VSS-zhv3` in 20.6, `VSS-3q2s` in 20.7), each closed with an AAR by its story. `VSS-3asx` spans Stories 20.1 and 20.3 and closes with 20.3. `VSS-571h` spans Stories 20.5 and 20.6 and closes with 20.6. `VSS-37a` is already fixed in the code and is verified and closed in 20.2. The old epic `VSS-029` "Web UI Test Coverage" (16 of 18 done) closes in Story 20.5, when its last two children (`VSS-37a`, `VSS-3mr`) are closed.

**One product change:** Story 20.6 adds the optional setting `VS_MOD_DB_URL` (ADR-9). It is the only change of the epic that an operator can see, and its commit is a `feat(api)` with a release note.

### Current State

- 75 of the API's 157 Python files are not in `ruff format`'s form, and nothing checks the format
- `just check` prints three Pyright warnings and four skipped web tests on every run; the web tests spend 43% of their time creating jsdom environments
- `VSS-37a` is open although its three tests were re-enabled and pass
- The 23 E2E specs are never type-checked; `scripts/sprint-status.sh` is left out of ShellCheck; `just test-api -k "a or b"` fails; every Playwright run rewrites two tracked files
- No static security scan runs anywhere, and code scanning has never received a result
- CI leaves out 36 of 149 E2E tests: 31 that read the live mod database and 5 file browser tests that need a nested directory. "A new directory appears on refresh" has no test. A connection reset seen once in the E2E helper is retried and unexplained
- The Dockerfile copies uv from a `latest` tag and builds on two tags without digests
- `project-context.md` says preparation stories are never numbered X.0; the four epics after Epic 12 that had one numbered it X.0

### Target State

- The API is formatted, the format commit is skipped by `git blame`, and `just lint-api` and CI fail on an unformatted file
- `just check` ends with 0 Pyright warnings and 0 skipped tests, and the web tests run in the `vmThreads` pool
- `just typecheck` covers the E2E specs, `just lint-scripts` covers every script, recipes pass quoted arguments intact, and a Playwright run leaves the tree clean
- `just semgrep` and a CI job scan the source with a pinned semgrep; a pull request fails only on a finding it adds, and `main`'s findings are in code scanning
- CI runs the file browser tests on a seeded directory tree, a test for a directory created while the page is open, and the mod database tests against recorded answers, which the API reaches through the new `VS_MOD_DB_URL` setting
- Every image the Dockerfile uses is pinned by digest and Renovate moves the pins
- The story numbering rule says what the project does

---

### Story 20.1: The API Is Formatted Once and Stays Formatted

**Sprint key:** `20-1-api-formatted-once`
**Beads:** `VSS-3asx` (TOOLS-006), the formatting half; the bead stays open until Story 20.3
**FRs:** FR234, FR235, FR236

As a **developer**,
I want **the whole API in the formatter's form and a check that keeps it there**,
So that **formatting a file I work on never adds changes that are not mine**.

**Acceptance Criteria:**

**Given** the API source and tests
**When** `ruff format --check` runs over `api/`
**Then** it reports no file that would be reformatted

*(Covers FR234)*

**Given** the format commit
**When** I read it
**Then** it holds only what `ruff format` wrote with the existing configuration (`line-length = 100`): no hand edit, no lint fix, no configuration change, and its subject is `chore(story-20.1/task-1): format the API with ruff format`

*(Covers FR234; Matt, 2026-11-17)*

**Given** the format commit's parent
**When** a reviewer runs the same `ruff format` on it
**Then** the resulting tree is identical to the format commit's tree

*(Covers FR234)*

**Given** the API tests, `ruff check` and Pyright
**When** they run before and after the format commit
**Then** the results are the same: the same tests pass, no new lint finding, no new type error or warning, and no `# noqa` or `# fmt:` comment was added

*(Covers FR234)*

**Given** `just lint-api`
**When** it runs
**Then** it runs `ruff check` and then `ruff format --check`, and it fails when any API file is not formatted

*(Covers FR235)*

**Given** a pull request that contains an unformatted API file
**When** CI runs
**Then** the `api` job fails at `just lint-api`, with no change to the workflow file

*(Covers FR235)*

**Given** the repository root
**When** I read `.git-blame-ignore-revs`
**Then** it names the format commit's full hash with a comment line, and it was added in a separate commit of the same pull request

*(Covers FR236)*

**Given** a fresh worktree set up with `scripts/worktree-setup.sh`
**When** I run `git blame` on a reformatted API file
**Then** the format commit is skipped, and the README says which git setting does that

*(Covers FR236)*

**Given** the epic's branches
**When** Story 20.1's pull request merges
**Then** it is merged with a merge commit like every other, no other branch of the epic exists yet, and the hash in `.git-blame-ignore-revs` is a commit on `main`

*(Covers FR236; Matt, 2026-11-17)*

**Tasks:**

- [ ] Run `ruff format` over `api/` and commit the result alone; record the file and line counts and that the tests, `ruff check` and Pyright give the same results as before (Epic 20 ADR-1 decisions 1, 2 and 6) (`VSS-3asx`)
- [ ] `.git-blame-ignore-revs` with the commit's hash; `blame.ignoreRevsFile` in `scripts/worktree-setup.sh`; a line in the README (ADR-1 decision 4)
- [ ] `ruff format --check` in `just lint-api`; update the recipe comment and the command lists in `CLAUDE.md` and `project-context.md` (ADR-1 decision 5)

---

### Story 20.2: A Green, Quiet `just check`

**Sprint key:** `20-2-green-quiet-check`
**Beads:** `VSS-1ar` (TEST-003), `VSS-hnl` (TEST-004), `VSS-37a` (bug), `VSS-6wj` (TEST-005), `VSS-eh41` (UI-098; pulled in, Matt, 2026-11-17)
**FRs:** FR237, FR238, FR239

As a **developer**,
I want **`just check` to end with no warning and no skipped test, and the web tests to run faster**,
So that **a new warning or skip is seen the day it appears, and the check is quick enough to run every time**.

**Acceptance Criteria:**

**Given** `just typecheck-api`
**When** it runs
**Then** it prints `0 errors, 0 warnings`, the three fixtures (`test_mod_service.py` `mod_without_releases` and `mod_without_tags`, `test_mods_router.py` `mods_without_tags`) have a type annotation, no `# pyright: ignore` or `# type: ignore` was added, and no rule level in `pyproject.toml` changed

*(Covers FR237)*

**Given** the three empty placeholder tests (`FilterControls.test.tsx:156`, `use-browse-mods.test.tsx:247` and `:253`)
**When** the story is done
**Then** they are gone, and selecting a game version in the filter controls and filtering the browse list by game version each have a test with assertions, written here if none existed

*(Covers FR238)*

**Given** `ModTable.test.tsx` "shows loading state in remove button when removing"
**When** the web tests run
**Then** it runs and passes without `act` around the click, or the state is covered by a Playwright test and the unit test is deleted, and the story says which and why

*(Covers FR238)*

**Given** `just test-web`
**When** it runs
**Then** it reports 0 skipped tests

*(Covers FR238)*

**Given** `VSS-37a`'s three tests ("shows confirmation dialog when remove button is clicked", "closes dialog when cancel is clicked", "removes mod when confirm is clicked")
**When** the web tests run
**Then** all three run and pass, and the bead is closed with an AAR that names commit `f393c3a`, which re-enabled them

*(Covers FR238)*

**Given** `web/vitest.config.ts`
**When** I read it
**Then** it sets `pool: 'vmThreads'`, does not set `isolate: false`, and no test file is moved to another pool; if a file cannot be made to pass, the story stops and asks the maintainer

*(Covers FR239; Matt, 2026-11-17)*

**Given** the three files that failed under `vmThreads` and remain (`use-log-stream.test.ts`, `use-console-websocket.test.ts`, `cookies.test.ts`; the fourth, `Terminal.test.tsx`, is deleted with its dead component)
**When** the web tests run under `vmThreads` and under the forks pool
**Then** every test passes under both, no test redefines `window.location` with `Object.defineProperty` or deletes `global.document`, and the tests assert what they asserted before

*(Covers FR239)*

**Given** the web suite before and after the story
**When** I compare the test counts
**Then** the only tests that are gone are the ones this story deleted on purpose, and the story lists them

*(Covers FR239)*

**Given** CI's `web` job
**When** it runs on the story's pull request
**Then** `just test-web` passes, and the story records its time before (60 s) and after

*(Covers FR239)*

**Given** `project-context.md`
**When** I read its testing rules
**Then** it says how to stub a browser global so that the test passes under `vmThreads`, and its forbidden-pattern list names `it.skip` and `describe.skip`

*(Covers FR238, FR239)*

**Given** the pull-in `VSS-eh41`
**When** the story is done
**Then** `web/src/features/terminal/Terminal.tsx`, its test and the unused `checkVersionCompatibility` are removed, nothing imports them, the E2E spec `terminal.spec.ts` (which tests the Console page, not this component) still passes, and the bead is closed with an AAR

*(Covers FR239; pulled in, Matt, 2026-11-17)*

**Tasks:**

- [ ] Annotate the three fixtures; `just typecheck-api` at 0 warnings (Epic 20 ADR-3 decision 3) (`VSS-1ar`)
- [ ] Delete the three placeholders after checking the game version filter's tests, writing the missing ones; rewrite the remove-button loading test (ADR-3 decisions 1 and 2) (`VSS-hnl`)
- [ ] Run and record `VSS-37a`'s three tests; close the bead with its AAR (ADR-3 decision 4) (`VSS-37a`)
- [ ] Pull-in (Matt, 2026-11-17): remove `Terminal.tsx`, `Terminal.test.tsx` and `checkVersionCompatibility`; list the deleted tests (ADR-2 decision 3) (`VSS-eh41`)
- [ ] Read every failure under `vmThreads`; change the stubs in the three remaining files so they pass under both pools (ADR-2 decision 2) (`VSS-6wj`)
- [ ] `pool: 'vmThreads'` in `web/vitest.config.ts`; local and CI times; the stubbing pattern and the skip patterns in `project-context.md` (ADR-2 decisions 1 and 6, ADR-3 decision 5) (`VSS-6wj`)

---

### Story 20.3: Lint and Type Checks Cover Everything

**Sprint key:** `20-3-lint-and-typecheck-coverage`
**Beads:** `VSS-3asx` (TOOLS-006), the type-check half, closed here; `VSS-1eb` (TOOLS-004); `VSS-6354` (TOOLS-009); `VSS-uw9z` (TOOLS-008)
**FRs:** FR240, FR241, FR242, FR243

As a **developer**,
I want **the checks to cover the E2E specs and every script, and the recipes to do what I type**,
So that **a mistake in a spec or a script is caught by `just check`, and running the tools leaves no mess**.

**Acceptance Criteria:**

**Given** `web/e2e/tsconfig.json`
**When** I read it
**Then** it extends the web configuration, sees Node's types and not Vitest's or Vite's, and includes the E2E directory and `playwright.config.ts`

*(Covers FR240)*

**Given** a type error in an E2E spec or in `playwright.config.ts`
**When** `just typecheck-web`, `just typecheck` or `just check` runs
**Then** it fails and names the file

*(Covers FR240)*

**Given** CI's `web` job
**When** it runs
**Then** it runs `just typecheck-web`, and `bun run build` is unchanged, so a spec's type error cannot stop the image build

*(Covers FR240)*

**Given** the E2E specs today
**When** the new check runs
**Then** it passes with no `@ts-expect-error` or `@ts-ignore` added

*(Covers FR240)*

**Given** `scripts/sprint-status.sh`
**When** ShellCheck runs on it
**Then** it reports nothing, the file contains no `shellcheck disable` directive, and every command behaves as before

*(Covers FR241)*

**Given** the status checks that were rewritten
**When** `just test-scripts` runs
**Then** tests cover a valid and an invalid status for a story, an epic, a retrospective and a retro item

*(Covers FR241)*

**Given** `just lint-scripts`
**When** it runs
**Then** it checks every `.sh` file in `scripts/` and `scripts/tests/` through globs, so a new script is covered without editing the recipe

*(Covers FR241)*

**Given** `just test-api -k "a or b"`
**When** it runs
**Then** pytest receives `a or b` as one expression and selects the tests that match either

*(Covers FR242)*

**Given** every recipe that passes arguments on to a tool
**When** I call it with an argument that contains spaces
**Then** the tool receives it as one argument; a script test proves it without running the tool, and it holds for `just sprint retro-add <key> "a comment"`

*(Covers FR242)*

**Given** the recipes' existing uses (`just test-api tests/test_server.py -xvs`, `just docker logs`, `just release --dry-run`, `just dev-api --port 8001`)
**When** I run them
**Then** they behave as before

*(Covers FR242)*

**Given** the repository
**When** I run `git ls-files web/playwright-report web/test-results`
**Then** it prints nothing, and both directories are in `.gitignore` and `.dockerignore`

*(Covers FR243)*

**Given** a clean working tree
**When** I run Playwright (`--list`, a passing run, or a failing run)
**Then** `git status` is still clean

*(Covers FR243)*

**Given** a failed `e2e` job in CI
**When** I open the run
**Then** the Playwright report is still attached as an artifact

*(Covers FR243)*

**Tasks:**

- [ ] `web/e2e/tsconfig.json`; the `typecheck` script checks both projects; `just typecheck-web` in CI's `web` job; fix whatever the check finds in the specs (Epic 20 ADR-4) (`VSS-3asx`)
- [ ] Positional arguments in every recipe that forwards `*ARGS`; the script test; update the examples in the `Justfile` header and `CLAUDE.md` (ADR-5 decisions 1 and 2) (`VSS-6354`)
- [ ] Make `sprint-status.sh` ShellCheck-clean with `case` statements and no directive; tests for the rewritten checks (ADR-5 decision 3) (`VSS-1eb`)
- [ ] `just lint-scripts` over globs; remove the `VSS-1eb` comment (ADR-5 decision 4) (`VSS-1eb`)
- [ ] Untrack the two Playwright files; `.gitignore` and `.dockerignore`; remove the "restore the report files" notes from `web/e2e/README.md` and the agent documentation if any mention them (ADR-5 decision 5) (`VSS-uw9z`)

---

### Story 20.4: Semgrep Locally and in CI

**Sprint key:** `20-4-semgrep`
**Beads:** `VSS-djg` (TOOLS-002), `VSS-4ac` (CICD-001)
**FRs:** FR244, FR245, FR246, FR247

As a **maintainer**,
I want **a static security scan on every pull request and one command to run it myself**,
So that **a risky pattern is caught when it is written, without old findings or noisy rules blocking unrelated work**.

**Acceptance Criteria:**

**Given** `just semgrep`
**When** it runs
**Then** it runs semgrep at one pinned version through `uvx`, with `--metrics=off`, the packs `p/python`, `p/typescript`, `p/react`, `p/secrets`, `p/github-actions` and `p/dockerfile`, over `api/src`, `web/src`, `.github`, `Dockerfile` and `scripts`, and exits non-zero on a finding

*(Covers FR244; Matt, 2026-11-17)*

**Given** the scan's scope
**When** I list the files semgrep scanned
**Then** no test file is among them (`*.test.ts`, `*.test.tsx`, `scripts/tests/`), the exclusions are in one `.semgrepignore`, and no rule file is stored in the repository

*(Covers FR244; Matt, 2026-11-17)*

**Given** the semgrep version
**When** I look for it
**Then** it is written in one place, CI and the recipe both read it from there, Renovate has a rule that updates it, and a script test checks that the line has the form that rule matches

*(Covers FR244)*

**Given** `just semgrep --baseline-commit origin/main`
**When** it runs on a branch
**Then** the arguments reach semgrep and only findings the branch adds are reported

*(Covers FR244)*

**Given** `just lint`, `just check`, `just test-api` and `just test-web`
**When** they run
**Then** none of them runs semgrep

*(Covers FR244; Matt, 2026-11-17)*

**Given** a pull request that adds a line a chosen rule matches
**When** CI runs
**Then** the `semgrep` job fails and its log names the rule, the file and the line

*(Covers FR245; Matt, 2026-11-17)*

**Given** a pull request that adds no finding, while `main` has findings or the registry has new rules
**When** CI runs
**Then** the `semgrep` job passes

*(Covers FR245; Matt, 2026-11-17)*

**Given** a push to `main` or a manual run
**When** the `semgrep` job runs
**Then** it scans the whole scope, uploads the results to GitHub code scanning as SARIF, and does not fail because of findings

*(Covers FR245, FR246; Matt, 2026-11-17)*

**Given** `ci.yml`
**When** I read it
**Then** only the `semgrep` job has `security-events: write`, the workflow's default permission is still `contents: read`, every action is pinned by commit, and the job has the same release-commit skip `if:` as the others

*(Covers FR246; Matt, 2026-11-17)*

**Given** `just test-scripts`
**When** it runs
**Then** `test-release.sh` expects the six jobs `api docker e2e scripts semgrep web`, checks the skip `if:` on each, and passes; `just lint-workflows` passes

*(Covers FR246)*

**Given** `api/src/vintagestory_api/services/server.py`
**When** semgrep runs with `p/python`
**Then** the checksum code uses `hashlib.md5(usedforsecurity=False)`, the rule `insecure-hash-algorithm-md5` no longer matches, the scope has no finding, and no `nosemgrep` comment was added for it

*(Covers FR247; Matt, 2026-11-17)*

**Given** `project-context.md`'s "No Silent Failures Rule"
**When** I read it
**Then** it states the one exception: `# nosemgrep: <rule-id> — <reason>` naming one rule, only for a verified false positive, each one checked in review, a bare `nosemgrep` never, and changing the code preferred where that states the intent better

*(Covers FR247; Matt, 2026-11-17)*

**Given** the CI job on the runner
**When** it runs
**Then** it finishes within five minutes, and the story records its time and, per pack, how many rules the engine could not run

*(Covers FR245)*

**Tasks:**

- [ ] `scripts/semgrep.sh` (version, packs, paths, `--metrics=off`, arguments passed through), `.semgrepignore`, and the `just semgrep` recipe; record the scanned file count, findings, rule errors and time (Epic 20 ADR-6 decisions 1, 2, 4, 5, 6 and 7) (`VSS-djg`)
- [ ] The Renovate rule for the version and the script test that pins the line's form (ADR-6 decision 3) (`VSS-djg`)
- [ ] `hashlib.md5(usedforsecurity=False)` in `services/server.py`; confirm the rule stops matching; the existing checksum tests still pass (ADR-7 decision 7) (`VSS-4ac`)
- [ ] The `semgrep` job in `ci.yml`: baseline scan on pull requests, full scan and SARIF upload on `main`, job-level permissions, the skip `if:`; update `test-release.sh` to six jobs (ADR-7 decisions 1 to 4) (`VSS-4ac`)
- [ ] The `nosemgrep` exception in `project-context.md`; `just semgrep` in `CLAUDE.md` and the README's development section; a note in the story of how a finding is triaged (ADR-7 decisions 5, 6 and 8) (`VSS-4ac`)
- [ ] Prove the gate on the story's own pull request: a temporary commit that adds a matching line fails the job, and removing it passes; record both runs

---

### Story 20.5: The File Browser E2E Tests Run in CI

**Sprint key:** `20-5-file-browser-e2e-in-ci`
**Beads:** `VSS-3mr` (UI-030); `VSS-571h` (TEST-006), parts 2, 3 and 4, the bead stays open until Story 20.6. Closes the old epic `VSS-029`
**FRs:** FR248, FR249, FR250, FR251

As a **maintainer**,
I want **the file browser's browser tests to run on every pull request, including a directory that appears while I watch**,
So that **the file browser is covered in CI and the old test-coverage epic can close**.

**Acceptance Criteria:**

**Given** `just test-e2e-ci`
**When** it starts the throwaway container
**Then** the container's `serverdata` holds a directory inside another directory with made-up names, owned by the manager's user, beside the seeded `serverconfig.json`

*(Covers FR248)*

**Given** `file-browser-navigation.spec.ts`
**When** CI runs
**Then** its five tests run and pass, the spec carries no `@game-server` tag, and it still creates, changes and deletes nothing

*(Covers FR248)*

**Given** the same spec on the dev stack with a game server
**When** `just test-e2e-web` runs
**Then** it passes as before

*(Covers FR248)*

**Given** the file manager open on a directory in the throwaway stack
**When** a new directory is created in that directory from outside the page and the page is loaded again
**Then** the new directory is in the list and can be opened

*(Covers FR249)*

**Given** that test on a stack that is not the throwaway container
**When** it runs
**Then** it skips with a message that says why and changes nothing in that stack's data; `scripts/tests/test-e2e-ci.sh` checks that the CI script gives the test what it needs, so CI cannot skip it

*(Covers FR249; Matt, 2026-11-17)*

**Given** `VSS-3mr` and `VSS-37a` closed
**When** the story is done
**Then** the old epic `VSS-029` "Web UI Test Coverage" has no open child and is closed with an AAR that names Stories 16.7, 20.2 and 20.5

*(Covers FR249)*

**Given** the `e2e` job
**When** it runs a second time with the same Playwright versions
**Then** it restores the browsers from a cache and does not download them, the cache action is pinned by commit, and the key changes only when a Playwright version or the runner's system changes

*(Covers FR250)*

**Given** the cache
**When** the story measures the job
**Then** it records the browser step's time before (43 s) and after, and the cache is removed again if it saves nothing

*(Covers FR250)*

**Given** the connection reset in the server-status stub
**When** the investigation is done
**Then** the comment in `web/e2e/config-js.ts` states the cause if it was reproduced, or what was tried if it was not, and the single retry either stays with that reason or is removed because the cause is gone

*(Covers FR251)*

**Given** `web/e2e/README.md`
**When** I read it
**Then** it lists the seeded directories, says what the new test needs, and says that no test carries `@game-server` now and when the tag is still the right one

*(Covers FR248, FR249)*

**Tasks:**

- [ ] Seed the nested directory in `scripts/e2e-ci.sh`; pin it in `scripts/tests/test-e2e-ci.sh` (Epic 20 ADR-8 decision 1) (`VSS-571h`)
- [ ] Run `file-browser-navigation.spec.ts` on the seeded stack and remove its tag; check it on the dev stack (ADR-8 decision 2) (`VSS-571h`)
- [ ] The "new directory appears after a reload" test and what the script exports for it (ADR-8 decision 3) (`VSS-3mr`)
- [ ] Cache the Playwright browsers in the `e2e` job; times before and after (ADR-8 decision 5) (`VSS-571h`)
- [ ] The time-boxed investigation of the connection reset; the comment and the retry (ADR-8 decision 6) (`VSS-571h`)
- [ ] `web/e2e/README.md`; close `VSS-3mr` and then `VSS-029`, each with an AAR (ADR-8 decision 4)

---

### Story 20.6: The Mod Database E2E Tests Run in CI

**Sprint key:** `20-6-mod-database-tests-in-ci`
**Beads:** `VSS-571h` (TEST-006), part 1, closed here; `VSS-zhv3` (DOCS-001; pulled in, Matt, 2026-11-17)
**FRs:** FR252, FR253, FR254, FR258, FR259

As a **maintainer**,
I want **the tests that read the mod database to run in CI against recorded answers**,
So that **the mod pages are covered on every pull request, the same way every time, without calling the live service**.

**Acceptance Criteria:**

**Given** a deployment that does not set `VS_MOD_DB_URL`
**When** the API starts and talks to the mod database
**Then** it uses `https://mods.vintagestory.at` for its API calls and downloads exactly as before, and logs no warning about the address

*(Covers FR258; Matt, 2026-11-17)*

**Given** `VS_MOD_DB_URL` set to another `https` address
**When** the API lists mods, looks a mod up, reads the game version list or downloads a mod file
**Then** each request goes to that address (`<base>/api/...`, `<base>/download`), and the start-up log has one warning that names the scheme and host

*(Covers FR258, FR259)*

**Given** `VS_MOD_DB_URL` set to another address
**When** the API passes on a mod's logo, screenshots, homepage and source links, and the web UI builds a link to a mod's page
**Then** the image host allow-list and the link rules are the same as without the setting (only `moddbcdn.vintagestory.at` images, `https` links), and the web UI's links still point at `mods.vintagestory.at`

*(Covers FR258)*

**Given** `VS_MOD_DB_URL` with the scheme `http` and `VS_DEBUG` unset or false
**When** the API starts
**Then** start-up stops with an error that names `VS_MOD_DB_URL` and says plain HTTP is for testing and needs `VS_DEBUG=true`

*(Covers FR259; Matt, 2026-11-17)*

**Given** `VS_MOD_DB_URL` with the scheme `http` and `VS_DEBUG=true`
**When** the API starts
**Then** it starts, uses the address, and logs the warning

*(Covers FR259; Matt, 2026-11-17)*

**Given** a value that is not an absolute URL, has another scheme, has no host, or carries a user name, a password, a path, a query or a fragment
**When** the API starts
**Then** start-up stops with an error that names the setting and what is wrong; a single trailing `/` is accepted and ignored

*(Covers FR259)*

**Given** the README, `.env.example` and the release notes
**When** I read them
**Then** the setting is documented as optional, with its default, what it is for (a mirror of the same database, or tests), the `http` rule, and that mods are downloaded from that address; and the commit that adds it has the subject `feat(api): add VS_MOD_DB_URL to use a mirror of the mod database`

*(Covers FR258)*

**Given** the built image with the setting pointed at a stub, before anything is recorded
**When** the second task is done
**Then** the story has shown that the listing, the mod lookup, the game version list and the download reach the stub, that no request goes to the live host (which stays blocked in the container), and that a request the stub has no answer for is reported with its URL

*(Covers FR252)*

**Given** `just test-e2e-ci`
**When** it runs
**Then** its first pass is as before (the untagged tests against a container in production mode), and a second pass starts a replay container and a second API container with `VS_DEBUG=true` and `VS_MOD_DB_URL` set to the replay, runs the `@moddb` tests that are not `@moddb-live` or `@install` against it, and removes everything it started, also after a failure

*(Covers FR252)*

**Given** the CI run
**When** I look at where its requests go
**Then** neither API container nor the browser sends a request to the live mod database or its image host; the browser's image requests are answered by a placeholder

*(Covers FR252)*

**Given** two CI runs of the same commit
**When** I compare the `@moddb` tests' results
**Then** they are the same

*(Covers FR252)*

**Given** `web/e2e/fixtures/moddb/`
**When** I read it
**Then** it holds one file per recorded request and a manifest that gives each request, its recording date, how it was trimmed and which spec needs it; the answers are real ones, trimmed, with their image and link URLs unchanged, and nothing but what the mod database's public API returned

*(Covers FR253; Matt, 2026-11-17)*

**Given** `just record-moddb`
**When** I run it with network access
**Then** it fetches the manifest's requests from the live mod database, rewrites the recordings with the same trimming, and prints which fields appeared or disappeared since the last recording

*(Covers FR253)*

**Given** the 31 `@moddb` tests
**When** the story has run each against the recordings
**Then** each one either runs in CI, or carries `@moddb-live` (it compares with live data) or `@install` (it installs a real mod) with a one-line reason, and the story lists how many tests are in each group

*(Covers FR254; Matt, 2026-11-17)*

**Given** `just test-e2e-web` on a developer's machine
**When** it runs
**Then** every spec still runs against the live mod database, with no recordings and no setting involved, and no workflow runs them against the live service on a schedule

*(Covers FR254; Matt, 2026-11-17)*

**Given** `web/e2e/README.md`
**When** I read it
**Then** it explains the tags as they now are, the two passes, how the replay works, how and when to refresh the recordings, and which tests remain live-only

*(Covers FR253, FR254)*

**Given** the `e2e` job
**When** the story is done
**Then** it still finishes within its 30 minute limit, and the story records its time before (3 min 16 s) and after

*(Covers FR252)*

**Given** the pull-in `VSS-zhv3`
**When** the story is done
**Then** `agentdocs/vintagestory-modapi.md` documents the fields and filters the bead lists, checked against the recordings, and the bead is closed with an AAR

*(Covers FR253; pulled in, Matt, 2026-11-17)*

**Tasks:**

- [ ] The `VS_MOD_DB_URL` setting: validation at start-up, the warning, `ModApiClient` building both addresses from it, tests for every accepted and refused form and for the fixed allow-lists; README and `.env.example`; its own `feat(api)` commit (Epic 20 ADR-9 decisions 1 to 5) (`VSS-571h`)
- [ ] Prove the path in the built image against a stub: every mod database request and the download follow the setting, nothing reaches the live host, a missing answer names its URL (ADR-9 decision 7) (`VSS-571h`)
- [ ] The replay server script, the recording script and `just record-moddb`; the manifest; the first recordings for the requests the specs make (ADR-9 decisions 6, 8, 9 and 10) (`VSS-571h`)
- [ ] The second pass in `scripts/e2e-ci.sh` (network, replay container, second API container, cleanup), pinned in `scripts/tests/test-e2e-ci.sh`; images answered by a placeholder (ADR-9 decisions 6 and 13) (`VSS-571h`)
- [ ] Run each `@moddb` test on the recordings; retag (`@moddb-live`) with reasons; fix tests that fail for a fault of their own; `web/e2e/README.md`; job time before and after; close `VSS-571h` with an AAR (ADR-9 decisions 11 and 12)
- [ ] Pull-in (Matt, 2026-11-17): complete `agentdocs/vintagestory-modapi.md` from what was recorded (`VSS-zhv3`)

---

### Story 20.7: Reproducible Image Inputs and the Numbering Rule

**Sprint key:** `20-7-reproducible-image-and-conventions`
**Beads:** `VSS-870` (INFRA-004), `VSS-as6` (TOOLS-005), `VSS-3q2s` (DOCS-002; pulled in, Matt, 2026-11-17)
**FRs:** FR255, FR256, FR257

As a **maintainer**,
I want **the image built from inputs that a commit names exactly, and the story numbering rule to say what we do**,
So that **a release build does not change without a commit, and the documentation stops contradicting the practice**.

**Acceptance Criteria:**

**Given** the Dockerfile
**When** I read the line that copies uv
**Then** it names a version and a digest, and the version is the one `.mise.toml` pins

*(Covers FR255)*

**Given** every `FROM` and `COPY --from` image in the Dockerfile (uv, the Node build image and the .NET runtime image)
**When** `just test-scripts` runs
**Then** a test passes only if each has `@sha256:` and the uv tag equals the uv version in `.mise.toml`

*(Covers FR255; Matt, 2026-11-17)*

**Given** the image built from the pinned Dockerfile
**When** CI's `docker` and `e2e` jobs run
**Then** the build succeeds and the E2E tests pass against it

*(Covers FR255)*

**Given** `renovate.json`
**When** Renovate runs
**Then** it proposes digest and version updates for the three images, uv in the Dockerfile and in `.mise.toml` move in one pull request, and the .NET runtime is still held below 11

*(Covers FR256)*

**Given** `RELEASING.md`
**When** I read what happens on a re-run of the image job
**Then** it says which inputs are pinned, that `apt-get upgrade` stays and the system package layer can therefore still differ, and that each run's attestations describe the digest that run pushed

*(Covers FR255; Matt, 2026-11-17)*

**Given** `project-context.md`'s "Story Numbering" section
**When** I read it
**Then** it says a preparation story is numbered X.0, an epic without one starts at X.1, and its table and history match what Epics 4 to 20 did

*(Covers FR257; Matt, 2026-11-17)*

**Given** `cliff.toml`, the BMAD story template and the sprint keys
**When** the story is done
**Then** none of them changed, and they agree with the rule

*(Covers FR257)*

**Given** the pull-in `VSS-3q2s`
**When** the story is done
**Then** the environment table in `architecture/project-structure-boundaries.md` lists `VS_API_KEY`, `VS_CSP_MODE` and Story 20.6's `VS_MOD_DB_URL`, says what `VS_DEBUG` also serves and that it allows a plain-HTTP mod database address, does not list `VS_GAME_VERSION`, and the bead is closed with an AAR

*(Covers FR257; pulled in, Matt, 2026-11-17)*

**Tasks:**

- [ ] Pin the uv image by version and digest, and the two base images by digest; build and run the E2E set on the result (Epic 20 ADR-10 decisions 1 and 2) (`VSS-870`)
- [ ] The Renovate rule that groups uv; the script test for digests and the uv version (ADR-10 decisions 3 and 4) (`VSS-870`)
- [ ] `RELEASING.md`: what a re-run can and cannot change (ADR-10 decision 5) (`VSS-870`)
- [ ] Rewrite the "Story Numbering" section of `project-context.md` (ADR-11) (`VSS-as6`)
- [ ] Pull-in (Matt, 2026-11-17): the architecture's environment table, with `VS_MOD_DB_URL` (`VSS-3q2s`)

---

## Epic 21: Maintainer Decisions and Web Polish

**Goal:** Five decisions the maintainer made after Epic 20 are carried out: the web is formatted by Prettier and stays formatted, Renovate holds uv like every other tool and stops writing release notes for image rebuilds, `VS_LOG_LEVEL` works, and the mod remove dialog waits for the removal. Fifteen open beads about the web's tables, dialogs, mod browser, mod detail page, tabs and layout, and about the config file viewer, are closed.

**Architecture:** `architecture/epic-21-maintainer-decisions-and-web-polish.md` (ADR-1 to ADR-16, with the facts checked at `05436da`). There is no preparation story. Story 21.7 starts its arrow key work with a time-boxed reproduction (ADR-12 decision 3).

**Decided by the maintainer (Matt, 2026-11-17):** the five decisions and the fourteen beads. For each decision: Prettier as a pinned dev dependency, one dedicated reformat commit that is first among the web stories and listed in `.git-blame-ignore-revs`, and a format check in `just lint-web` (ADR-1); the uv rule loses `minimumReleaseAge: null` and the red first day is documented (ADR-2); digest refreshes of Dockerfile images are `chore(container)` (ADR-3); `VS_LOG_LEVEL` with four values, case-insensitive, today's behaviour when unset and a start-up error when invalid (ADR-4); the remove dialog stays open with "Removing..." until the DELETE finishes and tracks its own mod (ADR-6). The same day he answered the proposal's ten open questions (`sprint-change-proposal-2026-11-17-epic-21.md`, section 5): every default stands, `VSS-q38r` is pulled into Story 21.4 and `VSS-koo1` is not pulled in. The answers are written into the ADRs' status lines. One planner decision made after his answers is not reviewed yet: what triggers the refresh for `VSS-q38r` (ADR-16 decision 1).

**Order:** 21.1, 21.2, 21.3, 21.4, 21.5, 21.6, 21.7, 21.8.

**Dependencies:**

- Story 21.1 comes first among the web stories and merges before any other web branch of the epic is cut: it rewrites about 231 web files, and every later web change is made on formatted code.
- Stories 21.2 and 21.3 touch no file under `web/`. They need no other story's code and may be done before, after or beside 21.1; they are numbered here so the epic can start with them while 21.1 is in review. They share only the README and `RELEASING.md` with other stories.
- Story 21.4 comes before 21.5: both edit `ModTable.tsx` and its test.
- Story 21.5 comes before 21.7: both edit `VersionTable.tsx` (21.5 its sort, `aria-sort` and casts; 21.7 its columns on phones).
- Story 21.6 needs no other story's code after 21.1. It comes after 21.5 because 21.5 changes the shared dialog close button that the screenshot dialog on the mod detail page uses.
- Story 21.8 comes last and directly after 21.7: both extend `web/e2e/layout-widths.spec.ts`, 21.7 measures every page at phone and tablet widths before 21.8 changes the sidebar default there, and 21.8 changes the width of almost every page.
- Stories 21.4 to 21.8 are run one after another.

**Beads:** fifteen in scope (the fourteen the maintainer picked and one pull-in he approved on 2026-11-17, `VSS-q38r` in 21.4), each closed with an AAR by its story: `VSS-wv0w` in 21.3; `VSS-oc28` and `VSS-q38r` in 21.4; `VSS-qxxo`, `VSS-whnb`, `VSS-759m` and `VSS-nuef` in 21.5; `VSS-woae`, `VSS-pzj8` and `VSS-4vbj` in 21.6; `VSS-3ry`, `VSS-vt4` and `VSS-f9y` in 21.7; `VSS-w85` and `VSS-alx` in 21.8. Stories 21.1 and 21.2 carry maintainer decisions and have no bead. What planning found is in the stories (the change proposal lists it), not in new beads.

**Product changes:** one new working setting, `VS_LOG_LEVEL` (21.3); three small corrections to the config file routes (21.3); the rest is behaviour and layout of the web UI. No route, response field or status code of an existing successful request changes. Nothing is breaking.

### Current State

- The web has no formatter: `just format-web` runs an unpinned Prettier with defaults that would rewrite almost every file, and nothing checks the format
- A uv update opens with both halves at once because the preset's one-day hold was cleared for it; a base image rebuild under the same tag is committed as `fix(container)` and becomes a release note
- `VS_LOG_LEVEL` is read into the settings and used nowhere; the log level follows `VS_DEBUG` only
- Discord webhook URLs on `ptb.` and `canary.` hosts are not redacted for read-only keys; an Admin directory listing shows links that leave the data directory; a read-only key gets an empty list instead of 403 when the data directory is missing
- The mod remove dialog closes at once and the removal runs behind it; its "Removing..." label is shared by every mod's dialog
- A failed mod install shows two error toasts, and so do a failed server install, uninstall and restart and a failed webhook setting
- After another game version is installed, browse cards keep the old version's badges for up to five minutes
- Sorting by version puts a release before its pre-releases in the installed mods list and on the Version page; the installed mods headers have no `aria-sort`; dialog and sheet close buttons are 16px
- Five links open a new tab without saying so, and SVG links in descriptions cannot; the mod detail page is 674px wide on a 390px screen; mod descriptions show headings, lists and links as plain text
- Tab buttons are about 30px tall on phones; the Settings tabs can lose arrow key presses just after they render; the Scheduled Jobs and Version tables scroll inside themselves on phones
- The sidebar is expanded by default at tablet widths; apart from Game Settings no page has a maximum width

### Target State

- The web is formatted by a pinned Prettier with a committed configuration, the format commit is skipped by `git blame`, and `just lint-web` and CI fail on an unformatted file
- A uv update follows the preset's hold, and `RELEASING.md` says its pull request is red for a day and must wait; image rebuilds are `chore(container)` and stay out of the release notes
- `VS_LOG_LEVEL` sets the log level, an invalid value stops start-up, and the debug switch still gives DEBUG
- The config file viewer redacts all four Discord hosts, lists nothing that leaves the data directory, and answers 403 before it looks for the directory
- The remove dialog waits for its own mod's removal and stays open on an error; every failed action shows one toast; mod data is fetched again when the installed game version changes
- Versions sort by Semantic Versioning precedence everywhere; sortable headers announce their state; close buttons are 44px
- Every new-tab link says so; the mod detail page fits a phone; descriptions are typeset in both themes
- Tabs are 44px tall below 1024px; the arrow key fault is fixed or explained; the two tables fit phones and every page has been measured there
- The sidebar follows the width until the user chooses; page content is at most 1280px wide, except the console

---

### Story 21.1: The Web Is Formatted Once and Stays Formatted

**Sprint key:** `21-1-web-formatted-once`
**Beads:** none (maintainer decision 5; Matt, 2026-11-17)
**FRs:** FR260, FR261, FR262, FR263

As a **developer**,
I want **the whole web in one formatter's form and a check that keeps it there**,
So that **formatting a file I work on never adds changes that are not mine**.

**Acceptance Criteria:**

**Given** `web/package.json` and `web/bun.lock`
**When** I read them
**Then** Prettier is a dev dependency at one exact version (no range), and `format` and `format:check` scripts run it over the web directory

*(Covers FR261; Matt, 2026-11-17)*

**Given** `web/.prettierrc.json`
**When** I read it
**Then** it sets `singleQuote: true`, `printWidth: 100` and `trailingComma: "es5"` and nothing else

*(Covers FR261; ADR-1 decision 2)*

**Given** `web/.prettierignore`
**When** Prettier runs over `web/`
**Then** it covers the tracked `.ts`, `.tsx`, `.css` and `.json` files in `src`, `e2e`, `tests` and at the top of `web/`, and leaves out `e2e/fixtures/`, Markdown and HTML files, `public/` and the build, coverage and Playwright output directories

*(Covers FR261; ADR-1 decisions 3 and 4)*

**Given** the web sources
**When** `prettier --check .` runs in `web/`
**Then** it reports no file that would be reformatted

*(Covers FR260)*

**Given** the format commit
**When** I read it
**Then** it holds only what `prettier --write .` wrote with the committed configuration: no hand edit, no configuration change, no `// prettier-ignore`, and its subject is `chore(story-21.1/task-2): format the web with prettier`

*(Covers FR260; Matt, 2026-11-17)*

**Given** the format commit's parent (which already holds the dependency, the configuration and the ignore file)
**When** a reviewer runs the same command on it
**Then** the resulting tree is identical to the format commit's tree

*(Covers FR260)*

**Given** `just typecheck-web`, `just test-web` and `just build-web`
**When** they run before and after the format commit
**Then** the results are the same: no new type error, the same tests pass, and the build succeeds

*(Covers FR260)*

**Given** the recorded mod database answers in `web/e2e/fixtures/moddb/`
**When** the format commit is made
**Then** no file under `web/e2e/fixtures/` has changed, and `just record-moddb` still writes files the check ignores

*(Covers FR260, FR261)*

**Given** `just lint-web`
**When** it runs
**Then** it runs the format check, fails when a covered file is not formatted, and no longer repeats the type check that `just typecheck-web` runs

*(Covers FR262)*

**Given** a pull request that contains an unformatted web file
**When** CI runs
**Then** the `web` job fails at a `just lint-web` step, and `scripts/tests/test-release.sh` still passes (the job list is unchanged)

*(Covers FR262)*

**Given** `just format-web` and `just format`
**When** they run on a formatted tree
**Then** they use the pinned Prettier and the committed configuration, and change no file

*(Covers FR261)*

**Given** the repository root
**When** I read `.git-blame-ignore-revs`
**Then** it names the web format commit's full hash under a comment line, below the API entry, and it was added in a separate commit of the same pull request

*(Covers FR263)*

**Given** the epic's branches
**When** Story 21.1's pull request merges
**Then** it is merged with a merge commit like every other, no other web branch of the epic exists yet, and the hash in `.git-blame-ignore-revs` is a commit on `main`

*(Covers FR263; Matt, 2026-11-17)*

**Tasks:**

- [ ] Add Prettier at an exact version, `web/.prettierrc.json`, `web/.prettierignore` and the `format` and `format:check` scripts; no source file changes in this commit (Epic 21 ADR-1 decisions 1 to 4)
- [ ] Run `prettier --write .` in `web/` and commit the result alone; record the file and line counts and that the type check, tests and build give the same results as before (ADR-1 decisions 5, 6 and 9)
- [ ] Add the commit's hash to `.git-blame-ignore-revs` (ADR-1 decision 7)
- [ ] `just lint-web` runs the format check and `just format-web` the pinned Prettier; add `just lint-web` to CI's `web` job; update the recipe comments and the command lists in `CLAUDE.md`, `project-context.md` and the README (ADR-1 decision 8)

---

### Story 21.2: Renovate: the uv Hold and Digest Refreshes

**Sprint key:** `21-2-renovate-uv-hold-and-digests`
**Beads:** none (maintainer decisions 1 and 2; Matt, 2026-11-17)
**FRs:** FR264, FR265

**Planning note (2026-11-17):** a Renovate pull request for uv 0.13.9 (#185, branch `renovate/uv`) is already open. It was opened under the current rule (no hold), so it holds both the Dockerfile and the `.mise.toml` change. Merging or closing it is the maintainer's call; this story does not merge, close or rebase it. If it is still open when the story merges, the story records what Renovate does with it under the new rule.

As the **maintainer**,
I want **uv held like every other tool and image rebuilds kept out of the release notes**,
So that **Renovate's pull requests follow the organisation's rules and the release notes list only what a user would notice**.

**Acceptance Criteria:**

**Given** `renovate.json`
**When** I read the uv rule
**Then** it has no `minimumReleaseAge`, it still groups `uv` and `ghcr.io/astral-sh/uv` as `chore(uv)`, and its description says the pull request opens with the Dockerfile half and must wait for the `.mise.toml` half

*(Covers FR264; Matt, 2026-11-17)*

**Given** `RELEASING.md`
**When** I read what it says about Renovate and uv
**Then** it says a uv pull request opens with only the Dockerfile change, that `scripts/tests/test-docker-context.sh` fails it for about a day until the `.mise.toml` change joins it, that this is expected, and that it must not be merged until it holds both files and CI is green

*(Covers FR264; Matt, 2026-11-17)*

**Given** `scripts/tests/test-docker-context.sh`
**When** the story is done
**Then** its uv version assertion is unchanged

*(Covers FR264; ADR-2 decision 4)*

**Given** `renovate.json`
**When** I read its rules
**Then** one rule matches the `dockerfile` manager with update types `digest` and `pinDigest` and sets the commit type `chore`, and no rule changes the type of a `patch`, `minor` or `major` update of a Dockerfile image

*(Covers FR265; Matt, 2026-11-17)*

**Given** a digest refresh of `node:26-slim` under the same tag
**When** Renovate commits it
**Then** the subject starts with `chore(container):`, and `just changelog` shows no note for it

*(Covers FR265; confirmed on the first such pull request after the merge, or by Renovate's dry run if one can be run; recorded in the story)*

**Given** a new version tag of a Dockerfile image
**When** Renovate commits it
**Then** the subject keeps the preset's `fix(container):` or `feat(container):`

*(Covers FR265)*

**Given** the changed `renovate.json`
**When** `renovate-config-validator --no-global` runs on it from a directory outside the repository
**Then** it reports the file as a valid repository configuration, and `web/package.json` and `web/bun.lock` are unchanged by the run

*(Covers FR264, FR265)*

**Tasks:**

- [ ] Remove `minimumReleaseAge: null` from the uv rule and rewrite its description; rewrite the uv paragraph of `RELEASING.md`; validate (Epic 21 ADR-2)
- [ ] Add the digest rule for the `dockerfile` manager; add a sentence to `RELEASING.md` on which image updates produce a release note; validate (ADR-3)
- [ ] Record the validator's output and, once Renovate has run with the new rules, what it did with the open uv pull request and the next digest refresh (ADR-2 consequences, ADR-3)

---

### Story 21.3: A Working `VS_LOG_LEVEL` and Config Viewer Edge Cases

**Sprint key:** `21-3-log-level-and-config-viewer`
**Beads:** `VSS-wv0w` (API-096); maintainer decision 3 (Matt, 2026-11-17)
**FRs:** FR266, FR267, FR268, FR269, FR270

As an **operator**,
I want **to set the API's log level with `VS_LOG_LEVEL`, and the config file viewer to behave the same in its edge cases**,
So that **I can have quieter or more detailed logs without debug mode, and read-only keys see neither webhook secrets nor wrong answers**.

**Acceptance Criteria:**

**Given** `VS_LOG_LEVEL=warning` (any letter case) and `VS_DEBUG` unset
**When** the API starts
**Then** INFO and DEBUG lines are not written and WARNING and ERROR lines are, in JSON, and the `api_starting` line reports `WARNING` as the level

*(Covers FR266)*

**Given** `VS_LOG_LEVEL` unset or blank
**When** the API starts
**Then** the level is DEBUG with `VS_DEBUG=true` and INFO otherwise, as before

*(Covers FR266; Matt, 2026-11-17)*

**Given** `VS_DEBUG=true` and `VS_LOG_LEVEL=INFO`
**When** the API starts
**Then** the level is INFO, the console renderer is used, and the documentation pages and test routes are served as in any debug mode

*(Covers FR266; ADR-4 decision 2)*

**Given** `VS_LOG_LEVEL=DEBUG` and `VS_DEBUG` unset
**When** the API starts
**Then** DEBUG lines are written in JSON, and the documentation pages and test routes are not served

*(Covers FR266)*

**Given** `VS_LOG_LEVEL=verbose`
**When** the API starts
**Then** start-up stops with an error that names `VS_LOG_LEVEL` and the four allowed values and does not print the value

*(Covers FR267; Matt, 2026-11-17)*

**Given** `VS_LOG_LEVEL=WARNING` and a running API
**When** an Admin turns debug logging on and then off again
**Then** the level is DEBUG while it is on and WARNING after it is turned off, and the three `/debug` responses have the fields they have today

*(Covers FR267; ADR-4 decision 3)*

**Given** `VS_DEBUG=on`
**When** the API starts
**Then** logging is in debug mode, as the documentation pages already are

*(Covers FR267; ADR-4 decision 6)*

**Given** the README's configuration table, `.env.example`, the architecture's environment table and the Logging section of `project-context.md`
**When** I read them
**Then** each describes `VS_LOG_LEVEL`: the four values, that letter case does not matter, the default, what the debug switch does to it, and that any other value stops start-up

*(Covers FR267)*

**Given** a config file with the value `https://ptb.discord.com/api/webhooks/1/abc` or `https://canary.discord.com/api/webhooks/1/abc`
**When** a Monitor key reads the file
**Then** the value is `[redacted]`, as for `discord.com` and `discordapp.com`, and the API has one definition of the four hosts

*(Covers FR268; `VSS-wv0w`)*

**Given** a directory symlink, or a `.json` file symlink, inside the server data directory that points outside it
**When** an Admin key or a Monitor key lists the directory that holds it
**Then** the entry is not in the listing

*(Covers FR269; `VSS-wv0w`)*

**Given** the server data directory does not exist
**When** a Monitor key lists a directory it may not see (for example `Playerdata`)
**Then** the answer is 403 `FORBIDDEN`, as when the data directory exists; a path traversal is 400; and a request for the root or `ModConfig` still answers with an empty list

*(Covers FR270; `VSS-wv0w`)*

**Tasks:**

- [ ] Validate `log_level` in the settings (normalise, blank is unset, a bad value raises naming `VS_LOG_LEVEL`) with tests for every accepted and refused form (Epic 21 ADR-4 decisions 1 and 8)
- [ ] Apply the level at start-up and keep it through the debug switch: `initialize_debug_state` takes the configured level and the debug flag from the settings, `set_debug_enabled` returns to it, `api_starting` reports the level set; tests for each combination; its own `feat(api)` commit (ADR-4 decisions 2 to 6)
- [ ] Document `VS_LOG_LEVEL` in the README, `.env.example`, `architecture/project-structure-boundaries.md` and `project-context.md` (ADR-4 decision 7)
- [ ] One set of Discord hosts for redaction and for the webhook sender, with tests for the two added hosts; its own `fix(api)` commit (ADR-5 decision 1) (`VSS-wv0w`)
- [ ] Listings leave out entries that resolve outside the data directory for every role, and the path and role checks run before the missing-directory shortcut; tests for both roles; update the route documentation strings (ADR-5 decisions 2 to 4) (`VSS-wv0w`)

---

### Story 21.4: The Mod Remove Dialog Waits, and One Toast per Failure

**Sprint key:** `21-4-remove-dialog-and-single-toast`
**Beads:** `VSS-oc28` (UI-096), `VSS-q38r` (UI-097; pulled in, Matt, 2026-11-17); maintainer decision 4 (Matt, 2026-11-17)
**FRs:** FR271, FR272, FR273, FR274, FR286

As an **administrator**,
I want **the remove dialog to show me the removal until it is done, one message when something fails, and mod data that follows the installed game version**,
So that **I know whether the mod was removed, am not told the same error twice, and do not read badges for a game version I no longer run**.

**Acceptance Criteria:**

**Given** the remove dialog of an installed mod
**When** I confirm
**Then** the dialog stays open, the confirm button shows a spinner and "Removing...", and the confirm and Cancel buttons are disabled

*(Covers FR271; Matt, 2026-11-17)*

**Given** a removal that is running
**When** I press Escape
**Then** the dialog stays open

*(Covers FR271; ADR-6 decision 4; Matt, 2026-11-17)*

**Given** a removal that is running
**When** the DELETE succeeds
**Then** the dialog closes, the mod is no longer in the list, and the success message is shown once

*(Covers FR271)*

**Given** a removal that is running
**When** the DELETE fails
**Then** exactly one error toast is shown, the dialog stays open with the confirm button enabled and labelled "Remove" again, and the mod is back in the list behind it

*(Covers FR272; ADR-6 decision 3; Matt, 2026-11-17)*

**Given** the dialog after a failed removal
**When** I confirm again or cancel
**Then** confirming sends a new DELETE and cancelling closes the dialog with the mod still installed

*(Covers FR272)*

**Given** a removal of mod A that failed or finished
**When** I open the remove dialog of mod B
**Then** its confirm button reads "Remove" and is enabled; "Removing..." is shown only in the dialog of the mod whose DELETE is running

*(Covers FR273; Matt, 2026-11-17)*

**Given** the installed mods as cards (below 1024px)
**When** I remove a mod from its card
**Then** the dialog behaves the same as from the table

*(Covers FR271)*

**Given** the server uninstall dialog while its request runs
**When** I press Escape
**Then** the dialog stays open, as its disabled Cancel button already implies

*(Covers FR271; ADR-6 decision 7, found in planning)*

**Given** a mod install that the API refuses
**When** the install dialog shows the failure
**Then** exactly one error toast is shown, titled "Installation failed" with the API's message

*(Covers FR274; `VSS-oc28`)*

**Given** a failed server install, server uninstall, server restart or mod update webhook change
**When** the request fails
**Then** exactly one error toast is shown, with the caller's title and the API's message

*(Covers FR274; ADR-7 decision 2; Matt, 2026-11-17)*

**Given** `project-context.md`
**When** I read its frontend rules
**Then** it says that a hook-level `onError` replaces the query client's default, that an `onError` passed to `mutate` runs in addition, and that a hook either reports its error or silences the default for its callers

*(Covers FR274; ADR-7 decision 5; Matt, 2026-11-17)*

**Given** the mod browser was opened while game version A was installed
**When** the server status reports game version B (after an install of another version has finished)
**Then** the browse cards are fetched again without a reload and show the "Has a release for" badges of version B, within one status poll and not after the five-minute cache time

*(Covers FR286; `VSS-q38r`)*

**Given** the installed game version changes, or the server is uninstalled, or a server is installed where none was
**When** I next open the installed mods list or a mod detail page
**Then** their compatibility and update information is fetched again for the new version

*(Covers FR286; ADR-16 decision 3)*

**Given** the server status is polled and the installed game version has not changed
**When** any number of polls arrive, including the first one after a page load
**Then** no mod query is invalidated

*(Covers FR286; ADR-16 decision 2)*

**Given** a server install has been started and has not finished
**When** the install request's success handler runs
**Then** the refresh of mod data does not depend on it: the trigger is the version the server status reports

*(Covers FR286; ADR-16 decision 1)*

**Given** the E2E suite
**When** CI runs it
**Then** untagged specs cover the remove dialog with the DELETE stubbed (a delayed success and an error) and the browse refresh with the server status and the browse answer stubbed (the version changes between two polls), send no request that changes the stack, and pass on the throwaway container

*(Covers FR271, FR272, FR286)*

**Tasks:**

- [ ] The remove dialog: a plain destructive confirm button, open until the DELETE succeeds, Cancel and Escape blocked while it runs, open with "Remove" again after an error; the same Escape guard for the server uninstall dialog; unit tests for running, success and failure; a `fix(web)` commit with the release note (Epic 21 ADR-6 decisions 1 to 4, 6 and 7)
- [ ] The pending state compares the mutation's `variables` with the dialog's mod; unit test with a second mod's dialog (ADR-6 decision 5)
- [ ] `useInstallMod` silences the default `onError`; a test that a failed install shows one toast; a `fix(web)` commit with its release note (ADR-7 decisions 1 and 3) (`VSS-oc28`)
- [ ] The same for `useRestartServer`, `useInstallServer`, `useUninstallServer` and `useSetModUpdateWebhook`, after checking every caller reports the error; one test each; a `fix(web)` commit with its release note; the rule in `project-context.md` (ADR-7 decisions 2, 5 and 6)
- [ ] A hook mounted once in the layout watches the installed game version in the server status and invalidates the mod queries when it changes; unit tests for a change, no change, the first value and uninstall; a `fix(web)` commit with its release note (ADR-16) (`VSS-q38r`)
- [ ] E2E specs with stubbed answers: the remove dialog (delayed success, error) and the browse refresh on a version change; update the counts in `web/e2e/README.md` (ADR-6 decision 8, ADR-16 decision 5)

---

### Story 21.5: Version Sort, Sort State for Screen Readers and Close Buttons

**Sprint key:** `21-5-version-sort-aria-sort-close-buttons`
**Beads:** `VSS-qxxo` (UI-099), `VSS-whnb` (UI-100), `VSS-759m` (UI-101), `VSS-nuef` (UI-095)
**FRs:** FR275, FR276, FR277

As a **user of the tables and dialogs**,
I want **versions in their real order, the sort order announced, and close buttons I can hit**,
So that **a pre-release is not listed as newer than its release, a screen reader tells me how a table is sorted, and I can close a dialog on a phone**.

**Acceptance Criteria:**

**Given** installed mods with the versions `1.0.0`, `1.0.0-rc.2`, `1.0.0-rc.12`, `1.9.0` and `1.10.0`
**When** I sort by Version ascending
**Then** the order is `1.0.0-rc.2`, `1.0.0-rc.12`, `1.0.0`, `1.9.0`, `1.10.0`, and descending is the reverse, in the table and in the cards below 1024px

*(Covers FR275; `VSS-qxxo`)*

**Given** the Version page's table with `1.22.0` and `1.22.0-rc.1`
**When** I sort by Version ascending
**Then** `1.22.0-rc.1` comes before `1.22.0`

*(Covers FR275; found in planning)*

**Given** an installed game version `1.22.0-rc.2` and a listed version `1.22.0-rc.12`
**When** the Version page marks newer versions
**Then** `1.22.0-rc.12` is marked as newer

*(Covers FR275; found in planning)*

**Given** versions the comparison cannot read (for example `1.2`, `v1.0.0`, `beta`)
**When** a table sorts them with others
**Then** nothing throws, a leading `v` is ignored, a missing part counts as 0, unreadable strings come after readable ones, and the order is the same on every render

*(Covers FR275; ADR-8 decision 3)*

**Given** the web's dependencies
**When** the story is done
**Then** no package was added for the comparison, and the two tables and the "newer" mark use one function

*(Covers FR275)*

**Given** the installed mods table sorted by Name ascending
**When** a screen reader reads the header row
**Then** the Name header has `aria-sort="ascending"`, the Version and Status headers have `aria-sort="none"`, and the headers that cannot be sorted have no `aria-sort`

*(Covers FR276; `VSS-whnb`)*

**Given** either sortable table
**When** I change the sort column or its direction
**Then** `aria-sort` moves with it: `ascending` or `descending` on the sorted column and `none` on the other sortable columns

*(Covers FR276)*

**Given** `VersionTable.tsx`
**When** I read how it uses column meta
**Then** it reads `meta.className` with no type assertion, and the rendered classes are the same as before

*(`VSS-759m`; a refactor with no requirement of its own)*

**Given** any dialog with a close button, and the phone navigation sheet
**When** I measure the close button at 390px and at 1440px
**Then** it is at least 44 by 44px, its icon is where it was, and it does not cover the dialog's title text

*(Covers FR277; `VSS-nuef`)*

**Tasks:**

- [ ] `web/src/lib/version-compare.ts` with unit tests for every rule and for unreadable input (Epic 21 ADR-8 decisions 1 to 5) (`VSS-qxxo`)
- [ ] Use it in the installed mods Version column and in the Version table (the column's sort and the "newer" mark, replacing the private function); table tests for both directions and the cards; a `fix(web)` commit with the release note (ADR-8 decision 1) (`VSS-qxxo`)
- [ ] `aria-sort` on the sortable headers of both tables, chevrons hidden from screen readers; unit tests for each state; a `fix(web)` commit with the release note (ADR-9 decisions 1 and 2) (`VSS-whnb`)
- [ ] Remove the two casts in `VersionTable.tsx`; a `refactor` commit (ADR-9 decision 3) (`VSS-759m`)
- [ ] 44px close buttons in `ui/dialog.tsx` and `ui/sheet.tsx`; an E2E check of the size at 390px for one dialog and the sheet; a `fix(web)` commit with the release note (ADR-9 decisions 4 and 5) (`VSS-nuef`)

---

### Story 21.6: Mod Detail Page Polish

**Sprint key:** `21-6-mod-detail-polish`
**Beads:** `VSS-woae` (UI-094), `VSS-pzj8` (UI-092), `VSS-4vbj` (UI-093)
**FRs:** FR278, FR279, FR280

As a **user reading about a mod**,
I want **the page to fit my phone, the description to look like a document, and links to say where they open**,
So that **I can read and install from a phone, and a screen reader tells me before a link leaves the app**.

**Acceptance Criteria:**

**Given** the mod detail page of a mod with a homepage and a source URL
**When** a screen reader reads the ModDB Page, Homepage, Source and trailer links
**Then** each is announced with "(opens in a new tab)", and each shows a visible mark that it leaves the app

*(Covers FR278; `VSS-woae`)*

**Given** the other links in the web UI that open a new tab (the mod links in the installed list and on browse cards, the changelog links, the sidebar link)
**When** a screen reader reads them
**Then** each announces that it opens in a new tab, in the same words

*(Covers FR278; ADR-10 decisions 1 and 2, found in planning)*

**Given** a mod description that contains an SVG with a link
**When** the description is shown
**Then** the link opens in a new tab with `rel="noopener noreferrer"` and has an accessible note that says so; sanitizing the result again adds no second note; and a note the mod author wrote cannot stand in for it

*(Covers FR278; `VSS-woae`; ADR-10 decisions 4 and 5)*

**Given** the mod detail page at 320, 390 and 430px
**When** I open a mod with a long name, tags and an install card
**Then** the page does not scroll sideways, the header is stacked with the install card at full width, every control is inside the viewport, and the install and version controls are at least 44px tall

*(Covers FR279; `VSS-pzj8`)*

**Given** the mod detail page at 768px and wider
**When** I open it
**Then** the header is the one row it is today

*(Covers FR279)*

**Given** a description with headings, paragraphs, a bulleted and a numbered list, a link, a quote, inline code, a code block and a table
**When** it is shown in the light and in the dark theme
**Then** headings are larger and bolder than body text, lists show their markers and indentation, the link is in the link colour and underlined, the quote, code and table are set apart, and every colour comes from the theme

*(Covers FR280; `VSS-4vbj`)*

**Given** a description with a table, an image, a code block or a URL wider than the card
**When** it is shown at 320px
**Then** the wide element scrolls or shrinks inside the card and the page does not scroll sideways

*(Covers FR279, FR280)*

**Given** `web/package.json` and the description container
**When** the story is done
**Then** no dependency was added and the container has no `prose` class

*(Covers FR280; ADR-11 decisions 5 and 6)*

**Given** a description whose author set inline styles
**When** it is shown
**Then** the author's styles still apply over the defaults

*(Covers FR280; ADR-11 decision 7)*

**Tasks:**

- [ ] A new-tab link component with the hidden note; use it for the five unmarked links; the same wording in the three `aria-label` links; the visible mark on Homepage and Source; unit tests; a `fix(web)` commit with the release note (Epic 21 ADR-10 decisions 1 to 3) (`VSS-woae`)
- [ ] SVG links in descriptions get a `<title>` note in the sanitizer hook; unit tests including idempotence; confirm in a browser's accessibility snapshot and record the result (ADR-10 decisions 4 to 6) (`VSS-woae`)
- [ ] The header stacks below `md`, with the skeleton; unit tests; a `fix(web)` commit with the release note (ADR-11 decisions 1 and 2) (`VSS-pzj8`)
- [ ] Description styles under `.mod-description`, wide content contained, `prose` classes removed; a `fix(web)` commit with the release note (ADR-11 decisions 3 to 7) (`VSS-4vbj`)
- [ ] E2E on a stubbed mod detail answer: no sideways scroll and a stacked header at 320, 390 and 430px, the unchanged row at 768px, heading, list and link styles in both themes (ADR-11 decision 8)

---

### Story 21.7: Tabs and Tables on Phones

**Sprint key:** `21-7-tabs-and-tables-on-phones`
**Beads:** `VSS-3ry` (UI-089), `VSS-vt4` (UI-091, bug), `VSS-f9y` (UI-087)
**FRs:** FR281, FR282, FR283

As a **user on a phone or tablet**,
I want **tabs I can tap, tabs that answer the keyboard at once, and tables that fit the screen**,
So that **I do not miss a tab, lose a key press or scroll a table sideways inside the page**.

**Acceptance Criteria:**

**Given** the Settings, Mods and Version pages below 1024px
**When** I measure their tab buttons
**Then** each is at least 44px tall, and from 1024px up they are the height they are today

*(Covers FR281; `VSS-3ry`)*

**Given** the Settings tab list at 320 to 430px
**When** it wraps to two rows
**Then** both rows are inside the list's background, nothing overlaps the panel below, and the page does not scroll sideways

*(Covers FR281)*

**Given** the arrow key fault of `VSS-vt4`
**When** the story starts on it
**Then** it is first reproduced with a real keyboard in Chromium and Firefox and with the scripted steps, within the time box, and what was seen is recorded in the story

*(Covers FR282; ADR-12 decision 3)*

**Given** the fault is reproduced and its cause is in this project's code
**When** I focus a Settings tab as soon as the list is shown and press ArrowRight three times
**Then** focus and selection move one tab per press, in a unit test and in an E2E with no added wait

*(Covers FR282; ADR-12 decision 4)*

**Given** the fault cannot be reproduced with a real keyboard, or its cause is inside the tabs library
**When** the story ends
**Then** no workaround was added, and the bead is closed with the evidence: what was tried, on which browsers, and what was seen

*(Covers FR282; ADR-12 decision 5)*

**Given** the Scheduled Jobs tab from 320 to 1023px, with the sidebar expanded and collapsed
**When** I open it with an Admin key
**Then** each job is a card with its name, schedule, next run and status labelled, nothing scrolls sideways inside the panel, and from 1024px up the table is unchanged

*(Covers FR283; `VSS-f9y`)*

**Given** the Version page at 320 and 390px
**When** I open it
**Then** the version table fits its container without scrolling inside itself, each row still shows its channel, and its install action is at least 44px tall

*(Covers FR283; `VSS-f9y`)*

**Given** every page of the web UI (Dashboard, Version, Game Settings, Mods installed and browse, mod detail, both console pages, each Settings tab)
**When** it is measured at 320, 390, 430, 768 and 1023px in both sidebar states
**Then** the measurements are saved in the story's folder, and each page that scrolls sideways or has a table scrolling inside itself is either fixed in this story or reported to the maintainer in the pull request with its numbers

*(Covers FR283; the comment on `VSS-f9y`; ADR-13 decision 4)*

**Tasks:**

- [ ] 44px tab triggers below `lg` in `ui/tabs.tsx`; check the three tab lists at 320, 390, 430 and 768px; extend `layout-widths.spec.ts`; a `fix(web)` commit with the release note (Epic 21 ADR-12 decisions 1 and 2) (`VSS-3ry`)
- [ ] Reproduce the arrow key fault (real keyboard, then scripted) and record it; fix it with a unit test and an E2E, or close the bead with the evidence (ADR-12 decisions 3 to 5) (`VSS-vt4`)
- [ ] Scheduled Jobs as cards below `lg`, with unit tests for both layouts (ADR-13 decision 1) (`VSS-f9y`)
- [ ] The Version table without a Channel column below `sm`, channel shown under the version; unit tests (ADR-13 decision 2) (`VSS-f9y`)
- [ ] Measure every page at the five widths in both sidebar states, save the numbers, fix what is of the same kind; extend `layout-widths.spec.ts` for the two tables; a `fix(web)` commit with the release note (ADR-13 decisions 3 to 5) (`VSS-f9y`)

---

### Story 21.8: Sidebar Default and Content Width

**Sprint key:** `21-8-sidebar-default-and-content-width`
**Beads:** `VSS-w85` (UI-090), `VSS-alx` (UI-088)
**FRs:** FR284, FR285

As a **user on a tablet or a wide monitor**,
I want **the sidebar out of the way where space is short, and pages that do not stretch across a wide screen**,
So that **content has room at tablet widths and stays readable on large monitors**.

**Acceptance Criteria:**

**Given** a browser with no stored preferences
**When** I open the app at 900px
**Then** the sidebar is collapsed (64px), and at 1024px and wider it is expanded (160px)

*(Covers FR284; `VSS-w85`)*

**Given** no stored sidebar choice
**When** I resize the window across 1024px
**Then** the sidebar collapses and expands with the width

*(Covers FR284; ADR-14 decision 3)*

**Given** any width from 768px
**When** I use the sidebar's toggle
**Then** the sidebar changes, the choice is stored, and it is kept at every width and after a reload

*(Covers FR284; ADR-14 decision 4)*

**Given** a cookie written before this story with `sidebarCollapsed: true`
**When** I open the app
**Then** the sidebar is collapsed at every width from 768px, as before

*(Covers FR284; ADR-14 decision 2)*

**Given** a cookie written before this story with `sidebarCollapsed: false`
**When** I open the app
**Then** the sidebar follows the width: collapsed from 768 to 1023px and expanded from 1024px

*(Covers FR284; ADR-14 decision 2)*

**Given** UI Preferences
**When** I open the sidebar setting
**Then** I can choose Automatic, Expanded or Collapsed, the current value is shown, and Automatic returns the sidebar to following the width

*(Covers FR284; ADR-14 decision 5)*

**Given** a phone width and a stored choice of Collapsed
**When** I open the navigation menu
**Then** the sheet shows the full sidebar with labels and no collapse toggle

*(Covers FR284; ADR-14 decision 6, found in planning)*

**Given** the Dashboard, the Version page, Game Settings, the Mods page with both tabs and Settings at 1920px, in both sidebar states
**When** I measure the content
**Then** it is at most 1280px wide and centered in the area right of the sidebar, and nothing is clipped

*(Covers FR285; `VSS-alx`)*

**Given** the mod browser at 1920px
**When** I open it
**Then** the grid has four columns inside the 1280px content width

*(Covers FR285; ADR-15 decision 3)*

**Given** the Console page and the game server page with the console at 1920px
**When** I measure the console
**Then** it uses the full width of the content area and is wider than 1280px

*(Covers FR285; ADR-15 decision 4)*

**Given** the code
**When** I search for the 1280px width
**Then** it is written in one place, and Game Settings uses it

*(Covers FR285; ADR-15 decision 1)*

**Given** every page below 1280px of content width
**When** I compare it with before the story
**Then** its layout is unchanged

*(Covers FR285)*

**Tasks:**

- [ ] The sidebar preference becomes `auto`, `expanded` or `collapsed` with the migration of the old key; the effective state follows the width when `auto`; unit tests at 767, 768, 1023 and 1024px and for both old cookie values (Epic 21 ADR-14 decisions 1 to 4) (`VSS-w85`)
- [ ] The three-way control in UI Preferences and the always-full sidebar in the phone sheet; unit tests; a `feat(web)` commit with the release note (ADR-14 decisions 5 and 6) (`VSS-w85`)
- [ ] `layout-widths.spec.ts` writes the new key and checks a fresh browser at 900px and 1024px (ADR-14 decision 7) (`VSS-w85`)
- [ ] The 1280px cap in `Layout` with one constant, the console pages opted out, Game Settings on the shared constant; unit tests; a `feat(web)` commit with the release note (ADR-15 decisions 1 to 5) (`VSS-alx`)
- [ ] Check each capped page and the console at 1440, 1920 and 2560px in both sidebar states and extend `layout-widths.spec.ts`; update the UX notes in the story on what the spec asked and what was built (ADR-15 decision 6) (`VSS-alx`)

---

## Epic 22: Server Operations and Metrics

**Goal:** An operator can watch the game server from Prometheus and the dashboard (players online, the game process's CPU and memory, uptime, state), restart it on a daily schedule with warnings to players, and keep the disk from filling with old log archives and backups; and every scheduled job can be turned off, and metrics collection set, from the API Settings tab. Four open beads are closed.

**Architecture:** `architecture/epic-22-server-operations-and-metrics.md` (ADR-1 to ADR-16, with the facts checked at `e16a7932`). There is no preparation story: what planning could not check (the stop time of a world save, whether the game prunes its own log archives, `VSS-zws`, the console prefix of the join and leave lines) is a task inside Stories 22.1, 22.3 and 22.4, run in throwaway containers or confirmed by the maintainer.

**Decided by the maintainer (Matt, 2026-11-18):** eleven answers given one at a time (`sprint-change-proposal-2026-11-18-epic-22.md`, section 5): a Prometheus `/metrics` at the root and `playersOnline` in the JSON metrics and the dashboard (ADR-2, ADR-3); `/metrics` open like `/healthz` (ADR-3); the metric set of ADR-4; players counted from the game's join and leave lines (ADR-1); restart times as a daily `HH:MM` list in the container's time zone (ADR-5); warnings at 15, 5 and 1 minutes with fixed text (ADR-6); a restart whenever the game runs, players or not, and never a start (ADR-6); cleanup of log archives older than 14 days with the newest 5 kept, backups only when a count is set, `BackupSaves` never (ADR-9); log rotation left to the game (ADR-10); an On switch per interval field and a Metrics Collection field from 1 second to 1 hour (ADR-11); `VSS-zws` pulled in, `VSS-hv60`, `VSS-3tb1` and `VSS-7z3` not (ADR-8). A twelfth answer the same day, after Story 22.3's Task 1 confirmed `VSS-zws`: fix it in a new Story 22.7, a small API story after 22.4, that keeps the restart-required edits made while the game runs and writes them to `serverconfig.json` again after the process exits, before any start (ADR-15). Planner decisions not reviewed yet: the job layout of ADR-6 and ADR-7, the 16-minute gap between restart times (ADR-6 decision 6), the 03:00 cleanup time and the safety rules (ADR-9), the hidden API Settings tab for Monitor (ADR-12, told to the maintainer with question 11), the UI of ADR-13, and the design of ADR-15 (edits kept on disk, when they are written back and dropped, a failed write-back not blocking a start). A thirteenth answer (Matt, 2026-11-19), after Story 22.7's throwaway run showed that `docker restart` kills the game without a world save: "Add Story 22.8 now: Small API story after 22.7: on API shutdown, stop a running game through the normal stop path (SIGTERM, wait up to 10 s, save measured < 1 s) before exiting; README notes the container stop grace period (Docker default 10 s; compose stop_grace_period / Kubernetes terminationGracePeriodSeconds). Verified in a throwaway container." (ADR-16). Its design (the stop before the scheduler shutdown, no start once the shutdown has begun, an 8-second stop timeout inside Docker's 10-second grace, the README only and no compose change) is the planner's and not reviewed yet.

**Order:** 22.1, 22.2, 22.3, 22.4, 22.7, 22.8, 22.5, 22.6. Story 22.7 was added after 22.3 (answer 12) and runs after 22.4 and before 22.5. Story 22.8 was added after 22.7 (answer 13) and runs after 22.7 and before 22.5.

**Dependencies:**

- Story 22.2 comes after 22.1: its `vintagestory_players_online` series reads the tracker 22.1 adds.
- Stories 22.3 and 22.4 both edit `services/api_settings.py`, `jobs/__init__.py` and the README's configuration table; 22.4 comes after 22.3 and uses the `apply_setting` function 22.3 adds (ADR-7).
- Stories 22.5 and 22.6 both edit `ApiSettingsPanel.tsx`, its test and `web/src/api/config.ts`; 22.6 comes after 22.5, and after 22.3 and 22.4, whose settings it edits.
- Story 22.7 comes after 22.4. It uses the shared pending-restart state of 22.2 and the throwaway-container steps of 22.3, and touches only API files (`services/game_config.py`, `services/server.py`, `main.py`, a new state store) and the README; 22.4 does not touch them. Stories 22.5 and 22.6 do not depend on 22.7 and 22.7 does not depend on them; it runs before them only to keep one branch at a time.
- Story 22.8 comes after 22.7. It edits the same `services/server.py` and `main.py` lifespan and the same README section 22.7 touched, and its shutdown stop runs 22.7's write-back after the exit; its branch starts from 22.7's. It touches no web file and no settings file, so 22.5 and 22.6 do not depend on it and it does not depend on them.
- Stories are run one after another. Each branch starts from the previous story's branch, and each pull request targets `main`; the merge order is the story order.

**Beads:** four in scope, each closed with an AAR by its story after merge: `VSS-bhw` in 22.2 (22.1 carries its first half), `VSS-29p` in 22.4 (22.3 carries its first half), `VSS-zws` in 22.7 (22.3 confirmed it), `VSS-9jv` in 22.5. Story 22.6 has no bead: it is the web half of `VSS-29p`'s settings. What planning found is in the stories (the change proposal lists it), not in new beads. Story 22.8 has no bead either: it was found inside the epic (Story 22.7's Run C) and is drawn down there.

**Product changes:** one new route (`GET /metrics`, open); one new field in the JSON metrics (`playersOnline`); two new API settings (`scheduled_restart_times`, `backup_keep_count`; the existing settings' API bounds do not change; amended 2026-11-19 by the maintainer's "Backups only + docs" decision, which dropped `log_archive_retention_days` and `log_archive_keep_min`); two new background jobs (`scheduled_restart_HHMM`, `disk_cleanup`); one new state file (`vsmanager/state/pending-config-edits.json`, Story 22.7); a stop of the running game when the manager shuts down (Story 22.8, no new setting; the shipped compose file is not changed); `TZ` documented; one new runtime dependency (`prometheus-client`). No existing route, field or status code changes. Nothing is breaking. Nothing is deleted by default: the game keeps its own log archives to 5, and old backups are deleted only when `backup_keep_count` is set above 0 (amended 2026-11-19, "Backups only + docs"; the plan was to delete old log archives by default).

### Current State

- Game CPU and memory are in the JSON metrics and uptime is in the server status, but there is no player count and no Prometheus endpoint, although the PRD describes one
- The game is restarted only by hand; there is no schedule and no warning to players
- The game moves each run's logs into `Logs/Archive/` and nothing deletes them; `/genbackup` files accumulate in `Backups/`
- Nobody has measured whether a stop's 10-second timeout leaves the world save enough time, and `VSS-zws` (does the game overwrite `serverconfig.json` edits made while it runs) is open
- Stopping or restarting the container kills the game without a world save: the API's shutdown does not stop it (found by Story 22.7's throwaway run)
- The API Settings tab cannot turn an interval job off, has no Metrics Collection field, caps the refresh intervals below the API's maximum, has two fallbacks that differ from the API defaults, and is shown to a Monitor key that cannot read it

### Target State

- The API counts players from the game's join and leave lines; the JSON metrics and a dashboard card show the count
- `/metrics` serves the game server's info, state, uptime, players and process metrics in the Prometheus format, read live, without a key
- Daily restart times, with warnings at 15, 5 and 1 minutes, restart a running game and never start a stopped one
- A daily cleanup deletes old log archives and, when asked, old backups, and never touches the world, mods or `BackupSaves`
- The stop time and `VSS-zws` are measured and recorded
- A `Port` or `Ip` change made while the game runs reaches the next start, even after a live setting change made the game rewrite its config
- Stopping, restarting or recreating the container stops the game through its normal stop first, so the world is saved
- Every interval job can be turned off and on in the UI, Metrics Collection has a field, the bounds and fallbacks match the API, and a Monitor key does not see the tab
- Restart times and the backup limit (`backup_keep_count`) are edited in the API Settings tab

---

### Story 22.1: Players Online Are Counted

**Sprint key:** `22-1-players-online-are-counted`
**Beads:** `VSS-bhw` (API-023), first half
**FRs:** FR287, FR288

As an **operator**,
I want **to see how many players are on the server**,
So that **I know whether anyone is playing before I restart or change something, and how busy the server is over time**.

**Acceptance Criteria:**

**Given** the game is running and prints a join line for `ExamplePlayer` (the `'{0} {1} joins.'` literal, with a documentation address such as `203.0.113.5:42420`)
**When** the line is read from the game's output
**Then** the count of players online is 1, and a second join line for another name makes it 2

*(Covers FR287; ADR-1 decision 2)*

**Given** `ExamplePlayer` is online
**When** the game prints `Player ExamplePlayer left.`
**Then** the count goes down by one; a leave line for a name not online, and a join line for a name already online (including `ExamplePlayer joined again, killing previous client.`), change nothing

*(Covers FR287; ADR-1 decisions 2 and 5)*

**Given** players are counted
**When** the game is started, stopped or exits by itself
**Then** the count is 0

*(Covers FR287; ADR-1 decision 3)*

**Given** a chat line whose text ends in "joins."
**When** it is read
**Then** it is not counted

*(Covers FR287; ADR-1 decision 6)*

**Given** players join and leave
**When** I read the API's log at INFO and the API responses
**Then** no player name appears in either

*(Covers FR287; ADR-1 decision 4)*

**Given** the game is running with two players online
**When** an authenticated client reads `GET /api/v1alpha1/metrics/current` and `/history` after a collection
**Then** the snapshots have `playersOnline: 2`; with the game stopped they have `playersOnline: null`; every other field is as before

*(Covers FR288; ADR-2 decisions 1 and 2)*

**Given** the dashboard
**When** the game is running, and when it is stopped
**Then** a Players card shows the count, or "Server stopped", next to the Uptime card, at every width the dashboard supports

*(Covers FR288; ADR-2 decision 3)*

**Given** one anonymised join line and one leave line from a real server, provided by the maintainer
**When** they are added as test cases
**Then** they are counted (manual check, reserved for the maintainer, ticked only on his confirmation)

*(Covers FR287; ADR-1 decision 2, ADR-14 decision 4)*

**Tasks:**

- [ ] `PlayerTracker` with the three patterns, the name set and the reset, and unit tests for every pattern and edge case listed in Epic 22 ADR-1 decision 6
- [ ] Wire the tracker into `ServerService`: every output line after the console append, resets on start, stop and exit; tests with a stubbed process (ADR-1 decisions 1 and 3)
- [ ] `players_online` in `MetricsSnapshot` and `playersOnline` in the responses, with API tests; a `feat(api)` commit with the release note (ADR-2 decisions 1 and 4)
- [ ] `playersOnline` in the web type and the Players card on the dashboard, with unit tests; a `feat(web)` commit with the release note (ADR-2 decisions 2 and 3)
- [ ] Ask the maintainer for the anonymised sample lines; fix the prefix pattern from them and add them as test cases (ADR-1 decision 2; manual check)

---

### Story 22.2: A Prometheus `/metrics` Endpoint

**Sprint key:** `22-2-prometheus-metrics-endpoint`
**Beads:** `VSS-bhw` (API-023), closes here
**FRs:** FR289, FR290, FR291, FR306

As an **operator who runs Prometheus and Grafana**,
I want **the manager to serve the game server's metrics in the Prometheus format**,
So that **I can graph players, CPU, memory and uptime, and alert when the server is down, with the tools I already use**.

**Acceptance Criteria:**

**Given** a running API
**When** a client without an API key requests `GET /metrics`
**Then** the answer is 200 with `Content-Type` `text/plain; version=0.0.4; charset=utf-8` (prometheus-client's `CONTENT_TYPE_LATEST`) and a body in the Prometheus text format

*(Covers FR289; ADR-3 decisions 2 and 6)*

**Given** the game is running, version 1.22.7, with two players, `MaxClients` 16 and no pending restart
**When** `/metrics` is scraped
**Then** it has `vintagestory_server_info{version="1.22.7"} 1`, `vintagestory_server_up 1`, `vintagestory_server_state{state="running"} 1` and a 0 series for every other state, `vintagestory_server_uptime_seconds`, `vintagestory_players_online 2`, `vintagestory_players_max 16`, `vintagestory_server_pending_restart 0`, `vintagestory_server_process_cpu_seconds_total` and `vintagestory_server_process_resident_memory_bytes`, each with `# HELP` and `# TYPE`, and the manager's `process_*` and `python_info` series

*(Covers FR289; ADR-4 decisions 1, 3 and 4)*

**Given** the game is installed and stopped
**When** `/metrics` is scraped
**Then** `vintagestory_server_up` is 0, `vintagestory_players_online` is 0, and the uptime and `server_process_*` series are absent

*(Covers FR290; ADR-4 decision 2)*

**Given** `metrics_collection_interval` is 0 (the collection job is off)
**When** `/metrics` is scraped twice a few seconds apart while the game runs
**Then** both answers carry current values, and the CPU counter does not go down

*(Covers FR290; ADR-3 decision 4)*

**Given** reading `MaxClients` (or another single source) raises
**When** `/metrics` is scraped
**Then** the answer is 200 without that source's series, and one WARNING is logged

*(Covers FR290; ADR-3 decision 5)*

**Given** the web UI is served by the API
**When** `/metrics` is requested
**Then** the metrics answer it, not the web UI's page

*(Covers FR289; ADR-3 decision 2)*

**Given** the README
**When** I read its metrics section
**Then** it lists each series with its meaning, says that the endpoint is open and how to keep it off the internet, and gives a Prometheus `scrape_configs` example with `metrics_path: /metrics` and a placeholder target

*(Covers FR291; ADR-3 decision 6)*

**Given** the API in a container (the CI E2E stack)
**When** the API E2E tests run
**Then** one test scrapes `/metrics` without a key and finds `vintagestory_server_up`

*(Covers FR289)*

**Given** an admin saves a game setting that needs a restart (the port or IP address)
**When** `/healthz`, the mods list and `/metrics` are read, and then the server is restarted
**Then** all three show a pending restart until the restart, which clears it (game settings and mods share one pending-restart state)

*(Covers FR306; pulled in during the story's validation, backlog drawdown)*

**Tasks:**

- [ ] Add `prometheus-client` with a minimum version and the next major excluded (`uv add`, lock updated), with a `build(api)` commit (Epic 22 ADR-3 decision 1)
- [ ] The custom collector and the project registry with the default collectors; unit tests for each series with the game running, stopped and not installed, and for a failing source (ADR-3 decisions 3 to 5, ADR-4)
- [ ] The root `GET /metrics` route without authentication; API tests for the content type, no key, and the web UI not answering it; a `feat(api)` commit with the release note (ADR-3 decision 2)
- [ ] An API E2E test that scrapes `/metrics` on the E2E stack (`api/tests/e2e`, base URL default `http://localhost:9080`) (FR289)
- [ ] The README's metrics section with the scrape example; the PRD's post-MVP line updated to say where it is built (ADR-3 decision 6)
- [ ] One pending-restart state for game settings and mods, with tests through `/healthz`, the mods list and `/metrics`; a `fix` commit (FR306)

---

### Story 22.3: Scheduled Restarts

**Sprint key:** `22-3-scheduled-restarts`
**Beads:** `VSS-29p` (API-011), first half; `VSS-zws` (API-073), checked here, fixed and closed by Story 22.7 (answer 12)
**FRs:** FR292, FR293, FR294, FR295, FR296

As an **operator**,
I want **the game server to restart at the times I set, after warning the players**,
So that **it runs fresh every day without me being there, and nobody is surprised**.

**Acceptance Criteria:**

**Given** an Admin key
**When** it sets `scheduled_restart_times` to `["16:00", "04:00", "04:00"]`
**Then** the setting is saved as `["04:00", "16:00"]`, and `GET /config/api` returns it

*(Covers FR292; ADR-5 decision 2)*

**Given** an Admin key
**When** it sets `scheduled_restart_times` to a list with `4:00`, `24:00`, `04:60`, a non-string, 25 entries, or `04:00` and `04:10`
**Then** the answer is 400 `API_SETTING_INVALID` with a message naming the problem, and the saved value does not change

*(Covers FR292; ADR-5 decision 2, ADR-6 decision 6)*

**Given** `scheduled_restart_times` is `["04:00"]`
**When** the API starts, or the setting is saved
**Then** the job `scheduled_restart_0400` is registered with a next run at 03:45 in the container's time zone, and is listed by `GET /api/v1alpha1/jobs`; saving `[]` removes it at once

*(Covers FR295; ADR-6 decisions 1 and 7, ADR-7)*

**Given** the scheduler cannot apply the saved times
**When** the setting is saved
**Then** the value is saved and the answer is `API_SETTING_NOT_APPLIED`, as for an interval

*(Covers FR295; ADR-7 decision 2)*

**Given** the game is running when `scheduled_restart_0400` fires
**When** the sequence runs (with a fake sleep in tests)
**Then** `/announce Server restarts in 15 minutes`, then `in 5 minutes`, then `in 1 minute` are sent at the right offsets, and the restart goes through `ServerService.restart_server()`, which clears the pending-restart flag; the log line says how many players were online

*(Covers FR293, FR294; ADR-6 decisions 1, 2, 4 and 5)*

**Given** the game is stopped when the job fires, or stops during the warnings
**When** the sequence reaches its next step
**Then** nothing more is announced, the game is not started, and `scheduled_restart_skipped reason=not_running` is logged

*(Covers FR293, FR294; ADR-6 decision 3)*

**Given** a manual restart (or start, stop, install, uninstall) holds the lifecycle lock when the restart is due
**When** the scheduled restart runs
**Then** it does not wait, does not restart, and logs `scheduled_restart_skipped reason=lifecycle_busy`

*(Covers FR293; ADR-6 decision 4)*

**Given** a throwaway container with a fresh world (never the dev stack)
**When** the game is stopped three times
**Then** the story records each stop's duration, whether it ended within 10 seconds and whether the log shows the world saved; if any stop needs more than 10 seconds or cuts the save short, the story stops for the maintainer's decision before the restart job is merged

*(Covers FR296; ADR-8 decisions 1 and 2, ADR-14)*

**Given** the same throwaway container
**When** `Port` is changed through the API while the game runs, a live `/serverconfig` command is sent, the game is stopped, and then started again
**Then** the story records what `serverconfig.json` holds after the stop and after the start, and the maintainer decides the fix (answered: Story 22.7, ADR-15)

*(Covers FR296; ADR-8 decision 3)*

**Given** the README
**When** I read its configuration table and the scheduled restarts paragraph
**Then** `TZ` is documented (UTC when unset, an example value), and the paragraph says when the warnings come, that a stopped server is not started, that a time less than 15 minutes ahead first runs the next day, and how a restart is skipped

*(Covers FR292, FR293; ADR-5 decision 4, ADR-6 decision 6)*

**Given** a scheduled restart on a real deployment
**When** the maintainer is in the game at the warning times
**Then** he sees the three warnings and the restart (manual check, reserved for the maintainer)

*(Covers FR294; ADR-14 decision 4)*

**Tasks:**

- [ ] The `scheduled_restart_times` setting with its validator and list handling in `update_setting`, with tests (Epic 22 ADR-5 decisions 1 to 3, ADR-6 decision 6)
- [ ] `apply_setting` and `apply_restart_schedule`, `SCHEDULED_SETTINGS`, the router's callback and start-up registration; tests for add, replace, remove and the not-applied path (ADR-7 decisions 1 to 3)
- [ ] The warning and restart sequence with injectable sleep, the skip rules and the log lines; tests for each path; a `feat(api)` commit with the release note (ADR-6 decisions 1 to 5)
- [ ] The throwaway-container run: stop time and world save, and `VSS-zws`; record the results in the story and the ADR; stop for the maintainer if the stop is too slow (ADR-8)
- [ ] The README: `TZ` and the scheduled restarts paragraph (ADR-5 decision 4, ADR-6 decision 6)

---

### Story 22.4: Log Archive and Backup Cleanup

**Sprint key:** `22-4-log-archive-and-backup-cleanup`
**Beads:** `VSS-29p` (API-011), closes here
**FRs:** FR297, FR298, FR299

**Amended by the maintainer (Matt, 2026-11-19, "Backups only + docs"):** the story's Task 3 found that the game keeps at most 5 log archives itself, so the log-archive cleanup and its two settings (`log_archive_retention_days`, `log_archive_keep_min`) are dropped. The story keeps the opt-in `backup_keep_count` (default 0 = keep all) and the daily `disk_cleanup` job for it at 03:00 container time, and the README says the game keeps 5 log archives itself and who rotates what. The criteria and tasks below about archives, and the release note that archives are deleted by default, no longer apply (kept as history; the story file marks each one). The feature commit's subject is now about deleting old backups when a limit is set.

As an **operator**,
I want **old log archives, and old backups when I ask for it, deleted every day**,
So that **the disk does not fill up over months of restarts, and my world and its own backups are never touched**.

**Acceptance Criteria:**

**Given** `serverdata/Logs/Archive/` holds 20 archive directories, one per day for the last 20 days, and the default settings
**When** the cleanup runs
**Then** the archives older than 14 days are deleted, the newest 14 remain, and each deletion is logged with its name and size

*(Covers FR297, FR299; ADR-9 decisions 1, 3 and 6)*

**Given** 7 archives, all older than 14 days, and `log_archive_keep_min` 5
**When** the cleanup runs
**Then** the newest 5 remain

*(Covers FR297; ADR-9 decision 3)*

**Given** `log_archive_retention_days` is 0
**When** the cleanup runs
**Then** no archive is deleted

*(Covers FR297; ADR-9 decision 1)*

**Given** an entry in `Archive/` whose name does not match `YYYY-MM-DD_HH_MM_SS`, a file in `Archive/`, or an archive that is a symbolic link
**When** the cleanup runs
**Then** it is not deleted; a symbolic link is logged at WARNING

*(Covers FR298; ADR-9 decisions 3 and 5)*

**Given** `serverdata/Backups/` holds 8 files and a directory, and `backup_keep_count` is 3
**When** the cleanup runs
**Then** the 3 newest files and the directory remain; with `backup_keep_count` 0 (the default) all 8 files remain

*(Covers FR298; ADR-9 decisions 1 and 4)*

**Given** files in `BackupSaves/`, `Saves/`, `Mods/`, `Playerdata/` and the live `server-*.log` files, and `Logs/Archive` itself a symbolic link to a directory outside `serverdata`
**When** the cleanup runs with every limit at its smallest
**Then** none of them is deleted

*(Covers FR298; ADR-9 decision 5)*

**Given** one entry cannot be deleted (permission denied)
**When** the cleanup runs
**Then** the error is logged, the other entries are still handled, and the summary line counts what was deleted

*(Covers FR299; ADR-9 decision 6)*

**Given** the API starts
**When** I list the jobs
**Then** `disk_cleanup` is registered as a cron job at 03:00 in the container's time zone, and it reads the limits when it runs, so a changed limit applies at the next run

*(Covers FR297; ADR-7 decisions 3 and 4, ADR-9 decision 6)*

**Given** each cleanup setting
**When** an Admin key saves a value outside its bounds
**Then** the answer is 400 `API_SETTING_INVALID` and nothing changes

*(Covers FR297, FR298; ADR-9 decision 1)*

**Given** a throwaway container (never the dev stack)
**When** the game is started and stopped several times
**Then** the story records the archive directory names the game writes and that it deletes none of them, and the cleanup deletes the expected ones

*(Covers FR297; ADR-9 decision 7, ADR-14)*

**Given** the README
**When** I read "Logs and disk use"
**Then** it says what the game rotates, what the cleanup deletes and when, the three settings, and how to rotate the manager's stdout with Docker's log options

*(Covers FR299; ADR-10)*

**Tasks:**

- [ ] The three cleanup settings with bounds and tests (Epic 22 ADR-9 decision 1)
- [ ] `DiskCleanupService` with the archive and backup rules, the path and symlink checks, and tests on temporary directories for every case above (ADR-9 decisions 2 to 5)
- [ ] The `disk_cleanup` cron job, always registered, with its log lines and tests; a `feat(api)` commit with the release note, saying that archives older than 14 days are now deleted by default (ADR-9 decision 6, ADR-7 decisions 3 and 4)
- [ ] The throwaway-container run for the archive names and the game's own behaviour; record the result in the story and the ADR (ADR-9 decision 7)
- [ ] The README's "Logs and disk use" section and the settings rows (ADR-10)

---

### Story 22.5: Interval Fields Can Turn Jobs Off

**Sprint key:** `22-5-interval-fields-can-turn-jobs-off`
**Beads:** `VSS-9jv` (UI-085)
**FRs:** FR300, FR301, FR302, FR303

As an **administrator**,
I want **to turn each background job off and on, and set how often metrics are collected, from the API Settings tab**,
So that **I do not have to call the API by hand for what the API already allows**.

**Acceptance Criteria:**

**Given** the API Settings tab with Mod List Refresh at 4h
**When** I turn its On switch off
**Then** 0 is saved, the duration input is replaced by "Off", one success toast is shown, and the job is no longer listed in Scheduled Jobs

*(Covers FR300; ADR-11 decision 1)*

**Given** Mod List Refresh is off (saved 0)
**When** I load the tab, and then turn the switch on
**Then** it shows Off on load, and turning it on saves 14400 and shows the duration input with 4h

*(Covers FR300; ADR-11 decisions 1 and 4)*

**Given** the API Settings tab
**When** I look at Refresh Intervals
**Then** there is a Metrics Collection field with an On switch, accepting 1 second to 1 hour, defaulting to 10 seconds, whose help text says the dashboard charts stop updating when it is off and `/metrics` keeps working

*(Covers FR301; ADR-11 decisions 2 and 3)*

**Given** Mod List Refresh or Server Versions Refresh
**When** I enter 30s, 2d or 400d
**Then** 30s and 400d are refused with the field's bounds message and 2d is saved (the bounds are 60 seconds to 365 days)

*(Covers FR302; ADR-11 decision 2)*

**Given** the settings have not loaded a value for Server Versions Refresh or Enforce Env on Restart
**When** the fields render
**Then** they show 1 day and off, the API's defaults, from one web constant

*(Covers FR302; ADR-11 decision 4)*

**Given** a save that fails, or that answers `API_SETTING_NOT_APPLIED`
**When** I use a switch
**Then** one toast is shown, as for the duration input

*(Covers FR300; ADR-11 decision 6)*

**Given** a Monitor key
**When** I open Settings, or a link to its API Settings tab
**Then** the API Settings tab is not shown and UI Preferences is shown; with an Admin key the tab is shown as before

*(Covers FR303; ADR-12)*

**Tasks:**

- [ ] The optional off/on pair in `DurationSettingField`, with unit tests; other users unchanged (Epic 22 ADR-11 decision 5)
- [ ] The switches on the two refresh fields, the bounds and the fallbacks from one constant of API defaults; unit tests; a `feat(web)` commit with the release note (ADR-11 decisions 1, 2 and 4)
- [ ] The Metrics Collection field with its help text; unit tests (ADR-11 decisions 2 and 3)
- [ ] Hide the API Settings tab for Monitor, with the fallback for a stored or linked tab; unit tests for both roles; a `fix(web)` commit with the release note (ADR-12)
- [ ] E2E: turn a job off and on in the tab and restore the saved value from a snapshot; the Monitor check with a precondition skip; base URL default `http://localhost:9080` (ADR-11, ADR-12, ADR-14 decision 3)

---

### Story 22.6: Restart and Cleanup Settings in the UI

**Sprint key:** `22-6-restart-and-cleanup-settings-in-the-ui`
**Beads:** none (the web half of `VSS-29p`'s settings, closed by Story 22.4)
**FRs:** FR304, FR305

**Amended (2026-11-19), following the maintainer's decision "Backups only + docs" (Matt, 2026-11-19; Story 22.4, ADR-9, ADR-10 and ADR-13):** `log_archive_retention_days` and `log_archive_keep_min` do not exist, so the tab shows one cleanup field, `backup_keep_count` (0 to 1000, 0 = keep all). The fourth criterion and the first and third tasks below say so.

As an **administrator**,
I want **to set the restart times and the backup limit in the API Settings tab**,
So that **I can schedule restarts and control disk use without calling the API**.

**Acceptance Criteria:**

**Given** no restart time is set
**When** I open the API Settings tab
**Then** a Scheduled Restarts group says no restart is scheduled and offers Add time; its help text says the times are in the server's time zone (`TZ`, UTC unless set), that players are warned at 15, 5 and 1 minutes, that a stopped server is not started, and that a time less than 15 minutes ahead first runs the next day

*(Covers FR304; ADR-13 decision 1)*

**Given** the Scheduled Restarts group
**When** I add 04:00, add 16:00, change 16:00 to 18:30, and remove 04:00
**Then** each change saves the whole list once (`["04:00"]`, `["04:00", "16:00"]`, `["04:00", "18:30"]`, `["18:30"]`), with one toast each

*(Covers FR304; ADR-13 decision 1)*

**Given** the API answers 400 for a list (for example two times 10 minutes apart)
**When** I save it
**Then** the edited list stays on screen with the API's message, and one error toast is shown

*(Covers FR304; ADR-13 decision 1)*

**Given** the API Settings tab
**When** I look at Backup Cleanup
**Then** it has one field, Backups kept (`backup_keep_count`, 0 to 1000, the API's bounds), whose help text says that 0 keeps all, that deletion is permanent, and that the cleanup runs every day at 03:00 server time; saving it shows one toast

*(Covers FR305; ADR-13 decision 2)*

**Given** a phone width (320px) and a desktop width
**When** I open the tab
**Then** the two groups fit without sideways scrolling, and each input and button is at least 44px tall below 1024px

*(Covers FR304, FR305)*

**Tasks:**

- [ ] The two settings in the web's API settings type and client, with tests (Epic 22 ADR-13 decision 4)
- [ ] The Scheduled Restarts group (time list, add, change, remove, one save per change, error state), with unit tests; a `feat(web)` commit with the release note (ADR-13 decision 1)
- [ ] The Backup Cleanup group (one field, `backup_keep_count`), with unit tests; a `feat(web)` commit with the release note (ADR-13 decision 2)
- [ ] E2E: set and clear a restart time and the backup limit in the tab, restoring the saved values from a snapshot, at 320px and desktop width; base URL default `http://localhost:9080` (ADR-13, ADR-14 decision 3)

---

### Story 22.7: Restart-Required Settings Survive a Live Change

**Sprint key:** `22-7-restart-required-settings-survive-a-live-change`
**Beads:** `VSS-zws` (API-073), closes here
**FRs:** FR307

As an **administrator**,
I want **a `Port` or `Ip` change I save while the game server runs to be the one the next start uses**,
So that **a later live setting change cannot quietly undo it while "Restart required" goes away as if it had worked**.

**Acceptance Criteria:**

**Given** the game is running and `serverconfig.json` holds `Port` 42420
**When** an Admin key sets `Port` to 42421, and the game then writes its own config with 42420 (as it does after a live `/serverconfig` command), and the game is stopped
**Then** after the exit `serverconfig.json` holds 42421 again, `pending_config_edits_reapplied trigger=exit` is logged, and the next start runs with 42421; after that start the pending edit is gone

*(Covers FR307; ADR-15 decisions 1, 3 and 4)*

**Given** the same pending edit and the game exits by itself (a crash or `/stop`)
**When** the exit is seen
**Then** the file holds 42421 again before anything starts the game; a Start, a Restart, a scheduled restart and auto-start each start with 42421

*(Covers FR307; ADR-15 decision 3)*

**Given** a pending edit and the API restarts while the game is not running (the container was restarted)
**When** the API starts
**Then** the edit is read from `vsmanager/state/pending-config-edits.json`, written to `serverconfig.json` before auto-start (`trigger=api_start`), and with auto-start off the file holds 42421 while the game stays stopped

*(Covers FR307; ADR-15 decisions 2 and 3)*

**Given** a pending `Port` edit of 42421
**When** `Port` is set again (to 42422 while the game runs, or to 42423 while it is stopped)
**Then** the pending edit holds 42422 in the first case and is dropped in the second, and an older value is never written over a newer one; a pending `ServerDescription` clear followed by a live `ServerDescription` change is dropped

*(Covers FR307; ADR-15 decision 4)*

**Given** a restart-required change saved while no game process lives
**When** it is saved
**Then** nothing is recorded (the game reads the file at its next start), and behaviour is as today

*(Covers FR307; ADR-15 decision 1)*

**Given** a pending edit and `serverconfig.json` cannot be read or written at a start
**When** the start runs
**Then** `pending_config_edits_reapply_failed` is logged at ERROR, the start goes on, the edit is kept, and the pending-restart flag is set again after the start so "Restart required" stays

*(Covers FR307; ADR-15 decision 5)*

**Given** the state file is missing, empty, not JSON, or names an unknown setting
**When** the API starts
**Then** it starts normally; a bad file or unknown key is logged at WARNING and ignored

*(Covers FR307; ADR-15 decision 2)*

**Given** a setting managed by a `VS_CFG_*` variable
**When** an Admin key tries to change it
**Then** it is refused as today and nothing is recorded; the write-back never reads `VS_CFG_*`

*(Covers FR307; ADR-15 decision 6)*

**Given** a throwaway container (never the dev stack)
**When** the steps of Story 22.3's `VSS-zws` check are repeated with the fix: `Port` 42420 -> 42421 while running, a live `ServerName` change, stop, start
**Then** the story records `serverconfig.json` after each step, the file holds 42421 after the stop, and the game listens on 42421 after the start; the same after `docker restart` of the container between the live change and the start

*(Covers FR307; ADR-15, ADR-14)*

**Tasks:**

- [ ] The `PendingConfigEdits` store (record, replace, drop, load and atomic save in `vsmanager/state/`, the load rules), with unit tests on temporary directories (Epic 22 ADR-15 decision 2)
- [ ] Record and drop edits in `GameConfigService.update_setting` and `_update_config_file` (a process lives, the same key changed again, nothing for env-managed keys), with tests (ADR-15 decisions 1, 4 and 6)
- [ ] Write back after exit (stop and monitor), before every spawn and at API start before auto-start; drop after a successful start; the failure rule and the log lines; tests with a stubbed process for each path, including a scheduled restart and auto-start; a `fix(api)` commit with the release note (ADR-15 decisions 3 to 5 and 7)
- [ ] The throwaway-container run (a `vss-22-7-*` container on its own `127.0.0.1` port, not 9080, 18080, 18081 or 18090; plain `docker build`/`docker run`, no compose, no bind mount, placeholder keys, removed with its image afterwards; never the dev stack at `http://localhost:9080` or its `./data`): repeat Story 22.3's `VSS-zws` steps with the fix and with a container restart in between; record the reads in the story and in ADR-15 (ADR-14)
- [ ] The README (it has no game settings section today): a short paragraph after the Configuration table saying that a restart-required change made while the server runs is kept until the next start, and that the Game Settings page shows the game's value until the server stops (ADR-15 consequences)
- [ ] `just check` green and the story moved to review; `VSS-zws` closed with an AAR after merge

### Story 22.8: Stopping the Container Saves the World

**Sprint key:** `22-8-container-stop-saves-the-world`
**Beads:** none (found inside the epic by Story 22.7's Run C; backlog drawdown, answer 13)
**FRs:** FR308

As an **administrator**,
I want **stopping or restarting the manager's container to stop the game server the normal way first**,
So that **the world is saved and players do not lose their progress when I upgrade, restart or stop the container**.

**Acceptance Criteria:**

**Given** the game server is running
**When** the API shuts down (the container gets SIGTERM)
**Then** before the scheduler is shut down, the game is stopped through the normal stop path (SIGTERM, a kill only if it has not exited after 8 seconds), and the log shows `api_shutdown_stopping_game`, the stop's own lines, `api_shutdown_game_stopped`, then `scheduler_stopped` and `api_shutting_down`

*(Covers FR308; ADR-16 decisions 1, 2, 3, 5 and 8)*

**Given** no game process lives (never started, stopped, or exited)
**When** the API shuts down
**Then** nothing is stopped, no service is built, and the shutdown is as today

*(Covers FR308; ADR-16 decisions 1 and 8)*

**Given** a game that does not exit on SIGTERM
**When** the API shuts down
**Then** it is killed after 8 seconds (`server_stop_timeout`, `server_killed`) and the shutdown goes on

*(Covers FR308; ADR-16 decision 5)*

**Given** a scheduled restart holding the lifecycle lock, or a scheduled restart sequence in its warnings
**When** the API shuts down
**Then** the game is not started again: the restart's start is refused (`start_server_failed reason=api_shutting_down`), the sequence ends without a start, and the game ends the shutdown stopped

*(Covers FR308; ADR-16 decisions 3 and 4)*

**Given** the shutdown stop fails
**When** the API shuts down
**Then** `api_shutdown_game_stop_failed` is logged at ERROR and the scheduler and the mod service are still shut down

*(Covers FR308; ADR-16 decisions 1 and 8)*

**Given** a restart-required game setting saved while the game ran, and the game rewrote `serverconfig.json` after a live change (Story 22.7)
**When** the API shuts down
**Then** `serverconfig.json` holds the saved value after the stop (`pending_config_edits_reapplied trigger=exit`)

*(Covers FR308; ADR-16 decision 7)*

**Given** a throwaway container (never the dev stack) with a running game
**When** it is stopped with `docker stop` (and restarted with `docker restart`, with an open console WebSocket, and with `docker stop -t` shorter and longer than the default)
**Then** the story records the game's save and stop lines in `server-main.log`, the API's lines in order, the container's exit inside the grace period, and the process tree

*(Covers FR308; ADR-16 decision 9, ADR-14)*

**Given** the README
**When** an operator reads how to run the container
**Then** it says that stopping or restarting the container saves the world first, that the manager waits up to 8 seconds for the game, and that the stop grace period should stay at Docker's default of 10 seconds or more (`docker stop -t`, compose `stop_grace_period`, Kubernetes `terminationGracePeriodSeconds`)

*(Covers FR308; ADR-16 decision 6)*

**Tasks:**

- [ ] `ServerService.stop_for_api_shutdown()` (the flag, the lock, the normal stop with 8 s, the log lines), the refusal in `_start_server_locked`, and the module-level `stop_game_server_for_api_shutdown()`, with tests on a fake process (graceful, killed, not running, a restart holding the lock, a sequence in its warnings, 22.7's write-back) (Epic 22 ADR-16 decisions 1 to 5, 7 and 8)
- [ ] The lifespan calls it after `yield` and before the scheduler shutdown, inside its own guard; an autouse conftest recorder keeps every lifespan test away from the real singleton; lifespan tests for the order and the failure; a `fix(api)` commit with the release note (ADR-16 decisions 1, 3 and 8)
- [ ] The throwaway-container run (a `vss-22-8-*` container and image on its own `127.0.0.1` port, not 9080, 18080, 18081, 18090, 18092 or 18094; plain `docker build`/`docker run`, no compose, no bind mount, no `--env-file`, placeholder key, removed afterwards; never the dev stack or `./data`): `docker stop`, `docker restart`, an open console WebSocket, `docker stop -t` shorter and longer than 10 s, the process tree; recorded in the story and in ADR-16 (ADR-16 decision 9, ADR-14)
- [ ] The README: stopping and restarting the container, and the stop grace period (ADR-16 decision 6)
- [ ] `just check` green and the story moved to review; the maintainer's manual check stays unticked

---

## Epic 23: Config File Editing

**Goal:** An administrator can read every mod config the game accepts, including those with comments, and can edit and save config files in the file browser while the game server is stopped, with the text kept exactly as typed. Every edit is kept as history that can be compared and restored. A Monitor key sees Game Settings read-only instead of fields that fail on save. Five open beads are closed.

**Architecture:** `architecture/epic-23-config-file-editing.md` (ADR-1 to ADR-9, with the facts checked at `fc525885`). There is no preparation story. The one thing planning could not check, how `pyjson5` reports an error's position, is Story 23.1's first task.

**Decided by the maintainer (Matt, 2026-11-19):** the scope `VSS-ato4`, `VSS-glz` and `VSS-hb4d`, with `VSS-o8s` and `VSS-7z3` pulled in. Eight answers in two rounds (`sprint-change-proposal-2026-11-19-epic-23.md`, section 5):

1. JSON5 through the `pyjson5` library (ADR-1).
2. `serverconfig.json` can be edited, but only as strict JSON, and a save drops the Story 22.7 pending edits it changes (ADR-1 decision 5, ADR-4 decision 7).
3. CodeMirror 6 as the editor (ADR-5).
4. Every `.json` file Admin can read can be edited (ADR-4).
5. Errors are checked by an API endpoint as the admin types (ADR-4 decision 10, ADR-5).
6. History limits are two API settings (ADR-7 decision 5).
7. Revisions are compared with CodeMirror's merge view (ADR-8).
8. Game Settings fields are disabled for Monitor, with a note (ADR-6).

Planner decisions not reviewed yet: the read's new fields (ADR-2), the save's lock, state and version rules (ADR-4 decisions 4 to 6), the history store and its failure rule (ADR-7 decisions 1 to 4), the `useIsAdmin` hook (ADR-6 decision 3), and the UI flows of ADR-5 and ADR-8.

**Order:** 23.1, 23.2, 23.3, 23.4, 23.5, 23.6, 23.7.

**Dependencies:**

- Story 23.4 comes after 23.1: the save uses 23.1's parser and returns the `version` that 23.1's read introduces.
- Story 23.5 comes after 23.2, 23.3 and 23.4. It edits `FileViewer.tsx` and `FileManagerPanel.tsx` after 23.2's refactor, uses 23.3's `useIsAdmin`, and calls 23.4's routes.
- Story 23.6 comes after 23.4 and hooks into its save path (`services/config_files.py`, `routers/config.py`). It adds two settings to `services/api_settings.py`.
- Story 23.7 comes after 23.5 and 23.6: it adds to the viewer header 23.5 built, calls 23.6's routes, and edits `ApiSettingsPanel.tsx`.
- Stories 23.2 and 23.3 are web-only and independent of 23.1. They run second and third so that 23.5 starts on top of both.
- Stories are run one after another. Each branch starts from the previous story's branch, each pull request targets `main`, and the merge order is the story order.

**Beads:** five in scope, each closed with an AAR by its story after merge: `VSS-ato4` in 23.1, `VSS-o8s` in 23.2, `VSS-7z3` in 23.3, `VSS-glz` in 23.5 (23.4 carries its first half), `VSS-hb4d` in 23.7 (23.6 carries its first half). What planning found is in the stories (the change proposal lists it), not in new beads.

**Product changes:**

- New routes: `PUT /config/files/{path}`, `POST /config/files/validate`, and `GET` and `POST .../restore` under `/config/history/{path}`, all Admin only.
- New fields in the config file read: `parseError` for every role; `text` and `version` for Admin.
- Two new API settings: `config_history_keep_count` and `config_history_max_age_days`.
- A new state directory: `vsmanager/state/config-history/`.
- A new runtime API dependency, `pyjson5`, and new web dependencies in the `@codemirror` scope, loaded on demand.
- The viewer accepts JSON5, so files that showed a parse error now show their content.
- No existing route, field or status code changes, and nothing is breaking.

### Current State

- A mod config with comments or trailing commas shows a parse error; the viewer's fallback shows an escaped string under `_raw` and `_parse_error` keys, and Monitor sees the whole file hidden
- Config files can only be read; changing one means a shell on the host, while the game is stopped, with no record of the earlier text
- The file browser keeps paths as slash-joined strings, and its breadcrumb splits them on `/`
- A Monitor key sees Game Settings as editable and gets "Update failed" after typing

### Target State

- The viewer reads JSON5. An unparseable file shows its error, with its line and column, and Admin sees its text
- Admin edits a config file in a highlighting editor that checks it as they type. Saving is possible only while the game server is stopped, and only if nobody else changed the file meanwhile. The text is written exactly as typed
- `serverconfig.json` stays strict JSON, and a save of it is not undone by Story 22.7's write-back
- Every save keeps the replaced text. Admin can list, compare and restore earlier versions, within limits set in API Settings
- Paths are lists of names from the panel to the API client
- Monitor sees Game Settings read-only, with a note

---

### Story 23.1: Configs with Comments Can Be Viewed

**Sprint key:** `23-1-configs-with-comments-can-be-viewed`
**Beads:** `VSS-ato4` (API-097)
**FRs:** FR309, FR310, FR311, FR326 (JSON5 part)

As an **administrator**,
I want **the file browser to show mod configs that have comments**,
So that **I can read the configs the game itself accepts instead of a parse error**.

**Acceptance Criteria:**

**Given** a `ModConfig` file with `//` line comments, a `/* */` block comment, a comment after the last property, a trailing comma, `null` in an array and a string value containing `http://example.com//path`
**When** an Admin key and a Monitor key read it
**Then** both get the parsed `content`, and the string value keeps its `//`; Monitor's content is redacted key by key (a `password` key reads `"[redacted]"`, other values are unchanged)

*(Covers FR309; ADR-1 decisions 1 and 3, ADR-2 decision 2)*

**Given** a file with single-quoted strings and unquoted keys
**When** it is read
**Then** it parses

*(Covers FR309; ADR-1 decision 1)*

**Given** a file that nests 201 levels, and a file holding `Infinity`
**When** they are read
**Then** each answers 200 with `_raw`/`_parse_error` and `parseError` ("Nested more than 200 levels deep", "Infinity and NaN cannot be shown"), and never a 500

*(Covers FR309; ADR-1 decisions 3 and 4)*

**Given** a file with a missing comma on line 3
**When** an Admin key reads it
**Then** `parseError` has the message, `line: 3` and the column; `content` keeps `_raw` (the text) and `_parse_error`; `text` is the text and `version` is the SHA-256 of the bytes; for a Monitor key `_raw` is `"[redacted]"` and there is no `text` or `version`

*(Covers FR310, FR311; ADR-1 decision 2, ADR-2 decision 1)*

**Given** a file that parses
**When** an Admin key reads it
**Then** `text` is the file's text with its comments (BOM dropped), `version` is the SHA-256 of its bytes (BOM included), and `parseError` is null; a Monitor key gets neither `text` nor `version`

*(Covers FR311; ADR-2 decision 1)*

**Given** a file that does not parse
**When** it is opened in the file browser
**Then** a warning shows the message with line and column; Admin sees the text below it in plain monospace; Monitor sees "The text of a file that cannot be parsed is shown only to an Admin key."

*(Covers FR310; ADR-2 decision 3)*

**Tasks:**

- [ ] Add `pyjson5` (`>=2.0.1,<3`, a `build(api)` commit) and find how its errors expose the position (attribute, `args` or message); pin it in a test (ADR-1 decisions 2 and 7)
- [ ] `services/config_parse.py`: `parse_config_text` with `strict`, `ConfigParseError` with line and column, `maxdepth`, the Infinity/NaN rule; unit tests from ADR-9 decision 4's fixture; remove `_nesting_depth_exceeds` (ADR-1 decisions 1 to 4)
- [ ] `read_file` uses it and returns `parseError`, plus `text` and `version` for Admin; router docstring; API tests for both roles; a `fix(api)` commit "show mod configs that contain comments" (ADR-2 decisions 1 and 2)
- [ ] Web: the type's new fields and `FileViewer`'s parse-error view for both roles, with unit tests; a `fix(web)` commit (ADR-2 decision 3)
- [ ] README file browser section: JSON5 and its difference from the game's reader (ADR-1 decision 6)
- [ ] `just check` green; read `seasonalflowers.json` on the dev stack through the viewer (read-only manual check)

---

### Story 23.2: File Browser Paths Are Lists of Names

**Sprint key:** `23-2-file-browser-paths-are-lists-of-names`
**Beads:** `VSS-o8s` (UI-081)
**FRs:** FR312

As a **developer**,
I want **the file browser to carry paths as lists of directory names**,
So that **a name is never split or joined by mistake, and the editor and history are built on one path representation**.

**Acceptance Criteria:**

**Given** the file browser at `ModConfig/sub` with a file selected
**When** I use the breadcrumb, open directories and select files
**Then** behaviour is as before (Story 16.7's breadcrumb tests pass unchanged in what they check), and the panel and breadcrumb state are `string[]`

*(Covers FR312; ADR-3 decision 1)*

**Given** a directory listing that returns a name containing `/`, `.`, `..` or an empty name (a mocked response)
**When** it is opened
**Then** the request is not sent and the panel shows an error instead of requesting another path

*(Covers FR312; ADR-3 decision 2)*

**Given** the API client
**When** a path is built for a request
**Then** it is built only by `toConfigPath`, which has unit tests for joining and for each rejected name

*(Covers FR312; ADR-3 decisions 2 and 3)*

**Tasks:**

- [ ] `toConfigPath` and the fetch functions taking `string[]`, and the query keys, with unit tests (ADR-3 decisions 2 and 3)
- [ ] `PathBreadcrumb` with `segments`, and `FileManagerPanel` with `string[]` state and the selected file as `{ directory, name }`; tests updated; a `refactor(web)` commit (ADR-3 decisions 1 and 4)
- [ ] `just check` green

---

### Story 23.3: Game Settings Are Read-Only for Monitor Keys

**Sprint key:** `23-3-game-settings-are-read-only-for-monitor-keys`
**Beads:** `VSS-7z3` (UI-084)
**FRs:** FR313

As an **operator with a Monitor key**,
I want **Game Settings to show me the values without letting me edit them**,
So that **I do not type a change that then fails with "Update failed"**.

**Acceptance Criteria:**

**Given** a Monitor key
**When** I open Game Settings
**Then** every field and switch is disabled, the note "Only an Admin key can change settings." is shown once at the top, Password keeps its status display, and no request is sent when I click or type

*(Covers FR313; ADR-6 decision 1)*

**Given** an Admin key
**When** I open Game Settings
**Then** the page is as before and no note is shown

*(Covers FR313; ADR-6 decision 1)*

**Given** the role is loading, or `GET /auth/me` fails
**When** I open Game Settings
**Then** the fields are disabled; while it loads there is no note, and on failure the note says the role could not be checked

*(Covers FR313; ADR-6 decision 2)*

**Given** `useIsAdmin`
**When** the file browser's note and `SettingsPage`'s tab hiding use it
**Then** their tests pass unchanged

*(ADR-6 decision 3)*

**Tasks:**

- [ ] `useIsAdmin` with unit tests; move the file browser note and `SettingsPage` to it with behaviour unchanged (a `refactor(web)` commit) (ADR-6 decision 3)
- [ ] `GameConfigPanel` disabled state and note, with unit tests for Admin, Monitor, loading and error; a `fix(web)` commit "show game settings read-only to Monitor keys" (ADR-6 decisions 1, 2 and 4)
- [ ] An E2E check with the Monitor key (skipped when the key is not configured, as the existing Monitor specs are) that the fields are disabled
- [ ] `just check` green

---

### Story 23.4: Config Files Can Be Saved Through the API

**Sprint key:** `23-4-config-files-can-be-saved-through-the-api`
**Beads:** `VSS-glz` (UI-025), first half
**FRs:** FR314, FR315, FR316, FR317, FR318

As an **administrator**,
I want **an API that saves a config file's text while the game server is stopped**,
So that **the web editor can change configs safely, keeping comments and formatting**.

**Acceptance Criteria:**

**Given** the game server is stopped, and an Admin key with the `version` from a read
**When** it sends `PUT /config/files/ModConfig/x.json` with text containing comments and odd spacing
**Then** the file holds exactly that text (and a BOM if it had one), its mode is kept, the answer is 200 with the new `version`, and the log has `config_file_saved` without the text

*(Covers FR314; ADR-4 decisions 1, 2, 6 and 9)*

**Given** a Monitor key, a path with `..`, a non-`.json` name, a missing file, a directory, or a text over 2 MiB
**When** it is saved
**Then** the answer is 403, 400, 400, 404, 400 or 413 as for a read (413 for size), and nothing is written

*(Covers FR314; ADR-4 decision 2)*

**Given** a text that does not parse, or a root `serverconfig.json` text with a comment
**When** it is saved
**Then** the answer is 422 `CONFIG_FILE_INVALID` with message, line and column, and nothing is written

*(Covers FR314; ADR-1 decision 5, ADR-4 decision 3)*

**Given** the game server is running, starting or stopping, or a lifecycle operation holds its lock
**When** a file is saved
**Then** the answer is 409 `CONFIG_FILE_SERVER_RUNNING` or `CONFIG_FILE_SERVER_BUSY`, and nothing is written

*(Covers FR315; ADR-4 decision 4)*

**Given** a save is in progress
**When** a start is requested
**Then** the start waits for the save to finish (a test with a stub start)

*(Covers FR315; ADR-4 decision 4, ADR-9 decision 2)*

**Given** the file changed after the read
**When** it is saved with the old `version`
**Then** the answer is 409 `CONFIG_FILE_CHANGED` and nothing is written

*(Covers FR316; ADR-4 decision 5)*

**Given** the temporary file cannot be written or the replace fails
**When** a file is saved
**Then** the answer is 500 `CONFIG_FILE_WRITE_FAILED` without a path, the original is unchanged, and no temporary file is left

*(Covers FR314; ADR-4 decision 6)*

**Given** a pending Story 22.7 edit for `Port`, and one for `Ip`
**When** `serverconfig.json` is saved with a changed `Port` and an unchanged `Ip`
**Then** the `Port` edit is dropped (reason `file_edited`) and the `Ip` edit stays

*(Covers FR318; ADR-4 decision 7)*

**Given** an Admin key
**When** it sends `POST /config/files/validate` with a valid or an invalid text, for `ModConfig/x.json` and for `serverconfig.json`
**Then** it gets `{valid, error}` under the same parser rule as a save, nothing is written, and the server state does not matter

*(Covers FR317; ADR-4 decision 10)*

**Tasks:**

- [ ] Error codes and exceptions; `ServerService.config_write()` with the zero-wait lock and the state rule, with tests including the waiting start (ADR-4 decision 4, ADR-9 decision 2)
- [ ] `ConfigFilesService.save_file`: path rules, size, parser, version, atomic write keeping BOM, mode and owner, clean-up on failure; a test for each refusal (ADR-4 decisions 2, 3, 5, 6 and 9)
- [ ] The pending-edit drop for `serverconfig.json` with the `file_edited` reason, with tests (ADR-4 decision 7)
- [ ] The `PUT` and `POST /validate` routes, with docstrings and router tests; a `feat(api)` commit "save config files through the API while the game server is stopped" (ADR-4 decisions 1 and 10)
- [ ] `just check` green

---

### Story 23.5: Config Files Are Edited in the File Browser

**Sprint key:** `23-5-config-files-are-edited-in-the-file-browser`
**Beads:** `VSS-glz` (UI-025), closes
**FRs:** FR319, FR320, FR326 (editing part)

As an **administrator**,
I want **to edit a config file in the file browser while the game server is stopped**,
So that **I can change mod and server configs without a shell on the host**.

**Acceptance Criteria:**

**Given** an Admin key and a stopped game server
**When** I open a file and press Edit
**Then** a CodeMirror editor shows the file's text with comments and highlighting; the status line shows "Valid", or the error with line and column (a click moves the cursor there), from the API check 500 ms after typing stops

*(Covers FR319; ADR-5 decisions 1, 3 and 4)*

**Given** valid, changed text
**When** I press Save
**Then** the file is saved, a toast says so, and the viewer shows the new text; Save is disabled for unchanged or invalid text, while a check is pending, and while the server is not stopped

*(Covers FR319; ADR-5 decisions 4 and 5)*

**Given** a 409 changed, running or busy answer, or a 422
**When** I save
**Then** my text is kept and the message explains it; for a change on disk, Reload discards my text after confirmation

*(Covers FR319; ADR-5 decision 5)*

**Given** unsaved changes
**When** I cancel, select another file or directory, use the breadcrumb, switch tabs or routes, or close the tab
**Then** I am asked before the changes are lost

*(Covers FR319; ADR-5 decision 6)*

**Given** the game server is running, starting or stopping
**When** I view a file as Admin
**Then** Edit is disabled with the explanation and a link to the server controls; a Monitor key sees no Edit button

*(Covers FR319; ADR-5 decision 3, ADR-6 decision 3)*

**Given** an Admin key and a file that parses
**When** I view it
**Then** it is shown as its text with comments in a read-only highlighted view, with word wrap working; a Monitor key sees the highlighted parsed content as before

*(Covers FR320; ADR-5 decision 7)*

**Given** the production build served with the CSP enforced
**When** the editor is opened
**Then** no CSP violation is reported, and the editor is in its own chunk

*(Covers FR319; ADR-5 decisions 1 and 2)*

**Tasks:**

- [ ] CodeMirror packages and the language choice (lang-json or lang-javascript, ADR-5 decision 1), with the editor and read-only view as one lazily loaded component; `build(web)` commit
- [ ] Edit mode: Edit button and its disabled state, the check-as-you-type status line, Save/Cancel, outcomes and 409/422 handling, with unit tests (ADR-5 decisions 3 to 5)
- [ ] Unsaved-change guards (dialog, `useBlocker`, `beforeunload`), with unit tests (ADR-5 decision 6)
- [ ] Admin's read-only text view and word wrap (ADR-5 decision 7); a `feat(web)` commit "edit config files in the file browser while the game server is stopped"
- [ ] E2E in the CI set only: create `ModConfig/e2e-<random>.json`, edit, save, reload and check, remove it; check for no CSP violations; Monitor sees no Edit button (ADR-9 decision 3)
- [ ] README file browser section: editing and the stopped-server rule
- [ ] `just check` green; the bundle report in the completion notes

---

### Story 23.6: Config Edits Are Kept as History

**Sprint key:** `23-6-config-edits-are-kept-as-history`
**Beads:** `VSS-hb4d` (API-098), first half
**FRs:** FR321, FR322, FR323, FR326 (history part)

As an **administrator**,
I want **each config save to keep the text it replaced**,
So that **I can see what changed and undo a bad edit**.

**Acceptance Criteria:**

**Given** a file saved through `PUT`
**When** the save succeeds
**Then** `vsmanager/state/config-history/<relative path>/` holds the replaced bytes as `<id>.json` and `index.json` lists it first with `savedAt`, `savedBy: "admin"`, `size` and `sha256`

*(Covers FR321; ADR-7 decisions 1 to 3)*

**Given** the history store cannot be written
**When** a file is saved
**Then** the answer is 500 `CONFIG_HISTORY_WRITE_FAILED` and the file is unchanged; if the file replace fails after the revision was written, the revision is removed

*(Covers FR321; ADR-7 decision 4)*

**Given** `config_history_keep_count` 3, and `config_history_max_age_days` 1 with revisions two days old
**When** the file is saved
**Then** only the newest 3, and none older than a day except the newest, remain; bounds outside 1 to 200 and 0 to 3650 are refused like other settings

*(Covers FR322; ADR-7 decision 5)*

**Given** an Admin key
**When** it lists, reads and restores a revision
**Then** the list is newest first; the read returns the text; the restore follows every save rule (stopped server, version, parser, pending edits), stores the current text as a new revision, and answers like `PUT`

*(Covers FR323; ADR-7 decision 6)*

**Given** a Monitor key, a malformed id (`../x`, `20261119T000000000000Z/../a`) or an unknown id
**When** it calls the history routes
**Then** the answers are 403, 400 and 404 `CONFIG_REVISION_NOT_FOUND`, and no path is built from the id

*(Covers FR323; ADR-7 decisions 2 and 6)*

**Tasks:**

- [ ] The history store (paths, ids, index, atomic index write, prune) with unit tests (ADR-7 decisions 1, 2 and 5)
- [ ] The two API settings with bounds and tests (ADR-7 decision 5)
- [ ] Hook the store into the save path with the failure rule, with tests (ADR-7 decisions 3 and 4)
- [ ] The three routes and restore through the save path, with router tests; a `feat(api)` commit "keep earlier versions of config files saved through the API, and restore them" (ADR-7 decisions 6 and 7)
- [ ] README: history location, what is and is not recorded, and the two settings
- [ ] `just check` green

---

### Story 23.7: Config History in the File Browser

**Sprint key:** `23-7-config-history-in-the-file-browser`
**Beads:** `VSS-hb4d` (API-098), closes
**FRs:** FR324, FR325

As an **administrator**,
I want **to browse a file's earlier versions, compare one with the current text and restore it**,
So that **I can see what an edit changed and undo it from the web UI**.

**Acceptance Criteria:**

**Given** an Admin key and a file with revisions
**When** I press History
**Then** a panel lists the revisions newest first with time, relative time, saved by and size; a file with none shows the empty message

*(Covers FR324; ADR-8 decision 1)*

**Given** a revision is chosen
**When** the screen is `md` or wider, and when it is narrower
**Then** it is compared with the current text side by side, or unified; "Show this version" shows it alone

*(Covers FR324; ADR-8 decision 2)*

**Given** the game server is stopped
**When** I restore a revision and confirm
**Then** the file holds that text, the viewer refreshes, and the history gains the replaced text; while the server is not stopped Restore is disabled with the explanation; while the editor has unsaved changes History is disabled

*(Covers FR324; ADR-8 decision 3)*

**Given** the API Settings tab
**When** an Admin opens it
**Then** a Config History group edits both limits within the API's bounds, with the help text of ADR-8 decision 4

*(Covers FR325; ADR-8 decision 4)*

**Tasks:**

- [ ] `@codemirror/merge` in the lazily loaded chunk; the history panel, comparison and Restore, with unit tests (ADR-8 decisions 1 to 3 and 5)
- [ ] The Config History group in `ApiSettingsPanel.tsx`, with unit tests (ADR-8 decision 4)
- [ ] A `feat(web)` commit "see, compare and restore earlier versions of config files" (ADR-8 decision 6)
- [ ] E2E in the CI set only: save a test file twice, compare, restore, check, remove it (ADR-9 decision 3)
- [ ] `just check` green

---

## Epic 24: Mod Management Follow-ups

**Goal:** An administrator can narrow a long installed-mods list by name, compatibility and available update. A mod copied into the mods folder by hand is picked up without restarting the API and gets its mod database link. Files in the mods folder that the manager does not use can be seen and deleted. Gaps left by Epic 19 are closed, the web UI gets its own icon, and the API tests run on a fresh clone. Seven open beads are closed.

**Architecture:** `architecture/epic-24-mod-management-follow-ups.md` (ADR-1 to ADR-8, with the facts checked at `804af73f`). There is no preparation story.

**Decided by the maintainer (Matt, 2026-11-20):** the scope `VSS-foq7`, `VSS-v3be`, `VSS-3tb1` and `VSS-hv60`, with `VSS-2bp` and `VSS-uhek` folded in and `VSS-koo1` pulled in. Five answers in two rounds (`sprint-change-proposal-2026-11-20-epic-24.md`, section 5):

1. A hand-added mod's asset ID is filled in by the update check (ADR-1).
2. The Installed tab gets an Admin Rescan action (ADR-4).
3. Unused files are listed with a confirmed Delete, including archives the sync skipped (ADR-3).
4. The installed filters are kept in the URL (ADR-6).
5. `VSS-koo1` is pulled in: the `/assets` headers go with the favicon story, and description media gets its own story (ADR-2, ADR-7).

Planner decisions not reviewed yet: the `MODS_BUSY` code and its two-way rule (ADR-4), "Restart required" after a rescan or archive delete while the game runs (ADR-4 decision 5), `.zip`-only import (ADR-3 decision 4), never overwriting a set asset ID (ADR-1 decision 2), the 404 rule's limit to paths outside the web UI's routes (ADR-2), and a loading compatibility matching only "All" (ADR-6 decision 4).

**Order:** 24.1, 24.2, 24.3, 24.4, 24.5, 24.6, 24.7, 24.8.

**Dependencies:**

- Story 24.1 comes first, so every later story's tests run in a worktree without `.env`.
- Story 24.5 comes after 24.3: the listing shares the sync's skip rules, and 24.3 changes the sync's removal path (ADR-5).
- Story 24.6 comes after 24.5 and calls its routes.
- Stories 24.2, 24.4, 24.7 and 24.8 are independent of each other. 24.4 and 24.7 both touch the Installed tab's update cell and `ModTable.tsx`, so 24.7 starts on top of 24.4.
- Stories are run one after another. Each branch starts from the previous story's branch, each pull request targets `main`, and the merge order is the story order.

**Beads:** seven in scope, each closed with an AAR by its story after merge: `VSS-uhek` in 24.1, `VSS-2bp` in 24.2 (with `VSS-koo1` item 1), `VSS-3tb1` in 24.5 (24.3 carries items 1, 3 and 4), `VSS-hv60` and `VSS-v3be` in 24.6 (24.4 and 24.5 carry their first halves), `VSS-foq7` in 24.7, `VSS-koo1` in 24.8. What planning found is in the stories (the change proposal lists it), not in new beads.

**Product changes:**

- New routes: `GET /mods/unused-files`, `DELETE /mods/unused-files/{name}` and `POST /mods/rescan`, all Admin only. A new error code, `MODS_BUSY` (409).
- `PUT /mods/{slug}/version` answers 409 `MOD_FILE_MISSING` instead of 500 when the mod's file is missing.
- The update check writes a missing asset ID to the mod state.
- Unknown static paths with a file extension answer 404; `/assets` responses carry the security headers; `/favicon.ico` is a real file.
- New web URL parameters on the Installed tab: `q`, `compat`, `updates`.
- No dependency is added, no route or field is removed, and nothing is breaking.

### Current State

- The Installed tab can be sorted but not filtered
- A mod copied into the mods folder by hand is picked up only when the API restarts, and has no ModDB link (asset ID 0)
- Leftover `.tmp` and `.bak` files and archives the sync skipped are reported only in a start-up log line
- A version change of a mod whose file is missing answers 500; cache eviction ignores release files other than `.zip` and `.cs`; a removed mod's cached `modinfo.json` stays behind
- The browser tab shows Vite's logo; `/favicon.ico` and other missing files answer with the web page; `/assets` has no security headers
- Description media other than images that the CSP blocks fails silently
- `just test-api` fails on a fresh clone without `.env`

### Target State

- The Installed tab filters by name, compatibility and available update, on both layouts, with the filters in the URL
- Rescan picks up a hand-added mod at once; the next update check gives it its ModDB link, or it shows as a local mod
- Admin sees the files the manager does not use, with the reason, and deletes them one at a time after confirming; `.cs` and folder mods are never offered
- Epic 19's mod file gaps are closed
- The web UI has its own icon; missing files are 404; `/assets` has the security headers
- Blocked description media shows a note
- `just test-api` runs on a fresh clone

---

### Story 24.1: API Tests Run on a Fresh Clone

**Sprint key:** `24-1-api-tests-run-on-a-fresh-clone`
**Beads:** `VSS-uhek` (TOOLS-010)
**FRs:** FR327

As a **developer**,
I want **the API tests to run on a fresh clone or a new worktree**,
So that **I do not have to copy a `.env` file before `just test-api` works**.

**Acceptance Criteria:**

**Given** a worktree with no root `.env` and no `VS_API_KEY_ADMIN` in the environment
**When** I run `just test-api`
**Then** every test passes, with no "VS_API_KEY_ADMIN must be set" error

*(Covers FR327; ADR-8)*

**Given** `VS_API_KEY_ADMIN` is set in the environment (from `.env` or CI)
**When** the tests run
**Then** that value is used, not the placeholder

*(Covers FR327)*

**Tasks:**

- [ ] `api/tests/conftest.py`: `os.environ.setdefault("VS_API_KEY_ADMIN", <placeholder>)` before the app is imported, next to `VS_DEBUG`, with a comment naming `VSS-uhek`
- [ ] A test that the placeholder applies only when the variable is unset
- [ ] README Development section: tests need no `.env`; running the app still does
- [ ] Run `just test-api` in a worktree without `.env`; `just check` green; a `test` commit

---

### Story 24.2: The Web UI Has Its Own Icon, and Missing Files Are 404

**Sprint key:** `24-2-web-ui-icon-and-missing-files-are-404`
**Beads:** `VSS-2bp` (UI-075), `VSS-koo1` (API-094, item 1)
**FRs:** FR328, FR329, FR330

As an **administrator**,
I want **the browser tab to show the Vintage Story icon and missing files to fail visibly**,
So that **I can find the manager's tab, and a broken asset is a 404 rather than a page**.

**Acceptance Criteria:**

**Given** the built web UI
**When** a browser loads it
**Then** `index.html` links `favicon.ico`, `favicon-32.png` and `apple-touch-icon.png`, each file exists in the build, `vite.svg` is gone, and `/favicon.ico` is served with an image content type

*(Covers FR328; ADR-2 decision 1)*

**Given** a path outside the web UI's routes whose last segment has a file extension and that is not a file (`/missing.png`, `/favicon.svg`)
**When** it is requested
**Then** it answers 404 with the security headers

*(Covers FR329; ADR-2 decision 2)*

**Given** a web UI route, including `/game-server/mods/browse/some.mod` and a route with a trailing slash
**When** it is requested
**Then** it gets `index.html`, as before

*(Covers FR329; ADR-2 decision 2)*

**Given** a file under `/assets`
**When** it is requested
**Then** the response carries the headers of `frontend_security_headers(settings.csp_mode)`, `X-Content-Type-Options: nosniff` included

*(Covers FR330; ADR-2 decision 3)*

**Tasks:**

- [ ] Generate the three icon files from `web/public/vintagestory-icon@2x.webp`, record the command in the story, commit them; remove `vite.svg`; update `index.html` (ADR-2 decision 1)
- [ ] `_resolve_frontend_file` / `serve_spa`: the 404 rule with the list of web UI route prefixes kept next to `register_frontend`; tests for missing files, client routes and a dotted mod slug (ADR-2 decision 2)
- [ ] The `/assets` mount sends the security headers; tests (ADR-2 decision 3)
- [ ] Commits: `feat(web): show the Vintage Story icon in the browser tab`; `fix(api): answer 404 for missing static files instead of the web page`; `fix(api): send security headers with the web UI's assets`
- [ ] `just check` green; the image's E2E smoke still passes

---

### Story 24.3: Mod File Follow-ups from Epic 19

**Sprint key:** `24-3-mod-file-follow-ups-from-epic-19`
**Beads:** `VSS-3tb1` (API-095, items 1, 3 and 4; item 2 is Story 24.5)
**FRs:** FR331, FR332, FR333

As an **administrator**,
I want **the mod file edge cases Epic 19 left open to behave like the rest**,
So that **a missing file gives a clear error, the cache stays within its limit and the state directory holds no stale data**.

**Acceptance Criteria:**

**Given** an installed mod whose own file is not in the mods directory
**When** its version is changed
**Then** the change is refused with 409 `MOD_FILE_MISSING` before any lookup or download, and nothing changes

*(Covers FR331; ADR-5 decision 1)*

**Given** a cache holding release files of several types (`.zip`, `.cs`, `.dll`, a name without an extension)
**When** eviction runs by age or by size
**Then** every type is counted and evicted, and an emptied file-ID directory is removed

*(Covers FR332; ADR-5 decision 2)*

**Given** the last entry of a mod ID is removed, by the start-up sync or by Remove
**When** the removal is saved
**Then** `state/mods/<slug>/` is removed; another entry with the same mod ID keeps it, and a version change keeps the old version's directory

*(Covers FR333; ADR-5 decision 3)*

**Tasks:**

- [ ] `change_version`: the missing-file check enable and disable use, before `_prepare_version_change`; router maps it to 409; tests; a `fix(api)` commit "answer a version change of a mod whose file is missing with 409, not 500"
- [ ] `CacheEvictionService`: every regular file in a file-ID directory; tests; a `fix(api)` commit "evict cached mod files of every type, not only .zip and .cs"
- [ ] The modinfo cache cleanup in the sync and in `ModService.remove_mod`; a failure is logged and never fails the removal; tests; a `refactor` commit
- [ ] `just check` green

---

### Story 24.4: Hand-Added Mods Get Their Mod Database Link

**Sprint key:** `24-4-hand-added-mods-get-their-mod-database-link`
**Beads:** `VSS-v3be` (API-093, first half)
**FRs:** FR334, FR335

As an **administrator**,
I want **a mod I copied into the mods folder to be linked to its mod database page**,
So that **it behaves like a mod installed through the manager**.

**Acceptance Criteria:**

**Given** an installed mod with asset ID 0 whose mod ID the mod database knows
**When** the update check runs
**Then** the mod's entry gets the payload's asset ID, the Installed tab links its ModDB page, and its update status is shown as for any mod

*(Covers FR334; ADR-1 decision 1)*

**Given** an installed mod with a non-zero asset ID, and a payload with another one
**When** the check runs
**Then** the stored asset ID is not changed and the difference is logged

*(Covers FR334; ADR-1 decision 2)*

**Given** a mod whose install or version change is running when the check reaches it
**When** the check runs
**Then** its asset ID is not written, the check does not fail, and the next check fills it in

*(Covers FR334; ADR-1 decision 3)*

**Given** a mod ID the mod database does not know
**When** the Installed tab shows it
**Then** its update cell reads "Local mod: not in the mod database", with no Update button and no ModDB link, and enable, disable and remove work

*(Covers FR335; ADR-1 decision 4)*

**Given** the mod database is unavailable
**When** the check runs
**Then** no asset ID changes and nothing else differs from today

*(Covers FR334)*

**Tasks:**

- [ ] `ModService.fill_asset_id(slug, asset_id)` under `_hold`, skipping a busy mod, only when the entry's `asset_id` is 0; tests (ADR-1)
- [ ] `ModUpdateService._check_one` passes the payload's `assetid` through the `InstalledModSource` protocol; tests with a hand-added mod, an unknown one and a busy one
- [ ] `ModUpdateCell`: the local-mod wording; unit tests (ADR-1 decision 4)
- [ ] A `fix(api)` commit "link mods added by hand to their mod database page after an update check"
- [ ] `just check` green

---

### Story 24.5: Unused Files and Rescan in the API

**Sprint key:** `24-5-unused-files-and-rescan-in-the-api`
**Beads:** `VSS-hv60` (UI-103, API half), `VSS-v3be` (API-093, rescan), `VSS-3tb1` (API-095, closes with item 2)
**FRs:** FR336, FR337, FR338, FR340

As an **administrator**,
I want **to list and delete files in the mods folder that the manager does not use, and to rescan the folder**,
So that **I can clean up leftovers and pick up a mod I copied in without restarting the API**.

**Acceptance Criteria:**

**Given** the mods folder holds `old.zip.bak`, `x.TMP`, an archive with no readable `modinfo.json`, a second archive of an installed mod ID, a `.cs` file, a folder, a `.vsm-bak` file and installed mods
**When** an Admin key calls `GET /mods/unused-files`
**Then** the first four are listed with size, modified time and reason (`leftover`, `unreadable`, `duplicate_mod_id` naming the installed file), and none of the others are; a Monitor key gets 403

*(Covers FR337, FR340; ADR-3)*

**Given** a listed file
**When** an Admin key calls `DELETE /mods/unused-files/{name}`
**Then** the file is deleted and the listing no longer has it; deleting a skipped archive while the game server runs sets "Restart required"

*(Covers FR338; ADR-3 decision 5, ADR-4 decision 5)*

**Given** a name that is not in the listing computed for the request (a mod's own file, a `.cs` file, a folder, a `.vsm-*` file, a name with `/` or `..`, a name that no longer exists)
**When** it is deleted
**Then** the answer is 404 and nothing is deleted

*(Covers FR338, FR340; ADR-3 decision 5)*

**Given** an archive copied into the mods folder while the API runs
**When** an Admin key calls `POST /mods/rescan`
**Then** it is added to the mod state, the answer has the numbers added, removed and skipped, and while the game server runs a change sets "Restart required"

*(Covers FR336; ADR-4 decisions 1 and 5)*

**Given** an install, version change, update all or update check is running
**When** a rescan or a delete is requested
**Then** it is refused with 409 `MODS_BUSY`; and while a rescan or delete runs, an install, version change, update all or update check is refused with 409 `MODS_BUSY`

*(Covers FR336, FR338; ADR-4 decisions 2 and 3)*

**Given** a version change to a new file name that was interrupted after the rename and before the old file was deleted (`VSS-3tb1` item 2)
**When** the listing is read
**Then** the old archive is listed as `duplicate_mod_id` and can be deleted

*(Covers FR337; ADR-3)*

**Tasks:**

- [ ] Move the sync's skip rules into one function the sync and the listing both use; the sync's behaviour and logs unchanged; tests (ADR-3 decision 3)
- [ ] `ModService.list_unused_files()` and `delete_unused_file(name)`; the `MODS_BUSY` rule in both directions (ADR-3, ADR-4)
- [ ] `ModService.rescan()`: the busy rule, `sync_state_with_disk`, "Restart required" when it changed something while the game runs; amend the sync's docstring and `sync_mod_state_at_startup`'s (ADR-4)
- [ ] Routes `GET /mods/unused-files`, `DELETE /mods/unused-files/{name}`, `POST /mods/rescan`, Admin only, registered so they do not collide with `/{slug}`; API tests for each criterion (ADR-8)
- [ ] Commits: `feat(api): rescan the mods folder for mods copied in by hand`; `feat(api): list and delete files in the mods folder that the manager does not use`
- [ ] Epic 19 ADR-10 decision 1 note already added in planning; `just check` green

---

### Story 24.6: Rescan and Unused Files on the Installed Tab

**Sprint key:** `24-6-rescan-and-unused-files-on-the-installed-tab`
**Beads:** `VSS-hv60` (UI-103, closes), `VSS-v3be` (API-093, closes)
**FRs:** FR336, FR339, FR340

As an **administrator**,
I want **a Rescan button and a list of unused files on the Installed tab**,
So that **I can pick up hand-added mods and clean up the mods folder from the web UI**.

**Acceptance Criteria:**

**Given** an Admin key on the Installed tab
**When** I press Rescan
**Then** the button shows progress, a toast gives the numbers added, removed and skipped, and the mods, updates and unused-files data refresh; a `MODS_BUSY` refusal is shown as a toast saying a mod operation is running

*(Covers FR336; ADR-4)*

**Given** the mods folder has unused files
**When** an Admin key opens the Installed tab
**Then** a notice says how many files the mods folder holds that the manager does not use; expanding it lists each with name, size, age and reason

*(Covers FR339; ADR-3)*

**Given** the list is open
**When** I press Delete on a file and confirm in the dialog that names it
**Then** it is deleted and the list refreshes; Cancel deletes nothing; the notice disappears when the list is empty

*(Covers FR339; ADR-3 decision 5)*

**Given** a Monitor key
**When** it opens the Installed tab
**Then** there is no Rescan button and no unused-files notice

*(Covers FR336, FR339)*

**Tasks:**

- [ ] Hooks for the three routes in `web/src/hooks/use-mods.ts`; query invalidation after a rescan or delete
- [ ] The Rescan button beside "Check for updates" (`useIsAdmin`); unit tests
- [ ] The unused-files notice and its `AlertDialog`, following `ModUpdatesNotice`; 44px targets on phones; unit tests for each state and role
- [ ] README mods section: hand-added mods, Rescan, unused files, `.cs` and folder mods left alone (FR340)
- [ ] E2E in the CI set only: copy an archive into the throwaway container, Rescan, see it listed; create a `.tmp` file, see it, delete it (ADR-8)
- [ ] Commits: `feat(web): rescan the mods folder from the Installed tab`; `feat(web): see and delete unused files in the mods folder`
- [ ] `just check` green; on the dev stack, read-only: the notice and Rescan render (manual)

---

### Story 24.7: Installed Mods Can Be Filtered

**Sprint key:** `24-7-installed-mods-can-be-filtered`
**Beads:** `VSS-foq7` (UI-104)
**FRs:** FR341, FR342

As an **administrator**,
I want **to filter the installed mods by name, compatibility and available update**,
So that **I can find a mod, or the mods that need attention, without scanning the whole list**.

**Acceptance Criteria:**

**Given** installed mods
**When** I type part of a mod's name or mod ID in the search box, in any letter case
**Then** only matching mods are shown, on the table and on the cards

*(Covers FR341; ADR-6 decision 1)*

**Given** the compatibility select
**When** I choose Compatible, Not verified or Incompatible
**Then** only mods with that status are shown; a mod whose status is still loading is shown only under All

*(Covers FR341; ADR-6 decision 4)*

**Given** the "Update available" toggle
**When** I turn it on
**Then** only mods whose update status is `update_available` are shown; "Update all" and its count are unchanged

*(Covers FR341; ADR-6 decision 5)*

**Given** filters are on
**When** the list is shown
**Then** it says "Showing N of M mods" with Clear filters; when nothing matches, the empty state names the filters and offers Clear filters

*(Covers FR342)*

**Given** filters are on
**When** I reload, open the URL in a new tab, or press Back after changing a filter
**Then** the URL's `q`, `compat` and `updates` restore the filters; typing does not add a history entry per key; an invalid value is ignored

*(Covers FR342; ADR-6 decisions 2 and 3)*

**Tasks:**

- [ ] TanStack Table column filters on `ModTable`'s instance; the cards render the filtered row model (ADR-6 decision 1)
- [ ] The filter bar, following BrowseTab's controls; 44px targets on phones; unit tests per filter, the combination and clear, on both layouts
- [ ] URL state with `useSearchParams`, replacing the entry while typing; unit tests for the round trip and invalid values (ADR-6 decisions 2 and 3)
- [ ] E2E: a filtered URL opened directly shows the filtered list
- [ ] A `feat(web)` commit "filter installed mods by name, compatibility and available update"
- [ ] `just check` green

---

### Story 24.8: Blocked Media in Mod Descriptions Shows a Note

**Sprint key:** `24-8-blocked-media-in-mod-descriptions-shows-a-note`
**Beads:** `VSS-koo1` (API-094, closes, item 2)
**FRs:** FR343

As an **administrator**,
I want **media a mod description cannot load to show a note**,
So that **I know something is missing instead of seeing a silent gap**.

**Acceptance Criteria:**

**Given** a description with `<video>`, `<audio>`, `<picture><source srcset>`, and an SVG `<image href>` from another host
**When** the mod detail page shows it
**Then** each is replaced with a note naming the kind of media, in the style of Story 19.3's image note

*(Covers FR343; ADR-7 decision 1)*

**Given** a description with a `poster` attribute, a `background` attribute or a `url()` in an inline style
**When** it is shown
**Then** the attribute or the declaration is removed without a note

*(Covers FR343; ADR-7 decision 2)*

**Given** a description with an `https:` image
**When** it is shown
**Then** it is unchanged, and the Content-Security-Policy is unchanged

*(Covers FR343; ADR-7 decision 3)*

**Tasks:**

- [ ] `web/src/lib/mod-description.ts`: the note for the media elements and the attribute removals; unit tests for each element and attribute (ADR-7)
- [ ] A `fix(web)` commit "show a note in place of video, audio and other media a mod description cannot load"
- [ ] `just check` green

---

## Epic 25: Server Config Read Correctly

**Goal:** An administrator is told when a mod or save path in `serverconfig.json` is wrong, including when the folder the manager installs mods into is not one the game loads. Entity Spawning shows the value the running game reports and is changed where the game keeps it, the world save. Two open beads are closed.

**Architecture:** `architecture/epic-25-server-config-read-correctly.md` (ADR-1 to ADR-6, with the facts checked at `7224a181`). There is no preparation story.

**Decided by the maintainer (Matt, 2026-11-20):** the scope `VSS-7ap` and `VSS-egi` (epic bead `VSS-m1qc`). Four answers in one round (`sprint-change-proposal-2026-11-20-epic-25.md`, section 5):

1. Entity Spawning is asked of the running game through the console, changed through the console, and never written to `serverconfig.json` again (ADR-4, ADR-6).
2. While the game is stopped, Entity Spawning shows the last value seen, read-only, with a note; "Not known yet" before the first read (ADR-5).
3. `VS_CFG_ENTITY_SPAWNING` is applied through the console after each start, and the setting shows as env-managed (ADR-6).
4. `VSS-7ap` gets a check endpoint and a warning in Game Settings; the typed model is internal, with no endpoint for the whole typed config (ADR-1, ADR-3).

Planner decisions not reviewed yet: four stories (API then web per bead), a 5-second reply timeout with 502 `SETTING_UPDATE_FAILED` (ADR-4), the new code `SETTING_NEEDS_RUNNING_SERVER` (409, ADR-6), paths outside `/data` reported by `stat` only (ADR-2), `OnlyWhitelisted` and `WhitelistMode` named in the model for Epic 27 (ADR-1), and an existing `EntitySpawning` key left in the file (ADR-6).

**Order:** 25.1, 25.2, 25.3, 25.4.

**Dependencies:**

- Story 25.2 comes after 25.1 and calls its route.
- Story 25.3 comes after 25.1: it removes EntitySpawning from the model's file reads.
- Story 25.4 comes after 25.3 and reads its fields.
- Stories are run one after another. Each branch starts from the previous story's branch, each pull request targets `main`, and the merge order is the story order.

**Beads:** two in scope, each closed with an AAR by its story after merge: `VSS-7ap` in 25.2 (25.1 carries the API half), `VSS-egi` in 25.4 (25.3 carries the API half, 25.4 the Story 17.6 review note). What planning found is in the stories (the change proposal lists it), not in new beads.

**Product changes:**

- New route: `GET /config/game/paths`, Admin and Monitor.
- `GET /config/game` answers 422 `CONFIG_FILE_INVALID` with line and column for a malformed `serverconfig.json` (was 500). EntitySpawning gets `source` and `observed_at` and loses `default`.
- `POST /config/game/settings/EntitySpawning` works only while the game runs; 409 `SETTING_NEEDS_RUNNING_SERVER` while stopped (a new error code); 502 `SETTING_UPDATE_FAILED` when the game does not reply.
- `VS_CFG_ENTITY_SPAWNING` is applied through the console after each start and no longer written to `serverconfig.json`.
- One new state file, `state/entity_spawning.json`.
- No dependency is added, no route is removed, and nothing is breaking: the old EntitySpawning write never reached the game.

### Current State

- `serverconfig.json` is read as a plain dict; a malformed file answers 500
- Nothing checks `ModPaths` or `SaveFileLocation`; a mods folder missing from `ModPaths` silently stops every installed mod from loading
- Entity Spawning reads a key game 1.22.7 never writes, so it always shows "Enabled (default)"; a change while stopped writes a key the game ignores, and a change while running is never shown
- `VS_CFG_ENTITY_SPAWNING` writes the same ignored key

### Target State

- `serverconfig.json` is read through one typed model; writes keep every key; a malformed file is reported with its line and column
- Game Settings warns about a wrong mod or save path, and about the manager's mods folder missing from `ModPaths`
- Entity Spawning shows what the running game reports, the last value seen while stopped, or "Not known yet"; it is changed through the console only
- `VS_CFG_ENTITY_SPAWNING` takes effect after each start

---

### Story 25.1: serverconfig.json Is Read Through One Typed Model, and Its Paths Are Checked

**Sprint key:** `25-1-serverconfig-is-read-through-one-typed-model-and-its-paths-are-checked`
**Beads:** `VSS-7ap` (API-012, API half)
**FRs:** FR344, FR345, FR346, FR347

As an **administrator**,
I want **the manager to check the mod and save paths in `serverconfig.json`**,
So that **I learn about a wrong path before I wonder why my mods do not load**.

**Acceptance Criteria:**

**Given** a `serverconfig.json` written by game 1.22.7
**When** the API reads it
**Then** it is parsed with `config_parse`'s strict mode into a `ServerConfigFile` model that names the keys the manager uses (the `LIVE_SETTINGS` keys, `ModPaths`, `WorldConfig.SaveFileLocation`, `OnlyWhitelisted`, `WhitelistMode`) and allows every other key

*(Covers FR344; ADR-1)*

**Given** a setting change
**When** the file is written
**Then** every key other than the changed one is unchanged, keys the model does not name included (a round-trip test on a 1.22.7 sample)

*(Covers FR344; ADR-1 decision 2)*

**Given** a `serverconfig.json` that is not valid JSON
**When** `GET /config/game` runs
**Then** it answers 422 `CONFIG_FILE_INVALID` with the line and column of the error

*(Covers FR345)*

**Given** the file
**When** `GET /config/game/paths` runs with an Admin or Monitor key
**Then** each `ModPaths` entry and the save file come back with `given`, `resolved`, `status` (`ok`, `missing`, `not_a_directory`, `not_a_file`, `not_readable`, `not_writable`, `not_installed`, `not_created_yet`) and `problem`; a save file that does not exist yet is reported by its parent folder, and a fresh install (no game installed, never started) has no problem

*(Covers FR346; ADR-2)*

**Given** `ModPaths` without the manager's mods folder (compared by resolved path)
**When** the check runs
**Then** the response has `manager_mods_folder_listed: false`

*(Covers FR347; ADR-2 decision 3)*

**Given** a path with `..` that resolves outside `/data`
**When** the check runs
**Then** it is reported with its resolved path and status, and nothing is listed or read beyond a `stat` and an access check

*(Covers FR346; ADR-2 decision 4)*

**Tasks:**

- [ ] Confirm on a throwaway container how a relative `ModPaths` entry and a null or relative `SaveFileLocation` resolve; record the rule in ADR-2 before the check is written
- [ ] `ServerConfigFile` model; `GameConfigService` reads through `config_parse` strict mode and the model; writes keep editing the parsed dict
- [ ] Round-trip test on a committed 1.22.7 sample (Password and StartupCommands blanked)
- [ ] The path check service and `GET /config/game/paths`; unit tests for every status, a traversal path and the mods-folder comparison
- [ ] 422 `CONFIG_FILE_INVALID` mapping for `GET /config/game`
- [ ] An E2E check in the CI set (throwaway container, no game installed) that the route answers for the fixture's paths with no problem: `Mods` `not_installed`, the manager's folder listed, the save file `not_created_yet` (ADR-2 decision 2)
- [ ] README (Game Settings) and `agentdocs/vs-server-troubleshooting.md`; a `feat(api)` commit "check that serverconfig.json's mod and save paths exist"; `just check` green

---

### Story 25.2: Game Settings Warns About a Wrong Path

**Sprint key:** `25-2-game-settings-warns-about-a-wrong-path`
**Beads:** `VSS-7ap` (API-012, closes)
**FRs:** FR348

As an **administrator**,
I want **Game Settings to tell me when a mod or save path is wrong**,
So that **I can fix it**.

**Acceptance Criteria:**

**Given** a path whose status is not `ok`, or `manager_mods_folder_listed: false`
**When** Game Settings opens
**Then** a warning names each problem, the path as given and as resolved, and the fix (an absolute path such as `/data/serverdata/Mods`), with a link to `serverconfig.json` in the file browser for an Admin key

*(Covers FR348; ADR-3)*

**Given** every path is `ok` and the mods folder is listed
**When** Game Settings opens
**Then** no warning shows

*(Covers FR348)*

**Given** the path check fails or `serverconfig.json` is missing
**When** Game Settings opens
**Then** it shows as today, with no warning and no error from the check

*(Covers FR348; ADR-3 decision 2)*

**Given** a Monitor key
**When** the warning shows
**Then** it has no file browser link

*(Covers FR348)*

**Tasks:**

- [ ] `useServerConfigPaths` query and the API client call
- [ ] The warning in `GameConfigPanel`, following `ModUpdatesNotice`; announced once to screen readers; 44px targets on phones
- [ ] Unit tests for each status, the mods-folder warning, the failed check and the Monitor view
- [ ] A `feat(web)` commit "warn in Game Settings when a mod or save path in serverconfig.json is wrong"; `just check` green

---

### Story 25.3: Entity Spawning Comes from the Running Game

**Sprint key:** `25-3-entity-spawning-comes-from-the-running-game`
**Beads:** `VSS-egi` (API-080, API half)
**FRs:** FR349, FR350, FR351, FR352, FR353

As an **administrator**,
I want **Entity Spawning to be the value the world uses**,
So that **what I see and change is what the game does**.

**Acceptance Criteria:**

**Given** a running 1.22.7 server on a throwaway container
**When** `/serverconfig entityspawning` and `/serverconfig entityspawning false` are sent
**Then** the replies (tag and bool spelling) are recorded in ADR-4, and the parser is written against them

*(ADR-4 decision 1)*

**Given** the game logs `Dedicated Server now running` and `VS_CFG_ENTITY_SPAWNING` is not set
**When** the manager sees the line
**Then** it sends `/serverconfig entityspawning`, reads `Current Entity spawning mode is on|off` within 5 seconds (the reply recorded in ADR-4), and records the value and the time

*(Covers FR349; ADR-4, ADR-5)*

**Given** `VS_CFG_ENTITY_SPAWNING` is set
**When** the game is ready
**Then** the manager sends `/serverconfig entityspawning <value>` and records the reply, and the setting is `env_managed`

*(Covers FR352; ADR-6 decision 3)*

**Given** the game runs
**When** `POST /config/game/settings/EntitySpawning` is called
**Then** the command is sent, and the response and the record carry the value from `Entity spawning mode set to on|off`; with no reply within 5 seconds the answer is 502 `SETTING_UPDATE_FAILED` and the record is unchanged

*(Covers FR351; ADR-4 decision 4)*

**Given** the game is stopped
**When** the same `POST` is called
**Then** it answers 409 `SETTING_NEEDS_RUNNING_SERVER` and `serverconfig.json` is not touched

*(Covers FR351; ADR-6 decision 2)*

**Given** any `Entity spawning mode set to on|off` line on stdout, from the UI or typed in the console
**When** the watcher sees it
**Then** the record follows it

*(Covers FR353; ADR-4 decision 3)*

**Given** `GET /config/game`
**When** it answers
**Then** EntitySpawning has `value` from the record, `source` (`game` while running and read since the start, `last_seen` otherwise, `unknown` with `value: null` before any read), `observed_at`, and no `default`

*(Covers FR349, FR350; ADR-5)*

**Given** a watcher fault or a reply timeout
**When** it happens
**Then** console capture and the start go on; the log line carries no console text

*(ADR-4 decision 5)*

**Tasks:**

- [ ] Record the reply sample (throwaway container)
- [ ] `ConsoleReplyWatcher` fed by `_read_stream` next to the player tracker; tests with a fake stream (match, interleaved lines, timeout, fault)
- [ ] `state/entity_spawning.json` record, written atomically; tests for load, save and a corrupt file
- [ ] The ready hook: the query, or the env var's set
- [ ] The set through the console, the 502 and the 409; `ErrorCode.SETTING_NEEDS_RUNNING_SERVER`
- [ ] `GET /config/game` fields; EntitySpawning out of the file reads and writes; `default` removed
- [ ] `config_init`: `VS_CFG_ENTITY_SPAWNING` no longer written to the file
- [ ] An E2E check tagged `@game-server` (local only; the CI set starts no game server): after start, EntitySpawning has `source: game`
- [ ] README and `agentdocs/vs-serverconfig-commands.md`; `fix(api)` commits "read and change Entity Spawning on the running game, where the world keeps it" and "apply VS_CFG_ENTITY_SPAWNING after each start"; `just check` green

---

### Story 25.4: Game Settings Shows Entity Spawning from the Game

**Sprint key:** `25-4-game-settings-shows-entity-spawning-from-the-game`
**Beads:** `VSS-egi` (API-080, closes)
**FRs:** FR349, FR350, FR352

As an **administrator**,
I want **to see where the Entity Spawning value comes from**,
So that **I know whether I can change it now**.

**Acceptance Criteria:**

**Given** `source: game`
**When** Game Settings shows Entity Spawning
**Then** the toggle shows the value and is enabled for an Admin key

*(Covers FR349)*

**Given** `source: last_seen`
**When** it shows
**Then** the toggle shows the value, is disabled, and the note says "Last reported by the game <relative time>. Changes only while the server runs."

*(Covers FR350)*

**Given** `source: unknown`
**When** it shows
**Then** the field says "Not known yet" and is disabled while stopped; this replaces Story 17.6's "Enabled (default)" for this setting (the Story 17.6 review note on `VSS-egi`)

*(Covers FR350)*

**Given** a change while the game runs
**When** the API answers
**Then** the field shows the value from the response; a 502 shows the error and keeps the previous value

*(Covers FR349)*

**Given** `env_managed`
**When** it shows
**Then** the field is locked with the env var's name, as other env-managed settings are

*(Covers FR352)*

**Given** the server starts or stops
**When** the status changes
**Then** the field updates without a reload

*(Covers FR349, FR350)*

**Tasks:**

- [ ] `SettingField` and `GameConfigPanel`: the three sources, the note, the disabled state
- [ ] The settings query is invalidated on a server state change
- [ ] Unit tests for each source, the 502 and the env-managed lock
- [ ] A `fix(web)` commit "show Entity Spawning as the game reports it, and the last value seen while stopped"; `just check` green

## Epic 28: Mods From Outside the Mod Database

**Goal:** An administrator can install a mod that is not on the mod database, by uploading its file or by giving an HTTPS link the server downloads (a GitHub or Forgejo release asset, an S3 object or presigned URL). The mod list says where each mod came from, an uploaded or linked mod is never confused with a mod-database mod of the same ID, and a mod installed from a GitHub or Forgejo release gets updates from that repo.

**Architecture:** `architecture/epic-28-mods-from-outside-the-mod-database.md` (ADR-1 to ADR-7, with the facts checked at `0da3d584`). There is no preparation story.

**Decided by the maintainer (Matt, 2026-11-27):** the scope, the five beads under the epic bead `VSS-guzf` (`VSS-guzf.1`, `VSS-cxuu`, `VSS-guzf.2`, `VSS-guzf.3`, `VSS-guzf.4`), and tokens for private sources out of scope. Every ADR is a planner decision, listed for review in `sprint-change-proposal-2026-11-27-epic-28.md`, section 5.

**FRs:** FR354 to FR366. Order: 28.1 to 28.5, each branch from the previous story's branch, each PR to `main`.

### Story 28.1: Each Installed Mod Records Where It Came From

As an administrator, I want to see where each installed mod came from, so that I know which mods the mod database updates and which I manage myself.

**Acceptance criteria:**

1. **Given** an install from the mod database, the start-up sync or a rescan, **then** the mod's state has `source` `moddb` or `folder`; **given** a state file written before this story, **then** an entry reads as `moddb` when its asset ID is set and `folder` otherwise, and loading rewrites nothing (FR354; ADR-1).
2. **Given** `GET /mods`, **then** each mod has `source` and `source_url` (FR354).
3. **Given** a mod with source `upload` or `url`, **when** the update check runs, **then** it is not looked up in the mod database, its asset ID is not filled in, and its status is `unknown` with reason `manual_install` (FR355; ADR-2).
4. **Given** a `folder` mod, **then** the check behaves as today: found mods get updates, others are local mods (ADR-2 decision 2).
5. **Given** a mod with source `upload` or `url` in the Installed tab, **then** its name has no mod database link, its compatibility is not looked up and reads "Not verified" with "Not from the mod database", and its update cell reads "Uploaded file" or "Installed from a link" (the host in the tooltip), on the table and the phone cards (FR355).
6. `just check` green; no suppression added.

### Story 28.2: A Mod Can Be Installed by Uploading Its File

As an administrator, I want to upload a mod's zip file, so that I can install a mod that is not on the mod database or a patched build of one that is.

**Acceptance criteria:**

1. **Given** an Admin key and a zip with a valid `modinfo.json`, **when** `POST /mods/upload?filename=<name>` sends it as the body, **then** the mod is installed with source `upload`, and the response has `slug`, `version`, `filename`, `compatibility` (`not_verified`), `pending_restart`, `source`, `replaced` and `previous_version` (FR356; ADR-3, ADR-4).
2. **Given** a body over `VS_MOD_UPLOAD_MAX_MB` (by `Content-Length` or while reading), **then** 413 `MOD_FILE_TOO_LARGE`, and nothing is left in the mods folder or the cache (FR357).
3. **Given** a name that is not a safe `.zip` base name, a body that is not a zip, or a zip without a `modinfo.json` that has a mod ID and a version, **then** 422 `MOD_FILE_INVALID` saying which (FR358).
4. **Given** the mod ID is installed, **when** `replace` is not set, **then** 409 `MOD_ALREADY_INSTALLED` with the installed version and source; **when** `replace=true`, **then** the file is swapped keeping the enabled state, the source becomes `upload`, the update record is removed, and a failure restores the original file and state (FR359; ADR-4).
5. **Given** the mod is busy or the name is taken, **then** 409 `MOD_OPERATION_IN_PROGRESS` or `MOD_FILE_CONFLICT`, as for an install.
6. **Given** a Monitor key, **then** 403. **Given** the server runs, **then** a restart is pending.
7. **Given** a crash during an upload, **then** the leftover working file is deleted at the next start.
8. `just check` green; README documents the upload and `VS_MOD_UPLOAD_MAX_MB`.

### Story 28.3: A Mod Can Be Installed from an HTTPS Link

As an administrator, I want to give the server a link to a mod's file, so that I can install a mod published on GitHub, Forgejo or S3 without downloading it first.

**Acceptance criteria:**

1. **Given** an Admin key and an `https` link to a mod zip, **when** `POST /mods/install-from-url` runs with `{url}`, **then** the file is downloaded and installed with source `url` and `source_url` the link without its query string, fragment or user info (FR360; ADR-1 decision 4, ADR-5).
2. **Given** a link or a redirect that is not `https` (without `VS_DEBUG`), more than 5 redirects, or a link with a user name or password, **then** 422 `MOD_URL_INVALID` (FR360).
3. **Given** a host that resolves to a private, loopback, link-local, multicast, reserved or unspecified address, on the first request or after a redirect, **then** 422 `MOD_URL_BLOCKED` and no connection is made to it; **given** the host is in `VS_MOD_URL_PRIVATE_HOSTS`, **then** a private address is allowed, and loopback, link-local and unspecified stay blocked (FR361).
4. **Given** a download over the size limit, slower than the limits, or a non-2xx answer, **then** 413 `MOD_FILE_TOO_LARGE` or 502 `DOWNLOAD_FAILED`, and nothing is left behind (FR362).
5. **Given** the file, **then** its name comes from `Content-Disposition`, else the URL path, else `{modid}_{version}.zip`, and it is checked and installed (with `replace`) as Story 28.2's ACs 3 to 6 (ADR-4, ADR-5).
6. Proxies from the environment are not used.
7. `just check` green; README documents the link install and `VS_MOD_URL_PRIVATE_HOSTS`.

### Story 28.4: The Mods Page Adds a Mod from a File or a Link

As an administrator, I want to add a mod from a file or a link on the mods page, so that I do not need the API to do it.

**Acceptance criteria:**

1. **Given** an Admin key, **then** the Installed tab has "Add from file or link" next to Rescan; **given** a Monitor key, **then** it does not (FR363; ADR-6).
2. **Given** the dialog's File tab, **when** a `.zip` is picked or dropped and Install is pressed, **then** it is uploaded as the request body (FR363).
3. **Given** the Link tab, **when** an `https` link is entered and Install is pressed, **then** the link install runs (FR363).
4. **Given** a `MOD_ALREADY_INSTALLED` answer, **then** the dialog names the installed mod, version and source, and "Replace it" resends with `replace=true` (FR364).
5. **Given** any other error, **then** the dialog shows the API's message and keeps the input. **Given** success, **then** it closes, a toast names the mod and version (and the restart when pending), and the mod list and update status refresh.
6. The dialog works on a phone (full width under 640 px, 44 px targets) and from the keyboard.
7. **E2E (CI set):** an upload of a generated mod zip shows the mod as "Uploaded file"; an upload of a zip without `modinfo.json` shows the error; a link to a loopback address shows the blocked message.
8. `just check` green.

### Story 28.5: Mods from GitHub and Forgejo Releases Get Updates

As an administrator, I want a mod I installed from a GitHub or Forgejo release to tell me when a newer release is out, so that I can update it like a mod-database mod.

**Acceptance criteria:**

1. **Given** a `url` mod whose link is a release asset (`/{owner}/{repo}/releases/download/{tag}/{asset}`), **when** the update check runs, **then** the repo's latest release is fetched (GitHub's API on `github.com`, `/api/v1` on any other host), through Story 28.3's transport (FR365; ADR-7).
2. **Given** the latest release, **then** the asset is matched by name with version-like parts removed, else the only `.zip`; no match gives `unknown` / `release_asset_not_matched` (ADR-7 decision 3).
3. **Given** a newer tag (a leading `v` removed), **then** `update_available` with `not_verified`; the same or older gives `up_to_date`; a tag that does not parse gives `unknown` / `version_unparsable` (FR365).
4. **Given** a lookup that fails, **then** the error is recorded as for a mod-database lookup and the check goes on.
5. **Given** `PUT /mods/{slug}/version` with the offered version, **then** the matching asset is installed with replace through Story 28.3's download; an archive with another mod ID is refused with 422 `MOD_FILE_INVALID` and the installed mod is kept (FR366).
6. **Given** the Installed tab, **then** such a mod shows the update with the Update button, and Update all skips it as not verified; the webhook alert includes it.
7. **Given** a link that is not a release asset, **then** its status stays `manual_install`.
8. `just check` green; README documents release updates.
