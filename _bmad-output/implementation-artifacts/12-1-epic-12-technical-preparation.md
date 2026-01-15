# Story 12.1: Epic 12 Technical Preparation

Status: ready-for-dev

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

- [ ] Task 1: Research psutil for process metrics collection + document findings (AC: 1)
  - [ ] Subtask 1.1: Document psutil installation and basic usage patterns
  - [ ] Subtask 1.2: Document how to get memory (RSS, VMS) and CPU percent for current process
  - [ ] Subtask 1.3: Document asyncio-friendly usage patterns (psutil is sync but fast)
  - [ ] Subtask 1.4: Add findings to architecture.md under new "Metrics Collection" section

- [ ] Task 2: Document game server process discovery + metrics extraction (AC: 1)
  - [ ] Subtask 2.1: Research how to find VintageStory game server process (by name pattern or PID file)
  - [ ] Subtask 2.2: Document existing `ServerService.get_status()` and container process tracking
  - [ ] Subtask 2.3: Document how to get external process metrics via psutil.Process(pid)
  - [ ] Subtask 2.4: Document graceful handling when game server is not running
  - [ ] Subtask 2.5: Add ADR to architecture.md for process discovery approach

- [ ] Task 3: Evaluate charting libraries + recommend choice (AC: 2)
  - [ ] Subtask 3.1: Research recharts - features, bundle size, React 19 compatibility
  - [ ] Subtask 3.2: Research lightweight alternatives (visx, Chart.js, uPlot)
  - [ ] Subtask 3.3: Document trade-offs (bundle size, features, TypeScript support, theming)
  - [ ] Subtask 3.4: Recommend library with rationale
  - [ ] Subtask 3.5: Add ADR to architecture.md for charting library selection

- [ ] Task 4: Design MetricsSnapshot data model + ring buffer storage (AC: 3)
  - [ ] Subtask 4.1: Define MetricsSnapshot schema (timestamp, api_memory_mb, api_cpu_percent, game_memory_mb, game_cpu_percent)
  - [ ] Subtask 4.2: Design in-memory ring buffer with configurable capacity (default: 360 samples = 1hr at 10s interval)
  - [ ] Subtask 4.3: Document retention policy and eviction strategy (FIFO)
  - [ ] Subtask 4.4: Specify thread-safety considerations for APScheduler job access
  - [ ] Subtask 4.5: Add data model to architecture.md

- [ ] Task 5: Research player count extraction methods (AC: 4)
  - [ ] Subtask 5.1: Check VintageStory console output for player join/leave messages
  - [ ] Subtask 5.2: Research if VintageStory has RCON or API for player info
  - [ ] Subtask 5.3: Check agentdocs/vs-server-troubleshooting.md for relevant info
  - [ ] Subtask 5.4: Document findings and limitations
  - [ ] Subtask 5.5: Add findings to architecture.md (may be deferred to future epic if complex)

- [ ] Task 6: Update architecture.md with Epic 12 technical decisions (AC: all)
  - [ ] Subtask 6.1: Create "Epic 12: Dashboard Metrics" section
  - [ ] Subtask 6.2: Add all ADRs from Tasks 1-5
  - [ ] Subtask 6.3: Document integration points with existing scheduler service
  - [ ] Subtask 6.4: Verify all findings are properly referenced

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

{{agent_model_name_version}}

### Debug Log References

### Completion Notes List

### File List

