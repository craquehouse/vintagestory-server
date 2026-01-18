# Story 12.5: Dashboard Time-Series Charts

Status: code-review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an **administrator**,
I want **charts showing metrics over time**,
So that **I can identify trends and anomalies**.

## Acceptance Criteria

1. **Given** I view the Dashboard
   **When** the page loads
   **Then** I see a Memory Usage chart showing API and Game memory over time

2. **Given** the chart is displayed
   **When** I view it
   **Then** it shows data for the selected time range (default 1 hour)
   **And** API and Game memory are shown as separate lines

3. **Given** I want to change the time range
   **When** I click a time range selector (15m, 1h, 6h, 24h)
   **Then** the chart updates to show that time period

4. **Given** the game server was stopped during the time range
   **When** I view the chart
   **Then** Game memory line has gaps where data is unavailable

5. **Given** I hover over a point on the chart
   **When** the tooltip appears
   **Then** I see the timestamp and exact values

## Tasks / Subtasks

<!--
Tasks designed to be 4-6 total per project-context.md guidelines.
Each task includes tests and maps to specific ACs.
-->

- [x] Task 1: Add Recharts dependency + verify setup + tests (AC: 1)
  - [x] Subtask 1.1: Install recharts via `bun add recharts`
  - [x] Subtask 1.2: Verify TypeScript types work correctly
  - [x] Subtask 1.3: Create simple smoke test to verify recharts renders
  - [x] Subtask 1.4: Run `just check` to verify no build/type issues

- [x] Task 2: Create MetricsChart component + tests (AC: 1, 2, 4, 5)
  - [x] Subtask 2.1: Create `web/src/features/dashboard/MetricsChart.tsx`
  - [x] Subtask 2.2: Implement dual-line LineChart for API and Game memory
  - [x] Subtask 2.3: Use Catppuccin theme colors for line strokes
  - [x] Subtask 2.4: Implement tooltip with timestamp and values (AC: 5)
  - [x] Subtask 2.5: Handle null game memory with connectNulls={false} for gaps (AC: 4)
  - [x] Subtask 2.6: Add responsive sizing via ResponsiveContainer
  - [x] Subtask 2.7: Write tests for MetricsChart (loading, data display, null handling)

- [x] Task 3: Create TimeRangeSelector component + tests (AC: 3)
  - [x] Subtask 3.1: Create `web/src/features/dashboard/TimeRangeSelector.tsx`
  - [x] Subtask 3.2: Implement button group with 15m, 1h (default), 6h, 24h options
  - [x] Subtask 3.3: Style with Catppuccin theme (selected state highlight)
  - [x] Subtask 3.4: Add onChange callback to parent
  - [x] Subtask 3.5: Write tests for TimeRangeSelector

- [x] Task 4: Integrate chart into Dashboard + tests (AC: 1, 2, 3)
  - [x] Subtask 4.1: Add state for selected time range in Dashboard
  - [x] Subtask 4.2: Use useMetricsHistory hook with time range conversion (minutes)
  - [x] Subtask 4.3: Add MetricsChart and TimeRangeSelector below stat cards
  - [x] Subtask 4.4: Handle loading and error states for chart
  - [x] Subtask 4.5: Add chart-specific error boundary (skipped - chart uses empty state instead)
  - [x] Subtask 4.6: Write integration tests for Dashboard with chart

- [x] Task 5: Manual browser verification (AC: all)
  - [x] Subtask 5.1: Start dev servers (`just dev-api` and `just dev-web`)
  - [x] Subtask 5.2: Navigate to Dashboard in browser
  - [x] Subtask 5.3: Verify Memory Usage chart displays with data (AC: 1, 2)
  - [x] Subtask 5.4: Test time range selector changes chart data (AC: 3)
  - [x] Subtask 5.5: Stop game server and verify chart shows gaps (AC: 4)
  - [x] Subtask 5.6: Hover over chart points and verify tooltip (AC: 5)
  - [x] Subtask 5.7: Test responsive layout at mobile breakpoint

## Dev Notes

### Technical Decisions (from Story 12.1)

All technical decisions are documented in [epic-12-dashboard-metrics.md](_bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md).

**Key ADRs:**
- **ADR-E12-003:** Use Recharts for charting - native TypeScript, React 19 compatible, excellent DX
- **ADR-E12-004:** Ring buffer using collections.deque (backend) - 360 samples = 1 hour at 10s intervals

