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
lastUpdated: '2026-01-10'
updates:
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

- Scheduled mod update checks with notifications
- Mod version switching (rollback to previous versions)
- Backup management (create, restore, download)
- Renovate integration for automated dependency updates
- SBOM generation and security scanning in CI
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
| **Mods** | `/mods`, `/mods/{slug}`, `/mods/{slug}/update`, `/mods/{slug}/enable`, `/mods/{slug}/disable`, `/mods/check-updates` | GET, POST, PUT, DELETE |
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

- Mod update detection and one-click updates
- Mod version switching (rollback capability)
- Backup management (create, restore, download)
- Prometheus `/metrics` endpoint
- Renovate integration for dependency updates
- SBOM generation and security scanning

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
