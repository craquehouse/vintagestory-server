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

/**
 * Format memory in MB to a readable string.
 */
function formatMemory(mb: number | null | undefined): string {
  if (mb === null || mb === undefined) {
    return 'N/A';
  }
  return `${mb.toFixed(1)} MB`;
}

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

  // Compute total memory (API + Game if available)
  const apiMemory = metrics.apiMemoryMb;
  const gameMemory = metrics.gameMemoryMb;
  const totalMemory =
    gameMemory !== null ? apiMemory + gameMemory : apiMemory;

  return (
    <StatCard
      icon={MemoryStick}
      title="Memory Usage"
      value={`${totalMemory.toFixed(1)} MB`}
      testId="memory-card"
    >
      <div className="mt-2 space-y-1 text-sm text-muted-foreground">
        <div data-testid="memory-card-api">API: {formatMemory(apiMemory)}</div>
        <div data-testid="memory-card-game">
          Game: {formatMemory(gameMemory)}
        </div>
      </div>
    </StatCard>
  );
}