### Existing Infrastructure (from Story 12.4)

**Metrics Hooks** (already implemented):
- `useCurrentMetrics()` - Polls every 10 seconds for latest snapshot
- `useMetricsHistory(minutes?)` - Fetches historical metrics (Story 12.5 consumer)

**API Endpoints** (implemented in Story 12.3):
- `GET /api/v1alpha1/metrics/current` - Latest MetricsSnapshot
- `GET /api/v1alpha1/metrics/history?minutes=N` - Historical metrics

**History Response Format:**
```json
{
  "status": "ok",
  "data": {
    "metrics": [
      {
        "timestamp": "2026-01-17T10:30:00Z",
        "apiMemoryMb": 128.5,
        "apiCpuPercent": 2.3,
        "gameMemoryMb": 512.0,
        "gameCpuPercent": 15.2
      }
    ]
  }
}
```

**When game server not running, gameMemoryMb and gameCpuPercent are null:**
```json
{
  "timestamp": "2026-01-17T10:35:00Z",
  "apiMemoryMb": 130.2,
  "apiCpuPercent": 1.8,
  "gameMemoryMb": null,
  "gameCpuPercent": null
}
```

### Recharts Implementation Patterns

**Installation:**
```bash
cd web && bun add recharts
```

**Basic LineChart with Two Lines:**
```tsx
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';

interface MetricsChartProps {
  data: Array<{
    timestamp: string;
    apiMemoryMb: number;
    gameMemoryMb: number | null;
  }>;
}

export function MetricsChart({ data }: MetricsChartProps) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <XAxis
          dataKey="timestamp"
          tickFormatter={(t) => new Date(t).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          tick={{ fill: 'var(--color-muted-foreground)' }}
        />
        <YAxis
          tick={{ fill: 'var(--color-muted-foreground)' }}
          label={{ value: 'MB', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip
          contentStyle={{
            backgroundColor: 'var(--color-card)',
            border: '1px solid var(--color-border)',
            borderRadius: '8px',
          }}
          labelFormatter={(t) => new Date(t).toLocaleString()}
        />
        <Legend />
        <Line
          type="monotone"
          dataKey="apiMemoryMb"
          name="API"
          stroke="var(--color-blue)"  // Catppuccin blue
          strokeWidth={2}
          dot={false}
        />
        <Line
          type="monotone"
          dataKey="gameMemoryMb"
          name="Game"
          stroke="var(--color-green)"  // Catppuccin green
          strokeWidth={2}
          dot={false}
          connectNulls={false}  // Creates gaps for null values (AC: 4)
        />
      </LineChart>
    </ResponsiveContainer>
  );
}
```

**Catppuccin Colors for Charts:**

The project uses Catppuccin theme colors defined in CSS variables. For charts:
- API Memory: `var(--color-blue)` or fallback `#89b4fa` (Catppuccin blue)
- Game Memory: `var(--color-green)` or fallback `#a6e3a1` (Catppuccin green)
- Grid/axis: `var(--color-muted-foreground)` or `var(--color-border)`

Check `web/src/index.css` for exact CSS variable names.

### Time Range Selector Pattern

**Button Group Component:**
```tsx
interface TimeRangeSelectorProps {
  value: number; // minutes
  onChange: (minutes: number) => void;
}

const TIME_RANGES = [
  { label: '15m', minutes: 15 },
  { label: '1h', minutes: 60 },
  { label: '6h', minutes: 360 },
  { label: '24h', minutes: 1440 },
] as const;

export function TimeRangeSelector({ value, onChange }: TimeRangeSelectorProps) {
  return (
    <div className="flex gap-1">
      {TIME_RANGES.map((range) => (
        <button
          key={range.minutes}
          onClick={() => onChange(range.minutes)}
          className={cn(
            'px-3 py-1 text-sm rounded',
            value === range.minutes
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted hover:bg-muted/80'
          )}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
}
```

### Dashboard Integration Pattern

