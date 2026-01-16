# Story 12.1: Epic 12 Technical Preparation

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a **developer**,
I want **to research metrics collection and visualization approaches**,
So that **subsequent stories have a solid technical foundation**.

## Acceptance Criteria

1. **Given** we need to collect process metrics
   **When** I research approaches
   **Then** I document how to use psutil for API server metrics
   **And** I document how to find and monitor the VintageStory game server process

2. **Given** we need to display charts
   **When** I evaluate charting libraries
   **Then** I recommend a library (recharts, visx, or lightweight alternative)
   **And** I document bundle size and feature trade-offs

3. **Given** we need to store historical metrics
   **When** I design the storage approach
   **Then** I document in-memory ring buffer design with configurable retention
   **And** I specify data structure for metrics snapshots

4. **Given** we may want player information
   **When** I research VintageStory server capabilities
   **Then** I document how to get player count (console parsing, RCON, or API)
   **And** I note any limitations

## Tasks / Subtasks

<!--
This is a RESEARCH/PREPARATION story - no code implementation, only documentation deliverables.
Each task produces documented findings in architecture.md.
-->

- [x] Task 1: Research psutil for process metrics collection + document findings (AC: 1)
  - [x] Subtask 1.1: Document psutil installation and basic usage patterns
  - [x] Subtask 1.2: Document how to get memory (RSS, VMS) and CPU percent for current process
  - [x] Subtask 1.3: Document asyncio-friendly usage patterns (psutil is sync but fast)
  - [x] Subtask 1.4: Add findings to architecture.md under new "Metrics Collection" section

- [x] Task 2: Document game server process discovery + metrics extraction (AC: 1)
  - [x] Subtask 2.1: Research how to find VintageStory game server process (by name pattern or PID file)
  - [x] Subtask 2.2: Document existing `ServerService.get_status()` and container process tracking
  - [x] Subtask 2.3: Document how to get external process metrics via psutil.Process(pid)
  - [x] Subtask 2.4: Document graceful handling when game server is not running
  - [x] Subtask 2.5: Add ADR to architecture.md for process discovery approach

- [x] Task 3: Evaluate charting libraries + recommend choice (AC: 2)
  - [x] Subtask 3.1: Research recharts - features, bundle size, React 19 compatibility
  - [x] Subtask 3.2: Research lightweight alternatives (visx, Chart.js, uPlot)
  - [x] Subtask 3.3: Document trade-offs (bundle size, features, TypeScript support, theming)
  - [x] Subtask 3.4: Recommend library with rationale
  - [x] Subtask 3.5: Add ADR to architecture.md for charting library selection

- [x] Task 4: Design MetricsSnapshot data model + ring buffer storage (AC: 3)
  - [x] Subtask 4.1: Define MetricsSnapshot schema (timestamp, api_memory_mb, api_cpu_percent, game_memory_mb, game_cpu_percent)
  - [x] Subtask 4.2: Design in-memory ring buffer with configurable capacity (default: 360 samples = 1hr at 10s interval)
  - [x] Subtask 4.3: Document retention policy and eviction strategy (FIFO)
  - [x] Subtask 4.4: Specify thread-safety considerations for APScheduler job access
  - [x] Subtask 4.5: Add data model to architecture.md

- [x] Task 5: Research player count extraction methods (AC: 4)
  - [x] Subtask 5.1: Check VintageStory console output for player join/leave messages
  - [x] Subtask 5.2: Research if VintageStory has RCON or API for player info
  - [x] Subtask 5.3: Check agentdocs/vs-server-troubleshooting.md for relevant info
  - [x] Subtask 5.4: Document findings and limitations
  - [x] Subtask 5.5: Add findings to architecture.md (may be deferred to future epic if complex)

- [x] Task 6: Update architecture.md with Epic 12 technical decisions (AC: all)
  - [x] Subtask 6.1: Create "Epic 12: Dashboard Metrics" section
  - [x] Subtask 6.2: Add all ADRs from Tasks 1-5
  - [x] Subtask 6.3: Document integration points with existing scheduler service
  - [x] Subtask 6.4: Verify all findings are properly referenced

## Dev Notes

### Research Focus Areas

This is a **technical preparation story** - no code implementation is required. The deliverable is comprehensive documentation in `architecture.md` that will guide Stories 12.2-12.6.

### Existing Infrastructure to Leverage

**Scheduler Service (Epic 7):**
- Location: [scheduler.py](api/src/vintagestory_api/services/scheduler.py)
- Pattern: `SchedulerService.add_interval_job(func, seconds, job_id)`
- Metrics collection will follow same pattern as `mod_cache_refresh` and `server_versions` jobs

