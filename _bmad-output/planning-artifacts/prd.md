---
stepsCompleted: [1, 2, 3, 4, 7, 8, 9, 10, 11]
workflowStatus: complete
inputDocuments:
  - '_bmad-output/analysis/brainstorming-session-2025-12-26.md'
  - 'agentdocs/vintagestory-modapi.md'
workflowType: 'prd'
lastStep: 0
documentCounts:
  briefs: 0
  research: 0
  brainstorming: 1
  projectDocs: 1
lastUpdated: '2026-11-17'
updates:
  - date: '2026-11-17'
    description: 'Added FR260-FR285 for Epic 21 (Maintainer Decisions and Web Polish); revised the same day: FR286 added for the pulled-in VSS-q38r'
  - date: '2026-11-17'
    description: 'Added FR234-FR259 for Epic 20 (Tooling and Test Health); revised the same day: FR252 changed and FR258-FR259 added for the mod database address setting'
  - date: '2026-11-17'
    description: 'Added FR205-FR233 for Epic 19 (API Security and Mod File Safety); revised twice the same day: follow-ups folded in, seven stories'
  - date: '2026-11-16'
    description: 'Added FR194-FR204 for Epic 18 (Mod Media and Fixes)'
  - date: '2026-11-15'
    description: 'Added FR177-FR193 for Epic 17 (Mod Data Correctness and Fixes)'
  - date: '2026-11-13'
    description: 'Added FR175-FR176 for Epic 16 Story 16.8 (Name sort, empty settings)'
  - date: '2026-11-13'
    description: 'Added FR167-FR174 for Epic 16 (UI Polish)'
  - date: '2026-11-10'
    description: 'Added FR152-FR166 and NFR17-NFR18 for Epic 15 (Release Engineering)'
  - date: '2026-11-09'
    description: 'Added FR129-FR151 for Epic 14 (Mod Updates)'
  - date: '2026-01-10'
    description: 'Added FR86-FR128 for Epic 11 (GameServer Navigation), Epic 12 (Enhanced Dashboard), Epic 13 (Version Browser)'
  - date: '2026-01-03'
    description: 'Added FR40-FR85 for Epic 9 (QoL Polish) and Epic 10 (Advanced Mod Browser)'
---

# Product Requirements Document - vintagestory-server

**Author:** Matt
**Date:** 2025-12-26

## Executive Summary

**The Problem:** Running a VintageStory server in Docker or Kubernetes today means no external control interface. Admins resort to workarounds - sidecar containers with VSCode, manual SSH sessions - just to edit a config file, install a mod, or see what's happening in the game console.

**The Solution:** VintageStory Server Manager is a self-hosted management platform that gives you a clean web UI to control your game server without ever touching a terminal.

**Target Users:** Built for homelab operators running VintageStory in containerized environments. Accessible enough for community server admins who want simple self-hosting.

### What Makes This Special

Two core capabilities define this product:

1. **Integrated Mod Management** - Install mods by slug with automatic compatibility validation against your game version. Get warnings for unverified compatibility. Check for updates on-demand or via scheduled jobs.

2. **Real-Time Console Access** - WebSocket-based console streaming lets you monitor server output and send commands directly from the browser. No more attaching to container processes.

**The "aha moment":** Manage your entire VintageStory server - mods, config, console - from a web UI. No SSH. No kubectl exec. No workarounds.

## Project Classification

| Attribute | Value |
|-----------|-------|
| **Technical Type** | API Backend + Web Application |
| **Domain** | General (Gaming Infrastructure / DevOps Tooling) |
| **Complexity** | Low-Medium |
| **Project Context** | Greenfield |

**Architecture:** Three-component system:

- **Docker Image** - Currently using `quartzar/vintage-story-server`; may create custom image from `mcr.microsoft.com/dotnet/runtime:8.0` as needs evolve
- **API Server** - Python/FastAPI backend for server lifecycle, mod management, and console streaming
- **Web UI** - Node.js frontend for administration

**Key Technical Decisions** (from brainstorming):

- FastAPI + uv + Ruff + pytest
- No database required - lightweight JSON persistence keeps deployment simple
- WebSocket console streaming
- API key authentication

## Success Criteria

### User Success

| Criteria | Measure |
|----------|---------|
| **Quick start** | Deploy via docker-compose, access web UI within minutes |
| **No terminal required** | Complete all admin tasks without shell access - Windows/Unraid users never touch a command line |
| **Console access relief** | Monitor and interact with game server from browser, no container exec needed |
| **Mod lifecycle management** | Install, update, version-switch mods without manual file management |
| **Update visibility** | See available mod updates at a glance |

**The "done" moment:** Admin installs a mod by slug, sees it appear in the mod list with compatibility status, and verifies it's working via the console stream - all without leaving the browser.

### Business Success

| Criteria | Measure |
|----------|---------|
| **Personal workflow solved** | VSCode sidecar retired; all server management through the web UI |
| **Craft development** | Polished GitHub repo demonstrating modern Python/FastAPI patterns |
| **Production-ready patterns** | Health endpoints, Prometheus metrics, graceful shutdown |
| **Community-ready** | Clean documentation, working docker-compose, approachable for non-Linux users |

**Explicitly NOT optimizing for:** Monetization, user growth metrics, multi-server fleet management (designed for future extension, not in scope).

### Technical Success

| Criteria | Measure |
|----------|---------|
| **Test coverage** | 80%+ across API and critical paths |
| **CI/CD maturity** | GitHub Actions → Automated releases → Renovate integration |
| **Code quality** | Ruff clean, type hints, consistent patterns |
| **Trust signals** | SBOM generation, code scanning, transparent AI-assisted development disclosure |
| **API design** | OpenAPI spec, versioned endpoints, consistent response envelope |

### Measurable Outcomes

- **Personal:** Stop using VSCode sidecar within 30 days of MVP deployment
- **Technical:** All CI checks green, 80%+ coverage, zero critical security findings
- **Community:** README, CONTRIBUTING.md, docker-compose.yaml ready for public release

## Product Scope

### MVP - Minimum Viable Product

