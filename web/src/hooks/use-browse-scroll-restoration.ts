/**
 * Hook for saving and restoring browse tab scroll position.
 *
 * Story 10.7: Scroll restoration after viewing mod details.
 *
 * Uses sessionStorage to persist scroll position and page number
 * so users return to their previous position when navigating back
 * from mod detail views.
 */

import { useCallback } from 'react';

/** Key for storing browse scroll position in sessionStorage */
export const BROWSE_SCROLL_KEY = 'browse-scroll-position';

/** Stored scroll state */
export interface ScrollState {
  scrollY: number;
  page: number;
}

/**
 * Get saved scroll state without consuming it.
 * Use this for synchronous initial state setup.
 * Call restorePosition() later to consume and clear the saved state.
 */
export function getSavedScrollState(): ScrollState | null {
  try {
    const stored = sessionStorage.getItem(BROWSE_SCROLL_KEY);
    if (!stored) return null;
    return JSON.parse(stored) as ScrollState;
  } catch {
    return null;
  }
}

/**
 * Hook providing functions to save and restore browse tab scroll position.
 *
 * @example
 * function BrowseTab() {
 *   const { savePosition, restorePosition, scrollToPosition } = useBrowseScrollRestoration();
 *
 *   // Save position before navigating to detail
 *   const handleModClick = (slug: string) => {
 *     savePosition(currentPage);
 *     navigate(`/mods/browse/${slug}`);
 *   };
 *
 *   // Restore on mount
 *   useEffect(() => {
 *     const saved = restorePosition();
 *     if (saved) {
 *       setPage(saved.page);
 *       // Wait for content to load, then scroll
 *       setTimeout(() => scrollToPosition(saved.scrollY), 100);
 *     }
 *   }, []);
 * }
 */
export function useBrowseScrollRestoration() {
  /**
   * Save current scroll position and page to sessionStorage.
   */
  const savePosition = useCallback((page: number = 1) => {
    try {
      const state: ScrollState = {
        scrollY: window.scrollY,
        page,
      };
      sessionStorage.setItem(BROWSE_SCROLL_KEY, JSON.stringify(state));
    } catch {
      // sessionStorage may not be available (e.g., private browsing)
    }
  }, []);

  /**
   * Restore saved scroll position from sessionStorage.
   * Returns the saved state or null if none exists.
   * Clears the saved position after reading.
   */
  const restorePosition = useCallback((): ScrollState | null => {
    try {
      const stored = sessionStorage.getItem(BROWSE_SCROLL_KEY);
      if (!stored) return null;

      // Clear after reading (one-time restoration)
      sessionStorage.removeItem(BROWSE_SCROLL_KEY);

      const state = JSON.parse(stored) as ScrollState;
      return state;
    } catch {
      // Invalid JSON or sessionStorage not available
      return null;
    }
  }, []);

  /**
   * Clear saved scroll position without using it.
   * Call this when search/filters change to invalidate old position.
   */
  const clearPosition = useCallback(() => {
    try {
      sessionStorage.removeItem(BROWSE_SCROLL_KEY);
    } catch {
      // sessionStorage may not be available
    }
  }, []);

  /**
   * Scroll window to a specific Y position.
   * Uses instant behavior to avoid jarring animation on restore.
   */
  const scrollToPosition = useCallback((scrollY: number) => {
    window.scrollTo({
      top: scrollY,
      behavior: 'instant',
    });
  }, []);

  return {
    savePosition,
    restorePosition,
    clearPosition,
    scrollToPosition,
  };
}
