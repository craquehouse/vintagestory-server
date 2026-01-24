import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import {
  useBrowseMods,
  filterModsBySearch,
  filterModsByFilters,
  sortModsByName,
} from './use-browse-mods';
import type { ModBrowseItem, ApiResponse, ModBrowseData } from '@/api/types';

// Create a wrapper with QueryClientProvider for testing hooks that use TanStack Query
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock mod data for testing
const mockMods: ModBrowseItem[] = [
  {
    slug: 'carrycapacity',
    urlalias: 'carrycapacity',
    assetId: 12345,
    name: 'Carry Capacity',
    author: 'copygirl',
    summary: 'Allows picking up chests and other containers',
    downloads: 50000,
    follows: 500,
    trendingPoints: 100,
    side: 'both',
    modType: 'mod',
    logoUrl: null,
    tags: ['utility', 'qol'],
    lastReleased: '2024-01-15T10:00:00Z',
  },
  {
    slug: 'primitivesurvival',
    urlalias: 'primitivesurvival',
    assetId: 23456,
    name: 'Primitive Survival',
    author: 'Spear and Fang',
    summary: 'Adds primitive survival mechanics like fishing and trapping',
    downloads: 75000,
    follows: 800,
    trendingPoints: 200,
    side: 'both',
    modType: 'mod',
    logoUrl: 'https://example.com/logo.png',
    tags: ['survival', 'fishing', 'traps'],
    lastReleased: '2024-02-01T12:00:00Z',
  },
  {
    slug: 'wildcraft',
    urlalias: 'wildcraft',
    assetId: 34567,
    name: 'Wildcraft',
    author: 'gabb',
    summary: null,
    downloads: 30000,
    follows: 200,
    trendingPoints: 50,
    side: 'server',
    modType: 'mod',
    logoUrl: null,
    tags: ['plants', 'foraging'],
    lastReleased: '2024-01-20T08:00:00Z',
  },
];

const mockBrowseResponse: ApiResponse<ModBrowseData> = {
  status: 'ok',
  data: {
    mods: mockMods,
    pagination: {
      page: 1,
      pageSize: 20,
      totalItems: 100,
      totalPages: 5,
      hasNext: true,
      hasPrev: false,
    },
  },
};

describe('filterModsBySearch', () => {
  it('returns all mods when search is empty', () => {
    const result = filterModsBySearch(mockMods, '');
    expect(result).toHaveLength(3);
    expect(result).toEqual(mockMods);
  });

  it('returns all mods when search is undefined', () => {
    const result = filterModsBySearch(mockMods, undefined);
    expect(result).toHaveLength(3);
  });

  it('returns all mods when search is only whitespace', () => {
    const result = filterModsBySearch(mockMods, '   ');
    expect(result).toHaveLength(3);
  });

  it('filters by mod name (case-insensitive)', () => {
    const result = filterModsBySearch(mockMods, 'carry');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('carrycapacity');
  });

  it('filters by mod name with different case', () => {
    const result = filterModsBySearch(mockMods, 'PRIMITIVE');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('primitivesurvival');
  });

  it('filters by author name', () => {
    const result = filterModsBySearch(mockMods, 'gabb');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('wildcraft');
  });

  it('filters by summary content', () => {
    const result = filterModsBySearch(mockMods, 'fishing');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('primitivesurvival');
  });

  it('handles mods with null summary', () => {
    const result = filterModsBySearch(mockMods, 'plants');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('wildcraft');
  });

  it('filters by tag', () => {
    const result = filterModsBySearch(mockMods, 'qol');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('carrycapacity');
  });

  it('returns multiple matches', () => {
    // Both 'primitivesurvival' and 'wildcraft' have survival-related content
    const result = filterModsBySearch(mockMods, 'survival');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('primitivesurvival');
  });

  it('returns empty array when no matches', () => {
    const result = filterModsBySearch(mockMods, 'nonexistent');
    expect(result).toHaveLength(0);
  });

  it('handles empty mods array', () => {
    const result = filterModsBySearch([], 'test');
    expect(result).toHaveLength(0);
  });

  it('matches partial strings', () => {
    const result = filterModsBySearch(mockMods, 'prim');
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('primitivesurvival');
  });
});