**Goal:** Replace the VSCode sidecar workflow entirely.

| Component | MVP Scope |
|-----------|-----------|
| **Docker Image** | Use existing `quartzar/vintage-story-server` with management hooks |
| **API Server** | Server start/stop, console streaming (WebSocket), mod install by slug, mod list with compatibility status, config file read/edit, health endpoints |
| **Web UI** | Dashboard with server status, console view with command input, mod management page, config editor |
| **DevOps** | docker-compose.yaml, GitHub Actions CI (lint, test, build), basic documentation |

### Growth Features (Post-MVP)

- Scheduled mod update checks with notifications (Epic 14)
- Mod version switching (rollback to previous versions) (Epic 14)
- Backup management (create, restore, download)
- Renovate integration for automated dependency updates
- SBOM generation (Epic 15) and security scanning in CI
- Versioned GitHub releases with changelogs and published images (Epic 15)
- Prometheus metrics endpoint (`/metrics`)
- Enhanced API documentation (OpenAPI UI)

### Vision (Future)

- Embedded mod browser with `vintagestorymodinstall://` URL interception
- Multi-server fleet management via shared API patterns
- Custom Docker image built from `mcr.microsoft.com/dotnet/runtime:8.0`
- Community contributions and plugin architecture

## User Journeys

### Journey 1: Alex Chen - First-Time Setup

Alex is a software engineer who runs a small Kubernetes homelab for his family's game servers. He's been running VintageStory in a basic container for months, but every time his kids ask for a new mod, he has to SSH into the cluster, exec into the pod, and manually wget files. Last week his daughter asked for three new mods and it took him 45 minutes. He searches for "vintagestory server management" and finds this project.

He clones the repo and runs `docker-compose up -d`. Within two minutes, he's looking at a clean web dashboard showing his server status: online, version 1.21.3, 0 mods installed. He clicks "Add Mod," types `smithingplus`, and watches as the system fetches mod details, shows "Compatible with 1.21.3 ✓", and installs it. The console stream shows the server reloading. His daughter's mod is live before his coffee gets cold.

That weekend, Alex retires his VSCode sidecar container and deletes the kubectl exec aliases from his shell config. He won't miss them.

### Journey 2: Alex Chen - Mod Update Day

It's been a month. Alex opens the dashboard and notices a yellow badge: "2 updates available." He clicks through to the mod list and sees two of his installed mods have newer versions. One shows "Compatible ✓" - the other shows "⚠️ Not verified for 1.21.3."

He updates the compatible mod with one click. For the unverified one, he clicks "View Details" and sees the mod's last release was tagged for 1.21.2. He decides to wait and makes a mental note to check the mod's Discord. The console stream shows the server reloading cleanly with the updated mod.

### Journey 3: Alex Chen - Troubleshooting a Crash

The server crashed overnight. Alex wakes up to a Discord message from his kids: "Server's down!" He opens the dashboard on his phone and sees the server status: "Stopped - Exit Code 1." He taps the console view and scrolls back through the buffer. There it is - a stack trace pointing to a mod conflict between two recently updated mods.

He disables one of the mods from the mod list, starts the server from the dashboard, and watches the console stream for errors. Clean startup. He'll investigate the mod conflict later, but for now his kids are happy.

### Journey 4: Kubernetes Administrator Perspective - Health Monitoring

Alex's homelab runs Prometheus and Grafana for observability. After deploying VintageStory Server Manager, he adds the API server's `/healthz` endpoint to his uptime monitor. The endpoint returns healthy when the API is responsive, and includes a check for whether the game server process is running.

When he configures his Kubernetes deployment, he sets the `/readyz` endpoint as the readiness probe - traffic only routes to the pod when the API is fully initialized. His alerting catches a situation where the game server crashed but the management API stayed up, allowing him to distinguish between "management plane down" and "game server down."

Later, he adds the `/metrics` endpoint to his Prometheus scrape config and builds a simple Grafana dashboard showing mod count, server uptime, and console message rate.

### Journey Requirements Summary

| Journey | Capabilities Revealed |
|---------|----------------------|
| **First-Time Setup** | docker-compose deployment, dashboard with server status, mod install by slug, compatibility checking, console streaming |
| **Mod Update Day** | Update availability detection, compatibility warnings, one-click update, mod details view |
| **Troubleshooting** | Server start/stop control, console history buffer, mod enable/disable, mobile-responsive UI |
| **K8s Administrator** | `/healthz` endpoint, `/readyz` endpoint, `/metrics` endpoint, game server process health check |

## API Backend Requirements

### API Overview

RESTful API with WebSocket support for real-time console streaming. Follows Kubernetes-style versioning to signal API maturity.

- **Base Path:** `/api/v1alpha1`
- **Data Format:** JSON (requests and responses)
- **Response Envelope:** `{"status": "ok|error", "data": {...}}`

### Endpoint Specification

| Category | Endpoints | Methods |
|----------|-----------|---------|
| **Server Lifecycle** | `/server/start`, `/server/stop`, `/server/restart`, `/server/status` | POST, GET |
| **Console** | `/console` (WebSocket), `/console/command` | WS, POST |
| **Mods** | `/mods`, `/mods/{slug}`, `/mods/updates`, `/mods/updates/check`, `/mods/updates/apply-all`, `/mods/{slug}/version`, `/mods/{slug}/enable`, `/mods/{slug}/disable` | GET, POST, PUT, DELETE |
| **Game Config** | `/config/files`, `/config/files/{filename}` | GET, PUT |
| **Settings** | `/settings`, `/settings/whitelist` | GET, PUT |
| **Backups** | `/backups`, `/backups/{id}`, `/backups/{id}/restore`, `/backups/{id}/download` | GET, POST, DELETE |
| **Health** | `/healthz`, `/readyz` | GET (no auth) |
| **Metrics** | `/metrics` | GET (no auth, POST-MVP) |

### Authentication Model

Three-tier API key authentication via `X-API-Key` header with role-based permissions.

