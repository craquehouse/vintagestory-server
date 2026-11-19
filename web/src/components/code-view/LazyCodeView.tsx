/**
 * LazyCodeView: CodeView loaded on demand, so CodeMirror is in its own chunk
 * (Story 23.5, Epic 23 ADR-5 decision 1).
 */

import { Suspense, forwardRef, lazy } from 'react';
import { Skeleton } from '@/components/ui/skeleton';
import type { CodeViewHandle, CodeViewProps } from './CodeView';

const CodeView = lazy(() => import('./CodeView'));

export const LazyCodeView = forwardRef<CodeViewHandle, CodeViewProps>(
  function LazyCodeView(props, ref) {
    return (
      <Suspense
        fallback={
          <div className="space-y-2 p-4" data-testid="code-view-loading">
            <Skeleton className="h-4 w-3/4" />
            <Skeleton className="h-4 w-1/2" />
            <Skeleton className="h-4 w-5/6" />
          </div>
        }
      >
        <CodeView ref={ref} {...props} />
      </Suspense>
    );
  }
);

export type { CodeViewHandle, CodeViewProps };
