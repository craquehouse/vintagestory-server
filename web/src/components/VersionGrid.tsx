/**
 * VersionGrid - Grid layout component for displaying server versions.
 *
 * Features:
 * - Responsive grid layout (1-4 columns based on viewport)
 * - Loading skeleton state
 * - Empty state when no versions match filters
 *
 * Story 13.3: Version List Page
 */

import { Card } from '@/components/ui/card';
import { VersionCard } from '@/components/VersionCard';
import type { VersionInfo } from '@/api/types';

interface VersionGridProps {
  /** Array of versions to display */
  versions: VersionInfo[];
  /** Whether the data is currently loading */
  isLoading?: boolean;
  /** Currently installed version string for highlighting */
  installedVersion?: string | null;
  /** Click handler for version card selection */
  onVersionClick?: (version: string) => void;
}

/**
 * Number of skeleton cards to show during loading state.
 */
const SKELETON_COUNT = 8;

/**
 * Responsive grid layout classes.
 */
const GRID_CLASSES = 'grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4';

/**
 * Skeleton card component for loading state.
 */
function VersionCardSkeleton() {
  return (
    <Card
      className="h-[120px] animate-pulse bg-muted"
      data-testid="version-card-skeleton"
    />
  );
}

/**
 * Grid component for displaying version cards or loading skeleton.
 *
 * @example
 * <VersionGrid
 *   versions={versionData}
 *   isLoading={isLoading}
 *   installedVersion={serverStatus?.version}
 *   onVersionClick={handleVersionClick}
 * />
 */
export function VersionGrid({
  versions,
  isLoading = false,
  installedVersion,
  onVersionClick,
}: VersionGridProps) {
  if (isLoading) {
    return (
      <div
        className={GRID_CLASSES}
        data-testid="version-grid-loading"
      >
        {Array.from({ length: SKELETON_COUNT }).map((_, index) => (
          <VersionCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div
        className="text-center py-8 text-muted-foreground"
        data-testid="version-grid-empty"
      >
        No versions found for this channel.
      </div>
    );
  }

  return (
    <div
      className={GRID_CLASSES}
      data-testid="version-grid"
    >
      {versions.map((version) => (
        <VersionCard
          key={version.version}
          version={version}
          installedVersion={installedVersion}
          // Story 13.5: Highlight versions newer than installed
          isNewer={installedVersion ? version.version > installedVersion : false}
          onClick={onVersionClick ? () => onVersionClick(version.version) : undefined}
        />
      ))}
    </div>
  );
}