| Role | Auth | Access |
|------|------|--------|
| **None** | No key required | `/healthz`, `/readyz`, `/metrics` only |
| **Monitor** | `VS_API_KEY_MONITOR` | Health + server status + mod list + config read (no console - sensitive data) |
| **Admin** | `VS_API_KEY_ADMIN` | Everything including console stream + commands + write operations |

- Health endpoints (`/healthz`, `/readyz`, `/metrics`) require no authentication
- Console stream contains sensitive data (player IPs, chat, errors) - Admin only
- Write operations with Monitor key return `403 Forbidden`

### Rate Limiting (Nice-to-have)

If trivial to implement:

- Global limit: ~10 requests/second or 300 requests/minute
- Purpose: Prevent abuse/misconfiguration, not throttle legitimate UI use
- Not MVP-blocking

### Implementation Considerations

- WebSocket console connection should maintain ring buffer for history
- Mod operations should validate against VintageStory mod API before installation
- Backup operations may be long-running; consider async patterns with status polling

## Project Scoping & Phased Development

### MVP Strategy & Philosophy

**MVP Approach:** Problem-Solving MVP - solve the core problem (retire VSCode sidecar) with minimal features
**Resource Requirements:** Solo developer, personal project with community release goal

### MVP Feature Set (Phase 1)

**Core User Journeys Supported:**

- Journey 1: First-Time Setup (full support)
- Journey 3: Troubleshooting (full support)
- Journey 4: K8s Administrator (health endpoints only)

**Must-Have Capabilities:**

| Category | MVP Scope |
|----------|-----------|
| **Server Lifecycle** | Start, stop, restart, status |
| **Console** | WebSocket streaming, command input, history buffer |
| **Mods** | List installed, install by slug, enable/disable, compatibility validation |
| **Game Config** | List config files, read/write JSON configs |
| **Settings** | Server name, boolean flags (whitelist_only, etc.) |
| **Health** | `/healthz`, `/readyz` endpoints |
| **DevOps** | docker-compose.yaml, GitHub Actions CI (lint, test, build), README |

**MVP Success Gate:** VSCode sidecar retired; all routine server management via web UI.

### Post-MVP Features

**Phase 2 - Growth:**

- Mod update detection and one-click updates (Epic 14)
- Mod version switching (rollback capability) (Epic 14)
- Backup management (create, restore, download)
- Prometheus `/metrics` endpoint
- Renovate integration for dependency updates
- SBOM generation (Epic 15) and security scanning
- Versioned GitHub releases with changelogs and published images (Epic 15)

**Phase 3 - Vision:**

- Embedded mod browser with URL interception
- Multi-server fleet management
- Custom Docker image from dotnet base
- Community plugin architecture

### Risk Mitigation Strategy

| Risk Type | Risk | Mitigation |
|-----------|------|------------|
| **Technical** | WebSocket console reliability | Simple ring buffer implementation, iterate based on usage |
| **Technical** | Mod API integration edge cases | Comprehensive API documentation available; validate compatibility before install |
| **Resource** | Solo developer bandwidth | Lean MVP scope, clear phase boundaries, no scope creep |

## Functional Requirements

### Server Lifecycle Management

- FR1: Admin can view current server status (running/stopped, uptime, game version)
- FR2: Admin can start the game server
- FR3: Admin can stop the game server gracefully
- FR4: Admin can restart the game server
- FR5: Monitor can view current server status (running/stopped, uptime, game version)

### Console Access

- FR6: Admin can view real-time game server console output via WebSocket stream
- FR7: Admin can scroll back through console history buffer
- FR8: Admin can send commands to the game server console
- FR9: Console access is restricted to Admin role only (sensitive data)

### Mod Management

- FR10: Admin can view list of installed mods with version and compatibility status
- FR11: Admin can install a mod by entering its slug
- FR12: System validates mod compatibility against current game version before installation
- FR13: System displays warning when mod is not explicitly compatible with current game version
- FR14: Admin can enable an installed mod
- FR15: Admin can disable an installed mod
- FR16: Admin can remove an installed mod
- FR17: Monitor can view list of installed mods (read-only)

### Game Configuration

- FR18: Admin can view list of game configuration files
- FR19: Admin can read contents of a game configuration file
- FR20: Admin can edit and save game configuration files
- FR21: Monitor can view list of game configuration files (read-only)
- FR22: Monitor can read contents of game configuration files (read-only)

### Settings Management

- FR23: Admin can view server management settings (server name, whitelist mode, etc.)
- FR24: Admin can update server management settings
- FR25: Admin can view player whitelist
- FR26: Admin can add/remove players from whitelist

### Health & Observability

- FR27: System exposes health check endpoint (`/healthz`) without authentication
- FR28: System exposes readiness check endpoint (`/readyz`) without authentication
- FR29: Health endpoints report game server process status (running/stopped)
- FR30: System exposes metrics endpoint (`/metrics`) without authentication (POST-MVP)

### Authentication & Authorization

- FR31: Protected API endpoints require valid API key via `X-API-Key` header
- FR32: System supports Monitor API keys with read-only access to non-sensitive data
- FR33: System supports Admin API keys with full access including console and write operations
- FR34: Console stream and history are restricted to Admin role (sensitive data protection)
- FR35: Write operations are restricted to Admin role
- FR36: System returns 401 Unauthorized for missing or invalid API key
- FR37: System returns 403 Forbidden when key lacks permission for requested operation

### Deployment & Setup

- FR38: System can be deployed via docker-compose with minimal configuration
- FR39: System configuration is provided via environment variables

## Non-Functional Requirements

### Performance

- NFR1: Console output appears in web UI within 1 second of being generated by game server
- NFR2: WebSocket preferred for real-time streaming; polling at 1-second intervals is acceptable fallback
- NFR3: API endpoints under local control (server lifecycle, console, config, settings) respond within 500ms. Endpoints requiring external API calls (mod installation, update checks) may take longer and should provide progress indication.

### Security

- NFR4: API keys are stored securely and never logged in plaintext
- NFR5: TLS termination is out of scope for MVP; users requiring HTTPS must provide a reverse proxy (e.g., Traefik, nginx, Caddy)
- NFR6: Console history buffer does not persist to disk (sensitive data protection)
- NFR7: Failed authentication attempts are logged for security monitoring

