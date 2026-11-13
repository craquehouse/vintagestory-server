/**
 * Mod browser state in the URL.
 *
 * Story 16.1 (Epic 16 ADR-1): the URL is the source of truth for the mod
 * browser's search, filters, sort and page, so the state survives opening a
 * mod's detail page, browser back and forward, refresh and shared links.
 *
 * | Parameter | Field                 | Default (omitted) |
 * |-----------|-----------------------|-------------------|
 * | q         | search (trimmed)      | ''                |
 * | sort      | sort                  | 'recent'          |
 * | side      | filters.side          | none              |
 * | tags      | filters.tags (a,b)    | none              |
 * | type      | filters.modType       | none              |
 * | version   | filters.gameVersion   | none              |
 * | page      | page                  | 1                 |
 *
 * Unknown or invalid values fall back to their defaults.
 */

import type { BrowseModSide, BrowseSortOption, ModFilters, ModType } from '@/api/types';

/** Route of the mod browser. */
export const BROWSE_PATH = '/game-server/mods/browse';

/** sessionStorage key holding the last browse URL search (including page). */
export const BROWSE_LAST_SEARCH_KEY = 'browse-last-search';

/** Mod browser state carried in the URL. */
export interface BrowseUrlState {
  search: string;
  sort: BrowseSortOption;
  filters: ModFilters;
  page: number;
}

export const DEFAULT_BROWSE_STATE: BrowseUrlState = {
  search: '',
  sort: 'recent',
  filters: {},
  page: 1,
};

const SORT_OPTIONS: readonly BrowseSortOption[] = ['recent', 'downloads', 'trending', 'name'];
const SIDE_OPTIONS: readonly BrowseModSide[] = ['client', 'server', 'both'];
const TYPE_OPTIONS: readonly ModType[] = ['mod', 'externaltool', 'other'];

function oneOf<T extends string>(value: string | null, options: readonly T[]): T | undefined {
  return options.find((option) => option === value);
}

function parsePage(value: string | null): number {
  if (!value || !/^\d+$/.test(value)) return 1;
  const page = Number(value);
  return page >= 1 ? page : 1;
}

/**
 * Parse a URL search string (with or without the leading `?`) into browse state.
 */
export function parseBrowseSearch(search: string): BrowseUrlState {
  const params = new URLSearchParams(search);

  const filters: ModFilters = {};
  const side = oneOf(params.get('side'), SIDE_OPTIONS);
  if (side) filters.side = side;
  const tags = (params.get('tags') ?? '')
    .split(',')
    .map((tag) => tag.trim())
    .filter((tag) => tag.length > 0);
  if (tags.length > 0) filters.tags = tags;
  const modType = oneOf(params.get('type'), TYPE_OPTIONS);
  if (modType) filters.modType = modType;
  const gameVersion = params.get('version')?.trim();
  if (gameVersion) filters.gameVersion = gameVersion;

  return {
    search: (params.get('q') ?? '').trim(),
    sort: oneOf(params.get('sort'), SORT_OPTIONS) ?? DEFAULT_BROWSE_STATE.sort,
    filters,
    page: parsePage(params.get('page')),
  };
}

/**
 * Build the URL search string for browse state: `''` for the default state,
 * otherwise `?` followed by the non-default parameters in a fixed order.
 */
export function buildBrowseSearch(state: BrowseUrlState): string {
  const params = new URLSearchParams();
  const search = state.search.trim();
  if (search) params.set('q', search);
  if (state.sort !== DEFAULT_BROWSE_STATE.sort) params.set('sort', state.sort);
  if (state.filters.side) params.set('side', state.filters.side);
  if (state.filters.tags && state.filters.tags.length > 0) {
    params.set('tags', state.filters.tags.join(','));
  }
  if (state.filters.modType) params.set('type', state.filters.modType);
  if (state.filters.gameVersion) params.set('version', state.filters.gameVersion);
  if (state.page > 1) params.set('page', String(state.page));

  const query = params.toString();
  return query ? `?${query}` : '';
}

function isSearchString(value: unknown): value is string {
  return typeof value === 'string' && (value === '' || value.startsWith('?'));
}

function readStateField(state: unknown, field: string): unknown {
  if (typeof state !== 'object' || state === null) return undefined;
  return (state as Record<string, unknown>)[field];
}

/**
 * Read the browse search a detail page was opened from (`state.browseSearch`).
 * Returns undefined when the detail page was not opened from the browser.
 */
export function readBrowseSearchState(state: unknown): string | undefined {
  const value = readStateField(state, 'browseSearch');
  return isSearchString(value) ? value : undefined;
}

/** Navigation state set by the links from a mod's detail page back into the browser. */
export const MOD_DETAIL_RETURN_STATE = { fromModDetail: true } as const;

/** Whether navigation state marks a return from a mod's detail page. */
export function isReturnFromModDetail(state: unknown): boolean {
  return readStateField(state, 'fromModDetail') === true;
}

/** Last browse search of this browser session, or null when none is saved. */
export function getLastBrowseSearch(): string | null {
  try {
    const value = sessionStorage.getItem(BROWSE_LAST_SEARCH_KEY);
    return isSearchString(value) ? value : null;
  } catch {
    // sessionStorage may be unavailable (e.g. private browsing)
    return null;
  }
}

/** Remember the browse search so the Browse tab can return to it. */
export function saveLastBrowseSearch(search: string): void {
  try {
    sessionStorage.setItem(BROWSE_LAST_SEARCH_KEY, search);
  } catch {
    // sessionStorage may be unavailable (e.g. private browsing)
  }
}