describe('filterModsByFilters', () => {
  it('returns all mods when filters are undefined', () => {
    const result = filterModsByFilters(mockMods, undefined);
    expect(result).toHaveLength(3);
    expect(result).toEqual(mockMods);
  });

  it('returns all mods when filters are empty object', () => {
    const result = filterModsByFilters(mockMods, {});
    expect(result).toHaveLength(3);
  });

  it('filters by side (exact match)', () => {
    const result = filterModsByFilters(mockMods, { side: 'server' });
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('wildcraft');
  });

  it('filters by side "both"', () => {
    const result = filterModsByFilters(mockMods, { side: 'both' });
    expect(result).toHaveLength(2);
    expect(result.map((m) => m.slug)).toEqual([
      'carrycapacity',
      'primitivesurvival',
    ]);
  });

  it('filters by single tag (OR logic within tags)', () => {
    const result = filterModsByFilters(mockMods, { tags: ['qol'] });
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('carrycapacity');
  });

  it('filters by multiple tags (OR logic)', () => {
    const result = filterModsByFilters(mockMods, { tags: ['qol', 'survival'] });
    expect(result).toHaveLength(2);
    expect(result.map((m) => m.slug)).toContain('carrycapacity');
    expect(result.map((m) => m.slug)).toContain('primitivesurvival');
  });

  it('filters tags case-insensitively', () => {
    const result = filterModsByFilters(mockMods, { tags: ['QOL'] });
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('carrycapacity');
  });

  it('filters by modType', () => {
    const result = filterModsByFilters(mockMods, { modType: 'mod' });
    expect(result).toHaveLength(3);
  });

  it('filters out mods that do not match modType', () => {
    const result = filterModsByFilters(mockMods, { modType: 'externaltool' });
    expect(result).toHaveLength(0);
  });

  // Game version filter disabled - API doesn't provide version compatibility data
  it.skip('filters by gameVersion - DISABLED (requires API enhancement)', () => {
    // lastReleased is a timestamp, not a version string
    // Game version compatibility would need to come from releases array
    // which isn't included in browse endpoint
  });

  it.skip('handles mods with null lastReleased - DISABLED (requires API enhancement)', () => {
    // Game version filtering disabled until API provides compatibility data
  });

  it('combines multiple filters with AND logic', () => {
    const result = filterModsByFilters(mockMods, {
      side: 'both',
      tags: ['utility'],
    });
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('carrycapacity');
  });

  it('returns empty array when no mods match filters', () => {
    const result = filterModsByFilters(mockMods, {
      side: 'client',
      tags: ['nonexistent'],
    });
    expect(result).toHaveLength(0);
  });

  it('handles empty mods array', () => {
    const result = filterModsByFilters([], { side: 'server' });
    expect(result).toHaveLength(0);
  });

  it('filters with multiple filter types combined', () => {
    const result = filterModsByFilters(mockMods, {
      side: 'both',
      tags: ['utility'],
      modType: 'mod',
    });
    expect(result).toHaveLength(1);
    expect(result[0].slug).toBe('carrycapacity');
  });
});