### Reliability

- NFR8: Management API remains available when game server is stopped or crashed
- NFR9: System recovers gracefully from game server process crashes without requiring restart
- NFR10: WebSocket disconnections reconnect automatically without losing significant console history

### Integration

- NFR11: System gracefully handles VintageStory mod API unavailability (cached data, clear error messages)
- NFR12: Mod installation failures due to network issues are reported clearly to user
- NFR13: System does not require external network access for core functionality (mod management requires it)

### Observability

- NFR14: API server logs are structured (JSON) for easy parsing; game server logs remain in their native format
- NFR15: Health endpoints differentiate between "API healthy" and "game server healthy"
- NFR16: Errors include sufficient context for debugging without exposing sensitive data

### Release & Supply Chain

- NFR17: Release automation uses least-privilege token permissions per job and actions pinned to commit SHAs
- NFR18: Published images carry OCI labels recording their version, source revision and repository

---

## Post-MVP Functional Requirements

### Epic 9: Quality of Life Polish Pass

#### WebSocket Security

- FR40: WebSocket connections use secure token authentication instead of passing API key in URL query parameters
- FR41: WebSocket authentication tokens are short-lived and validated server-side

#### System Initialization

- FR42: API server creates expected directories under data/vsmanager (cache, state, logs) on startup if they don't exist
- FR43: Missing directory creation is logged for operational visibility

#### Mod Cache Management

- FR44: System implements cache eviction strategy for downloaded mod files (LRU, TTL, or size-based)
- FR45: Admin can configure cache size limits or retention policies
- FR46: System logs cache eviction events for operational visibility

#### Debug Logging

- FR47: API server provides comprehensive debug-level logging throughout all service layers
- FR48: Debug logging can be enabled/disabled via environment variable without restart
- FR49: Debug logs include correlation IDs for request tracing

#### Console Display Enhancements

- FR50: Commands entered by the user are displayed in a distinct color in the console output
- FR51: User-entered commands are prefixed with [CMD] marker for easy identification

#### File Viewer Enhancements

- FR52: File viewer applies JSON syntax colorization when displaying .json files
- FR53: JSON colorization highlights keys, strings, numbers, booleans, and null values distinctly

#### File Browser Enhancements

- FR54: File browser displays all directories under /data/serverdata including ModConfigs, Macros, Playerdata, and others
- FR55: Directory listing is dynamically generated rather than hardcoded

### Epic 10: Advanced Mod Browser

#### Mod Tab Restructure

- FR56: Mods view is split into two distinct tabs: "Installed" (mod management) and "Browse" (mod discovery)
- FR57: Installed tab contains existing mod management functionality (list, enable, disable, remove, update)
- FR58: Browse tab provides new mod discovery and installation experience

#### Smart Landing Page

- FR59: Browse tab displays newest mods by default when opened, matching mods.vintagestory.at behavior
- FR60: Default results are pre-filtered to show mods compatible with the current game server version
- FR61: Landing page loads content immediately without requiring user to initiate a search

#### Mod Search

- FR62: Admin can search for mods by keyword (searches mod name and description)
- FR63: Search results update as user types (debounced) or on explicit submit
- FR64: Search maintains current filter and sort selections

#### Mod Filtering

- FR65: Admin can filter mods by side: Any, Client-only, Server-only, Both
- FR66: Admin can filter mods by tags (Crafting, Creatures, Food, QoL, Storage, Utility, Weapons, Worldgen, etc.)
- FR67: Admin can filter mods by game version compatibility
- FR68: Admin can filter mods by type: Content Mod, Code Mod, Theme Pack, External Tool
- FR69: Multiple filters can be combined (AND logic)
- FR70: Active filters are clearly displayed and individually removable

#### Mod Sorting

- FR71: Admin can sort mod results by: Newest, Most Downloaded, Recently Updated, Trending, Name
- FR72: Default sort order is Newest (matching landing page behavior)
- FR73: Sort selection persists during the browse session

#### Mod Display

- FR74: Mods are displayed in card format showing: thumbnail image, name, author, download count, short description
- FR75: Mod cards indicate compatibility status with current game server version
- FR76: Mod cards are clickable to view full mod details

#### Mod Details

- FR77: Mod detail view shows full description, all releases, dependencies, and compatibility information
- FR78: Mod detail view provides install button with version selection
- FR79: If mod is already installed, detail view shows current installed version and update option if available

#### Pagination

- FR80: Browse results support pagination for large result sets (5000+ mods in database)
- FR81: Pagination can be implemented as infinite scroll or traditional page controls
- FR82: Current page/position is maintained when returning from mod detail view

#### Install Integration

- FR83: Admin can install a mod directly from browse results or detail view
- FR84: Installation shows compatibility check result before confirming
- FR85: After successful installation, mod appears in Installed tab and browse UI updates to reflect installed state

### Epic 11: GameServer Navigation Refactor

#### Sub-Navigation Structure

- FR86: Sidebar displays expandable Game Server section with sub-navigation items
- FR87: Game Server sub-navigation includes: Version/Installation, Settings, Mods, Console (in that order)
- FR88: Sub-navigation expanded/collapsed state persists across sessions
- FR89: First sub-item label dynamically shows "Installation" when no server installed, "Version" when installed
- FR90: Top-level "Settings" is renamed to "VSManager" to distinguish from game settings
- FR91: Mods is accessible under Game Server navigation, not as top-level item

#### Dedicated Pages

- FR92: Console is accessible as dedicated full-page view at `/game-server/console`
- FR93: Game settings is accessible as dedicated full-page view at `/game-server/settings`
- FR94: Version/Installation is accessible at `/game-server/version`
- FR95: Mods is accessible at `/game-server/mods` with redirect from legacy `/mods` URLs
- FR96: Pages show appropriate empty state when server is not installed

#### Dashboard Simplification

- FR97: Dashboard no longer contains server installation UI (moved to Version page)
- FR98: Dashboard shows link to Version page when server is not installed
- FR99: Default route `/game-server` redirects to `/game-server/version`

