/**
 * PlayersCard component for displaying the players online.
 *
 * Story 22.1: Players Online Are Counted
 *
 * Shows the count from the current metrics (the query MemoryCard already polls),
 * or "Stopped" when the game server is not running.
 */

import { memo } from 'react';
import { Users } from 'lucide-react';
import { StatCard } from '@/components/StatCard';
import { useCurrentMetrics } from '@/hooks/use-metrics';
import { isValidNumeric } from '@/lib/numeric-utils';

export interface PlayersCardProps {
  /** Whether the game server is running (from the server status) */
  isRunning: boolean;
}

function describePlayers(count: number): string {
  if (count === 0) {
    return 'No players online';
  }
  return count === 1 ? '1 player online' : `${count} players online`;
}

/**
 * PlayersCard displays the number of players online.
 *
 * A stopped game always reads Stopped, even while the metrics snapshot
 * still lags the server status by up to one poll.
 * Memoized to prevent unnecessary re-renders when parent updates.
 */
export const PlayersCard = memo(function PlayersCard({ isRunning }: PlayersCardProps) {
  const { data: metricsResponse, isLoading, error } = useCurrentMetrics();
  const playersOnline = metricsResponse?.data?.playersOnline;

  // Loading state
  if (isLoading) {
    return <StatCard icon={Users} title="Players" value="Loading..." testId="players-card" />;
  }

  // Server not running
  if (!isRunning) {
    return (
      <StatCard
        icon={Users}
        title="Players"
        value="Stopped"
        subtitle="Server stopped"
        testId="players-card"
      />
    );
  }

  // Error state
  if (error) {
    return (
      <StatCard
        icon={Users}
        title="Players"
        value="Error"
        subtitle={error.message}
        testId="players-card"
      />
    );
  }

  // No snapshot yet, or no valid count in it
  if (!isValidNumeric(playersOnline)) {
    return (
      <StatCard
        icon={Users}
        title="Players"
        value="N/A"
        subtitle="Waiting for metrics..."
        testId="players-card"
      />
    );
  }

  return (
    <StatCard
      icon={Users}
      title="Players"
      value={playersOnline}
      subtitle={describePlayers(playersOnline)}
      testId="players-card"
    />
  );
});
