/**
 * DiskSpaceWarningBanner - Banner shown when disk space is low.
 *
 * Features:
 * - Shows when disk_space.warning is true from server status
 * - Displays available space and usage percentage
 * - Warning color scheme to draw attention
 */

import { HardDrive } from 'lucide-react';
import type { DiskSpaceData } from '@/api/types';

interface DiskSpaceWarningBannerProps {
  /** Disk space data from server status */
  diskSpace: DiskSpaceData | null | undefined;
}

/**
 * Banner indicating that disk space is running low.
 *
 * Only renders when diskSpace.warning is true.
 *
 * @example
 * <DiskSpaceWarningBanner diskSpace={serverStatus?.diskSpace} />
 */
export function DiskSpaceWarningBanner({ diskSpace }: DiskSpaceWarningBannerProps) {
  // Only show banner when warning is triggered
  if (!diskSpace?.warning) {
    return null;
  }

  return (
    <div
      className="flex items-center gap-2 rounded-md bg-yellow-500/20 px-3 py-1.5 text-sm"
      data-testid="disk-space-warning-banner"
    >
      <HardDrive
        className="h-4 w-4 text-yellow-500"
        aria-hidden="true"
        data-testid="disk-warning-icon"
      />
      <span className="text-yellow-500">
        Low disk space: {diskSpace.availableGb.toFixed(1)} GB available ({diskSpace.usagePercent.toFixed(0)}% used)
      </span>
    </div>
  );
}