### Epic 12: Enhanced Dashboard with Server Metrics

#### Metrics Collection

- FR100: System collects API server memory and CPU metrics periodically
- FR101: System collects game server process memory and CPU metrics when running
- FR102: Metrics collection interval is configurable via environment variable
- FR103: Historical metrics are stored in memory with configurable retention period

#### Metrics API

- FR104: Admin can retrieve current metrics snapshot via API
- FR105: Admin can retrieve historical metrics with optional time range filter
- FR106: Metrics endpoints are restricted to Admin role

#### Dashboard Display

- FR107: Dashboard displays stat cards for server status, memory usage, disk space, and uptime
- FR108: Memory card shows both API and game server memory separately
- FR109: Dashboard displays time-series chart of memory usage over time
- FR110: Chart supports selectable time ranges (15m, 1h, 6h, 24h)
- FR111: Dashboard provides quick links to Console, Settings, Mods, and Version pages
- FR112: Quick links show disabled state when server is not installed

### Epic 13: Server Version Browser

#### Version Listing

- FR113: Admin can view list of available server versions from both stable and unstable channels
- FR114: Version list can be filtered by channel (All, Stable, Unstable)
- FR115: Each version displays: version number, channel, file size, and badges for Installed/Latest
- FR116: Version data is cached with periodic refresh

#### Version Display

- FR117: Versions are displayed as cards similar to mod browser
- FR118: Currently installed version is prominently indicated
- FR119: Latest version in each channel is indicated with badge
- FR120: Version list is sorted by version number (newest first)

#### Install/Upgrade Flow

- FR121: Admin can install a version by clicking Install button on version card
- FR122: Install confirmation dialog shows version details before proceeding
- FR123: Upgrade confirmation shows current → new version comparison
- FR124: Downgrade shows prominent warning about risks
- FR125: If server is running, warning indicates server will be stopped
- FR126: Installation progress is displayed with stage and percentage
- FR127: "Install Latest Stable" quick action available when no server installed
- FR128: "Update to Latest" quick action available when update exists

### Epic 14: Mod Updates

#### Update Detection

- FR129: System determines whether a newer release exists for each installed mod using the mod database's release order, not by comparing version strings (except the base-version check for mods on a pre-release in FR130)
- FR130: The offered update is the newest newer release compatible with the current game version, or if none exists, the newest newer release that is not verified. A stable installed version is only offered stable releases; a mod already on a pre-release can be offered a newer release only if its base version (the numeric part before any `-`) is not lower than the installed one (Epic 14 ADR-1)
- FR131: No update is offered when every newer release is incompatible with the current game version
- FR132: A mod not found in the mod database, or whose installed version is not listed there, shows its update status as unknown rather than up to date
- FR133: Admin and Monitor can view update status for installed mods, including offered version, its compatibility, and when it was last checked
- FR134: Admin can trigger an update check on demand

#### One-Click Update

- FR135: Admin can update a mod to its offered version with a single action
- FR136: Updating to a not-verified release requires confirming a warning
- FR137: The installed version stays in place until the new version is downloaded and validated; a failed update leaves the mod unchanged
- FR138: Updating or switching versions preserves the mod's enabled or disabled state
- FR139: If the game server is running, updating or switching versions marks a restart as pending

#### Version Switching

- FR140: Admin can switch an installed mod to any release listed in the mod database for the installed mod's modid, including older releases
- FR141: Switching shows the target release's compatibility and warns before installing a not-verified or incompatible release, a pre-release when the installed version is stable, or a release older than the installed one (by the mod database's release order)
- FR142: Switching uses a cached copy of the release when available and downloads it otherwise

#### Update All

- FR143: Admin can update every mod that has a compatible update in a single action
- FR144: Update all skips mods whose offered update is not verified and reports them for individual review
- FR145: A failure updating one mod does not stop the others; results are reported per mod

#### Scheduled Checks and Alerts

- FR146: System checks for mod updates on the existing mod refresh interval; an interval of 0 disables scheduled checks
- FR147: Update status remains available after an API restart, without waiting for the next scheduled check
- FR148: Dashboard and Mods navigation show a count of mods with updates available
- FR149: Admin can configure an outbound webhook URL for update alerts; the URL is treated as a secret, is Admin-only, and is never logged or exposed to Monitor
- FR150: A webhook alert is sent once for each newly available update, not repeated on every check
- FR151: A webhook delivery failure is logged and does not affect update checks

### Epic 15: Release Engineering

#### Versioning

- FR152: The API, web UI and container image share one Semantic Versioning version, kept in the project files a release updates and hard-coded nowhere else
- FR153: The API reports its version in the OpenAPI document and the `/healthz` response
- FR154: The web UI shows the running version

#### Changelog

- FR155: The changelog is generated from conventional commit messages, listing features, fixes, performance improvements and breaking changes grouped by type; other commit types, merge commits and non-conventional messages are left out
- FR156: Changelog entries omit internal planning scopes (story, task and review identifiers)
- FR157: Developer can preview the changelog for unreleased changes without making a release

#### Cutting a Release

- FR158: Developer can cut a release with one command that uses the version computed from commits since the last release, or an explicit bump or version, then updates the version files and CHANGELOG.md, commits, tags and pushes
- FR159: The release command refuses to run unless on an up-to-date `main` with a clean working tree, and refuses a version that is already tagged or not newer than the last release
- FR160: The release command offers a dry run that shows the version and notes without changing anything

#### Publishing

- FR161: Pushing a version tag publishes a GitHub release whose notes are that version's changelog section
- FR162: Pushing a version tag publishes the image to GHCR as `X.Y.Z`, `X.Y` and `latest`; a pre-release version (e.g. `0.2.0-rc.1`) gets only its full tag and is marked as a pre-release on GitHub
- FR163: Publishing stops before anything is published if the tag does not match the repository's version
- FR164: Each published image has an SBOM and signed build provenance that users can verify; the SBOM is attached to the GitHub release

#### Runtime Configuration and Documentation

