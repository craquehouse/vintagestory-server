/**
 * DiskSpaceCard component for displaying disk usage.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * Shows disk space metrics using data from useServerStatus hook.
 * Displays free/total disk space with usage percentage.
 */

import { HardDrive } from 'lucide-react';
import { StatCard } from '@/components/StatCard';
import type { DiskSpaceData } from '@/api/types';

export interface DiskSpaceCardProps {
  /** Disk space data from server status */
  diskSpace: DiskSpaceData | null | undefined;
  /** Whether the data is loading */
  isLoading?: boolean;
}

/**
 * DiskSpaceCard displays server disk usage.
 *
 * Uses existing disk space data from useServerStatus hook.
 */
export function DiskSpaceCard({ diskSpace, isLoading }: DiskSpaceCardProps) {
  // Loading state
  if (isLoading) {
    return (
      <StatCard
        icon={HardDrive}
        title="Disk Space"
        value="Loading..."
        testId="disk-card"
      />
    );
  }

  // No data available
  if (!diskSpace) {
    return (
      <StatCard
        icon={HardDrive}
        title="Disk Space"
        value="N/A"
        subtitle="Disk data unavailable"
        testId="disk-card"
      />
    );
  }

  const { availableGb, totalGb, usagePercent } = diskSpace;

  return (
    <StatCard
      icon={HardDrive}
      title="Disk Space"
      value={`${availableGb.toFixed(1)} GB`}
      subtitle={`Free of ${totalGb.toFixed(1)} GB (${usagePercent.toFixed(0)}% used)`}
      testId="disk-card"
    />
  );
}
