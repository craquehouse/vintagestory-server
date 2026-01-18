/**
 * MemoryCard component for displaying API and Game memory usage.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * Shows memory usage metrics with separate API and Game breakdowns.
 * Game memory shows "N/A" when server is not running (AC: 4).
 */

import { MemoryStick } from 'lucide-react';
import { StatCard } from '@/components/StatCard';
import { useCurrentMetrics } from '@/hooks/use-metrics';
import { isValidNumeric, formatMemoryAdaptive } from '@/lib/numeric-utils';

/**
 * MemoryCard displays API and Game server memory usage.
 *
 * Uses useCurrentMetrics hook with 10-second polling (AC: 2).
 * Shows "N/A" for game memory when server is not running (AC: 4).
 */
export function MemoryCard() {
  const { data: metricsResponse, isLoading, error } = useCurrentMetrics();
  const metrics = metricsResponse?.data;

  // Loading state
  if (isLoading) {
    return (
      <StatCard
        icon={MemoryStick}
        title="Memory Usage"
        value="Loading..."
        testId="memory-card"
      />
    );
  }

  // Error state
  if (error) {
    return (
      <StatCard
        icon={MemoryStick}
        title="Memory Usage"
        value="Error"
        subtitle={error.message}
        testId="memory-card"
      />
    );
  }

  // No metrics available yet
  if (!metrics) {
    return (
      <StatCard
        icon={MemoryStick}
        title="Memory Usage"
        value="No data"
        subtitle="Waiting for metrics..."
        testId="memory-card"
      />
    );
  }

  // Compute total memory (API + Game if both valid)
  const apiMemory = metrics.apiMemoryMb;
  const gameMemory = metrics.gameMemoryMb;
  const validApiMemory = isValidNumeric(apiMemory);
  const validGameMemory = isValidNumeric(gameMemory);

  // Calculate total: use valid values only
  let totalMemory: number | null = null;
  if (validApiMemory && validGameMemory) {
    totalMemory = apiMemory + gameMemory;
  } else if (validApiMemory) {
    totalMemory = apiMemory;
  }

  return (
    <StatCard
      icon={MemoryStick}
      title="Memory Usage"
      value={formatMemoryAdaptive(totalMemory)}
      testId="memory-card"
    >
      <div className="mt-2 space-y-1 text-sm text-muted-foreground">
        <div data-testid="memory-card-api">API: {formatMemoryAdaptive(apiMemory)}</div>
        <div data-testid="memory-card-game">
          Game: {formatMemoryAdaptive(gameMemory)}
        </div>
      </div>
    </StatCard>
  );
}