```tsx
// In Dashboard.tsx
import { useState } from 'react';
import { useMetricsHistory } from '@/hooks/use-metrics';
import { MetricsChart } from './MetricsChart';
import { TimeRangeSelector } from './TimeRangeSelector';

export function Dashboard() {
  // ... existing code ...

  // Time range state (default 60 minutes = 1 hour)
  const [timeRangeMinutes, setTimeRangeMinutes] = useState(60);

  // Fetch historical metrics for chart
  const { data: historyResponse, isLoading: historyLoading } = useMetricsHistory(timeRangeMinutes);
  const historyData = historyResponse?.data?.metrics ?? [];

  return (
    <div className="space-y-6">
      {/* ... existing stat cards grid ... */}

      {/* Metrics Chart Section (Story 12.5) */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Memory Usage Over Time</CardTitle>
          <TimeRangeSelector
            value={timeRangeMinutes}
            onChange={setTimeRangeMinutes}
          />
        </CardHeader>
        <CardContent>
          {historyLoading ? (
            <div className="h-[300px] flex items-center justify-center">
              <span className="text-muted-foreground">Loading chart...</span>
            </div>
          ) : historyData.length === 0 ? (
            <div className="h-[300px] flex items-center justify-center">
              <span className="text-muted-foreground">No metrics data available</span>
            </div>
          ) : (
            <MetricsChart data={historyData} />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
```

### Testing Requirements

**CRITICAL:** Tests must be written alongside implementation, not as a separate phase.

**Test Patterns for Recharts:**

Testing Recharts components requires careful handling since they render SVG:

```tsx
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MetricsChart } from './MetricsChart';

const mockData = [
  { timestamp: '2026-01-17T10:00:00Z', apiMemoryMb: 100, gameMemoryMb: 500 },
  { timestamp: '2026-01-17T10:10:00Z', apiMemoryMb: 105, gameMemoryMb: 510 },
  { timestamp: '2026-01-17T10:20:00Z', apiMemoryMb: 102, gameMemoryMb: null }, // gap
];

describe('MetricsChart', () => {
  it('renders chart with data', () => {
    render(<MetricsChart data={mockData} />);
    // Recharts renders SVG, check for svg element
    expect(document.querySelector('svg')).toBeInTheDocument();
  });

  it('shows legend with API and Game labels', () => {
    render(<MetricsChart data={mockData} />);
    expect(screen.getByText('API')).toBeInTheDocument();
    expect(screen.getByText('Game')).toBeInTheDocument();
  });

  it('handles empty data gracefully', () => {
    render(<MetricsChart data={[]} />);
    // Should render without errors
    expect(document.querySelector('svg')).toBeInTheDocument();
  });
});
```

**Test file locations:**
- `web/src/features/dashboard/MetricsChart.test.tsx`
- `web/src/features/dashboard/TimeRangeSelector.test.tsx`
- `web/src/features/dashboard/Dashboard.test.tsx` (modify - add chart tests)

### Security Requirements

**Follow patterns in `project-context.md` -> Security Patterns section:**

- Metrics endpoints require Admin role (enforced by API)
- No additional security requirements for frontend chart components
- API key is handled automatically by apiClient

### Development Commands

Use `just` for all development tasks:
- `just test` - Run all tests
- `just test-web` - Run web tests only
- `just test-web src/features/dashboard/MetricsChart.test.tsx` - Run specific file
- `just check` - Full validation (lint + typecheck + test)
- `just lint` - Run all linters
- `just dev-web` - Start web dev server
- `just dev-api` - Start API dev server (needed for manual testing)

### Previous Story Intelligence (Story 12.4)

From [12-4-dashboard-stats-cards.md](_bmad-output/implementation-artifacts/12-4-dashboard-stats-cards.md):

1. **useMetricsHistory hook ready** - Created for Story 12.5 consumption
2. **Dashboard grid layout** - 2-column responsive grid with error boundaries
3. **StatCardErrorBoundary** - Can be reused for chart error boundary
4. **All 1464 tests passing** - No regressions from 12.4 implementation
5. **Review follow-ups addressed** - Input validation, memoization, accessibility all done

**Code Patterns from Story 12.4 to Follow:**
- Use `StatCardErrorBoundary` for chart error boundary
- Follow memoization patterns for chart components
- Use `numeric-utils.ts` for memory formatting if needed
- Follow accessibility patterns (ARIA labels) from stat cards

### Git Intelligence (Recent Commits)

**From Story 12.4 (merged to main):**
- `020e781` - PR merge for story/12-4-dashboard-stats-cards
- `6210859` - Code review follow-ups (memoization, accessibility, validation)
- `8ea8e32` - Task 4: Dashboard grid redesign

**Patterns to follow:**
- Task-level commits: `feat(story-12.5/task-N): description`
- Review fixes: `fix(story-12.5/review): description`
- All tests must pass before commits

### Architecture & Patterns

