/**
 * PathBreadcrumb: the current directory path as clickable segments.
 *
 * The root and every ancestor directory are buttons that navigate to that directory;
 * the current directory is plain text marked `aria-current="page"`. Navigation is
 * component state (no URL), so segments are buttons rather than links. Styling
 * matches the mod detail breadcrumb (`ModDetailPage`).
 *
 * Story 16.7: File Browser Breadcrumbs (FR174)
 * Story 23.2: the path is a list of directory names, never split or joined here (FR312)
 */

import { useEffect, useRef } from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PathBreadcrumbProps {
  /** Directory names from the root; `[]` is the root (Story 23.2). */
  segments: readonly string[];
  /** Label of the root segment. */
  rootLabel: string;
  /** Called with the root (`[]`) or the names up to and including the clicked segment. */
  onNavigate: (segments: string[]) => void;
  /** Additional CSS class names for the `nav`. */
  className?: string;
}

// Phones get a 44px-tall touch target (UX spec); from md the compact desktop look (Story 16.7 review)
const segmentButtonClass = cn(
  'min-h-11 px-1 md:min-h-0 md:px-0',
  'max-w-full truncate rounded-sm hover:text-foreground transition-colors',
  'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring'
);

/**
 * Breadcrumb for a directory path.
 *
 * Only the root (`[]`) or a prefix of `segments` is ever passed to `onNavigate`.
 * After a jump through the breadcrumb, focus moves to the new current segment so
 * keyboard users keep their place (the clicked button is replaced by text).
 *
 * @example
 * <PathBreadcrumb segments={['Logs', 'Archive']} rootLabel="serverdata" onNavigate={setDirectory} />
 */
export function PathBreadcrumb({
  segments,
  rootLabel,
  onNavigate,
  className,
}: PathBreadcrumbProps) {
  // A string key for the list that cannot collide for different lists (names may hold anything)
  const currentPath = JSON.stringify(segments);
  const currentRef = useRef<HTMLSpanElement>(null);
  // Path requested by the last breadcrumb click (its key), until the next render
  const focusTarget = useRef<string | null>(null);

  // Runs after every render: focus the current segment only if this render shows the
  // path the click asked for, and forget the request either way, so a click that did not
  // change the path cannot steal focus on a later, unrelated path change.
  useEffect(() => {
    if (focusTarget.current === null) return;
    if (focusTarget.current === currentPath) {
      currentRef.current?.focus();
    }
    focusTarget.current = null;
  });

  const navigate = (target: string[]) => {
    focusTarget.current = JSON.stringify(target);
    onNavigate(target);
  };

  const names = [rootLabel, ...segments];
  const lastIndex = names.length - 1;

  return (
    <nav aria-label="Breadcrumb" className={cn('min-w-0', className)} data-testid="path-breadcrumb">
      <ol className="flex min-w-0 flex-wrap items-center gap-1 text-sm text-muted-foreground">
        {names.map((name, index) => {
          const isRoot = index === 0;
          const isCurrent = index === lastIndex;
          return (
            <li
              key={isRoot ? 'root' : `segment-${index}`}
              className="flex min-w-0 max-w-full items-center gap-1"
            >
              {!isRoot && <ChevronRight className="h-4 w-4 shrink-0" aria-hidden="true" />}
              {isCurrent ? (
                <span
                  ref={currentRef}
                  tabIndex={-1}
                  aria-current="page"
                  title={name}
                  className="max-w-full truncate rounded-sm font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  data-testid="path-breadcrumb-current"
                >
                  {name}
                </span>
              ) : (
                <button
                  type="button"
                  title={name}
                  className={segmentButtonClass}
                  onClick={() => navigate(segments.slice(0, index))}
                  data-testid={
                    isRoot ? 'path-breadcrumb-root' : `path-breadcrumb-segment-${index - 1}`
                  }
                >
                  {name}
                </button>
              )}
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
