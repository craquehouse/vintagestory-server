/**
 * Tests for mod browser URL state helpers.
 *
 * Story 16.1: Mod Browser State Survives Mod Details (Epic 16 ADR-1)
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  BROWSE_PATH,
  BROWSE_LAST_SEARCH_KEY,
  DEFAULT_BROWSE_STATE,
  parseBrowseSearch,
  buildBrowseSearch,
  readBrowseSearchState,
  isReturnFromModDetail,
  getLastBrowseSearch,
  saveLastBrowseSearch,
} from './browse-search';

describe('BROWSE_PATH', () => {
  it('is the mod browser route', () => {
    expect(BROWSE_PATH).toBe('/game-server/mods/browse');
  });
});

describe('parseBrowseSearch', () => {
  it('returns the default state for an empty search', () => {
    expect(parseBrowseSearch('')).toEqual(DEFAULT_BROWSE_STATE);
    expect(DEFAULT_BROWSE_STATE).toEqual({
      search: '',
      sort: 'recent',
      filters: {},
      page: 1,
    });
  });

  it('accepts a search with or without the leading question mark', () => {
    expect(parseBrowseSearch('?q=food').search).toBe('food');
    expect(parseBrowseSearch('q=food').search).toBe('food');
  });

  it('parses every parameter, including the game version filter', () => {
    const state = parseBrowseSearch(
      '?q=carry+on&sort=downloads&side=server&tags=Utility,QoL&type=mod&version=1.22.7&page=3'
    );
    expect(state).toEqual({
      search: 'carry on',
      sort: 'downloads',
      filters: {
        side: 'server',
        tags: ['Utility', 'QoL'],
        modType: 'mod',
        gameVersion: '1.22.7',
      },
      page: 3,
    });
  });

  it('trims the search text', () => {
    expect(parseBrowseSearch('?q=%20%20food%20').search).toBe('food');
  });

  it.each([
    ['sort', '?sort=newest', { sort: 'recent' }],
    ['sort', '?sort=', { sort: 'recent' }],
    ['side', '?side=everywhere', { filters: {} }],
    ['type', '?type=plugin', { filters: {} }],
    ['page', '?page=0', { page: 1 }],
    ['page', '?page=-2', { page: 1 }],
    ['page', '?page=2.5', { page: 1 }],
    ['page', '?page=abc', { page: 1 }],
    ['page', '?page=', { page: 1 }],
    ['version', '?version=', { filters: {} }],
    ['tags', '?tags=', { filters: {} }],
    ['tags', '?tags=,,', { filters: {} }],
  ])('falls back to the default for an invalid %s (%s)', (_name, search, expected) => {
    expect(parseBrowseSearch(search)).toEqual({ ...DEFAULT_BROWSE_STATE, ...expected });
  });

  it('drops empty tag items and keeps tags with spaces', () => {
    expect(parseBrowseSearch('?tags=Quality+of+Life,,Food').filters.tags).toEqual([
      'Quality of Life',
      'Food',
    ]);
  });

  it('accepts every sort option', () => {
    for (const sort of ['recent', 'downloads', 'trending', 'name'] as const) {
      expect(parseBrowseSearch(`?sort=${sort}`).sort).toBe(sort);
    }
  });

  it('ignores unknown parameters', () => {
    expect(parseBrowseSearch('?foo=bar&q=x')).toEqual({ ...DEFAULT_BROWSE_STATE, search: 'x' });
  });
});

describe('buildBrowseSearch', () => {
  it('returns an empty string for the default state', () => {
    expect(buildBrowseSearch(DEFAULT_BROWSE_STATE)).toBe('');
  });

  it('omits defaults and page 1', () => {
    expect(buildBrowseSearch({ ...DEFAULT_BROWSE_STATE, sort: 'recent', page: 1 })).toBe('');
  });

  it('writes parameters in a fixed order, including the game version', () => {
    const search = buildBrowseSearch({
      search: 'food',
      sort: 'trending',
      filters: { gameVersion: '1.22.7', modType: 'mod', tags: ['A', 'B'], side: 'client' },
      page: 2,
    });
    expect(search).toBe('?q=food&sort=trending&side=client&tags=A%2CB&type=mod&version=1.22.7&page=2');
  });

  it('trims the search text and omits it when blank', () => {
    expect(buildBrowseSearch({ ...DEFAULT_BROWSE_STATE, search: '  food ' })).toBe('?q=food');
    expect(buildBrowseSearch({ ...DEFAULT_BROWSE_STATE, search: '   ' })).toBe('');
  });

  it('omits an empty tag list', () => {
    expect(buildBrowseSearch({ ...DEFAULT_BROWSE_STATE, filters: { tags: [] } })).toBe('');
  });

  it('round-trips through parseBrowseSearch', () => {
    const state = {
      search: 'carry on',
      sort: 'downloads' as const,
      filters: {
        side: 'both' as const,
        tags: ['Quality of Life', 'Food'],
        modType: 'externaltool' as const,
        gameVersion: '1.21.6',
      },
      page: 4,
    };
    expect(parseBrowseSearch(buildBrowseSearch(state))).toEqual(state);
  });
});

describe('readBrowseSearchState', () => {
  it('returns browseSearch from navigation state', () => {
    expect(readBrowseSearchState({ browseSearch: '?q=food&version=1.22.7' })).toBe(
      '?q=food&version=1.22.7'
    );
    expect(readBrowseSearchState({ browseSearch: '' })).toBe('');
  });

  it.each([
    ['null state', null],
    ['undefined state', undefined],
    ['a string state', '?q=food'],
    ['no browseSearch', { other: 1 }],
    ['a non-string browseSearch', { browseSearch: 42 }],
    ['a path instead of a search', { browseSearch: '/elsewhere' }],
    ['an absolute URL', { browseSearch: 'https://example.com/?q=x' }],
  ])('returns undefined for %s', (_name, state) => {
    expect(readBrowseSearchState(state)).toBeUndefined();
  });
});

describe('isReturnFromModDetail', () => {
  it('is true only for fromModDetail === true', () => {
    expect(isReturnFromModDetail({ fromModDetail: true })).toBe(true);
    expect(isReturnFromModDetail({ fromModDetail: 'true' })).toBe(false);
    expect(isReturnFromModDetail({})).toBe(false);
    expect(isReturnFromModDetail(null)).toBe(false);
    expect(isReturnFromModDetail(undefined)).toBe(false);
  });
});

describe('last browse search (sessionStorage)', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('returns null when nothing is saved', () => {
    expect(getLastBrowseSearch()).toBeNull();
  });

  it('saves and reads the full browse search', () => {
    saveLastBrowseSearch('?q=food&version=1.22.7&page=2');
    expect(sessionStorage.getItem(BROWSE_LAST_SEARCH_KEY)).toBe('?q=food&version=1.22.7&page=2');
    expect(getLastBrowseSearch()).toBe('?q=food&version=1.22.7&page=2');
  });

  it('saves the default state as an empty string', () => {
    saveLastBrowseSearch('?q=food');
    saveLastBrowseSearch('');
    expect(getLastBrowseSearch()).toBe('');
  });

  it('ignores a saved value that is not a search string', () => {
    sessionStorage.setItem(BROWSE_LAST_SEARCH_KEY, '/somewhere');
    expect(getLastBrowseSearch()).toBeNull();
  });

  it('survives sessionStorage being unavailable', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('denied');
    });
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('denied');
    });
    expect(() => saveLastBrowseSearch('?q=x')).not.toThrow();
    expect(getLastBrowseSearch()).toBeNull();
  });
});