- FR165: The published image contains no API key; the web UI receives its API key from the server's configuration at runtime, so one image works for every deployment
- FR166: Documentation explains installing and upgrading to a specific release, verifying an image, writing commits that become release notes, and cutting a release

### Epic 16: UI Polish

#### Mod Browser

- FR167: The mod browser keeps its search term, filters and sort when the admin opens a mod's detail page and returns with Back to Browse or the browser's back button
- FR168: Returning to the mod browser restores the page and scroll position that went with that search, filters and sort
- FR169: The mod detail page recognizes an installed mod when any mod ID in the database entry matches it
- FR170: For a mod that is not verified or is incompatible with the installed game version, the UI shows the most recent game version the mod supports
- FR171: The mod lookup preview shows the mod description as formatted, sanitized HTML instead of raw markup (withdrawn 2026-11-13: the lookup preview was removed in VSS-195; Story 16.4 delivers the shared sanitizer and safe description links instead)

#### Layout and Navigation

- FR172: On narrow screens, installed mods are shown as cards with version, update status and Update action, enable toggle and remove action, without horizontal scrolling
- FR173: Game server settings use the available width on desktop screens instead of full-width stacked cards
- FR174: The file browser shows the current path as clickable segments, each opening that directory

#### Fixes Found During the Epic (added 2026-11-13, Story 16.8)

- FR175: The mod browser's Name (A-Z) sort lists mods alphabetically by name, ignoring leading spaces, letter case and accents, sorted across all matching mods by the server and paged like the other sorts, so page numbers, search and filters work with it
- FR176: Game server settings with no value (Description, Password, IP Address) are shown as empty fields, never as the text "null"; clearing one of them saves it as no value (null), never as the text "null" or "None"; the Password field is masked and can be revealed on request

### Epic 17: Mod Data Correctness and Fixes

#### Mod Data and Install

- FR177: Mod lookup, browsing, sorting, tag listing and update checks succeed when the mod database returns null for any field of a mod or release; a null takes the field's default, and a release without a file ID is listed with a null file ID
- FR178: The mod detail page's error state offers Back to Browse, returning to the browse state the page was opened from
- FR179: Installing a mod considers only releases whose mod ID is the mod being installed, with or without a named version
- FR180: Installing without a named version picks the newest stable release of that mod ID that has a downloadable file; a pre-release is installed only when its version is named or the mod ID has no stable release
- FR181: The install version list shows only the releases of the mod ID that will be installed, and "(Latest)" marks the release that an install without a named version picks
- FR182: Install, enable, disable, remove and version change for the same mod never run at the same time; a request that arrives while another is running is refused with 409 and changes nothing
- FR183: A mod archive whose `modinfo.json` uses capitalized top-level keys (for example `ModID`, `Version`) is imported with its real mod ID and version
- FR184: Mod browser cards show a mod as installed when any mod ID of its database entry is installed
- FR185: A newly installed mod has an update status in the Installed list without waiting for the next update check; a mod with no update data shows "Not checked yet", not "Unknown"

#### Access and Settings

- FR186: A Monitor key never receives the game server password: game settings report only whether a password is set, and the config file viewer redacts it; Admin access is unchanged
- FR187: Changing a refresh interval setting reschedules its job without restarting the API; setting it to 0 stops the job and raising it from 0 starts it
- FR188: A boolean game setting with no value in the server config shows the game's default, marked as the default, or "Not set" when the default is not known; it is never shown as Disabled because it is missing

#### Navigation and Layout

- FR189: On a mod detail page, Browse is the active Mods tab and the Installed tab opens the Installed list
- FR190: A browse link whose page is beyond the results opens the last page (page 1 when there are no results) without adding a history entry
- FR191: At tablet widths (768-1023px) the installed mods list fits the screen without horizontal scrolling
- FR192: On phones, the Settings tab list does not make the page scroll horizontally
- FR193: On wide screens, the Game Settings title row is aligned with the centered settings panel

### Epic 18: Mod Media and Fixes

#### Mod Detail Page

- FR194: The mod detail page shows the mod's screenshots from the mod database as a gallery with thumbnails, previous and next, and a larger view; the gallery is hidden when the mod has no screenshots
- FR195: The gallery works with the keyboard and on touch screens, gives each image alt text from its file name, loads images lazily, and fits phone widths in the light and dark themes
- FR196: A mod with a trailer video has a link on its detail page that opens the trailer in a new tab; no video player is embedded
- FR197: The API passes on only screenshot URLs that use https on the mod database's image host, and only trailer URLs that name a YouTube video; anything else is left out and never fails the lookup
- FR198: Links in a mod description are marked as opening in a new tab, visibly and for screen readers

#### Install and Version Change

- FR199: Installing a mod whose file name is already used in the mods directory, enabled or disabled, is refused with 409 and changes no file and no state
- FR200: After a version change, the mod's stored update record comes from that change's own lookup, so the Installed list shows a real status for the new version without waiting for the next update check

#### Mod Browser

- FR201: Mod browser cards show whether the mod has a release tagged for the installed game version, from one cached request per game version and never a request per card
- FR202: When the installed game version is unknown or the mod database cannot answer, cards show no game version indicator and browsing works as before

#### Installed Mods

- FR203: The installed mod cards have a sort control (name, version or status, ascending or descending) that uses the same saved preference as the table headers
- FR204: At 1024px and wider, the installed mods table fits its container when a mod has a long name: nothing scrolls sideways and the enable toggle and remove action are on screen

### Epic 19: API Security and Mod File Safety

#### Secrets and Roles

- FR205: The config file viewer lists and serves only `.json` files under the server data directory, up to 2 MiB
- FR206: A config file request for anything else (another file type, a directory, a file that is too large or not UTF-8 text) is refused with a 4xx status and an error code, never a 500
- FR207: For every role other than Admin, config file content is redacted at every depth: values under secret key names, `StartupCommands`, URLs that contain credentials and Discord webhook URLs; Admin receives files unchanged
- FR208: Roles other than Admin can list and read only the root of the server data directory and `ModConfig`; any other directory (saves, backups, player data) is listed and read by Admin only
- FR209: `VS_GAME_VERSION` is removed from the settings and the documentation; a deployment that still sets it starts as before

