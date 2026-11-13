/**
 * Return to the opened mod card when coming back to the mod browser.
 *
 * Story 10.7: Scroll restoration after viewing mod details.
 * Story 16.1 (Epic 16 ADR-1): The browse state (search, filters, sort, page) lives in
 * the URL. The position is the card that was opened: just before a mod's detail page
 * opens, `{ search, slug }` is saved in sessionStorage. Every browser mount consumes
 * or clears that entry, and scrolls to the card only on a return from its detail
 * page to the same browse URL, once the results containing it have rendered. This
 * replaces the `{ scrollY, page }` offset and its 100 ms timeout, and never restores
 * after a detour, a refresh or a first load.
 */

import { useCallback, useEffect, useRef, useState } from 'react';

/** sessionStorage key for the mod opened from the browser. */
export const BROWSE_OPENED_MOD_KEY = 'browse-opened-mod';

/** The mod opened from the browser, and the browse URL search it was opened from. */
export interface OpenedModEntry {
  search: string;
  slug: string;
}

function isOpenedModEntry(value: unknown): value is OpenedModEntry {
  if (typeof value !== 'object' || value === null) return false;
  const { search, slug } = value as Record<string, unknown>;
  return (
    typeof slug === 'string' &&
    slug.length > 0 &&
    typeof search === 'string' &&
    (search === '' || search.startsWith('?'))
  );
}

/** Save the mod being opened. Call immediately before navigating to its detail page. */
export function saveOpenedMod(entry: OpenedModEntry): void {
  try {
    sessionStorage.setItem(BROWSE_OPENED_MOD_KEY, JSON.stringify(entry));
  } catch {
    // sessionStorage may be unavailable (e.g. private browsing)
  }
}

/** Read the saved entry without consuming it; null when missing or malformed. */
export function readOpenedMod(): OpenedModEntry | null {
  try {
    const stored = sessionStorage.getItem(BROWSE_OPENED_MOD_KEY);
    if (!stored) return null;
    const parsed: unknown = JSON.parse(stored);
    return isOpenedModEntry(parsed) ? parsed : null;
  } catch {
    // Invalid JSON or sessionStorage unavailable
    return null;
  }
}

/** Remove the saved entry. */
export function clearOpenedMod(): void {
  try {
    sessionStorage.removeItem(BROWSE_OPENED_MOD_KEY);
  } catch {
    // sessionStorage may be unavailable
  }
}

/**
 * Whether to return to the saved card: only on a return from the detail page to the
 * browse URL the mod was opened from.
 */
export function shouldRestoreOpenedMod(
  saved: OpenedModEntry | null,
  currentSearch: string,
  isReturn: boolean
): saved is OpenedModEntry {
  return saved !== null && isReturn && saved.search === currentSearch;
}

/** Center a rendered mod card in the viewport. Returns false when it is not rendered. */
export function scrollToModCard(slug: string): boolean {
  const testId = `mod-card-${slug}`;
  const card = Array.from(document.querySelectorAll<HTMLElement>('[data-testid]')).find(
    (element) => element.dataset.testid === testId
  );
  if (!card) return false;
  card.scrollIntoView({ block: 'center' });
  return true;
}

export interface BrowseScrollRestorationOptions {
  /** The browser's current URL search (`location.search`). */
  currentSearch: string;
  /** Whether this mount is a return from a detail page (link state or browser back). */
  isReturn: boolean;
  /** Slugs of the cards in the current results. */
  renderedSlugs: string[];
  /** Whether the current results have rendered (not loading). */
  isReady: boolean;
}

/**
 * Return to the opened card on a return from its detail page.
 *
 * @example
 * const { saveOpenedMod } = useBrowseScrollRestoration({
 *   currentSearch: location.search,
 *   isReturn: isReturnFromModDetail(location.state) || navigationType === 'POP',
 *   renderedSlugs: mods.map((mod) => mod.slug),
 *   isReady: !isLoading,
 * });
 * // Before opening a mod:
 * saveOpenedMod(slug);
 */
export function useBrowseScrollRestoration({
  currentSearch,
  isReturn,
  renderedSlugs,
  isReady,
}: BrowseScrollRestorationOptions) {
  // Decide once per mount, without side effects (StrictMode may call this twice)
  const [restoreSlug] = useState(() => {
    const saved = readOpenedMod();
    return shouldRestoreOpenedMod(saved, currentSearch, isReturn) ? saved.slug : null;
  });
  const pendingSlugRef = useRef(restoreSlug);

  // Every mount consumes or clears the saved entry
  useEffect(() => {
    clearOpenedMod();
  }, []);

  // Scroll once the results have rendered; if the card is gone, start at the top
  useEffect(() => {
    const slug = pendingSlugRef.current;
    if (!slug || !isReady) return;
    pendingSlugRef.current = null;
    if (!renderedSlugs.includes(slug) || !scrollToModCard(slug)) {
      window.scrollTo({ top: 0, behavior: 'instant' });
    }
  }, [isReady, renderedSlugs]);

  const saveCurrentOpenedMod = useCallback(
    (slug: string) => saveOpenedMod({ search: currentSearch, slug }),
    [currentSearch]
  );

  return { saveOpenedMod: saveCurrentOpenedMod };
}
