/**
 * useMediaQuery - whether a CSS media query matches, kept current (Story 16.5).
 *
 * Used where a component must render one of two layouts rather than render both and
 * hide one with CSS (e.g. ModTable: table at lg and up, cards below).
 */

import { useCallback, useSyncExternalStore } from 'react';

/** Tailwind v4's `md` breakpoint (`@media (width >= 48rem)`), 768px at the default root font size. */
export const MD_UP_QUERY = '(min-width: 48rem)';

/**
 * Tailwind v4's `lg` breakpoint (`@media (width >= 64rem)`), 1024px at the default root font
 * size (Story 17.8).
 */
export const LG_UP_QUERY = '(min-width: 64rem)';

export function useMediaQuery(query: string): boolean {
  const subscribe = useCallback(
    (onChange: () => void) => {
      const list = window.matchMedia(query);
      list.addEventListener('change', onChange);
      return () => list.removeEventListener('change', onChange);
    },
    [query]
  );
  const getSnapshot = useCallback(() => window.matchMedia(query).matches, [query]);

  return useSyncExternalStore(subscribe, getSnapshot);
}
