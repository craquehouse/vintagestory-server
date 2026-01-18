# Story 12.4: Dashboard Stats Cards

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **stat cards showing current server metrics**,
So that **I can see server health at a glance**.

## Acceptance Criteria

1. **Given** I view the Dashboard
   **When** the page loads
   **Then** I see stat cards for: Server Status, Memory Usage, Disk Space, Uptime

2. **Given** the Memory Usage card is displayed
   **When** metrics are available
   **Then** I see API memory and Game memory separately
   **And** values update in real-time (polling every 10 seconds)

3. **Given** the Server Status card is displayed
   **When** I view it
   **Then** I see status badge (running/stopped/etc.)
   **And** Start/Stop/Restart buttons are available

4. **Given** the game server is not running
   **When** I view the Memory card
   **Then** Game memory shows "N/A" or "-"
   **And** API memory is still displayed

5. **Given** I am on a mobile device
   **When** I view the Dashboard
   **Then** stat cards stack vertically in a responsive layout

## Tasks / Subtasks

<!--
Tasks designed to be 4-6 total per project-context.md guidelines.
Each task includes tests and maps to specific ACs.
-->

- [x] Task 1: Create useMetrics hook + API integration + tests (AC: 2, 4)
  - [x] Subtask 1.1: Add metrics types to `web/src/api/types.ts`
  - [x] Subtask 1.2: Add metrics query keys to `web/src/api/query-keys.ts`
  - [x] Subtask 1.3: Create `web/src/hooks/use-metrics.ts` with useCurrentMetrics hook
  - [x] Subtask 1.4: Configure 10-second polling interval
  - [x] Subtask 1.5: Write tests for useMetrics hook

- [x] Task 2: Create StatCard component + tests (AC: 1, 5)
  - [x] Subtask 2.1: Create `web/src/components/StatCard.tsx` base component
  - [x] Subtask 2.2: Support icon, label, value, optional trend indicator
  - [x] Subtask 2.3: Add responsive styling (stack on mobile)
  - [x] Subtask 2.4: Write tests for StatCard component

- [x] Task 3: Create specialized metric cards + tests (AC: 1, 2, 3, 4)
  - [x] Subtask 3.1: Create MemoryCard component with API/Game breakdown
  - [x] Subtask 3.2: Create DiskSpaceCard component (using existing status data)
  - [x] Subtask 3.3: Create UptimeCard component
  - [x] Subtask 3.4: Enhance ServerStatusCard with controls integration
  - [x] Subtask 3.5: Handle null game metrics gracefully (show "N/A")
  - [x] Subtask 3.6: Write tests for all metric cards

- [x] Task 4: Redesign Dashboard layout with card grid + tests (AC: 1, 5)
  - [x] Subtask 4.1: Refactor Dashboard.tsx to use card grid layout
  - [x] Subtask 4.2: Integrate all stat cards into Dashboard
  - [x] Subtask 4.3: Add responsive grid (2 cols on desktop, 1 col on mobile)
  - [x] Subtask 4.4: Move server controls into Status card
  - [x] Subtask 4.5: Write integration tests for Dashboard with stat cards

- [x] Task 5: Manual browser verification (AC: all)
  - [x] Subtask 5.1: Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Subtask 5.2: Navigate to Dashboard in browser
  - [x] Subtask 5.3: Verify all 4 stat cards display correctly
  - [x] Subtask 5.4: Test with server running (all metrics populated)
  - [x] Subtask 5.5: Test with server stopped (game metrics show N/A)
  - [x] Subtask 5.6: Test responsive layout at mobile breakpoint
  - [x] Subtask 5.7: Verify metrics update every 10 seconds

## Dev Notes

### Technical Decisions (from Story 12.1)

All technical decisions are documented in [epic-12-dashboard-metrics.md](_bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md).

**Key ADRs:**
- **ADR-E12-001:** Use psutil for process metrics (implemented in 12.2)
- **ADR-E12-002:** Game server PID via ServerService._process (implemented in 12.2)
- **ADR-E12-003:** Use Recharts for charting (Story 12.5)
- **ADR-E12-004:** Ring buffer using collections.deque (implemented in 12.2)

### Existing Infrastructure (from Story 12.2 & 12.3)

**Metrics API Endpoints** (implemented in 12.3):
- `GET /api/v1alpha1/metrics/current` - Returns latest MetricsSnapshot
- `GET /api/v1alpha1/metrics/history?minutes=N` - Returns historical metrics
- Both endpoints require Admin role

