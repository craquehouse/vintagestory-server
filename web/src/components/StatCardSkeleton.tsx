/**
 * Skeleton loading component for StatCard.
 *
 * Story 12.4: Dashboard Stats Cards (Review Follow-up)
 *
 * Provides a loading skeleton placeholder that matches
 * the StatCard layout for smooth loading transitions.
 */

import { Card, CardContent, CardHeader } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export interface StatCardSkeletonProps {
  /** Optional additional class names */
  className?: string;
  /** Test ID for testing */
  testId?: string;
  /** Whether to show subtitle skeleton */
  showSubtitle?: boolean;
}

/**
 * StatCardSkeleton displays a loading placeholder for StatCard.
 *
 * Matches the layout of StatCard for smooth loading transitions.
 */
export function StatCardSkeleton({
  className,
  testId,
  showSubtitle = true,
}: StatCardSkeletonProps) {
  return (
    <Card
      className={cn('min-h-[140px]', className)}
      data-testid={testId}
      aria-busy="true"
      aria-label="Loading..."
    >
      <CardHeader className="pb-2">
        <div className="flex items-center gap-3">
          {/* Icon placeholder */}
          <Skeleton className="size-5 rounded" />
          {/* Title placeholder */}
          <Skeleton className="h-5 w-24" />
        </div>
      </CardHeader>
      <CardContent>
        {/* Value placeholder */}
        <Skeleton className="h-8 w-32" />
        {/* Subtitle placeholder */}
        {showSubtitle && <Skeleton className="mt-2 h-4 w-40" />}
      </CardContent>
    </Card>
  );
}
