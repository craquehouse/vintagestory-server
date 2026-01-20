/**
 * InstalledTab component tests.
 *
 * Story 10.2: Mods Tab Restructure - AC2
 * VSS-195: Removed ModLookupInput - mod discovery moved to BrowseTab.
 *
 * Tests the Installed tab which displays and manages installed mods.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

// Mock next-themes before importing components that use PreferencesContext
vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'dark',
    setTheme: vi.fn(),
    resolvedTheme: 'dark',
    systemTheme: 'dark',
  }),
}));

// Mock cookies
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn(() => null),
  setCookie: vi.fn(),
}));

import { InstalledTab } from './InstalledTab';
import { PreferencesProvider } from '@/contexts/PreferencesContext';

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

// Wrapper component for rendering with QueryClientProvider and PreferencesProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <PreferencesProvider>{children}</PreferencesProvider>
      </QueryClientProvider>
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

const mockServerStatusResponse = {
  status: 'ok',
  data: {
    state: 'stopped',
  },
};

describe('InstalledTab', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('AC2: Installed tab contains mod management UI', () => {
    it('renders the tab container', async () => {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/mods')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyModsResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
    });

    // VSS-195: ModLookupInput removed - mod discovery moved to BrowseTab
    it('does not render ModLookupInput', async () => {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/mods')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyModsResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      // Verify ModLookupInput is NOT present
      expect(
        screen.queryByPlaceholderText('Enter mod slug or paste URL')
      ).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-search-input')).not.toBeInTheDocument();
    });

    it('renders Installed Mods section heading', async () => {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/mods')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyModsResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByText('Installed Mods')).toBeInTheDocument();
    });

    it('displays installed mods in table', async () => {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/mods')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockModsResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Smithing Plus')).toBeInTheDocument();
      });
    });

    it('shows empty state when no mods installed', async () => {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/mods')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockEmptyModsResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

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

      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/mods')) {
          await pendingPromise;
          return {
            ok: true,
            json: () => Promise.resolve(mockEmptyModsResponse),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

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