**Component Organization:**
- `MetricsChart.tsx` in `features/dashboard/` (alongside metric cards)
- `TimeRangeSelector.tsx` in `features/dashboard/`
- Follow existing Card patterns from Dashboard

**Data Flow:**
```
Metrics History API → useMetricsHistory(minutes) → Dashboard state → MetricsChart
                                                  → TimeRangeSelector (controls minutes)
```

**State Management:**
- Time range: Local React state in Dashboard (UI-only state)
- Metrics data: TanStack Query (server state)
- NO mixing with React Context

### Project Structure Notes

Files to create:
- `web/src/features/dashboard/MetricsChart.tsx` (NEW)
- `web/src/features/dashboard/MetricsChart.test.tsx` (NEW)
- `web/src/features/dashboard/TimeRangeSelector.tsx` (NEW)
- `web/src/features/dashboard/TimeRangeSelector.test.tsx` (NEW)

Files to modify:
- `web/package.json` (MODIFY - add recharts dependency)
- `web/src/features/dashboard/Dashboard.tsx` (MODIFY - add chart section)
- `web/src/features/dashboard/Dashboard.test.tsx` (MODIFY - add chart tests)

### CSS Variables Reference

Check these files for Catppuccin color variables:
- `web/src/index.css` - Global CSS variables
- `web/tailwind.config.ts` - Tailwind theme extensions

Likely variable names for chart colors:
- `--color-blue` / `--blue` - For API memory line
- `--color-green` / `--green` - For Game memory line
- `--color-muted-foreground` - For axis text
- `--color-border` - For grid lines
- `--color-card` - For tooltip background

### References

- `project-context.md` - Critical implementation rules and patterns
- [Source: _bmad-output/planning-artifacts/epics.md#Story 12.5] - Epic requirements
- [Source: _bmad-output/planning-artifacts/architecture/epic-12-dashboard-metrics.md#ADR-E12-003] - Recharts decision
- [Source: web/src/hooks/use-metrics.ts] - useMetricsHistory hook
- [Source: web/src/features/dashboard/Dashboard.tsx] - Current Dashboard implementation
- [Source: web/src/components/StatCardErrorBoundary.tsx] - Error boundary pattern
- [Source: 12-4-dashboard-stats-cards.md] - Previous story learnings

## Dev Agent Record

### Agent Model Used

claude-opus-4-5-20251101

### Debug Log References

### Completion Notes List

- Task 1: Installed recharts v3.6.0, verified TypeScript types work, created 4 smoke tests in RechartsSetup.test.tsx. All 1468 tests pass.
- Task 2: Created MetricsChart.tsx with dual-line chart for API/Game memory. Custom tooltip with timestamp and values (AC: 5). Handles null game memory with gaps (AC: 4). 13 tests covering empty state, data handling, null values. All 1481 tests pass.
- Task 3: Created TimeRangeSelector.tsx with 15m, 1h (default), 6h, 24h options. Catppuccin theme styling, accessible, memoized. 17 tests covering rendering, selection, interaction, accessibility. All 1498 tests pass.
- Task 4: Integrated chart into Dashboard.tsx below stat cards. Added time range state (default 1h), loading/error states. 8 new integration tests for chart in Dashboard. All 1506 tests pass.
- Task 5: Manual browser verification passed. All acceptance criteria verified in browser.
- Enhancement: Added auto-refresh to metrics chart - polls every 10 seconds to display new data (same as metrics collection interval).
- Enhancement: Added chart type toggle - switch between line chart and stacked area chart. Stacked area shows combined total in tooltip.

### File List

- web/package.json (MODIFIED - added recharts dependency)
- web/bun.lock (MODIFIED - dependency lockfile)
- web/src/features/dashboard/RechartsSetup.test.tsx (CREATED - smoke tests)
- web/src/features/dashboard/MetricsChart.tsx (CREATED - chart component with line/stacked area toggle)
- web/src/features/dashboard/MetricsChart.test.tsx (CREATED - chart tests including toggle tests)
- web/src/features/dashboard/TimeRangeSelector.tsx (CREATED - time range selector)
- web/src/features/dashboard/TimeRangeSelector.test.tsx (CREATED - selector tests)
- web/src/features/dashboard/Dashboard.tsx (MODIFIED - added chart section)
- web/src/features/dashboard/Dashboard.test.tsx (MODIFIED - added chart tests)
- web/src/hooks/use-metrics.ts (MODIFIED - added polling to useMetricsHistory)

