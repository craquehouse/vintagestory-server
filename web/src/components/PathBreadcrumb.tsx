/**
 * PathBreadcrumb: the current directory path as clickable segments.
 *
 * The root and every ancestor directory are buttons that navigate to that directory;
 * the current directory is plain text marked `aria-current="page"`. Navigation is
 * component state (no URL), so segments are buttons rather than links. Styling
 * matches the mod detail breadcrumb (`ModDetailPage`).
 *
 * Story 16.7: File Browser Breadcrumbs (FR174)
 */

import { useEffect, useRef } from 'react';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

export interface PathBreadcrumbProps {
  /** Slash-separated path relative to the root; `null` or empty is the root. */
  path: string | null;
  /** Label of the root segment. */
  rootLabel: string;
  /** Called with the root (`null`) or the path up to and including the clicked segment. */
  onNavigate: (path: string | null) => void;
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
 * Only the root or a prefix of `path` is ever passed to `onNavigate`.
 * After a jump through the breadcrumb, focus moves to the new current segment so
 * keyboard users keep their place (the clicked button is replaced by text).
 *
 * @example
 * <PathBreadcrumb path="Logs/Archive" rootLabel="serverdata" onNavigate={setDirectory} />
 */
export function PathBreadcrumb({ path, rootLabel, onNavigate, className }: PathBreadcrumbProps) {
  const segments = (path ?? '').split('/').filter((segment) => segment !== '');
  const currentRef = useRef<HTMLSpanElement>(null);
  const shouldFocusCurrent = useRef(false);

  useEffect(() => {
    if (shouldFocusCurrent.current) {
      shouldFocusCurrent.current = false;
      currentRef.current?.focus();
    }
  }, [path]);

  const navigate = (target: string | null) => {
    shouldFocusCurrent.current = true;
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
            <li key={isRoot ? 'root' : `segment-${index}`} className="flex min-w-0 max-w-full items-center gap-1">
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
                  onClick={() => navigate(isRoot ? null : segments.slice(0, index).join('/'))}
                  data-testid={isRoot ? 'path-breadcrumb-root' : `path-breadcrumb-segment-${index - 1}`}
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
