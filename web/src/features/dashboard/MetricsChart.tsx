/**
 * Memory Usage Chart component.
 *
 * Story 12.5: Dashboard Time-Series Charts
 * Task 2: Create MetricsChart component + tests (AC: 1, 2, 4, 5)
 *
 * Displays API and Game memory usage over time as a dual-line chart.
 * - Uses Catppuccin theme colors via CSS variables
 * - Handles null game memory values with gaps (AC: 4)
 * - Shows tooltip with timestamp and exact values (AC: 5)
 */

import { memo, useMemo } from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import type { MetricsSnapshot } from '@/api/types';

/** Custom tooltip props - matches what Recharts passes to content function */
interface CustomTooltipProps {
  active?: boolean;
  payload?: Array<{
    dataKey?: string;
    name?: string;
    value?: number | null;
    color?: string;
  }>;
  label?: string | number;
}

export interface MetricsChartProps {
  /** Array of metrics snapshots to display */
  data: MetricsSnapshot[];
  /** Height of the chart in pixels (default: 300) */
  height?: number;
}

// Catppuccin colors with inline fallbacks for CSS variable access
// In Recharts, we need to provide inline styles since CSS variables don't work directly
const CHART_COLORS = {
  // Catppuccin Mocha blue for API memory
  api: 'var(--chart-2, #89dceb)',
  // Catppuccin Mocha green for Game memory
  game: 'var(--chart-3, #a6e3a1)',
  // Muted foreground for axis text
  axis: 'var(--muted-foreground, #a6adc8)',
  // Card background for tooltip
  tooltipBg: 'var(--card, #1e1e2e)',
  // Border for tooltip
  tooltipBorder: 'var(--border, #313244)',
};

/**
 * Format timestamp for X-axis ticks.
 * Shows HH:MM format for readability.
 */
function formatAxisTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return timestamp;
  }
}

/**
 * Format timestamp for tooltip label.
 * Shows full date and time for precision.
 */
function formatTooltipTime(timestamp: string): string {
  try {
    const date = new Date(timestamp);
    return date.toLocaleString([], {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch {
    return timestamp;
  }
}

/**
 * Format memory value for display.
 */
function formatMemory(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  return `${value.toFixed(1)} MB`;
}

/**
 * Custom tooltip component for the chart (AC: 5).
 * Shows timestamp and exact values for both API and Game memory.
 */
function CustomTooltip({ active, payload, label }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  return (
    <div
      className="rounded-lg border bg-card px-3 py-2 shadow-md"
      data-testid="chart-tooltip"
    >
      <p className="mb-1 text-xs text-muted-foreground">
        {formatTooltipTime(String(label ?? ''))}
      </p>
      {payload.map((entry) => (
        <p
          key={entry.dataKey}
          className="text-sm"
          style={{ color: entry.color }}
        >
          {entry.name}: {formatMemory(entry.value)}
        </p>
      ))}
    </div>
  );
}

/**
 * Memory Usage Chart component.
 *
 * Renders a dual-line chart showing API and Game memory usage over time.
 * - API memory shown in cyan/sky (chart-2)
 * - Game memory shown in green (chart-3)
 * - Null game memory values create gaps in the line (AC: 4)
 *
 * Uses ResponsiveContainer for responsive sizing in production,
 * but tests should provide fixed dimensions for JSDOM compatibility.
 *
 * @example
 * ```tsx
 * function Dashboard() {
 *   const { data } = useMetricsHistory(60);
 *   return <MetricsChart data={data?.data?.metrics ?? []} />;
 * }
 * ```
 */
export const MetricsChart = memo(function MetricsChart({
  data,
  height = 300,
}: MetricsChartProps) {
  // Memoize the chart content to avoid re-renders on parent updates
  const chartContent = useMemo(() => {
    return (
      <LineChart
        data={data}
        margin={{ top: 5, right: 20, bottom: 5, left: 0 }}
      >
        <XAxis
          dataKey="timestamp"
          tickFormatter={formatAxisTime}
          tick={{ fill: CHART_COLORS.axis, fontSize: 12 }}
          tickLine={{ stroke: CHART_COLORS.axis }}
          axisLine={{ stroke: CHART_COLORS.axis }}
        />
        <YAxis
          tick={{ fill: CHART_COLORS.axis, fontSize: 12 }}
          tickLine={{ stroke: CHART_COLORS.axis }}
          axisLine={{ stroke: CHART_COLORS.axis }}
          label={{
            value: 'MB',
            angle: -90,
            position: 'insideLeft',
            fill: CHART_COLORS.axis,
            fontSize: 12,
          }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend
          wrapperStyle={{ fontSize: 12 }}
          iconType="line"
        />
        <Line
          type="monotone"
          dataKey="apiMemoryMb"
          name="API"
          stroke={CHART_COLORS.api}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
        />
        <Line
          type="monotone"
          dataKey="gameMemoryMb"
          name="Game"
          stroke={CHART_COLORS.game}
          strokeWidth={2}
          dot={false}
          activeDot={{ r: 4, strokeWidth: 0 }}
          // connectNulls={false} creates gaps for null values (AC: 4)
          connectNulls={false}
        />
      </LineChart>
    );
  }, [data]);

  // Empty state - show message instead of empty chart
  if (data.length === 0) {
    return (
      <div
        className="flex items-center justify-center text-muted-foreground"
        style={{ height }}
        data-testid="metrics-chart-empty"
      >
        No metrics data available
      </div>
    );
  }

  return (
    <div data-testid="metrics-chart" style={{ width: '100%', height }}>
      <ResponsiveContainer width="100%" height="100%">
        {chartContent}
      </ResponsiveContainer>
    </div>
  );
});
