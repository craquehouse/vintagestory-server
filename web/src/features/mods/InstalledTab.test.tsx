/**
 * InstalledTab component tests.
 *
 * Story 10.2: Mods Tab Restructure - AC2
 * VSS-195: Removed ModLookupInput - mod discovery moved to BrowseTab.
 *
 * Tests the Installed tab which displays and manages installed mods.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
  },
}));

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

// Mock useModsCompatibility to avoid complex fetch handling
vi.mock('@/hooks/use-mods', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/use-mods')>();
  return {
    ...actual,
    useModsCompatibility: () => ({
      compatibilityMap: new Map(),
      sideMap: new Map(),
      isLoading: false,
    }),
  };
});

import { InstalledTab } from './InstalledTab';
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import { toast } from 'sonner';

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

const mockServerRunningResponse = {
  status: 'ok',
  data: {
    state: 'running',
  },
};

describe('InstalledTab', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
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

  describe('toast notifications', () => {
    it('shows success toast when mod is disabled (server stopped)', async () => {
      const disableFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              filename: 'smithingplus-1.5.0.zip',
              slug: 'smithingplus',
              version: '1.5.0',
              enabled: false,
            },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/disable')) {
          return disableFetch();
        }
        if (url.includes('/status')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockServerStatusResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-toggle-smithingplus')).toBeInTheDocument();
      });

      // Click toggle to disable the mod
      fireEvent.click(screen.getByTestId('mod-toggle-smithingplus'));

      await waitFor(() => {
        expect(disableFetch).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('smithingplus disabled', {
          description: undefined,
        });
      });
    });

    it('shows success toast with restart message when mod is enabled (server running)', async () => {
      const enableFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              filename: 'smithingplus-1.5.0.zip',
              slug: 'smithingplus',
              version: '1.5.0',
              enabled: true,
            },
          }),
      });

      const modsWithDisabled = {
        status: 'ok',
        data: {
          mods: [
            {
              filename: 'smithingplus-1.5.0.zip',
              slug: 'smithingplus',
              version: '1.5.0',
              enabled: false,
              installedAt: '2024-01-15T10:30:00Z',
              name: 'Smithing Plus',
              authors: ['TestAuthor'],
              description: 'Enhanced smithing features',
            },
          ],
          pendingRestart: false,
        },
      };

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/enable')) {
          return enableFetch();
        }
        if (url.includes('/status')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockServerRunningResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(modsWithDisabled),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-toggle-smithingplus')).toBeInTheDocument();
      });

      // Click toggle to enable the mod
      fireEvent.click(screen.getByTestId('mod-toggle-smithingplus'));

      await waitFor(() => {
        expect(enableFetch).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('smithingplus enabled', {
          description: 'A server restart is required for changes to take effect.',
        });
      });
    });

    it('shows success toast when mod is removed (server stopped)', async () => {
      const removeFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Mod removed successfully' },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
        if (options?.method === 'DELETE') {
          return removeFetch();
        }
        if (url.includes('/status')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockServerStatusResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-remove-smithingplus')).toBeInTheDocument();
      });

      // Click remove button
      fireEvent.click(screen.getByTestId('mod-remove-smithingplus'));

      // Confirm removal in dialog
      await waitFor(() => {
        expect(screen.getByTestId('remove-dialog')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('remove-dialog-confirm'));

      await waitFor(() => {
        expect(removeFetch).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Removed smithingplus', {
          description: undefined,
        });
      });
    });

    it('shows success toast with restart message when mod is removed (server running)', async () => {
      const removeFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Mod removed successfully' },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options?: RequestInit) => {
        if (options?.method === 'DELETE') {
          return removeFetch();
        }
        if (url.includes('/status')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockServerRunningResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsResponse),
        });
      });

      const queryClient = createTestQueryClient();
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-remove-smithingplus')).toBeInTheDocument();
      });

      // Click remove button
      fireEvent.click(screen.getByTestId('mod-remove-smithingplus'));

      // Confirm removal in dialog
      await waitFor(() => {
        expect(screen.getByTestId('remove-dialog')).toBeInTheDocument();
      });

      fireEvent.click(screen.getByTestId('remove-dialog-confirm'));

      await waitFor(() => {
        expect(removeFetch).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Removed smithingplus', {
          description: 'A server restart may be required for changes to take effect.',
        });
      });
    });
  });
});