**API Response Format:**
```json
{
  "status": "ok",
  "data": {
    "timestamp": "2026-01-17T10:30:00Z",
    "apiMemoryMb": 128.5,
    "apiCpuPercent": 2.3,
    "gameMemoryMb": 512.0,
    "gameCpuPercent": 15.2
  }
}
```

**Empty/Null Response (game server not running):**
```json
{
  "status": "ok",
  "data": {
    "timestamp": "2026-01-17T10:30:00Z",
    "apiMemoryMb": 128.5,
    "apiCpuPercent": 2.3,
    "gameMemoryMb": null,
    "gameCpuPercent": null
  }
}
```

### Frontend Patterns to Follow

**TanStack Query Hook Pattern:**
```typescript
// web/src/hooks/use-metrics.ts
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { queryKeys } from '../api/query-keys';

interface MetricsSnapshot {
  timestamp: string;
  apiMemoryMb: number;
  apiCpuPercent: number;
  gameMemoryMb: number | null;
  gameCpuPercent: number | null;
}

export function useCurrentMetrics() {
  return useQuery({
    queryKey: queryKeys.metrics.current,
    queryFn: async () => {
      const response = await apiClient<MetricsSnapshot | null>('/api/v1alpha1/metrics/current');
      return response.data;
    },
    refetchInterval: 10000,  // Poll every 10 seconds (matches collection interval)
    refetchIntervalInBackground: false,
  });
}
```

**Query Keys Pattern:**
```typescript
// Add to web/src/api/query-keys.ts
metrics: {
  current: ['metrics', 'current'] as const,
  history: (minutes?: number) => ['metrics', 'history', minutes] as const,
},
```

**StatCard Component Pattern:**
```tsx
// web/src/components/StatCard.tsx
import { Card, CardContent, CardHeader, CardTitle } from './ui/card';
import type { LucideIcon } from 'lucide-react';

interface StatCardProps {
  icon: LucideIcon;
  title: string;
  value: string | number;
  subtitle?: string;
  className?: string;
}

export function StatCard({ icon: Icon, title, value, subtitle, className }: StatCardProps) {
  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center gap-3">
          <Icon className="size-5 text-muted-foreground" />
          <CardTitle className="text-base">{title}</CardTitle>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        {subtitle && <div className="text-sm text-muted-foreground">{subtitle}</div>}
      </CardContent>
    </Card>
  );
}
```

**Dashboard Grid Layout:**
```tsx
// Responsive grid: 2 cols on md+, 1 col on mobile
<div className="grid gap-4 md:grid-cols-2">
  <ServerStatusCard />
  <MemoryCard />
  <DiskSpaceCard />
  <UptimeCard />
</div>
```

### Current Dashboard State

The Dashboard (`web/src/features/dashboard/Dashboard.tsx`) currently:
- Uses `useServerStatus()` hook with 5-second polling
- Shows server state badge, version, uptime, disk space
- Has ServerControls component for Start/Stop/Restart
- Uses Card components from shadcn/ui

**Current data available from `useServerStatus()`:**
- `state` - Server state (running, stopped, starting, etc.)
- `version` - Game version string
- `uptime` - Uptime in seconds
- `diskSpaceFreeGb` - Free disk space
- `diskSpaceTotalGb` - Total disk space

**New data needed from metrics API:**
- `apiMemoryMb` - API server memory usage
- `apiCpuPercent` - API server CPU usage
- `gameMemoryMb` - Game server memory (null if not running)
- `gameCpuPercent` - Game server CPU (null if not running)

### UI/UX Requirements

**Card Icons (lucide-react):**
- Server Status: `Server`
- Memory Usage: `MemoryStick` or `Cpu`
- Disk Space: `HardDrive`
- Uptime: `Clock`

**Color Scheme (Catppuccin):**
- Use `text-success` for healthy metrics
- Use `text-warning` for concerning metrics
- Use `text-destructive` for critical issues
- Use `text-muted-foreground` for labels

**Memory Display Format:**
```
Memory Usage
API: 128.5 MB
Game: 512.0 MB (or "N/A" if null)
```

**Responsive Behavior:**
- Desktop (md+): 2-column grid
- Mobile (<md): Single column, full width

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

**Test Patterns:**
- Use `@testing-library/react` for component tests
- Mock API responses with MSW or direct mocks
- Test loading, error, and success states
- Test null/undefined handling for game metrics
- Co-locate tests with components (`*.test.tsx`)