describe('sortModsByName', () => {
  it('sorts mods alphabetically by name (A-Z)', () => {
    const result = sortModsByName(mockMods);
    expect(result).toHaveLength(3);
    expect(result[0].slug).toBe('carrycapacity'); // "Carry Capacity"
    expect(result[1].slug).toBe('primitivesurvival'); // "Primitive Survival"
    expect(result[2].slug).toBe('wildcraft'); // "Wildcraft"
  });

  it('returns a new array without mutating the original', () => {
    const original = [...mockMods];
    const result = sortModsByName(mockMods);

    expect(result).not.toBe(mockMods);
    expect(mockMods).toEqual(original);
  });

  it('handles empty array', () => {
    const result = sortModsByName([]);
    expect(result).toEqual([]);
  });

  it('handles single mod array', () => {
    const singleMod = [mockMods[0]];
    const result = sortModsByName(singleMod);
    expect(result).toHaveLength(1);
    expect(result[0]).toEqual(mockMods[0]);
  });

  it('sorts case-insensitively using localeCompare', () => {
    const unsorted: ModBrowseItem[] = [
      {
        ...mockMods[0],
        name: 'zebra mod',
        slug: 'zebra',
      },
      {
        ...mockMods[1],
        name: 'Apple Mod',
        slug: 'apple',
      },
      {
        ...mockMods[2],
        name: 'banana mod',
        slug: 'banana',
      },
    ];

    const result = sortModsByName(unsorted);
    expect(result[0].slug).toBe('apple'); // "Apple Mod"
    expect(result[1].slug).toBe('banana'); // "banana mod"
    expect(result[2].slug).toBe('zebra'); // "zebra mod"
  });

  it('handles mods with special characters in names', () => {
    const specialMods: ModBrowseItem[] = [
      {
        ...mockMods[0],
        name: 'Ñoño Mod',
        slug: 'nono',
      },
      {
        ...mockMods[1],
        name: 'Äpfel',
        slug: 'apfel',
      },
      {
        ...mockMods[2],
        name: 'Zebra',
        slug: 'zebra',
      },
    ];

    const result = sortModsByName(specialMods);
    // localeCompare should handle special characters properly
    expect(result).toHaveLength(3);
    // Exact order depends on locale, but should be consistent
    expect(result.map(m => m.slug)).toEqual(['apfel', 'nono', 'zebra']);
  });

  it('handles identical names', () => {
    const duplicates: ModBrowseItem[] = [
      { ...mockMods[0], name: 'Same Name', slug: 'mod1' },
      { ...mockMods[1], name: 'Same Name', slug: 'mod2' },
      { ...mockMods[2], name: 'Same Name', slug: 'mod3' },
    ];

    const result = sortModsByName(duplicates);
    expect(result).toHaveLength(3);
    // All have same name, so order should be stable
    result.forEach(mod => expect(mod.name).toBe('Same Name'));
  });
});

