/**
 * BrowseTab component tests.
 *
 * Story 10.3: Browse Landing Page & Search
 * Story 10.4: Filter & Sort Controls
 * VSS-195: Slug/URL detection in search
 *
 * Tests cover:
 * - AC1: Loads mods immediately on page load
 * - AC2: Search input with placeholder
 * - AC3: Debounced search (300ms)
 * - AC5: Clear button and Escape key
 * - AC6: Error state with retry
 * - AC7: Loading state
 * - AC8-11: Filter and sort integration
 * - VSS-195: Direct navigation on Enter with slug/URL
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useEffect, type ReactNode } from 'react';
import {
  MemoryRouter,
  RouterProvider,
  createMemoryRouter,
  useLocation,
  useNavigationType,
} from 'react-router';
import { BrowseTab } from './BrowseTab';
import { BROWSE_PATH, BROWSE_LAST_SEARCH_KEY } from '@/lib/browse-search';
import type { ApiResponse, ModBrowseData } from '@/api/types';

// Mock useNavigate
const mockNavigate = vi.fn();
vi.mock('react-router', async () => {
  const actual = await vi.importActual('react-router');
  return {
    ...actual,
    useNavigate: () => mockNavigate,
  };
});

// Mock useMods (needed for install button feature in Story 10.8)
vi.mock('@/hooks/use-mods', async () => {
  const actual = await vi.importActual('@/hooks/use-mods');
  return {
    ...actual,
    useMods: vi.fn(() => ({
      data: { status: 'ok', data: { mods: [], pendingRestart: false } },
      isLoading: false,
      isError: false,
      error: null,
    })),
    useInstallMod: vi.fn(() => ({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      isSuccess: false,
      isIdle: true,
      data: undefined,
      variables: undefined,
      reset: vi.fn(),
      status: 'idle',
      mutateAsync: vi.fn(),
      context: undefined,
      failureCount: 0,
      failureReason: null,
      submittedAt: 0,
      isPaused: false,
    })),
  };
});

// VSS-vth: Mock useGameVersions for game version filter
vi.mock('@/hooks/use-game-versions', () => ({
  useGameVersions: vi.fn(() => ({
    data: {
      status: 'ok',
      data: { versions: ['1.21.3', '1.21.2', '1.21.1', '1.21.0'] },
    },
    isLoading: false,
    isError: false,
    error: null,
  })),
}));

// VSS-1u2: Mock useServerStatus for installed version
vi.mock('@/hooks/use-server-status', () => ({
  useServerStatus: vi.fn(() => ({
    data: {
      status: 'ok',
      data: { state: 'running', version: '1.21.3' },
    },
    isLoading: false,
    isError: false,
    error: null,
  })),
}));

// VSS-y7u: Mock useModTags for tags filter
vi.mock('@/hooks/use-mod-tags', () => ({
  useModTags: vi.fn(() => ({
    data: {
      status: 'ok',
      data: { tags: ['utility', 'qol', 'food', 'building'] },
    },
    isLoading: false,
    isError: false,
    error: null,
  })),
}));

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Story 16.1: Every location BrowseTab's router passes through, with how it got there
const locationLog: Array<{ search: string; navigationType: string }> = [];

function LocationProbe() {
  const location = useLocation();
  const navigationType = useNavigationType();
  useEffect(() => {
    locationLog.push({ search: location.search, navigationType });
  }, [location, navigationType]);
  return null;
}

/** Search string of the router's current location. */
function currentSearch(): string | undefined {
  return locationLog.at(-1)?.search;
}

// Wrapper component for rendering with QueryClientProvider and a router
// Story 16.1: BrowseTab reads and writes its state through the URL
function createWrapper(queryClient: QueryClient, initialEntry: string = BROWSE_PATH) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[initialEntry]}>
          {children}
          <LocationProbe />
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

/** URL of the n-th browse request (0-based). */
function browseRequestUrl(index = 0): URL {
  const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
  return new URL(String(calls[index][0]));
}