**Test file locations:**
- `web/src/hooks/use-metrics.test.ts`
- `web/src/components/StatCard.test.tsx`
- `web/src/features/dashboard/Dashboard.test.tsx`

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- Metrics endpoints require Admin role (enforced by API)
- No additional security requirements for frontend
- API key is handled automatically by apiClient

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just test-web src/hooks/use-metrics.test.ts` - Run specific file
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server
- `just dev-api` - Start API dev server (needed for manual testing)

### Previous Story Intelligence (Story 12.3)

From [12-3-metrics-api-endpoints.md](_bmad-output/implementation-artifacts/12-3-metrics-api-endpoints.md):

1. **Metrics API fully implemented** - `/current` and `/history` endpoints ready
2. **Response format established** - camelCase JSON, null for unavailable game metrics
3. **Admin-only access** - 403 returned for Monitor role
4. **Empty buffer handled** - Returns null for current, empty list for history
5. **All 1293 tests pass** - No regressions from metrics API implementation

### Architecture & Patterns

**Component Organization:**
- Generic `StatCard` in `components/` folder
- Specialized cards (MemoryCard, etc.) can be in `features/dashboard/` or `components/`
- Follow existing Card component patterns from shadcn/ui

**Data Flow:**
```
Metrics API → useCurrentMetrics hook → Dashboard → Stat Cards
                     ↓
              10-second polling
```

**State Management:**
- Server state from API → TanStack Query (existing `useServerStatus`)
- Metrics state from API → TanStack Query (new `useCurrentMetrics`)
- NO mixing with React Context

### Project Structure Notes

Files to create:
- `web/src/api/types.ts` (MODIFY - add metrics types)
- `web/src/api/query-keys.ts` (MODIFY - add metrics keys)
- `web/src/hooks/use-metrics.ts` (NEW)
- `web/src/hooks/use-metrics.test.ts` (NEW)
- `web/src/components/StatCard.tsx` (NEW)
- `web/src/components/StatCard.test.tsx` (NEW)
- `web/src/features/dashboard/MemoryCard.tsx` (NEW)
- `web/src/features/dashboard/DiskSpaceCard.tsx` (NEW)
- `web/src/features/dashboard/UptimeCard.tsx` (NEW)
- `web/src/features/dashboard/Dashboard.tsx` (MODIFY - add grid layout)
- `web/src/features/dashboard/Dashboard.test.tsx` (MODIFY - add stat card tests)

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 12.4] - Epic requirements
- [Source: _bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md] - Technical decisions
- [Source: api/src/vintagestory_api/routers/metrics.py] - Metrics API implementation
- [Source: web/src/features/dashboard/Dashboard.tsx] - Current Dashboard implementation
- [Source: web/src/components/ui/card.tsx] - Card component patterns
- [Source: web/src/hooks/use-server-status.ts] - Query hook patterns

## Dev Agent Record

### Agent Model Used

Claude Opus 4.5 (claude-opus-4-5-20251101)

### Debug Log References

### Completion Notes List

- Task 1: Created useMetrics hook with 10-second polling (AC: 2), null game metrics handling (AC: 4), and useMetricsHistory hook for Story 12.5. All 11 tests passing.
- Task 2: Created StatCard base component with icon, title, value, subtitle support. Supports children for custom content. All 15 tests passing.
- Task 3: Created MemoryCard, DiskSpaceCard, UptimeCard, ServerStatusCard. MemoryCard shows N/A for game metrics when not running (AC: 4). ServerStatusCard includes controls (AC: 3). All 22 tests passing.
- Task 4: Refactored Dashboard to use 2-column responsive grid with all 4 stat cards. Added grid tests. Full test suite passes (1293 API + 1415 web tests).
- Task 5: Manual browser verification completed via Docker. All acceptance criteria verified.

### File List

- web/src/api/types.ts (MODIFIED - added MetricsSnapshot and MetricsHistoryResponse types)
- web/src/api/query-keys.ts (MODIFIED - added metrics query keys)
- web/src/hooks/use-metrics.ts (NEW)
- web/src/hooks/use-metrics.test.tsx (NEW)
- web/src/components/StatCard.tsx (NEW)
- web/src/components/StatCard.test.tsx (NEW)
- web/src/features/dashboard/MemoryCard.tsx (NEW)
- web/src/features/dashboard/DiskSpaceCard.tsx (NEW)
- web/src/features/dashboard/UptimeCard.tsx (NEW)
- web/src/features/dashboard/ServerStatusCard.tsx (NEW)
- web/src/features/dashboard/MetricCards.test.tsx (NEW)
- web/src/features/dashboard/Dashboard.tsx (MODIFIED - refactored to stat cards grid)
- web/src/features/dashboard/Dashboard.test.tsx (MODIFIED - added stat cards grid tests)

