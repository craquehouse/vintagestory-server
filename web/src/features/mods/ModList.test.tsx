import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { ModList } from './ModList';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
      mutations: {
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

// Mock mods list response
const mockModsResponse = {
  status: 'ok',
  data: {
    mods: [
      {
        filename: 'smithingplus-1.5.0.zip',
        slug: 'smithingplus',
        version: '1.5.0',
        enabled: true,
        installedAt: '2024-01-15T10:30:00Z',
        name: 'Smithing Plus',
        authors: ['TestAuthor'],
        description: 'Enhanced smithing features',
      },
    ],
    pendingRestart: false,
  },
};

const mockEmptyModsResponse = {
  status: 'ok',
  data: {
    mods: [],
    pendingRestart: false,
  },
};

describe('ModList', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('page structure (AC: 1)', () => {
    it('renders page with heading', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockEmptyModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModList />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByTestId('mod-list-page')).toBeInTheDocument();
      expect(screen.getByText('Mods')).toBeInTheDocument();
      expect(
        screen.getByText('Search, install, and manage server mods')
      ).toBeInTheDocument();
    });

    it('renders ModLookupInput component', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockEmptyModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModList />, { wrapper: createWrapper(queryClient) });

      expect(
        screen.getByPlaceholderText('Enter mod slug or paste URL')
      ).toBeInTheDocument();
    });

    it('renders Installed Mods section heading', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockEmptyModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModList />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByText('Installed Mods')).toBeInTheDocument();
    });
  });

  describe('mods table integration', () => {
    it('displays installed mods in table', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModList />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Smithing Plus')).toBeInTheDocument();
      });
    });

    it('shows empty state when no mods installed', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockEmptyModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModList />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('No mods installed yet')).toBeInTheDocument();
      });
    });
  });

  describe('loading states', () => {
    it('shows loading state while fetching mods', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      globalThis.fetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve(mockEmptyModsResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ModList />, { wrapper: createWrapper(queryClient) });

      // Table should show loading
      expect(screen.getByTestId('mod-table-loading')).toBeInTheDocument();

      // Resolve fetch
      resolvePromise!();

      await waitFor(() => {
        expect(screen.queryByTestId('mod-table-loading')).not.toBeInTheDocument();
      });
    });
  });
});
