/**
 * ModBrowseGrid - Grid layout component for displaying browsable mods.
 *
 * Features:
 * - Responsive grid layout (1-4 columns based on viewport)
 * - Loading skeleton state
 * - Empty state when no mods match filters
 * - Story 10.8: Install buttons on cards with confirmation dialog
 */

import { Skeleton } from '@/components/ui/skeleton';
import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { ModCard } from '@/components/ModCard';
import type { ModBrowseItem } from '@/api/types';

interface ModBrowseGridProps {
  /** Array of mods to display */
  mods: ModBrowseItem[];
  /** Whether the data is currently loading */
  isLoading?: boolean;
  /** Click handler for mod card navigation (passed to each ModCard) */
  onModClick?: (slug: string) => void;
  /** Set of installed mod slugs for showing install state (Story 10.8) */
  installedSlugs?: Set<string>;
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
function ModCardSkeleton() {
  return (
    <Card className="h-full" data-testid="mod-card-skeleton">
      <CardHeader className="pb-2">
        <Skeleton className="h-5 w-3/4" />
        <Skeleton className="h-4 w-1/2 mt-1" />
      </CardHeader>
      <CardContent className="pt-0">
        <Skeleton className="h-4 w-full mb-1" />
        <Skeleton className="h-4 w-2/3 mb-3" />
        <div className="flex items-center gap-4">
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-4 w-12" />
        </div>
      </CardContent>
    </Card>
  );
}

/**
 * Grid component for displaying mod cards or loading skeleton.
 *
 * @example
 * <ModBrowseGrid mods={filteredMods} isLoading={isLoading} />
 */
export function ModBrowseGrid({
  mods,
  isLoading = false,
  onModClick,
  installedSlugs,
}: ModBrowseGridProps) {
  if (isLoading) {
    return (
      <div
        className={GRID_CLASSES}
        data-testid="mod-browse-grid-loading"
      >
        {Array.from({ length: SKELETON_COUNT }).map((_, index) => (
          <ModCardSkeleton key={index} />
        ))}
      </div>
    );
  }

  if (mods.length === 0) {
    return (
      <div
        className="text-center py-12 text-muted-foreground"
        data-testid="mod-browse-grid-empty"
      >
        No mods found matching your criteria
      </div>
    );
  }

  return (
    <div
      className={GRID_CLASSES}
      data-testid="mod-browse-grid"
    >
      {mods.map((mod) => (
        <ModCard
          key={mod.slug}
          mod={mod}
          onClick={onModClick ? () => onModClick(mod.slug) : undefined}
          installedSlugs={installedSlugs}
        />
      ))}
    </div>
  );
}
