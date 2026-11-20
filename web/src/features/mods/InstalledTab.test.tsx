/**
 * InstalledTab component tests.
 *
 * Story 10.2: Mods Tab Restructure - AC2
 * VSS-195: Removed ModLookupInput - mod discovery moved to BrowseTab.
 *
 * Tests the Installed tab which displays and manages installed mods.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { MemoryRouter, useLocation, useNavigate } from 'react-router';
import userEvent from '@testing-library/user-event';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
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

// Mock useModsCompatibility to avoid complex fetch handling; Story 24.7's filter tests
// set statuses in `compat.map` (a mod not in it is still loading)
const compat = vi.hoisted(() => ({ map: new Map<string, string>() }));
vi.mock('@/hooks/use-mods', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/hooks/use-mods')>();
  return {
    ...actual,
    useModsCompatibility: () => ({
      compatibilityMap: compat.map,
      compatibilityDetails: new Map(),
      sideMap: new Map(),
      isLoading: false,
    }),
  };
});

import { InstalledTab } from './InstalledTab';
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import { toast } from 'sonner';
import { queryKeys } from '@/api/query-keys';
import { setViewportWidth } from '../../../tests/viewport';

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
function createWrapper(queryClient: QueryClient, initialEntry = '/game-server/mods/installed') {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialEntry]}>
        <QueryClientProvider client={queryClient}>
          <PreferencesProvider>{children}</PreferencesProvider>
        </QueryClientProvider>
      </MemoryRouter>
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
      expect(screen.queryByPlaceholderText('Enter mod slug or paste URL')).not.toBeInTheDocument();
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

  describe('Check for updates (Story 14.3)', () => {
    const updates = (checkedAt: string | null) => ({
      game_version: '1.22.7',
      checked_at: checkedAt,
      update_count: 1,
      mods: [],
    });

    function mockApi(check: () => Promise<unknown>) {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/mods/updates/check')) return check();
        const body = url.includes('/mods/updates')
          ? { status: 'ok', data: updates('2026-11-09T12:00:00Z') }
          : url.includes('/mods')
            ? mockModsResponse
            : mockServerStatusResponse;
        return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
      });
      globalThis.fetch = mockFetch;
      return mockFetch;
    }

    it('shows when the last full check finished', async () => {
      mockApi(() => Promise.reject(new Error('unused')));

      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });

      const expected = `Last checked ${new Date('2026-11-09T12:00:00Z').toLocaleString()}`;
      await waitFor(() => {
        expect(screen.getByTestId('mod-updates-last-checked')).toHaveTextContent(expected);
      });
    });

    it('shows Not checked yet before any check', async () => {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const body = url.includes('/mods/updates')
          ? { status: 'ok', data: updates(null) }
          : url.includes('/mods')
            ? mockModsResponse
            : mockServerStatusResponse;
        return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
      });

      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-updates-last-checked')).toHaveTextContent('Not checked yet');
      });
    });

    it('runs a check and reports the result', async () => {
      const mockFetch = mockApi(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: {
                ...updates('2026-11-09T12:00:00Z'),
                check: { checked: 3, failed: 0, failed_slugs: [] },
              },
            }),
        })
      );

      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });
      fireEvent.click(screen.getByTestId('mod-updates-check'));

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Checked 3 mods', {
          description: '1 update available.',
        });
      });
      const checkCall = mockFetch.mock.calls.find(([url]) =>
        String(url).includes('/mods/updates/check')
      );
      expect(checkCall?.[1].method).toBe('POST');
    });

    it('warns when some mods could not be checked', async () => {
      mockApi(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: {
                ...updates(null),
                check: { checked: 3, failed: 1, failed_slugs: ['carryon'] },
              },
            }),
        })
      );

      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });
      fireEvent.click(screen.getByTestId('mod-updates-check'));

      await waitFor(() => {
        expect(toast.warning).toHaveBeenCalledWith('Checked 3 mods; 1 could not be checked', {
          description: 'carryon. 1 update available.',
        });
      });
    });

    it('shows an error toast when a check is already running', async () => {
      mockApi(() =>
        Promise.resolve({
          ok: false,
          status: 409,
          statusText: 'Conflict',
          json: () =>
            Promise.resolve({
              detail: {
                code: 'MOD_UPDATE_CHECK_IN_PROGRESS',
                message: 'An update check is already running',
              },
            }),
        })
      );

      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });
      fireEvent.click(screen.getByTestId('mod-updates-check'));

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Update check failed', {
          description: 'An update check is already running',
        });
      });
    });
  });

  describe('Update all (Story 14.4)', () => {
    function offer(slug: string, compatibility: string) {
      return {
        slug,
        name: slug,
        installed_version: '1.0.0',
        status: 'update_available',
        offered_version: '1.1.0',
        offered_compatibility: compatibility,
        offered_prerelease: false,
        reason: null,
        checked_at: null,
        error: null,
      };
    }

    function mockUpdates(mods: unknown[]) {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const body = url.includes('/mods/updates')
          ? {
              status: 'ok',
              data: { game_version: '1.22.7', checked_at: null, update_count: 1, mods },
            }
          : url.includes('/mods')
            ? mockModsResponse
            : mockServerStatusResponse;
        return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
      });
    }

    it('offers Update all with the number of compatible updates', async () => {
      mockUpdates([offer('a', 'compatible'), offer('b', 'not_verified'), offer('c', 'compatible')]);

      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });

      const button = await screen.findByTestId('mod-updates-update-all');
      expect(button).toHaveTextContent('Update all (2)');
      fireEvent.click(button);
      expect(await screen.findByTestId('update-all-dialog')).toBeInTheDocument();
    });

    it('hides Update all when no update is compatible', async () => {
      mockUpdates([offer('smithingplus', 'not_verified')]);

      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });

      // The row's Update action proves the update status has loaded
      await screen.findByTestId('mod-update-button-smithingplus');
      expect(screen.queryByTestId('mod-updates-update-all')).not.toBeInTheDocument();
    });
  });

  describe('toolbar on phones (Story 16.5)', () => {
    function mockOffer() {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const body = url.includes('/mods/updates')
          ? {
              status: 'ok',
              data: {
                game_version: '1.22.7',
                checked_at: '2026-11-09T00:00:00Z',
                update_count: 1,
                mods: [
                  {
                    slug: 'smithingplus',
                    name: 'Smithing Plus',
                    installed_version: '1.5.0',
                    status: 'update_available',
                    offered_version: '1.6.0',
                    offered_compatibility: 'compatible',
                    offered_prerelease: false,
                    reason: null,
                    checked_at: null,
                    error: null,
                  },
                ],
              },
            }
          : url.includes('/mods')
            ? mockModsResponse
            : mockServerStatusResponse;
        return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
      });
    }

    it('wraps the last-checked text and buttons instead of widening the page', async () => {
      mockOffer();
      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });

      const updateAll = await screen.findByTestId('mod-updates-update-all');
      const group = updateAll.parentElement!;
      expect(group).toHaveClass('flex-wrap');
      expect(group).toContainElement(screen.getByTestId('mod-updates-check'));
      expect(group).toContainElement(screen.getByTestId('mod-updates-last-checked'));
    });

    // Story 17.8: the cards, and with them the 44px targets, go up to lg
    it('makes Update all and Check for updates 44px tall below lg', async () => {
      mockOffer();
      render(<InstalledTab />, { wrapper: createWrapper(createTestQueryClient()) });

      expect(await screen.findByTestId('mod-updates-update-all')).toHaveClass('max-lg:h-11');
      expect(screen.getByTestId('mod-updates-check')).toHaveClass('max-lg:h-11');
    });
  });

  describe('Rescan (Story 24.6)', () => {
    function rescanFetch(rescan: () => Promise<Partial<Response>>) {
      return vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        if (url.includes('/mods/rescan') && init?.method === 'POST') {
          return rescan();
        }
        if (url.includes('/mods/unused-files')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: { files: [] } }),
          });
        }
        if (url.includes('/mods')) {
          return Promise.resolve({ ok: true, json: () => Promise.resolve(mockEmptyModsResponse) });
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        });
      });
    }

    function renderAs(role: string) {
      const queryClient = createTestQueryClient();
      queryClient.setQueryData(queryKeys.auth.me, { status: 'ok', data: { role } });
      render(<InstalledTab />, { wrapper: createWrapper(queryClient) });
    }

    it('rescans and reports what changed', async () => {
      const fetchMock = rescanFetch(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: { added: 2, removed: 1, skipped: 0, pending_restart: false },
            }),
        })
      );
      globalThis.fetch = fetchMock;
      renderAs('admin');

      fireEvent.click(await screen.findByTestId('mods-rescan'));

      await waitFor(() =>
        expect(toast.success).toHaveBeenCalledWith('Rescanned the mods folder', {
          description: '2 added, 1 removed, 0 skipped.',
        })
      );
      expect(
        fetchMock.mock.calls.filter(([url]) => String(url).includes('/mods/rescan'))
      ).toHaveLength(1);
    });

    it('says a restart is needed when the server runs', async () => {
      globalThis.fetch = rescanFetch(() =>
        Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: { added: 1, removed: 0, skipped: 0, pending_restart: true },
            }),
        })
      );
      renderAs('admin');

      fireEvent.click(await screen.findByTestId('mods-rescan'));

      await waitFor(() =>
        expect(toast.success).toHaveBeenCalledWith('Rescanned the mods folder', {
          description:
            '1 added, 0 removed, 0 skipped. A server restart is required for the changes to take effect.',
        })
      );
    });

    it('reports a refused rescan', async () => {
      globalThis.fetch = rescanFetch(() =>
        Promise.resolve({
          ok: false,
          status: 409,
          statusText: 'Conflict',
          json: () =>
            Promise.resolve({
              detail: { code: 'MODS_BUSY', message: 'A mod install is running.' },
            }),
        })
      );
      renderAs('admin');

      fireEvent.click(await screen.findByTestId('mods-rescan'));

      await waitFor(() =>
        expect(toast.error).toHaveBeenCalledWith('Rescan failed', {
          description: 'A mod install is running.',
        })
      );
    });

    it('is not shown to a Monitor key', async () => {
      globalThis.fetch = rescanFetch(() => Promise.reject(new Error('not called')));
      renderAs('monitor');

      await screen.findByTestId('mod-updates-check');
      expect(screen.queryByTestId('mods-rescan')).not.toBeInTheDocument();
    });

    it('is 44px tall on phones, like the other toolbar buttons', async () => {
      globalThis.fetch = rescanFetch(() => Promise.reject(new Error('not called')));
      renderAs('admin');

      expect(await screen.findByTestId('mods-rescan')).toHaveClass('max-lg:h-11');
    });
  });

  describe('Filters (Story 24.7)', () => {
    const navigation: { navigate: (delta: number) => void } = { navigate: () => {} };

    function LocationProbe() {
      const location = useLocation();
      const navigate = useNavigate();
      navigation.navigate = (delta) => void navigate(delta);
      return <div data-testid="location-search">{location.search}</div>;
    }

    const modsBody = {
      status: 'ok',
      data: {
        mods: [
          {
            filename: 'smithingplus-1.5.0.zip',
            slug: 'smithingplus',
            version: '1.5.0',
            enabled: true,
            installed_at: '2024-01-15T10:30:00Z',
            asset_id: 1,
            name: 'Smithing Plus',
            authors: [],
            description: null,
          },
          {
            filename: 'carryon-1.0.0.zip',
            slug: 'carryon',
            version: '1.0.0',
            enabled: true,
            installed_at: '2024-01-15T10:30:00Z',
            asset_id: 2,
            name: 'Carry On',
            authors: [],
            description: null,
          },
        ],
        pending_restart: false,
      },
    };

    const updatesBody = {
      status: 'ok',
      data: {
        game_version: '1.22.7',
        checked_at: '2026-11-19T00:00:00Z',
        update_count: 1,
        mods: [
          {
            slug: 'smithingplus',
            name: 'Smithing Plus',
            installed_version: '1.5.0',
            status: 'update_available',
            reason: null,
            offered_version: '1.6.0',
            offered_compatibility: 'compatible',
            offered_prerelease: false,
            checked_at: '2026-11-19T00:00:00Z',
            error: null,
          },
          {
            slug: 'carryon',
            name: 'Carry On',
            installed_version: '1.0.0',
            status: 'up_to_date',
            reason: null,
            offered_version: null,
            offered_compatibility: null,
            offered_prerelease: null,
            checked_at: '2026-11-19T00:00:00Z',
            error: null,
          },
        ],
      },
    };

    function renderAt(entry: string) {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        const body = url.includes('/mods/updates')
          ? updatesBody
          : url.includes('/mods')
            ? modsBody
            : mockServerStatusResponse;
        return Promise.resolve({ ok: true, json: () => Promise.resolve(body) });
      });
      const queryClient = createTestQueryClient();
      queryClient.setQueryData(queryKeys.auth.me, { status: 'ok', data: { role: 'admin' } });
      const Wrapper = createWrapper(queryClient, entry);
      render(
        <Wrapper>
          <InstalledTab />
          <LocationProbe />
        </Wrapper>
      );
    }

    beforeEach(() => {
      compat.map = new Map([
        ['smithingplus', 'compatible'],
        ['carryon', 'incompatible'],
      ]);
    });

    it('filters by part of the name, ignoring case, and keeps it in the URL', async () => {
      renderAt('/game-server/mods/installed');
      await screen.findByTestId('mod-row-carryon');

      fireEvent.change(screen.getByTestId('installed-mods-filter-query'), {
        target: { value: 'SMITH' },
      });

      expect(screen.getByTestId('mod-row-smithingplus')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-row-carryon')).not.toBeInTheDocument();
      expect(screen.getByTestId('mod-filter-status')).toHaveTextContent('Showing 1 of 2 mods');
      expect(screen.getByTestId('location-search')).toHaveTextContent('?q=SMITH');
    });

    it('matches the mod ID too', async () => {
      renderAt('/game-server/mods/installed?q=yon');

      expect(await screen.findByTestId('mod-row-carryon')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-row-smithingplus')).not.toBeInTheDocument();
    });

    it('restores the compatibility filter from the URL', async () => {
      renderAt('/game-server/mods/installed?compat=incompatible');

      expect(await screen.findByTestId('mod-row-carryon')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-row-smithingplus')).not.toBeInTheDocument();
      expect(screen.getByTestId('installed-mods-filter-compat')).toHaveTextContent('Incompatible');
    });

    it('shows a mod whose compatibility is loading only under All', async () => {
      compat.map = new Map([['smithingplus', 'compatible']]);
      renderAt('/game-server/mods/installed?compat=not_verified');

      expect(await screen.findByTestId('mod-filter-empty')).toBeInTheDocument();
    });

    it('filters to mods with an update available, leaving Update all unchanged', async () => {
      renderAt('/game-server/mods/installed');
      await screen.findByTestId('mod-row-carryon');

      fireEvent.click(screen.getByTestId('installed-mods-filter-updates'));

      expect(screen.getByTestId('mod-row-smithingplus')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-row-carryon')).not.toBeInTheDocument();
      expect(screen.getByTestId('location-search')).toHaveTextContent('?updates=1');
      expect(screen.getByTestId('mod-updates-update-all')).toHaveTextContent('Update all (1)');
    });

    it('combines the filters', async () => {
      renderAt('/game-server/mods/installed?updates=1&compat=incompatible');

      expect(await screen.findByTestId('mod-filter-empty')).toHaveTextContent(
        'No installed mods match these filters.'
      );
    });

    it('clears every filter from the no-match state', async () => {
      renderAt('/game-server/mods/installed?q=nothing&updates=1&tab=keep');
      await screen.findByTestId('mod-filter-empty');

      fireEvent.click(screen.getByTestId('mod-filter-clear'));

      expect(await screen.findByTestId('mod-row-carryon')).toBeInTheDocument();
      expect(screen.getByTestId('mod-row-smithingplus')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-filter-status')).not.toBeInTheDocument();
      expect(screen.getByTestId('location-search')).toHaveTextContent('?tab=keep');
    });

    it('Back restores the previous filter', async () => {
      renderAt('/game-server/mods/installed');
      await screen.findByTestId('mod-row-carryon');

      fireEvent.click(screen.getByTestId('installed-mods-filter-updates'));
      expect(screen.queryByTestId('mod-row-carryon')).not.toBeInTheDocument();
      act(() => navigation.navigate(-1));

      expect(await screen.findByTestId('mod-row-carryon')).toBeInTheDocument();
      expect(screen.getByTestId('location-search')).toHaveTextContent('');
    });

    it('a compatibility choice pushes a history entry that Back undoes', async () => {
      Element.prototype.hasPointerCapture ??= () => false;
      Element.prototype.releasePointerCapture ??= () => {};
      Element.prototype.scrollIntoView ??= () => {};
      const user = userEvent.setup();
      renderAt('/game-server/mods/installed?q=n');
      await screen.findByTestId('mod-row-carryon');

      await user.click(screen.getByRole('combobox', { name: 'Compatibility' }));
      await user.click(await screen.findByTestId('installed-mods-filter-compat-incompatible'));

      expect(screen.getByTestId('location-search')).toHaveTextContent('?q=n&compat=incompatible');
      expect(screen.queryByTestId('mod-row-smithingplus')).not.toBeInTheDocument();
      act(() => navigation.navigate(-1));

      expect(await screen.findByTestId('mod-row-smithingplus')).toBeInTheDocument();
      expect(screen.getByTestId('location-search')).toHaveTextContent('?q=n');
    });

    it('ignores invalid values', async () => {
      renderAt('/game-server/mods/installed?compat=sometimes&updates=yes');

      expect(await screen.findByTestId('mod-row-carryon')).toBeInTheDocument();
      expect(screen.getByTestId('mod-row-smithingplus')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-filter-status')).not.toBeInTheDocument();
    });

    it('filters the cards on phones too', async () => {
      setViewportWidth(390);
      renderAt('/game-server/mods/installed?q=carry');

      const cards = await screen.findByTestId('installed-mod-cards');
      await waitFor(() =>
        expect(within(cards).getByTestId('installed-mod-card-carryon')).toBeInTheDocument()
      );
      expect(
        within(cards).queryByTestId('installed-mod-card-smithingplus')
      ).not.toBeInTheDocument();
    });
  });
});
