/**
 * BrowseTab component tests.
 *
 * Story 10.3: Browse Landing Page & Search
 *
 * Tests cover:
 * - AC1: Loads mods immediately on page load
 * - AC2: Search input with placeholder
 * - AC3: Debounced search (300ms)
 * - AC5: Clear button and Escape key
 * - AC6: Error state with retry
 * - AC7: Loading state
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { BrowseTab } from './BrowseTab';
import type { ApiResponse, ModBrowseData } from '@/api/types';

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
    it('waits for debounce before filtering', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockBrowseResponse),
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

      // Before debounce completes, should still show both mods
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-primitivesurvival')).toBeInTheDocument();

      // Fast-forward past debounce (300ms)
      await act(async () => {
        vi.advanceTimersByTime(350);
      });

      // After debounce, should filter to only matching mod
      await waitFor(() => {
        expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
        expect(screen.queryByTestId('mod-card-primitivesurvival')).not.toBeInTheDocument();
      });
    });

    it('updates results count with search term', async () => {
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
});
