/**
 * LazyRevisionCompare: RevisionCompare loaded on demand with the CodeMirror chunk
 * (Story 23.7, Epic 23 ADR-8 decision 5).
 */

import { Suspense, lazy } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import type { RevisionCompareProps } from './RevisionCompare';

const RevisionCompare = lazy(() => import('./RevisionCompare'));

export function LazyRevisionCompare(props: RevisionCompareProps) {
  return (
    <Suspense fallback={<Skeleton className="m-4 h-24" data-testid="revision-compare-loading" />}>
      <RevisionCompare {...props} />
    </Suspense>
  );
}

export type { RevisionCompareProps };