#### The Web UI's Key

- FR210: When `VS_API_KEY` is unset or blank, the web UI is given no API key: the API starts, `/config.js` serves an empty key, and the web UI shows a set-up message and makes no API request
- FR211: The API logs a start-up warning whenever the web UI's key is the Admin key and whenever the web UI has no key, never logging a key
- FR212: The README, `.env.example` and the compose examples explain `VS_API_KEY`, recommend the Monitor key or an authenticating proxy for the web UI, the production example does not hand out the Admin key by default, and the release notes list the change as breaking with what to set

#### Content-Security-Policy and API Docs

- FR213: The web UI's pages are served with an enforced Content-Security-Policy that allows scripts from the manager's own origin only and forbids framing; it is not sent on API or health routes
- FR214: Every page of the web UI, including the console WebSocket, the mod gallery and mod description images, works under the policy in the light and dark themes with no policy violation
- FR215: `VS_CSP_MODE` switches the policy between enforced, report-only and off, and the web UI's pages also send `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer` and `X-Frame-Options: DENY`
- FR216: An image in a mod description that the policy would block (any address that is not https or an image data URL) is replaced by a short text with its alt text, with no request and no broken-image icon
- FR217: The API documentation pages and the OpenAPI schema (`/docs`, `/redoc`, `/openapi.json`) are served only when the API runs in debug mode

#### Mod Files

- FR218: Enabling or disabling a mod whose target file name is already used is refused with 409 `MOD_FILE_CONFLICT` and changes no file and no state
- FR219: A version change whose new file name is already used is refused with 409 `MOD_FILE_CONFLICT` instead of a 500, changes nothing, and in Update All is one failed item that does not stop the run
- FR220: File-name collisions for install, enable, disable and version change are detected ignoring letter case, so the result does not depend on the volume's filesystem
- FR221: The mod download cache keeps each release under its file ID with a temporary file per download, so mods whose releases share a file name never replace or mix each other's cached archives
- FR222: Enabling or disabling a mod whose own file is missing is refused with 409 `MOD_FILE_MISSING` and a message that says what to do, never a 500
- FR223: At start-up the manager recovers from an interrupted install or version change: its own working files are removed or put back so that every mod's file matches the mod state; files it did not create are reported and left alone

#### Mod Database Data

- FR224: The API passes on a mod's logo URL only when it uses https on the mod database's image host, and the web requests logo images without a referrer
- FR225: The API passes on a mod's homepage and source URLs only when they are well-formed https URLs; anything else is left out and never fails the lookup
- FR226: A mod database response that is not a JSON object is answered with 502 `EXTERNAL_API_ERROR` on every mod route, never a 500, and is not cached
- FR227: Requests that arrive while the mod listing or the game version list is not cached share one request to the mod database

#### E2E in CI

- FR228: CI builds the image, starts it without a game server but with a seeded fixture `serverconfig.json`, and runs the E2E tests against it on every pull request and push to `main`, keeping the report of a failed run
- FR229: E2E tests that need the live mod database, an installed game server or a real mod install are tagged and left out of CI; they still run locally. The settings specs run in CI against the seeded configuration
- FR230: No E2E spec sets an API key in `localStorage`; every spec gets its key through one shared `/config.js` helper

#### Decided on Review (Matt, 2026-11-17)

- FR231: At start-up, after recovering its own working files, the manager reconciles the mod state with the mods directory once: a mod archive added by hand gets an entry and an entry whose file is gone is removed, each change is logged, and there is no endpoint or button for it
- FR232: The start-up reconcile looks only at mod archives, skips with a warning an archive it cannot read or whose mod is already installed under another file, ignores working, `.tmp` and `.bak` files, and never stops the API from starting
- FR233: With a key whose role is not Admin, the web file browser shows a short static note that some folders are only shown to Admin keys, without folder names or counts

### Epic 20: Tooling and Test Health

#### Formatting

- FR234: Every Python file of the API is in `ruff format`'s form; the reformat is one commit that holds nothing else
- FR235: `just lint-api`, and through it CI and `just check`, fails when an API file is not formatted
- FR236: The reformat commit is listed in `.git-blame-ignore-revs`, so `git blame` skips it on GitHub and in a set-up worktree

#### A Quiet Check

- FR237: `just typecheck-api` reports 0 errors and 0 warnings, with no ignore comment and no lowered rule
- FR238: The web test suite reports 0 skipped tests; empty placeholders are gone and the remove-button loading state is tested
- FR239: The web tests run in Vitest's `vmThreads` pool and pass there locally and in CI

#### Lint and Type Check Coverage

- FR240: `just typecheck` and CI type-check the E2E specs and the Playwright configuration; the web build does not depend on them
- FR241: `just lint-scripts` checks every script, `scripts/sprint-status.sh` included, and that script passes ShellCheck with no directive
- FR242: Every `just` recipe that passes arguments on hands each argument to the tool as it was quoted, so `just test-api -k "a or b"` works
- FR243: Playwright's report and result files are not tracked and are ignored, so a local E2E run leaves the working tree clean

#### Static Analysis

- FR244: `just semgrep` runs a pinned semgrep with the packs `p/python`, `p/typescript`, `p/react`, `p/secrets`, `p/github-actions` and `p/dockerfile` over the source (`api/src`, `web/src`, `.github`, `Dockerfile`, `scripts`), not over test files, with metrics off
- FR245: In CI a pull request fails only on semgrep findings it adds; a full scan of `main` reports every finding and does not fail because of them
- FR246: The full scan's results are uploaded to GitHub code scanning as SARIF by a job that alone has `security-events: write`, with pinned actions and the release-commit skip
- FR247: The source has no open semgrep finding; a verified false positive may be marked with an inline `nosemgrep` comment that names one rule and gives a reason, as a documented exception to the no-suppressions rule

#### E2E Coverage in CI

