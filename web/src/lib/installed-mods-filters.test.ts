import { describe, it, expect } from 'vitest';
import {
  EMPTY_FILTERS,
  filtersFromSearchParams,
  filtersToSearchParams,
  hasFilters,
  matchesFilters,
  type FilterableMod,
} from './installed-mods-filters';

function mod(overrides: Partial<FilterableMod> = {}): FilterableMod {
  return {
    slug: 'carryon',
    name: 'Carry On',
    compatibilityStatus: 'compatible',
    compatibilityKnown: true,
    updateStatus: undefined,
    ...overrides,
  };
}

describe('filtersFromSearchParams (Story 24.7, ADR-6 decisions 2 and 3)', () => {
  it('reads q, compat and updates', () => {
    expect(
      filtersFromSearchParams(new URLSearchParams('q=carry&compat=incompatible&updates=1'))
    ).toEqual({ query: 'carry', compat: 'incompatible', updates: true });
  });

  it('gives no filters for an empty URL', () => {
    expect(filtersFromSearchParams(new URLSearchParams())).toEqual(EMPTY_FILTERS);
  });

  it('ignores invalid values', () => {
    expect(filtersFromSearchParams(new URLSearchParams('compat=sometimes&updates=yes&q='))).toEqual(
      EMPTY_FILTERS
    );
  });
});

describe('filtersToSearchParams', () => {
  it('writes only the filters that are on, keeping other parameters', () => {
    const params = filtersToSearchParams(
      { query: 'carry', compat: null, updates: true },
      new URLSearchParams('tab=x&compat=compatible')
    );

    expect(params.toString()).toBe('tab=x&q=carry&updates=1');
  });

  it('drops invalid values on the next change', () => {
    const params = filtersToSearchParams(EMPTY_FILTERS, new URLSearchParams('compat=sometimes'));

    expect(params.toString()).toBe('');
  });

  it('round-trips', () => {
    const filters = { query: 'a b', compat: 'not_verified' as const, updates: false };

    expect(filtersFromSearchParams(filtersToSearchParams(filters, new URLSearchParams()))).toEqual(
      filters
    );
  });
});

describe('hasFilters', () => {
  it('is false only when nothing is filtered', () => {
    expect(hasFilters(EMPTY_FILTERS)).toBe(false);
    expect(hasFilters({ ...EMPTY_FILTERS, query: '  ' })).toBe(false);
    expect(hasFilters({ ...EMPTY_FILTERS, updates: true })).toBe(true);
  });
});

describe('matchesFilters (FR341)', () => {
  it('matches part of the name or the mod ID, ignoring case', () => {
    const filters = (query: string) => ({ ...EMPTY_FILTERS, query });

    expect(matchesFilters(mod(), filters('CARRY'))).toBe(true);
    expect(matchesFilters(mod(), filters('ryon'))).toBe(true);
    expect(matchesFilters(mod({ name: null }), filters('carry'))).toBe(true);
    expect(matchesFilters(mod({ name: 'Smithing', slug: 'smithingplus' }), filters('carry'))).toBe(
      false
    );
    expect(matchesFilters(mod(), filters('  carry  '))).toBe(true);
  });

  it('matches the compatibility status', () => {
    const filters = { ...EMPTY_FILTERS, compat: 'not_verified' as const };

    expect(matchesFilters(mod({ compatibilityStatus: 'not_verified' }), filters)).toBe(true);
    expect(matchesFilters(mod({ compatibilityStatus: 'compatible' }), filters)).toBe(false);
  });

  it('matches a loading compatibility only under All (ADR-6 decision 4)', () => {
    const loading = mod({ compatibilityStatus: 'not_verified', compatibilityKnown: false });

    expect(matchesFilters(loading, { ...EMPTY_FILTERS, compat: 'not_verified' })).toBe(false);
    expect(matchesFilters(loading, EMPTY_FILTERS)).toBe(true);
  });

  it('matches an available update', () => {
    const filters = { ...EMPTY_FILTERS, updates: true };

    expect(matchesFilters(mod({ updateStatus: { status: 'update_available' } }), filters)).toBe(
      true
    );
    expect(matchesFilters(mod({ updateStatus: { status: 'up_to_date' } }), filters)).toBe(false);
    expect(matchesFilters(mod({ updateStatus: undefined }), filters)).toBe(false);
  });

  it('combines the filters', () => {
    const filters = { query: 'carry', compat: 'compatible' as const, updates: true };

    expect(matchesFilters(mod({ updateStatus: { status: 'update_available' } }), filters)).toBe(
      true
    );
    expect(matchesFilters(mod({ updateStatus: { status: 'up_to_date' } }), filters)).toBe(false);
  });
});
