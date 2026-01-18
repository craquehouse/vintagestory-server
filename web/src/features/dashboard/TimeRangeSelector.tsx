/**
 * Time Range Selector component for chart time filtering.
 *
 * Story 12.5: Dashboard Time-Series Charts
 * Task 3: Create TimeRangeSelector component + tests (AC: 3)
 *
 * Provides button group to select time range for metrics charts.
 * Options: 15m, 1h (default), 6h, 24h
 */

import { memo } from 'react';
import { cn } from '@/lib/utils';

/** Time range option configuration */
interface TimeRangeOption {
  label: string;
  minutes: number;
}

/** Available time range options */
const TIME_RANGES: readonly TimeRangeOption[] = [
  { label: '15m', minutes: 15 },
  { label: '1h', minutes: 60 },
  { label: '6h', minutes: 360 },
  { label: '24h', minutes: 1440 },
] as const;

export interface TimeRangeSelectorProps {
  /** Currently selected time range in minutes */
  value: number;
  /** Callback when time range is changed */
  onChange: (minutes: number) => void;
  /** Optional className for the container */
  className?: string;
}

/**
 * Time Range Selector component.
 *
 * Renders a button group for selecting chart time ranges.
 * Highlights the currently selected option.
 *
 * @example
 * ```tsx
 * function Dashboard() {
 *   const [timeRange, setTimeRange] = useState(60);
 *   return (
 *     <TimeRangeSelector
 *       value={timeRange}
 *       onChange={setTimeRange}
 *     />
 *   );
 * }
 * ```
 */
export const TimeRangeSelector = memo(function TimeRangeSelector({
  value,
  onChange,
  className,
}: TimeRangeSelectorProps) {
  return (
    <div
      className={cn('flex gap-1', className)}
      role="group"
      aria-label="Time range selector"
      data-testid="time-range-selector"
    >
      {TIME_RANGES.map((range) => (
        <button
          key={range.minutes}
          type="button"
          onClick={() => onChange(range.minutes)}
          className={cn(
            'rounded px-3 py-1 text-sm font-medium transition-colors',
            value === range.minutes
              ? 'bg-primary text-primary-foreground'
              : 'bg-muted text-muted-foreground hover:bg-muted/80'
          )}
          aria-pressed={value === range.minutes}
          data-testid={`time-range-${range.minutes}`}
        >
          {range.label}
        </button>
      ))}
    </div>
  );
});

/** Default time range in minutes (1 hour) */
export const DEFAULT_TIME_RANGE = 60;

/** Export TIME_RANGES for use in tests */
export { TIME_RANGES };