**Server Status Service:**
- Location: `api/src/vintagestory_api/services/server.py`
- Already provides: state, version, uptime, disk space
- May need to extend or wrap for process-level metrics

**Current Dashboard:**
- Location: [Dashboard.tsx](web/src/features/dashboard/Dashboard.tsx)
- Currently displays: server state badge, version, uptime, disk space
- Uses TanStack Query with 5-second polling
- Stories 12.4-12.6 will enhance this

### Technology Stack Context

**Backend:**
- Python >= 3.12 with FastAPI 0.127.1+
- APScheduler v3.11.x (NOT v4.x)
- structlog for logging
- uv for package management

**Frontend:**
- React 19.2, TypeScript 5.x
- TanStack Query v5 for server state
- Tailwind CSS v4 with Catppuccin theme
- Bun 1.3.5 for package management
- **No charting library currently installed** - Task 3 will recommend one

### Research Hints

**psutil:**
- Well-maintained Python library for system/process utilities
- `pip install psutil` (or `uv add psutil`)
- Key methods: `psutil.Process().memory_info()`, `psutil.Process().cpu_percent()`
- Consider async wrappers if needed (psutil is sync but operations are fast)

**Charting Libraries to Evaluate:**
- **recharts** - Popular React charting, ~400KB bundle, good theming
- **visx** - Low-level Airbnb library, smaller bundle, more control
- **uPlot** - Ultra-lightweight (~50KB), very fast, less React-native
- **Chart.js** - Canvas-based, ~200KB, needs react-chartjs-2 wrapper

**VintageStory Player Count:**
- Console may log "Player X joined" / "Player X left" messages
- May need to parse `ConsoleService` buffer
- No known REST API for player info
- RCON support unknown - research needed

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- Metrics endpoints should be Admin-only (FR106)
- No sensitive data in metrics (no player names, no API keys)
- DEBUG mode gating not needed (metrics are operational data)

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters

### Architecture & Patterns

- New MetricsService follows existing service patterns (see `ServerService`, `ModService`)
- Background job follows `jobs/` module pattern (see `mod_cache_refresh.py`)
- Router follows existing `/api/v1alpha1/` prefix pattern

### Project Structure Notes

Files to create/modify in subsequent stories:
- `api/src/vintagestory_api/services/metrics.py` (Story 12.2)
- `api/src/vintagestory_api/jobs/metrics_collection.py` (Story 12.2)
- `api/src/vintagestory_api/routers/metrics.py` (Story 12.3)
- `web/src/hooks/use-metrics.ts` (Story 12.4)
- `web/src/features/dashboard/components/StatCard.tsx` (Story 12.4)
- `web/src/features/dashboard/components/MetricsChart.tsx` (Story 12.5)

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Epic 12] - Full epic definition
- [Source: _bmad-output/planning-artifacts/architecture.md] - Current architecture (to be updated)
- [Source: agentdocs/vs-server-troubleshooting.md] - VintageStory server quirks

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

N/A - Research/documentation story, no code implementation

### Completion Notes List

1. **Task 1-2 (psutil research)**: Documented psutil usage patterns for process metrics (RSS, VMS, CPU percent). Researched using Context7 documentation. Found psutil provides simple API for both current process and external process by PID. AsyncIO not needed - operations are fast enough for direct sync calls.

2. **Task 2 (game server discovery)**: Analyzed ServerService._process to confirm direct PID access is available when game server is running. Documented graceful degradation when server is not running (return None for metrics).

3. **Task 3 (charting library)**: Evaluated Recharts, visx, Chart.js, and uPlot. Recommended **Recharts** for: native TypeScript, React 19 compatibility, excellent DX, built-in tooltips/responsive containers. Bundle size (~400KB) acceptable given feature set.

4. **Task 4 (MetricsSnapshot + ring buffer)**: Designed frozen dataclass for MetricsSnapshot with timestamp and 4 metric fields. Designed MetricsBuffer using collections.deque (same pattern as ConsoleBuffer). Default 360 samples = 1 hour at 10s intervals.

5. **Task 5 (player count)**: Researched VintageStory capabilities. No RCON or HTTP API available. Console parsing possible but complex. **Deferred** to future epic due to fragility and complexity vs value.

6. **Task 6 (architecture.md)**: Created comprehensive `architecture/epic-12-dashboard-metrics.md` with 5 ADRs covering all decisions. Updated main architecture.md index to include new file.

### File List

- `_bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md` (created)
- `_bmad-output/planning-artifacts/architecture.md` (modified - added Epic 12 to index)

