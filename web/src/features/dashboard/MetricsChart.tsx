/**
 * Memory Usage Chart component.
 *
 * Story 12.5: Dashboard Time-Series Charts
 * Task 2: Create MetricsChart component + tests (AC: 1, 2, 4, 5)
 *
 * Displays API and Game memory usage over time.
 * Supports two chart types:
 * - Line chart: dual lines for API and Game memory
 * - Stacked area: shows combined total with individual area colors
 *
 * Features:
 * - Uses Catppuccin theme colors via CSS variables
 * - Handles null game memory values with gaps (AC: 4)
 * - Shows tooltip with timestamp and exact values (AC: 5)
 * - Toggle between line and stacked area views
 */

import { memo, useMemo, useState } from 'react';
import {
  LineChart,
  AreaChart,
  Line,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  ResponsiveContainer,
} from 'recharts';
import { AreaChart as AreaChartIcon, LineChart as LineChartIcon } from 'lucide-react';
import { cn } from '@/lib/utils';
import type { MetricsSnapshot } from '@/api/types';

/** Chart display type */
export type ChartType = 'line' | 'stacked';

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
  /** Whether to show total (for stacked area chart) */
  showTotal?: boolean;
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
export function formatAxisTime(timestamp: string): string {
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
export function formatTooltipTime(timestamp: string): string {
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
export function formatMemory(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return 'N/A';
  }
  return `${value.toFixed(1)} MB`;
}

/**
 * Custom tooltip component for the chart (AC: 5).
 * Shows timestamp and exact values for both API and Game memory.
 * When showTotal is true (stacked area mode), also displays the combined total.
 */
export function CustomTooltip({ active, payload, label, showTotal }: CustomTooltipProps) {
  if (!active || !payload || payload.length === 0) {
    return null;
  }

  // Calculate total for stacked area mode
  const total = showTotal
    ? payload.reduce((sum, entry) => sum + (entry.value ?? 0), 0)
    : null;

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
      {showTotal && total !== null && (
        <p className="mt-1 border-t border-border pt-1 text-sm font-medium text-foreground">
          Total: {formatMemory(total)}
        </p>
      )}
    </div>
  );
}

/**
 * Chart type toggle button component.
 */
function ChartTypeToggle({
  chartType,
  onChange,
}: {
  chartType: ChartType;
  onChange: (type: ChartType) => void;
}) {
  return (
    <div
      className="flex gap-1"
      role="group"
      aria-label="Chart type selector"
      data-testid="chart-type-toggle"
    >
      <button
        type="button"
        onClick={() => onChange('line')}
        className={cn(
          'rounded p-1.5 transition-colors',
          chartType === 'line'
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground hover:bg-muted/80'
        )}
        aria-pressed={chartType === 'line'}
        aria-label="Line chart"
        data-testid="chart-type-line"
      >
        <LineChartIcon className="size-4" />
      </button>
      <button
        type="button"
        onClick={() => onChange('stacked')}
        className={cn(
          'rounded p-1.5 transition-colors',
          chartType === 'stacked'
            ? 'bg-primary text-primary-foreground'
            : 'bg-muted text-muted-foreground hover:bg-muted/80'
        )}
        aria-pressed={chartType === 'stacked'}
        aria-label="Stacked area chart"
        data-testid="chart-type-stacked"
      >
        <AreaChartIcon className="size-4" />
      </button>
    </div>
  );
}

/**
 * Memory Usage Chart component.
 *
 * Renders memory usage over time with two view modes:
 * - Line chart: dual lines for API and Game memory
 * - Stacked area: shows combined total with individual areas
 *
 * Features:
 * - API memory shown in cyan/sky (chart-2)
 * - Game memory shown in green (chart-3)
 * - Null game memory values create gaps (AC: 4)
 * - Toggle between line and stacked area views
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
  const [chartType, setChartType] = useState<ChartType>('line');

  // Shared axis and legend configuration
  const axisConfig = useMemo(
    () => ({
      xAxis: {
        dataKey: 'timestamp',
        tickFormatter: formatAxisTime,
        tick: { fill: CHART_COLORS.axis, fontSize: 12 },
        tickLine: { stroke: CHART_COLORS.axis },
        axisLine: { stroke: CHART_COLORS.axis },
      },
      yAxis: {
        tick: { fill: CHART_COLORS.axis, fontSize: 12 },
        tickLine: { stroke: CHART_COLORS.axis },
        axisLine: { stroke: CHART_COLORS.axis },
        label: {
          value: 'MB',
          angle: -90,
          position: 'insideLeft' as const,
          fill: CHART_COLORS.axis,
          fontSize: 12,
        },
      },
    }),
    []
  );

  // Memoize the line chart content
  const lineChartContent = useMemo(() => {
    return (
      <LineChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <XAxis {...axisConfig.xAxis} />
        <YAxis {...axisConfig.yAxis} />
        <Tooltip content={<CustomTooltip showTotal={false} />} />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="line" />
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
          connectNulls={false}
        />
      </LineChart>
    );
  }, [data, axisConfig]);

  // Memoize the stacked area chart content
  const areaChartContent = useMemo(() => {
    return (
      <AreaChart data={data} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
        <XAxis {...axisConfig.xAxis} />
        <YAxis {...axisConfig.yAxis} />
        <Tooltip content={<CustomTooltip showTotal={true} />} />
        <Legend wrapperStyle={{ fontSize: 12 }} iconType="rect" />
        <Area
          type="monotone"
          dataKey="apiMemoryMb"
          name="API"
          stackId="1"
          stroke={CHART_COLORS.api}
          fill={CHART_COLORS.api}
          fillOpacity={0.6}
        />
        <Area
          type="monotone"
          dataKey="gameMemoryMb"
          name="Game"
          stackId="1"
          stroke={CHART_COLORS.game}
          fill={CHART_COLORS.game}
          fillOpacity={0.6}
          connectNulls={false}
        />
      </AreaChart>
    );
  }, [data, axisConfig]);

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
    <div data-testid="metrics-chart">
      <div className="mb-2 flex justify-end">
        <ChartTypeToggle chartType={chartType} onChange={setChartType} />
      </div>
      <div style={{ width: '100%', height }}>
        <ResponsiveContainer width="100%" height="100%">
          {chartType === 'line' ? lineChartContent : areaChartContent}
        </ResponsiveContainer>
      </div>
    </div>
  );
});