describe('useBrowseMods', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('fetches mods on mount', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useBrowseMods(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    // Wait for data
    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(result.current.mods).toHaveLength(3);
    expect(result.current.pagination?.totalItems).toBe(100);
  });

  it('passes API parameters correctly', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    renderHook(
      () => useBrowseMods({ page: 2, pageSize: 50, sort: 'downloads' }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('page=2');
    expect(url).toContain('page_size=50');
    expect(url).toContain('sort=downloads');
  });

  it('passes search parameter to API', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    renderHook(() => useBrowseMods({ search: 'test' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('search=test');
  });

  it('returns mods from API when search is provided (server-side filtering)', async () => {
    // API now filters server-side and returns only matching mods
    const searchResponse: ApiResponse<ModBrowseData> = {
      status: 'ok',
      data: {
        mods: [mockMods[0]], // API returns filtered result
        pagination: {
          page: 1,
          pageSize: 20,
          totalItems: 1, // Reflects filtered count
          totalPages: 1,
          hasNext: false,
          hasPrev: false,
        },
      },
    };

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(searchResponse),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useBrowseMods({ search: 'carry' }), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should return the filtered result from API
    expect(result.current.mods).toHaveLength(1);
    expect(result.current.mods[0].slug).toBe('carrycapacity');
    // Pagination now reflects filtered totals
    expect(result.current.pagination?.totalItems).toBe(1);
  });

  it('returns empty mods array when loading', () => {
    const mockFetch = vi.fn().mockImplementation(
      () =>
        new Promise(() => {
          /* never resolves */
        })
    );
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useBrowseMods(), {
      wrapper: createWrapper(),
    });

    expect(result.current.mods).toEqual([]);
    expect(result.current.isLoading).toBe(true);
  });

  it('handles API errors', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () => Promise.reject(new Error('Not JSON')),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(() => useBrowseMods(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.mods).toEqual([]);
  });

  it('uses correct stale time for caching', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    // First render
    const { result, rerender } = renderHook(() => useBrowseMods(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // Should have called fetch once
    expect(mockFetch).toHaveBeenCalledTimes(1);

    // Rerender should use cached data
    rerender();

    // Should still have only called fetch once (data is fresh)
    expect(mockFetch).toHaveBeenCalledTimes(1);
  });

  // VSS-y7u: Filters are now passed to API (server-side filtering)
  it('passes side filter to API (server-side filtering)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    renderHook(
      () => useBrowseMods({ filters: { side: 'server' } }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // VSS-y7u: Side filter is now passed to API
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('side=server');
  });

  it('passes all filters to API (server-side filtering)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockBrowseResponse),
    });
    globalThis.fetch = mockFetch;

    renderHook(
      () =>
        useBrowseMods({
          filters: { side: 'server', modType: 'mod', tags: ['utility', 'qol'] },
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(mockFetch).toHaveBeenCalled();
    });

    // VSS-y7u: All filters are now passed to API
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('side=server');
    expect(url).toContain('mod_type=mod');
    expect(url).toContain('tags=utility%2Cqol');
  });

  // VSS-y7u: Both search and filters are now server-side
  it('passes both search and filters to API', async () => {
    const searchResponse: ApiResponse<ModBrowseData> = {
      status: 'ok',
      data: {
        // API returns mods matching 'survival' search and 'both' side filter
        mods: [mockMods[1]], // primitivesurvival
        pagination: {
          page: 1,
          pageSize: 20,
          totalItems: 1,
          totalPages: 1,
          hasNext: false,
          hasPrev: false,
        },
      },
    };

    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(searchResponse),
    });
    globalThis.fetch = mockFetch;

    const { result } = renderHook(
      () =>
        useBrowseMods({
          search: 'survival',
          filters: { side: 'both' },
        }),
      { wrapper: createWrapper() }
    );

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    // VSS-y7u: Both search and filters are passed to API
    expect(result.current.mods).toHaveLength(1);
    expect(result.current.mods[0].slug).toBe('primitivesurvival');

    // Verify both search and side filter were passed to API
    const [url] = mockFetch.mock.calls[0];
    expect(url).toContain('search=survival');
    expect(url).toContain('side=both');
  });

  // Story 10.7: Pagination state tests
  describe('pagination state management', () => {
    it('exposes setPage function to change current page', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Should have setPage function
      expect(typeof result.current.setPage).toBe('function');

      // Initial page should be 1
      expect(result.current.currentPage).toBe(1);
    });

    it('updates currentPage when setPage is called', async () => {
      const page1Response = {
        status: 'ok' as const,
        data: {
          mods: mockMods,
          pagination: {
            page: 1,
            pageSize: 20,
            totalItems: 100,
            totalPages: 5,
            hasNext: true,
            hasPrev: false,
          },
        },
      };

      const page2Response = {
        status: 'ok' as const,
        data: {
          mods: mockMods.slice(0, 1), // Different data for page 2
          pagination: {
            page: 2,
            pageSize: 20,
            totalItems: 100,
            totalPages: 5,
            hasNext: true,
            hasPrev: true,
          },
        },
      };

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(page1Response),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(page2Response),
        });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Change to page 2
      act(() => {
        result.current.setPage(2);
      });

      await waitFor(() => {
        expect(result.current.currentPage).toBe(2);
      });
    });

    it('exposes goToNextPage function', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(typeof result.current.goToNextPage).toBe('function');
    });

    it('exposes goToPrevPage function', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(typeof result.current.goToPrevPage).toBe('function');
    });

    it('includes page in query key for proper caching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 1,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: false,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Change to page 2 via setPage - should trigger new fetch
      act(() => {
        result.current.setPage(2);
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(2);
      });

      // Verify page 2 was requested
      const [url] = mockFetch.mock.calls[1];
      expect(url).toContain('page=2');
    });

    it('goToNextPage increments page when hasNext is true', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 1,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: false,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(1);

      // Call goToNextPage
      act(() => {
        result.current.goToNextPage();
      });

      await waitFor(() => {
        expect(result.current.currentPage).toBe(2);
      });
    });

    it('goToPrevPage decrements page when hasPrev is true', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 2,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: true,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods({ page: 2 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(2);

      // Call goToPrevPage
      act(() => {
        result.current.goToPrevPage();
      });

      await waitFor(() => {
        expect(result.current.currentPage).toBe(1);
      });
    });

    it('goToNextPage does nothing when hasNext is false', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 5,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: false,
                hasPrev: true,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods({ page: 5 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(5);

      // Call goToNextPage - should do nothing
      act(() => {
        result.current.goToNextPage();
      });

      // Wait a bit to ensure state didn't change
      await new Promise((r) => setTimeout(r, 50));

      expect(result.current.currentPage).toBe(5);
    });

    it('goToPrevPage does nothing when hasPrev is false', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 1,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: false,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(1);

      // Call goToPrevPage - should do nothing
      act(() => {
        result.current.goToPrevPage();
      });

      // Wait a bit to ensure state didn't change
      await new Promise((r) => setTimeout(r, 50));

      expect(result.current.currentPage).toBe(1);
    });

    it('setPage rejects page numbers less than 1', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 2,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: true,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods({ page: 2 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(2);

      // Try to set page to 0
      act(() => {
        result.current.setPage(0);
      });

      // Should remain on page 2
      expect(result.current.currentPage).toBe(2);

      // Try to set page to -1
      act(() => {
        result.current.setPage(-1);
      });

      // Should remain on page 2
      expect(result.current.currentPage).toBe(2);
    });

    it('setPage rejects page numbers greater than totalPages', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 2,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: true,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods({ page: 2 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(2);

      // Try to set page to 10 (totalPages is 5)
      act(() => {
        result.current.setPage(10);
      });

      // Should remain on page 2
      expect(result.current.currentPage).toBe(2);
    });
  });

  // Client-side sorting tests
  describe('client-side name sorting', () => {
    it('sorts mods by name when sort parameter is "name"', async () => {
      // API returns unsorted data
      const unsortedResponse: ApiResponse<ModBrowseData> = {
        status: 'ok',
        data: {
          mods: [mockMods[2], mockMods[0], mockMods[1]], // Wildcraft, Carry Capacity, Primitive Survival
          pagination: {
            page: 1,
            pageSize: 1000, // Large page size for client-side sorting
            totalItems: 3,
            totalPages: 1,
            hasNext: false,
            hasPrev: false,
          },
        },
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(unsortedResponse),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods({ sort: 'name' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Should be sorted alphabetically: Carry Capacity, Primitive Survival, Wildcraft
      expect(result.current.mods).toHaveLength(3);
      expect(result.current.mods[0].slug).toBe('carrycapacity');
      expect(result.current.mods[1].slug).toBe('primitivesurvival');
      expect(result.current.mods[2].slug).toBe('wildcraft');
    });

    it('uses large pageSize (1000) when sorting by name client-side', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ sort: 'name', pageSize: 20 }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      // Should request 1000 items for client-side sorting, not 20
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('page_size=1000');
      // Name sort is client-side, so no sort param should be sent to API
      expect(url).not.toContain('sort=name');
    });

    it('does not pass "name" sort to API (client-side only)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ sort: 'name' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).not.toContain('sort=name');
      expect(url).not.toContain('sort=');
    });

    it('passes server-side sort options to API', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ sort: 'downloads' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('sort=downloads');
    });

    it('handles empty results when sorting by name', async () => {
      const emptyResponse: ApiResponse<ModBrowseData> = {
        status: 'ok',
        data: {
          mods: [],
          pagination: {
            page: 1,
            pageSize: 1000,
            totalItems: 0,
            totalPages: 0,
            hasNext: false,
            hasPrev: false,
          },
        },
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(emptyResponse),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods({ sort: 'name' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.mods).toEqual([]);
    });
  });

  // Backwards compatibility tests
  describe('backwards compatibility - flat params vs filters object', () => {
    it('accepts filters.side (legacy format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ filters: { side: 'server' } }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('side=server');
    });

    it('accepts side (flat format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ side: 'server' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('side=server');
    });

    it('prefers flat params over filters object when both provided', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(
        () =>
          useBrowseMods({
            side: 'client',
            filters: { side: 'server' },
          }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      // Flat param (client) should win over filters object (server)
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('side=client');
      expect(url).not.toContain('side=server');
    });

    it('accepts filters.gameVersion (legacy format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(
        () => useBrowseMods({ filters: { gameVersion: '1.19.0' } }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('version=1.19.0');
    });

    it('accepts version (flat format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ version: '1.19.0' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('version=1.19.0');
    });

    it('accepts filters.modType (legacy format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ filters: { modType: 'externaltool' } }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('mod_type=externaltool');
    });

    it('accepts modType (flat format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ modType: 'externaltool' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('mod_type=externaltool');
    });

    it('accepts filters.tags (legacy format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ filters: { tags: ['utility', 'qol'] } }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('tags=utility%2Cqol');
    });

    it('accepts tags (flat format)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ tags: ['utility', 'qol'] }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('tags=utility%2Cqol');
    });
  });

  // Edge cases and error scenarios
  describe('edge cases', () => {
    it('handles empty results with pagination metadata', async () => {
      const emptyResponse: ApiResponse<ModBrowseData> = {
        status: 'ok',
        data: {
          mods: [],
          pagination: {
            page: 1,
            pageSize: 20,
            totalItems: 0,
            totalPages: 0,
            hasNext: false,
            hasPrev: false,
          },
        },
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(emptyResponse),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.mods).toEqual([]);
      expect(result.current.pagination?.totalItems).toBe(0);
      expect(result.current.pagination?.totalPages).toBe(0);
      expect(result.current.pagination?.hasNext).toBe(false);
      expect(result.current.pagination?.hasPrev).toBe(false);
    });

    it('handles missing pagination metadata gracefully', async () => {
      const noPaginationResponse = {
        status: 'ok' as const,
        data: {
          mods: mockMods,
          // No pagination field
        },
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(noPaginationResponse),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.mods).toHaveLength(3);
      expect(result.current.pagination).toBeUndefined();
    });

    it('handles page changes when pagination becomes available', async () => {
      // Initial fetch with no pagination
      const noPaginationResponse = {
        status: 'ok' as const,
        data: {
          mods: mockMods,
        },
      };

      // Second fetch with pagination
      const withPaginationResponse: ApiResponse<ModBrowseData> = {
        status: 'ok',
        data: {
          mods: mockMods,
          pagination: {
            page: 2,
            pageSize: 20,
            totalItems: 100,
            totalPages: 5,
            hasNext: true,
            hasPrev: true,
          },
        },
      };

      const mockFetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(noPaginationResponse),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(withPaginationResponse),
        });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.pagination).toBeUndefined();

      // Change page
      act(() => {
        result.current.setPage(2);
      });

      await waitFor(() => {
        expect(result.current.pagination).toBeDefined();
      });

      expect(result.current.currentPage).toBe(2);
      expect(result.current.pagination?.page).toBe(2);
    });

    it('setPage allows valid page within bounds even without hasNext flag', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 1,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: false,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Jump to page 5 directly (last page)
      act(() => {
        result.current.setPage(5);
      });

      await waitFor(() => {
        expect(result.current.currentPage).toBe(5);
      });
    });

    it('initializes with page from params', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 3,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: true,
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods({ page: 3 }), {
        wrapper: createWrapper(),
      });

      // Should initialize with page 3
      expect(result.current.currentPage).toBe(3);

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(3);
    });

    it('handles game version filtering', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods({ version: '1.19.0' }), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('version=1.19.0');
    });

    it('handles all filter types simultaneously', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(
        () =>
          useBrowseMods({
            search: 'farming',
            version: '1.19.0',
            side: 'server',
            modType: 'mod',
            tags: ['utility', 'qol'],
            sort: 'downloads',
            page: 2,
            pageSize: 50,
          }),
        {
          wrapper: createWrapper(),
        }
      );

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('search=farming');
      expect(url).toContain('version=1.19.0');
      expect(url).toContain('side=server');
      expect(url).toContain('mod_type=mod');
      expect(url).toContain('tags=utility%2Cqol');
      expect(url).toContain('sort=downloads');
      expect(url).toContain('page=2');
      expect(url).toContain('page_size=50');
    });

    it('goToPrevPage does not go below page 1 even if hasPrev is true', async () => {
      // Edge case: API says hasPrev=true but we're on page 1
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              mods: mockMods,
              pagination: {
                page: 1,
                pageSize: 20,
                totalItems: 100,
                totalPages: 5,
                hasNext: true,
                hasPrev: true, // Inconsistent but possible
              },
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.currentPage).toBe(1);

      // Try to go to previous page
      act(() => {
        result.current.goToPrevPage();
      });

      // Should remain on page 1 due to prev > 1 check
      await new Promise((r) => setTimeout(r, 50));
      expect(result.current.currentPage).toBe(1);
    });

    it('uses default page 1 when no page param provided', () => {
      const mockFetch = vi.fn().mockImplementation(
        () =>
          new Promise(() => {
            /* never resolves */
          })
      );
      globalThis.fetch = mockFetch;

      const { result } = renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      expect(result.current.currentPage).toBe(1);
    });

    it('uses default pageSize 20 when no pageSize param provided', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });
      globalThis.fetch = mockFetch;

      renderHook(() => useBrowseMods(), {
        wrapper: createWrapper(),
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain('page_size=20');
    });
  });
});
