/**
 * UptimeCard component for displaying server uptime.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * Shows server uptime in a human-readable format.
 * Shows "N/A" when server is not running.
 */

import { memo } from 'react';
import { Clock } from 'lucide-react';
import { StatCard } from '@/components/StatCard';
import { isValidNumeric } from '@/lib/numeric-utils';

export interface UptimeCardProps {
  /** Uptime in seconds */
  uptimeSeconds: number | null | undefined;
  /** Whether the server is running */
  isRunning: boolean;
  /** Whether the data is loading */
  isLoading?: boolean;
}

/**
 * Format uptime seconds into a human-readable string.
 * Handles invalid values by returning 'N/A'.
 *
 * Examples:
 * - 45 -> "45s"
 * - 125 -> "2m 5s"
 * - 3665 -> "1h 1m"
 * - 90061 -> "1d 1h"
 */
function formatUptime(seconds: number): string {
  // Guard against invalid values that slipped through
  if (!Number.isFinite(seconds) || seconds < 0) {
    return 'N/A';
  }

  // Round to integer to avoid fractional display issues
  const roundedSeconds = Math.floor(seconds);

  if (roundedSeconds < 60) {
    return `${roundedSeconds}s`;
  }

  const minutes = Math.floor(roundedSeconds / 60);
  const remainingSeconds = roundedSeconds % 60;
  if (minutes < 60) {
    return remainingSeconds > 0 ? `${minutes}m ${remainingSeconds}s` : `${minutes}m`;
  }

  const hours = Math.floor(minutes / 60);
  const remainingMinutes = minutes % 60;
  if (hours < 24) {
    return remainingMinutes > 0 ? `${hours}h ${remainingMinutes}m` : `${hours}h`;
  }

  const days = Math.floor(hours / 24);
  const remainingHours = hours % 24;
  return remainingHours > 0 ? `${days}d ${remainingHours}h` : `${days}d`;
}

/**
 * Get a human-readable description of the uptime.
 */
function getUptimeDescription(seconds: number): string {
  if (seconds < 60) {
    return 'Just started';
  }
  if (seconds < 3600) {
    return 'Running for minutes';
  }
  if (seconds < 86400) {
    return 'Running for hours';
  }
  return 'Running for days';
}

/**
 * UptimeCard displays server uptime.
 *
 * Uses existing uptime data from useServerStatus hook.
 * Memoized to prevent unnecessary re-renders when parent updates.
 */
export const UptimeCard = memo(function UptimeCard({
  uptimeSeconds,
  isRunning,
  isLoading,
}: UptimeCardProps) {
  // Loading state
  if (isLoading) {
    return (
      <StatCard
        icon={Clock}
        title="Uptime"
        value="Loading..."
        testId="uptime-card"
      />
    );
  }

  // Server not running
  if (!isRunning) {
    return (
      <StatCard
        icon={Clock}
        title="Uptime"
        value="Stopped"
        subtitle="Server is not running"
        testId="uptime-card"
      />
    );
  }

  // No uptime data available or invalid value (NaN, Infinity, negative)
  if (!isValidNumeric(uptimeSeconds)) {
    return (
      <StatCard
        icon={Clock}
        title="Uptime"
        value="N/A"
        subtitle="Uptime unavailable"
        testId="uptime-card"
      />
    );
  }

  return (
    <StatCard
      icon={Clock}
      title="Uptime"
      value={formatUptime(uptimeSeconds)}
      subtitle={getUptimeDescription(uptimeSeconds)}
      testId="uptime-card"
    />
  );
});
