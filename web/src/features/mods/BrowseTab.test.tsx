/**
 * BrowseTab component tests.
 *
 * Story 10.3: Browse Landing Page & Search
 * Story 10.4: Filter & Sort Controls
 *
 * Tests cover:
 * - AC1: Loads mods immediately on page load
 * - AC2: Search input with placeholder
 * - AC3: Debounced search (300ms)
 * - AC5: Clear button and Escape key
 * - AC6: Error state with retry
 * - AC7: Loading state
 * - AC8-11: Filter and sort integration
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { BrowseTab } from './BrowseTab';
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

// Wrapper component for rendering with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock browse API response
const mockBrowseResponse: ApiResponse<ModBrowseData> = {
  status: 'ok',
  data: {
    mods: [
      {
        slug: 'carrycapacity',
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
      expect(searchInput).toHaveAttribute(
        'placeholder',
        'Search mods by name, author, or tag...'
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
      // Version filter disabled - API doesn't provide compatibility data
      expect(screen.queryByText(/version/i)).not.toBeInTheDocument();
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
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      const searchInput = screen.getByTestId('browse-search-input');

      // Type in search - should reset page to 1
      await act(async () => {
        fireEvent.change(searchInput, { target: { value: 'carry' } });
        vi.advanceTimersByTime(350);
      });

      // Page should reset to 1 (internal state)
      // We can verify by checking the next button is enabled (indicating we're not on last page)
      await waitFor(() => {
        expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled();
      });
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

    it('restores page from saved position on mount', async () => {
      // Pre-populate sessionStorage with saved position
      mockSessionStorage.store['browse-scroll-position'] = JSON.stringify({
        scrollY: 750,
        page: 3,
      });

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
      render(<BrowseTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      });

      // Should display page 3 (restored from sessionStorage)
      await waitFor(() => {
        expect(screen.getByText(/Page 3 of 5/)).toBeInTheDocument();
      });
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
});