- FR248: CI's E2E stack is seeded with a nested directory, and the file browser navigation tests run in CI
- FR249: An E2E test shows that a directory created while the file manager is open is listed after the page is loaded again
- FR250: CI's E2E job restores the Playwright browsers from a cache keyed by the Playwright versions
- FR251: The connection reset seen in the E2E server-status stub has a recorded cause or a record of what was tried, and its retry is explained or removed
- FR252: CI runs the E2E tests that need mod database answers against recorded answers, served by a replay that the API reaches through `VS_MOD_DB_URL`, with no request to the live service
- FR253: The recorded answers are files in the repository with a manifest of what was recorded and when, and one command refreshes them from the live mod database and reports changes in shape
- FR254: Tests that must compare with the live mod database or install a real mod are tagged and stay local-only; every spec still runs against the live service on a developer's machine

#### Image and Conventions

- FR255: Every image the Dockerfile builds from or copies from is pinned by digest, the uv version equals the one in `.mise.toml`, and a script test enforces both
- FR256: Renovate proposes updates for the pinned image digests and moves uv in the Dockerfile and in `.mise.toml` together
- FR257: The story numbering rule in `project-context.md` matches the practice: a preparation story is X.0, and an epic without one starts at X.1

#### The Mod Database's Address (Matt, 2026-11-17)

- FR258: `VS_MOD_DB_URL` sets the base address the API uses for mod database requests and mod downloads; it defaults to `https://mods.vintagestory.at`, and the image host allow-list, the link rules and the links the web UI builds do not follow it
- FR259: The address is validated at start-up: it must be an `https` URL with a host and nothing else, `http` is accepted only when `VS_DEBUG=true`, anything else stops start-up with an error that names the setting, and an address other than the default is logged as a warning

### Epic 21: Maintainer Decisions and Web Polish

#### Web Formatting (Matt, 2026-11-17)

- FR260: Every TypeScript, CSS and JSON file of the web that Prettier covers is in Prettier's form under the committed configuration; the reformat is one commit that holds nothing else
- FR261: Prettier is a dev dependency of the web pinned to an exact version, with a committed configuration and ignore file; `just format-web` uses it, and recorded test fixtures, Markdown and HTML are not covered
- FR262: `just lint-web`, and through it CI's `web` job and `just check`, fails when a covered web file is not formatted
- FR263: The web reformat commit is listed in `.git-blame-ignore-revs`, so `git blame` skips it on GitHub and in a set-up worktree

#### Renovate (Matt, 2026-11-17)

- FR264: A uv update keeps the organisation preset's one-day hold on its `.mise.toml` half, and `RELEASING.md` says that its pull request opens with the Dockerfile half only, fails the uv version test for about a day, and must not be merged until it holds both halves
- FR265: A digest refresh of a Dockerfile image under an unchanged tag is committed as `chore(container)` and adds no release note; a version change of an image keeps the preset's `fix` or `feat` type

#### Log Level (Matt, 2026-11-17)

- FR266: `VS_LOG_LEVEL` (`DEBUG`, `INFO`, `WARNING` or `ERROR`, in any letter case) sets the API's log level at start-up; unset or blank, the level is DEBUG with `VS_DEBUG=true` and INFO otherwise, as before; it changes nothing else that `VS_DEBUG` controls
- FR267: Any other value of `VS_LOG_LEVEL` stops start-up with an error that names the setting; turning debug logging on at run time still sets DEBUG and turning it off returns to the configured level; the setting is documented in the README and `.env.example`

#### Config File Viewer

- FR268: Discord webhook URLs on `ptb.discord.com` and `canary.discord.com` are redacted for roles other than Admin like those on `discord.com` and `discordapp.com`, from one list of hosts
- FR269: A config directory listing never shows an entry that resolves outside the server data directory, for any role
- FR270: A role other than Admin asking for a directory it may not list gets 403 whether or not the server data directory exists

#### Mod Removal and Error Messages

- FR271: After the administrator confirms, the mod remove dialog stays open and shows that the removal is running, cannot be dismissed while it runs, and closes when the removal has succeeded (Matt, 2026-11-17)
- FR272: When a removal fails, one error message is shown and the dialog stays open so the administrator can try again or cancel
- FR273: The running state of the remove dialog belongs to the mod being removed; another mod's dialog never shows it (Matt, 2026-11-17)
- FR274: A failed action in the web UI shows exactly one error message: a mod install, a server install, uninstall or restart, and a change of the mod update webhook

#### Tables and Dialogs

- FR275: Versions are sorted by Semantic Versioning precedence (a pre-release before its release, numeric parts as numbers) in the installed mods list and on the Version page, by one comparison function and without a new dependency
- FR276: Sortable column headers expose their sort state to assistive technology (`aria-sort`: ascending, descending or none) in the installed mods table and the Version table
- FR277: The close button of every dialog and of the phone navigation sheet is at least 44 by 44px

#### Mod Detail Page

- FR278: Every link in the web UI that opens a new tab says so to assistive technology in the same words, including SVG links inside mod descriptions
- FR279: The mod detail page does not scroll sideways from 320px up: its header stacks below 768px and wide description content stays inside its card
- FR280: Mod descriptions are typeset (headings, paragraphs, lists, links, quotes, code and tables) with the theme's colours in both themes, without a new dependency

#### Tabs, Tables and Layout

- FR281: Tab buttons are at least 44px tall below 1024px in every tab list
- FR282: Arrow keys move focus and selection in the Settings tab list as soon as a tab can receive focus, or the cause of the reported delay is recorded with evidence when it cannot be reproduced with a real keyboard or lies outside the project's code
- FR283: The Scheduled Jobs and Version tables do not scroll inside themselves from 320 to 1023px in either sidebar state, and every page of the web UI has recorded measurements at those widths
- FR284: With no sidebar choice stored, the sidebar is collapsed from 768 to 1023px and expanded from 1024px; an explicit choice applies at every width and is kept; the choice can be set back to automatic
- FR285: Page content is at most 1280px wide and centered; the console pages use the full width

#### Pulled In (Matt, 2026-11-17)

- FR286: When the installed game version changes, the mod data in the web UI that depends on it (the browse cards' release badges, compatibility and update status) is fetched again without a reload, triggered by the version the server status reports