// Mock browse API response
const mockBrowseResponse: ApiResponse<ModBrowseData> = {
  status: 'ok',
  data: {
    mods: [
      {
        slug: 'carrycapacity',
        urlalias: 'carrycapacity',
        assetId: 12345,
        name: 'Carry Capacity',
        author: 'copygirl',
        summary: 'Allows picking up chests',
        downloads: 50000,
        follows: 500,
        trendingPoints: 100,
        side: 'both',
        modType: 'mod',
        logoUrl: null,
        tags: ['utility'],
        lastReleased: '2024-01-15T10:00:00Z',
      },
      {
        slug: 'primitivesurvival',
        urlalias: 'primitivesurvival',
        assetId: 23456,
        name: 'Primitive Survival',
        author: 'Spear and Fang',
        summary: 'Survival mechanics',
        downloads: 75000,
        follows: 800,
        trendingPoints: 200,
        side: 'both',
        modType: 'mod',
        logoUrl: null,
        tags: ['survival'],
        lastReleased: '2024-02-01T12:00:00Z',
      },
    ],
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

describe('BrowseTab', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    mockNavigate.mockClear();
    locationLog.length = 0;
    vi.useFakeTimers({ shouldAdvanceTime: true });
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  describe('AC1: Mods load immediately', () => {
    it('fetches and displays mods on mount', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      // Should show loading state initially
      expect(screen.getByTestId('mod-browse-grid-loading')).toBeInTheDocument();

      // Wait for data to load
      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Should display the mods
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-primitivesurvival')).toBeInTheDocument();
    });

    it('displays results count after loading', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('browse-results-count')).toBeInTheDocument();
      });

      expect(screen.getByText(/Showing 2 of 100 mods/)).toBeInTheDocument();
    });
  });

  describe('AC2: Search input', () => {
    it('renders search input with placeholder', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      const searchInput = screen.getByTestId('browse-search-input');
      expect(searchInput).toBeInTheDocument();
      // VSS-195: Updated placeholder to hint at slug/URL support
      expect(searchInput).toHaveAttribute(
        'placeholder',
        'Search mods or enter slug/URL and press Enter...'
      );
    });

    it('accepts user input', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry' } });
      });

      expect(searchInput).toHaveValue('carry');
    });
  });

  describe('AC3: Debounced search', () => {
    it('waits for debounce before making API request', async () => {
      // Search response returns filtered result (server-side filtering)
      const searchResponse: ApiResponse<ModBrowseData> = {
        status: 'ok',
        data: {
          mods: [mockBrowseResponse.data.mods[0]], // Just carrycapacity
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

      // Mock returns different responses based on whether search param is present
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const hasSearch = url.includes('search=');
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(hasSearch ? searchResponse : mockBrowseResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      // Type in search
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry' } });
      });

      // Before debounce completes, should still show both mods (old data)
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-primitivesurvival')).toBeInTheDocument();

      // Fast-forward past debounce (300ms)
      await act(async () => {
        vi.advanceTimersByTime(350);
      });

      // After debounce, API returns filtered results
      await waitFor(() => {
        expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
        expect(screen.queryByTestId('mod-card-primitivesurvival')).not.toBeInTheDocument();
      });
    });

    it('updates results count with search term', async () => {
      // Search response returns filtered result (server-side filtering)
      const searchResponse: ApiResponse<ModBrowseData> = {
        status: 'ok',
        data: {
          mods: [mockBrowseResponse.data.mods[0]], // Just carrycapacity
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

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const hasSearch = url.includes('search=');
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(hasSearch ? searchResponse : mockBrowseResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByText(/Found 1 mod matching "carry"/)).toBeInTheDocument();
      });
    });
  });

  describe('AC5: Clear search', () => {
    it('shows clear button when search has text', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      const searchInput = screen.getByTestId('browse-search-input');

      // Initially no clear button
      expect(screen.queryByTestId('browse-search-clear')).not.toBeInTheDocument();

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'test' } });
      });

      // Clear button appears
      expect(screen.getByTestId('browse-search-clear')).toBeInTheDocument();
    });

    it('clears search when clear button is clicked', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'test' } });
      });

      const clearButton = screen.getByTestId('browse-search-clear');

      await act(async () => {
        fireEvent.click(clearButton);
      });

      expect(searchInput).toHaveValue('');
      expect(screen.queryByTestId('browse-search-clear')).not.toBeInTheDocument();
    });

    it('clears search when Escape key is pressed', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'test' } });
      });

      expect(searchInput).toHaveValue('test');

      await act(async () => {
        fireEvent.keyDown(searchInput, { key: 'Escape' });
      });

      expect(searchInput).toHaveValue('');
    });

    it('returns to full results after clearing search', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      // Search for something
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.queryByTestId('mod-card-primitivesurvival')).not.toBeInTheDocument();
      });

      // Clear the search
      const clearButton = screen.getByTestId('browse-search-clear');
      await act(async () => {
        fireEvent.click(clearButton);
        vi.advanceTimersByTime(350);
      });

      // Should show all mods again
      await waitFor(() => {
        expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
        expect(screen.getByTestId('mod-card-primitivesurvival')).toBeInTheDocument();
      });
    });
  });

  describe('AC6: Error state', () => {
    it('displays error message when fetch fails', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.reject(new Error('Not JSON')),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-error')).toBeInTheDocument();
      });

      expect(screen.getByTestId('browse-error-message')).toHaveTextContent(
        'Failed to load mods:'
      );
    });

    it('displays retry button on error', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.reject(new Error('Not JSON')),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('browse-retry-button')).toBeInTheDocument();
      });

      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('refetches when retry button is clicked', async () => {
      let callCount = 0;
      globalThis.fetch = vi.fn().mockImplementation(() => {
        callCount++;
        if (callCount === 1) {
          return Promise.resolve({
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            json: () => Promise.reject(new Error('Not JSON')),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBrowseResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByTestId('browse-retry-button')).toBeInTheDocument();
      });

      // Click retry
      await act(async () => {
        fireEvent.click(screen.getByTestId('browse-retry-button'));
      });

      // Should now show successful content
      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });
    });
  });

  describe('AC7: Loading state', () => {
    it('shows loading skeleton while fetching', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      globalThis.fetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve(mockBrowseResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      // Should show loading state
      expect(screen.getByTestId('mod-browse-grid-loading')).toBeInTheDocument();

      // Resolve the fetch
      await act(async () => {
        resolvePromise!();
      });

      // Should show content
      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });
    });

    it('does not show results count while loading', () => {
      globalThis.fetch = vi.fn().mockImplementation(
        () => new Promise(() => { /* never resolves */ })
      );

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      expect(screen.queryByTestId('browse-results-count')).not.toBeInTheDocument();
    });
  });

  describe('search container', () => {
    it('renders the search container', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByTestId('browse-search-container')).toBeInTheDocument();
    });
  });

  describe('empty results', () => {
    it('shows empty state when search returns no results', async () => {
      // Empty response for no search results
      const emptySearchResponse: ApiResponse<ModBrowseData> = {
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

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const hasSearch = url.includes('search=');
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(hasSearch ? emptySearchResponse : mockBrowseResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      // Search for something that doesn't exist
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'xyznotexists123' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid-empty')).toBeInTheDocument();
      });
    });
  });

  describe('Story 10.4: Filter and Sort Integration', () => {
    it('renders filter controls', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText(/side/i)).toBeInTheDocument();
      });

      expect(screen.getByText(/tags/i)).toBeInTheDocument();
      expect(screen.getByText(/type/i)).toBeInTheDocument();
      // VSS-vth: Version filter is now enabled
      expect(screen.getByText(/version/i)).toBeInTheDocument();
    });

    it('renders sort control', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Sort by:')).toBeInTheDocument();
      });

      expect(screen.getByRole('button', { name: /newest/i })).toBeInTheDocument();
    });

    it('combines search and filters correctly', async () => {
      // Search response returns filtered result (server-side filtering)
      const searchResponse: ApiResponse<ModBrowseData> = {
        status: 'ok',
        data: {
          mods: [mockBrowseResponse.data.mods[0]], // Just carrycapacity
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

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const hasSearch = url.includes('search=');
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(hasSearch ? searchResponse : mockBrowseResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Both mods should be visible initially
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-primitivesurvival')).toBeInTheDocument();

      // Apply search
      const searchInput = screen.getByTestId('browse-search-input');
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry' } });
        vi.advanceTimersByTime(350);
      });

      // Only carrycapacity should be visible (from server-side filtered results)
      await waitFor(() => {
        expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
        expect(screen.queryByTestId('mod-card-primitivesurvival')).not.toBeInTheDocument();
      });
    });
  });

  describe('Story 16.1: browse state in the URL', () => {
    const multiPageResponse = (page: number) => ({
      status: 'ok' as const,
      data: {
        mods: mockBrowseResponse.data.mods,
        pagination: {
          page,
          pageSize: 20,
          totalItems: 100,
          totalPages: 5,
          hasNext: page < 5,
          hasPrev: page > 1,
        },
      },
    });

    function mockFetchPage(page = 1) {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(multiPageResponse(page)),
      });
    }

    beforeEach(() => {
      window.sessionStorage.removeItem(BROWSE_LAST_SEARCH_KEY);
    });

    it('loads search, sort, every filter including the game version, and page from the URL', async () => {
      mockFetchPage(2);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(
          queryClient,
          `${BROWSE_PATH}?q=food&sort=downloads&side=server&tags=qol,food&type=mod&version=1.21.2&page=2`
        ),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const request = browseRequestUrl();
      expect(request.searchParams.get('search')).toBe('food');
      expect(request.searchParams.get('sort')).toBe('downloads');
      expect(request.searchParams.get('side')).toBe('server');
      expect(request.searchParams.get('tags')).toBe('qol,food');
      expect(request.searchParams.get('mod_type')).toBe('mod');
      expect(request.searchParams.get('version')).toBe('1.21.2');
      expect(request.searchParams.get('page')).toBe('2');

      // The controls show the same state
      expect(screen.getByTestId('browse-search-input')).toHaveValue('food');
      expect(screen.getByTestId('version-filter-button')).toHaveTextContent('v1.21.2');
      expect(screen.getByRole('button', { name: /most downloaded/i })).toBeInTheDocument();
      expect(screen.getByLabelText('Remove version filter: 1.21.2')).toBeInTheDocument();
      expect(screen.getByText(/Page 2 of 5/)).toBeInTheDocument();
    });

    it('uses the default state for /game-server/mods/browse without parameters', async () => {
      mockFetchPage(1);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(globalThis.fetch).toHaveBeenCalled();
      });

      const request = browseRequestUrl();
      expect(request.searchParams.get('page')).toBe('1');
      expect(request.searchParams.get('sort')).toBe('recent');
      for (const name of ['search', 'side', 'tags', 'mod_type', 'version']) {
        expect(request.searchParams.has(name)).toBe(false);
      }
      expect(screen.getByTestId('browse-search-input')).toHaveValue('');
    });

    it('falls back to defaults for invalid URL values', async () => {
      mockFetchPage(1);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?sort=bogus&side=nowhere&type=x&page=abc`),
      });

      await waitFor(() => {
        expect(globalThis.fetch).toHaveBeenCalled();
      });

      const request = browseRequestUrl();
      expect(request.searchParams.get('sort')).toBe('recent');
      expect(request.searchParams.get('page')).toBe('1');
      expect(request.searchParams.has('side')).toBe(false);
      expect(request.searchParams.has('mod_type')).toBe(false);
    });

    it('writes the debounced search with replace, one entry, and removes the page', async () => {
      mockFetchPage(3);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?version=1.21.2&page=3`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'c' } });
        vi.advanceTimersByTime(100);
        fireEvent.change(searchInput, { target: { value: 'ca' } });
        vi.advanceTimersByTime(100);
        fireEvent.change(searchInput, { target: { value: 'carry ' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(currentSearch()).toBe('?q=carry&version=1.21.2');
      });
      expect(locationLog.at(-1)?.navigationType).toBe('REPLACE');
      // No entry per keystroke
      expect(locationLog.map((entry) => entry.search)).toEqual([
        '?version=1.21.2&page=3',
        '?q=carry&version=1.21.2',
      ]);
    });

    it('pushes a filter change and goes back to page 1', async () => {
      mockFetchPage(3);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?q=food&side=server&version=1.21.2&page=3`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByLabelText('Remove version filter: 1.21.2'));
      });

      expect(currentSearch()).toBe('?q=food&side=server');
      expect(locationLog.at(-1)?.navigationType).toBe('PUSH');
    });

    it('pushes a sort change, keeps the game version filter, and goes back to page 1', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      mockFetchPage(3);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?version=1.21.2&page=3`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /newest/i }));
      await user.click(await screen.findByRole('menuitem', { name: /trending/i }));

      expect(currentSearch()).toBe('?sort=trending&version=1.21.2');
      expect(locationLog.at(-1)?.navigationType).toBe('PUSH');
      await waitFor(() => {
        const lastCall = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls.length - 1;
        const request = browseRequestUrl(lastCall);
        expect(request.searchParams.get('sort')).toBe('trending');
        expect(request.searchParams.get('version')).toBe('1.21.2');
        expect(request.searchParams.get('page')).toBe('1');
      });
    });

    it('pushes a page change into the URL', async () => {
      mockFetchPage(1);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?version=1.21.2`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('pagination')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByRole('button', { name: /next/i }));
      });

      expect(currentSearch()).toBe('?version=1.21.2&page=2');
      expect(locationLog.at(-1)?.navigationType).toBe('PUSH');
    });

    it('does not add an entry when a control is set to its current value', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      mockFetchPage(1);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?sort=trending`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('button', { name: /trending/i }));
      await user.click(await screen.findByRole('menuitem', { name: /trending/i }));

      expect(locationLog).toHaveLength(1);
    });

    it('follows the URL when browser back and forward change it', async () => {
      mockFetchPage(1);
      const queryClient = createTestQueryClient();
      const router = createMemoryRouter(
        [{ path: BROWSE_PATH, element: <><BrowseTab /><LocationProbe /></> }],
        { initialEntries: [`${BROWSE_PATH}?q=food&version=1.21.2`, `${BROWSE_PATH}?q=carry&version=1.21.3`] }
      );
      render(
        <QueryClientProvider client={queryClient}>
          <RouterProvider router={router} />
        </QueryClientProvider>
      );

      await waitFor(() => {
        expect(screen.getByTestId('browse-search-input')).toHaveValue('carry');
      });

      await act(async () => {
        await router.navigate(-1);
      });
      expect(screen.getByTestId('browse-search-input')).toHaveValue('food');
      expect(screen.getByTestId('version-filter-button')).toHaveTextContent('v1.21.2');

      // The old debounced text must not be written back over the restored search
      await act(async () => {
        vi.advanceTimersByTime(400);
      });
      expect(router.state.location.search).toBe('?q=food&version=1.21.2');
      await waitFor(() => {
        const calls = (globalThis.fetch as ReturnType<typeof vi.fn>).mock.calls;
        const request = new URL(String(calls[calls.length - 1][0]));
        expect(request.searchParams.get('search')).toBe('food');
        expect(request.searchParams.get('version')).toBe('1.21.2');
      });

      await act(async () => {
        await router.navigate(1);
      });
      expect(screen.getByTestId('browse-search-input')).toHaveValue('carry');
      expect(screen.getByTestId('version-filter-button')).toHaveTextContent('v1.21.3');
    });

    it('remembers the browse search, including the game version, in sessionStorage', async () => {
      mockFetchPage(1);
      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?version=1.21.2`),
      });

      await waitFor(() => {
        expect(window.sessionStorage.getItem(BROWSE_LAST_SEARCH_KEY)).toBe('?version=1.21.2');
      });

      await act(async () => {
        fireEvent.change(screen.getByTestId('browse-search-input'), { target: { value: 'carry' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(window.sessionStorage.getItem(BROWSE_LAST_SEARCH_KEY)).toBe('?q=carry&version=1.21.2');
      });
    });
  });

  describe('Story 10.7: Pagination Integration', () => {
    it('renders pagination controls when results span multiple pages', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('pagination')).toBeInTheDocument();
      });

      // Should show page info
      expect(screen.getByText(/Page 1 of 5/)).toBeInTheDocument();
    });

    it('does not render pagination for single page results', async () => {
      const singlePageResponse = {
        status: 'ok' as const,
        data: {
          mods: mockBrowseResponse.data.mods,
          pagination: {
            page: 1,
            pageSize: 20,
            totalItems: 2,
            totalPages: 1,
            hasNext: false,
            hasPrev: false,
          },
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(singlePageResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Should NOT show pagination
      expect(screen.queryByTestId('pagination')).not.toBeInTheDocument();
    });

    it('changes page when clicking next button', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });

      const page1Response = {
        status: 'ok' as const,
        data: {
          mods: mockBrowseResponse.data.mods,
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
          mods: [
            {
              ...mockBrowseResponse.data.mods[0],
              slug: 'page2mod',
              name: 'Page 2 Mod',
            },
          ],
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

      globalThis.fetch = vi
        .fn()
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(page1Response),
        })
        .mockResolvedValueOnce({
          ok: true,
          json: () => Promise.resolve(page2Response),
        });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('pagination')).toBeInTheDocument();
      });

      // Click next page
      const nextButton = screen.getByRole('button', { name: /next/i });
      await user.click(nextButton);

      await waitFor(() => {
        expect(screen.getByText(/Page 2 of 5/)).toBeInTheDocument();
      });
    });

    it('resets to page 1 when search changes', async () => {
      // Start on page 2
      const page2Response = {
        status: 'ok' as const,
        data: {
          mods: mockBrowseResponse.data.mods,
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

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(page2Response),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?page=2`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      // Type in search - should reset page to 1
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry' } });
        vi.advanceTimersByTime(350);
      });

      // Story 16.1: page 1 is the default, so the page leaves the URL
      await waitFor(() => {
        expect(currentSearch()).toBe('?q=carry');
      });
    });

    // VSS-vth: Test page reset when the version filter changes
    // Story 16.1: The reset is part of the URL write; sort changes are covered in
    // "Story 16.1: browse state in the URL".
    it('resets to page 1 when the version filter changes', async () => {
      // Start on page 2
      const page2Response = {
        status: 'ok' as const,
        data: {
          mods: mockBrowseResponse.data.mods,
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

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(page2Response),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?version=1.21.3`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Navigate to page 2 using fireEvent (works better with fake timers)
      const nextButton = screen.getByRole('button', { name: /next/i });
      await act(async () => {
        fireEvent.click(nextButton);
      });
      expect(currentSearch()).toBe('?version=1.21.3&page=2');

      // Removing the version filter goes back to page 1
      await act(async () => {
        fireEvent.click(screen.getByLabelText('Remove version filter: 1.21.3'));
      });
      expect(currentSearch()).toBe('');
    });
  });

  describe('Story 10.7: Scroll Position Restoration (AC3)', () => {
    // Mock sessionStorage
    const mockSessionStorage = {
      store: {} as Record<string, string>,
      getItem: vi.fn((key: string) => mockSessionStorage.store[key] ?? null),
      setItem: vi.fn((key: string, value: string) => {
        mockSessionStorage.store[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete mockSessionStorage.store[key];
      }),
    };

    beforeEach(() => {
      mockSessionStorage.store = {};
      Object.defineProperty(window, 'sessionStorage', {
        value: mockSessionStorage,
        writable: true,
      });
      Object.defineProperty(window, 'scrollY', {
        value: 500,
        configurable: true,
      });
      window.scrollTo = vi.fn();
    });

    it('saves scroll position when clicking a mod card', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Click on a mod card
      const card = screen.getByTestId('mod-card-carrycapacity');
      await user.click(card);

      // Should have saved position to sessionStorage
      expect(mockSessionStorage.setItem).toHaveBeenCalledWith(
        'browse-scroll-position',
        expect.any(String)
      );
    });

    // Story 16.1: The page is part of the browse URL, which every way back restores
    it('restores the page from the browse URL on return', async () => {

      const page3Response = {
        status: 'ok' as const,
        data: {
          mods: mockBrowseResponse.data.mods,
          pagination: {
            page: 3,
            pageSize: 20,
            totalItems: 100,
            totalPages: 5,
            hasNext: true,
            hasPrev: true,
          },
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(page3Response),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, {
        wrapper: createWrapper(queryClient, `${BROWSE_PATH}?version=1.21.2&page=3`),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText(/Page 3 of 5/)).toBeInTheDocument();
      });
      expect(browseRequestUrl().searchParams.get('page')).toBe('3');
      expect(browseRequestUrl().searchParams.get('version')).toBe('1.21.2');
    });

    it('clears saved position when search changes', async () => {
      mockSessionStorage.store['browse-scroll-position'] = JSON.stringify({
        scrollY: 500,
        page: 2,
      });

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      // Type in search
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'test' } });
        vi.advanceTimersByTime(350);
      });

      // Should have cleared saved position
      expect(mockSessionStorage.removeItem).toHaveBeenCalledWith(
        'browse-scroll-position'
      );
    });
  });

  describe('Story 10.5: Card Navigation (AC 3)', () => {
    it('navigates to mod detail when card is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Click on a mod card
      const card = screen.getByTestId('mod-card-carrycapacity');
      await user.click(card);

      expect(mockNavigate).toHaveBeenCalledWith('/game-server/mods/browse/carrycapacity');
    });

    it('navigates to correct mod when different card is clicked', async () => {
      const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime });
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Click on second mod card
      const card = screen.getByTestId('mod-card-primitivesurvival');
      await user.click(card);

      expect(mockNavigate).toHaveBeenCalledWith('/game-server/mods/browse/primitivesurvival');
    });

    it('mod cards are clickable (have cursor-pointer)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const card = screen.getByTestId('mod-card-carrycapacity');
      expect(card.className).toContain('cursor-pointer');
    });
  });

  describe('VSS-195: Slug/URL Direct Navigation', () => {
    it('navigates to mod detail when pressing Enter with a slug', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'smithingplus' } });
      });

      await act(async () => {
        fireEvent.keyDown(searchInput, { key: 'Enter' });
      });

      expect(mockNavigate).toHaveBeenCalledWith('/game-server/mods/browse/smithingplus');
    });

    it('navigates to mod detail when pressing Enter with a URL', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, {
          target: { value: 'https://mods.vintagestory.at/carrycapacity' },
        });
      });

      await act(async () => {
        fireEvent.keyDown(searchInput, { key: 'Enter' });
      });

      expect(mockNavigate).toHaveBeenCalledWith('/game-server/mods/browse/carrycapacity');
    });

    it('does not navigate when pressing Enter with a multi-word search', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry capacity mod' } });
      });

      await act(async () => {
        fireEvent.keyDown(searchInput, { key: 'Enter' });
      });

      // Should not navigate - it's a search query, not a slug
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('does not navigate when pressing Enter with empty search', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.keyDown(searchInput, { key: 'Enter' });
      });

      // Should not navigate with empty input
      expect(mockNavigate).not.toHaveBeenCalled();
    });

    it('lowercases the slug before navigation', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
      });

      const queryClient = createTestQueryClient();
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'SmithingPlus' } });
      });

      await act(async () => {
        fireEvent.keyDown(searchInput, { key: 'Enter' });
      });

      // Should lowercase the slug
      expect(mockNavigate).toHaveBeenCalledWith('/game-server/mods/browse/smithingplus');
    });
  });
});
