/**
 * ModsPage routing and tab navigation tests.
 *
 * Story 10.2: Mods Tab Restructure - AC4, AC5, AC6
 * Story 11.4: Updated to /game-server/mods paths
 *
 * Tests cover:
 * - AC4: URL updates when switching tabs, browser history works
 * - AC5: Direct navigation to /game-server/mods/browse works
 * - AC6: Redirect from /game-server/mods to /game-server/mods/installed
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { act, render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { BrowserRouter, MemoryRouter, Routes, Route, Navigate, useLocation, type InitialEntry } from 'react-router';
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

import { ModsPage } from './ModsPage';
import { InstalledTab } from './InstalledTab';
import { BrowseTab } from './BrowseTab';
import { ModDetailPage } from './ModDetailPage';
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import { BROWSE_LAST_SEARCH_KEY } from '@/lib/browse-search';

/** Story 16.1: Shows the router's current location and whether it marks a return. */
function LocationProbe() {
  const location = useLocation();
  const state = location.state as { fromModDetail?: unknown } | null;
  return (
    <>
      <span data-testid="probe-path">{location.pathname}</span>
      <span data-testid="probe-search">{location.search}</span>
      <span data-testid="probe-from-detail">{String(state?.fromModDetail === true)}</span>
    </>
  );
}

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

// Mock mods response for API calls
const mockEmptyModsResponse = {
  status: 'ok',
  data: {
    mods: [],
    pendingRestart: false,
  },
};

// Mock browse mods response
const mockBrowseModsResponse = {
  status: 'ok',
  data: {
    mods: [
      {
        slug: 'testmod',
        modIds: ['testmod'],
        name: 'Test Mod',
        author: 'Test Author',
        summary: 'A test mod',
        downloads: 1000,
        follows: 100,
        trendingPoints: 50,
        side: 'both',
        modType: 'mod',
        logoUrl: null,
        tags: ['test'],
        lastReleased: '2024-01-01T00:00:00Z',
      },
    ],
    // Story 17.7: enough pages for the Story 16.1 test that opens page 2 (a page beyond
    // the results would be replaced by the last page)
    pagination: {
      page: 1,
      pageSize: 20,
      totalItems: 41,
      totalPages: 3,
      hasNext: false,
      hasPrev: false,
    },
  },
};

// Mock server status response
const mockServerStatusResponse = {
  status: 'ok',
  data: {
    state: 'stopped',
  },
};

// Wrapper for tests that need routing - Story 11.4: Uses /game-server/mods paths
function createTestRouter(initialEntries: string[], queryClient: QueryClient) {
  return function TestRouter({ children }: { children?: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <PreferencesProvider>
          <MemoryRouter initialEntries={initialEntries}>
            <Routes>
              <Route path="/game-server/mods" element={<ModsPage />}>
                <Route index element={<Navigate to="installed" replace />} />
                <Route path="installed" element={<InstalledTab />} />
                <Route path="browse" element={<BrowseTab />} />
              </Route>
            </Routes>
            {children}
          </MemoryRouter>
        </PreferencesProvider>
      </QueryClientProvider>
    );
  };
}

/**
 * Redirect component for testing legacy /mods routes (mirrors App.tsx ModsRedirect).
 */
function ModsRedirect() {
  const location = useLocation();
  const newPath = location.pathname.replace(/^\/mods/, '/game-server/mods');
  return <Navigate to={newPath} replace />;
}

// Wrapper for tests that include legacy route redirects - Story 11.4
function createTestRouterWithRedirects(initialEntries: InitialEntry[], queryClient: QueryClient) {
  return function TestRouter({ children }: { children?: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <PreferencesProvider>
          <MemoryRouter initialEntries={initialEntries}>
            <Routes>
              <Route path="/game-server/mods" element={<ModsPage />}>
                <Route index element={<Navigate to="installed" replace />} />
                <Route path="installed" element={<InstalledTab />} />
                <Route path="browse" element={<BrowseTab />} />
                <Route path="browse/:slug" element={<ModDetailPage />} />
              </Route>
              {/* Legacy route redirects */}
              <Route path="/mods/*" element={<ModsRedirect />} />
            </Routes>
            {children}
          </MemoryRouter>
        </PreferencesProvider>
      </QueryClientProvider>
    );
  };
}

describe('ModsPage routing', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';

    // Mock all fetch calls
    globalThis.fetch = vi.fn().mockImplementation((url: string) => {
      if (url.includes('/mods/browse')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockBrowseModsResponse),
        });
      }
      if (url.includes('/mods')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockEmptyModsResponse),
        });
      }
      if (url.includes('/server/status')) {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockServerStatusResponse),
        });
      }
      return Promise.resolve({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: {} }),
      });
    });
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('AC6: redirect from /game-server/mods to /game-server/mods/installed', () => {
    it('redirects /game-server/mods to /game-server/mods/installed', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods'], queryClient);

      render(<Router />);

      // Should show the Installed tab content (via redirect)
      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });

      // Installed tab trigger should be active
      const installedTabTrigger = screen.getByRole('tab', { name: /installed/i });
      expect(installedTabTrigger).toHaveAttribute('data-state', 'active');
    });
  });

  describe('AC5: direct navigation to /game-server/mods/browse', () => {
    it('shows Browse tab when navigating directly to /game-server/mods/browse', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods/browse'], queryClient);

      render(<Router />);

      // Should show the Browse tab content
      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });

      // Should show the search input (Story 10.3 implementation)
      await waitFor(() => {
        expect(screen.getByTestId('browse-search-input')).toBeInTheDocument();
      });
    });

    it('shows Installed tab when navigating directly to /game-server/mods/installed', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods/installed'], queryClient);

      render(<Router />);

      // Should show the Installed tab content
      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });

      // VSS-195: ModLookupInput removed, verify "Installed Mods" heading instead
      expect(screen.getByText('Installed Mods')).toBeInTheDocument();
    });
  });

  describe('AC4: tab switching updates URL', () => {
    it('switches to Browse tab when clicked', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods/installed'], queryClient);

      render(<Router />);

      // Wait for initial render
      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });

      // Click the Browse tab trigger
      const browseTabTrigger = screen.getByRole('tab', { name: /browse/i });
      await user.click(browseTabTrigger);

      // Should now show Browse tab content
      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });
    });

    it('switches to Installed tab when clicked', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods/browse'], queryClient);

      render(<Router />);

      // Wait for initial render with Browse tab
      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });

      // Click the Installed tab trigger
      const installedTabTrigger = screen.getByRole('tab', { name: /installed/i });
      await user.click(installedTabTrigger);

      // Should now show Installed tab content
      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });
    });
  });

  describe('Story 16.1: Browse tab returns to the browse state', () => {
    const lastSearch = '?q=farming&version=1.20.0';
    const openedSearch = '?q=food&side=server&tags=qol&type=mod&version=1.21.2&sort=downloads&page=2';

    beforeEach(() => {
      window.sessionStorage.removeItem(BROWSE_LAST_SEARCH_KEY);
    });

    async function clickBrowseTab(initialEntry: Parameters<typeof createTestRouterWithRedirects>[0][number]) {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      const Router = createTestRouterWithRedirects([initialEntry], queryClient);
      render(
        <Router>
          <LocationProbe />
        </Router>
      );
      await user.click(await screen.findByRole('tab', { name: /browse/i }));
      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });
    }

    it('on a detail page opened from browse, opens the state the mod was opened from', async () => {
      window.sessionStorage.setItem(BROWSE_LAST_SEARCH_KEY, lastSearch);

      await clickBrowseTab({
        pathname: '/game-server/mods/browse/testmod',
        state: { browseSearch: openedSearch },
      });

      expect(screen.getByTestId('probe-path')).toHaveTextContent('/game-server/mods/browse');
      expect(screen.getByTestId('probe-search')).toHaveTextContent(openedSearch);
      expect(screen.getByTestId('probe-from-detail')).toHaveTextContent('true');
      expect(screen.getByTestId('browse-search-input')).toHaveValue('food');
      expect(screen.getByLabelText('Remove version filter: 1.21.2')).toBeInTheDocument();
    });

    it('from the Installed tab, opens the last browse state including the game version', async () => {
      window.sessionStorage.setItem(BROWSE_LAST_SEARCH_KEY, lastSearch);

      await clickBrowseTab('/game-server/mods/installed');

      expect(screen.getByTestId('probe-search')).toHaveTextContent(lastSearch);
      expect(screen.getByTestId('probe-from-detail')).toHaveTextContent('false');
      expect(screen.getByLabelText('Remove version filter: 1.20.0')).toBeInTheDocument();
    });

    it('on a detail page opened directly, opens the last browse state', async () => {
      window.sessionStorage.setItem(BROWSE_LAST_SEARCH_KEY, lastSearch);

      await clickBrowseTab('/game-server/mods/browse/testmod');

      expect(screen.getByTestId('probe-search')).toHaveTextContent(lastSearch);
    });

    it('does not add a history entry when the active Browse tab is clicked', async () => {
      const user = userEvent.setup();
      const keys: string[] = [];
      function KeyProbe() {
        const location = useLocation();
        if (keys.at(-1) !== location.key) keys.push(location.key);
        return null;
      }
      window.sessionStorage.setItem(BROWSE_LAST_SEARCH_KEY, lastSearch);
      const queryClient = createTestQueryClient();
      const Router = createTestRouterWithRedirects([`/game-server/mods/browse${lastSearch}`], queryClient);
      render(
        <Router>
          <KeyProbe />
        </Router>
      );
      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });

      await user.click(screen.getByRole('tab', { name: /browse/i }));

      expect(keys).toHaveLength(1);

      // The probe does see a real tab change
      await user.click(screen.getByRole('tab', { name: /installed/i }));
      await waitFor(() => {
        expect(keys).toHaveLength(2);
      });
    });

    it('opens the default browser when no browse state is saved', async () => {
      await clickBrowseTab('/game-server/mods/installed');

      expect(screen.getByTestId('probe-path')).toHaveTextContent('/game-server/mods/browse');
      expect(screen.getByTestId('probe-search')).toBeEmptyDOMElement();
    });
  });

  describe('Story 17.7: Mods tabs on a mod detail page', () => {
    const detailPath = '/game-server/mods/browse/testmod';

    beforeEach(() => {
      window.sessionStorage.removeItem(BROWSE_LAST_SEARCH_KEY);
    });

    /** Records each distinct location key, so a test can count history entries. */
    function createKeyProbe() {
      const keys: string[] = [];
      function KeyProbe() {
        const location = useLocation();
        if (keys.at(-1) !== location.key) keys.push(location.key);
        return null;
      }
      return { keys, KeyProbe };
    }

    function renderAt(initialEntry: InitialEntry, extra?: ReactNode) {
      const queryClient = createTestQueryClient();
      const Router = createTestRouterWithRedirects([initialEntry], queryClient);
      render(
        <Router>
          <LocationProbe />
          {extra}
        </Router>
      );
    }

    it('shows Browse as the active tab on a detail page', async () => {
      renderAt(detailPath);

      const browseTab = await screen.findByTestId('browse-tab');
      expect(browseTab).toHaveAttribute('data-state', 'active');
      expect(browseTab).toHaveAttribute('aria-selected', 'true');
      expect(screen.getByTestId('installed-tab')).toHaveAttribute('data-state', 'inactive');
      expect(screen.getByTestId('installed-tab')).toHaveAttribute('aria-selected', 'false');
    });

    it('shows Browse as the active tab on the browse list with a trailing slash', async () => {
      renderAt('/game-server/mods/browse/');

      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });
      expect(screen.getByTestId('browse-tab')).toHaveAttribute('data-state', 'active');
      expect(screen.getByTestId('installed-tab')).toHaveAttribute('data-state', 'inactive');
    });

    it('opens the Installed list when Installed is clicked on a detail page', async () => {
      const user = userEvent.setup();
      renderAt(detailPath);

      await user.click(await screen.findByTestId('installed-tab'));

      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });
      expect(screen.getByTestId('probe-path')).toHaveTextContent(/^\/game-server\/mods\/installed$/);
      expect(screen.getByTestId('installed-tab')).toHaveAttribute('data-state', 'active');
    });

    it('opens the Installed list from a detail page with the keyboard', async () => {
      const user = userEvent.setup();
      renderAt(detailPath);
      await screen.findByTestId('installed-tab');

      act(() => screen.getByTestId('installed-tab').focus());
      await user.keyboard('{Enter}');

      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });
      expect(screen.getByTestId('probe-path')).toHaveTextContent(/^\/game-server\/mods\/installed$/);
    });

    it.each([
      ['a click', async (user: ReturnType<typeof userEvent.setup>) => {
        await user.click(screen.getByTestId('browse-tab'));
      }],
      ['Space', async (user: ReturnType<typeof userEvent.setup>) => {
        act(() => screen.getByTestId('browse-tab').focus());
        await user.keyboard(' ');
      }],
      ['Enter', async (user: ReturnType<typeof userEvent.setup>) => {
        act(() => screen.getByTestId('browse-tab').focus());
        await user.keyboard('{Enter}');
      }],
    ])('opens the state the mod was opened from with %s on the active Browse tab, adding one history entry', async (_name, activate) => {
      const user = userEvent.setup();
      window.sessionStorage.setItem(BROWSE_LAST_SEARCH_KEY, '?q=farming');
      const { keys, KeyProbe } = createKeyProbe();
      renderAt({ pathname: detailPath, state: { browseSearch: '?q=food' } }, <KeyProbe />);
      await screen.findByTestId('browse-tab');
      expect(keys).toHaveLength(1);

      await activate(user);

      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });
      expect(screen.getByTestId('probe-path')).toHaveTextContent(/^\/game-server\/mods\/browse$/);
      expect(screen.getByTestId('probe-search')).toHaveTextContent(/^\?q=food$/);
      expect(screen.getByTestId('probe-from-detail')).toHaveTextContent('true');
      expect(keys).toHaveLength(2);
    });
  });

  // Story 17.7 review M1: Radix's mousedown focuses the trigger (onFocus reports the
  // value) and then reports it again, both before the navigation commits
  describe('Story 17.7: one history entry per tab change', () => {
    beforeEach(() => {
      window.sessionStorage.removeItem(BROWSE_LAST_SEARCH_KEY);
    });

    /**
     * Renders the Mods routes in a BrowserRouter, as the app does, and returns a function
     * that counts the history entries added since. A render probe cannot count them:
     * two pushes before one render show up as one location.
     */
    function renderInBrowserRouter(path: string) {
      window.history.replaceState(null, '', path);
      const startLength = window.history.length;
      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <PreferencesProvider>
            <BrowserRouter>
              <Routes>
                <Route path="/game-server/mods" element={<ModsPage />}>
                  <Route path="installed" element={<InstalledTab />} />
                  <Route path="browse" element={<BrowseTab />} />
                  <Route path="browse/:slug" element={<ModDetailPage />} />
                </Route>
              </Routes>
              <LocationProbe />
            </BrowserRouter>
          </PreferencesProvider>
        </QueryClientProvider>
      );
      return () => window.history.length - startLength;
    }

    /** Let a second navigation commit if one were coming. */
    async function settle() {
      await new Promise((resolve) => setTimeout(resolve, 50));
    }

    it.each([
      ['the browse list', '/game-server/mods/browse', 'installed-tab', '/game-server/mods/installed'],
      ['the Installed list', '/game-server/mods/installed', 'browse-tab', '/game-server/mods/browse'],
      ['a mod detail page', '/game-server/mods/browse/testmod', 'installed-tab', '/game-server/mods/installed'],
    ])('a mouse click on the inactive tab on %s adds one history entry', async (_name, start, tab, target) => {
      const user = userEvent.setup();
      const addedEntries = renderInBrowserRouter(start);
      await screen.findByTestId(tab);
      expect(addedEntries()).toBe(0);

      await user.click(screen.getByTestId(tab));

      await waitFor(() => {
        expect(screen.getByTestId('probe-path')).toHaveTextContent(new RegExp(`^${target}$`));
      });
      await settle();
      expect(addedEntries()).toBe(1);
    });

    it('clicking back and forth adds one entry per click', async () => {
      const user = userEvent.setup();
      const addedEntries = renderInBrowserRouter('/game-server/mods/installed');
      await screen.findByTestId('browse-tab');

      await user.click(screen.getByTestId('browse-tab'));
      await waitFor(() => {
        expect(screen.getByTestId('browse-tab')).toHaveAttribute('data-state', 'active');
      });
      await user.click(screen.getByTestId('installed-tab'));
      await waitFor(() => {
        expect(screen.getByTestId('installed-tab')).toHaveAttribute('data-state', 'active');
      });
      await user.click(screen.getByTestId('browse-tab'));
      await waitFor(() => {
        expect(screen.getByTestId('browse-tab')).toHaveAttribute('data-state', 'active');
      });
      await settle();

      expect(addedEntries()).toBe(3);
      expect(screen.getByTestId('probe-path')).toHaveTextContent(/^\/game-server\/mods\/browse$/);
    });

    it('moving to the other tab with an arrow key adds one history entry', async () => {
      const user = userEvent.setup();
      const addedEntries = renderInBrowserRouter('/game-server/mods/installed');
      await screen.findByTestId('installed-tab');
      act(() => screen.getByTestId('installed-tab').focus());

      await user.keyboard('{ArrowRight}');

      await waitFor(() => {
        expect(screen.getByTestId('probe-path')).toHaveTextContent(/^\/game-server\/mods\/browse$/);
      });
      await settle();
      expect(addedEntries()).toBe(1);
    });
  });

  describe('Story 11.4 AC2: legacy /mods route redirects', () => {
    it('redirects /mods to /game-server/mods/installed', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouterWithRedirects(['/mods'], queryClient);

      render(<Router />);

      // Should show the Installed tab content (via redirect chain: /mods → /game-server/mods → /game-server/mods/installed)
      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });
    });

    it('redirects /mods/installed to /game-server/mods/installed', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouterWithRedirects(['/mods/installed'], queryClient);

      render(<Router />);

      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });
    });

    it('redirects /mods/browse to /game-server/mods/browse', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouterWithRedirects(['/mods/browse'], queryClient);

      render(<Router />);

      await waitFor(() => {
        expect(screen.getByTestId('browse-tab-content')).toBeInTheDocument();
      });
    });

    it('redirects /mods/browse/:slug to /game-server/mods/browse/:slug', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouterWithRedirects(['/mods/browse/testmod'], queryClient);

      render(<Router />);

      // Should render the ModDetailPage (shows loading state initially)
      await waitFor(() => {
        expect(screen.getByTestId('mod-detail-loading')).toBeInTheDocument();
      });
    });
  });

  describe('AC1: page structure', () => {
    it('renders page with correct heading', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods/installed'], queryClient);

      render(<Router />);

      expect(screen.getByTestId('mods-page')).toBeInTheDocument();
      expect(screen.getByText('Mods')).toBeInTheDocument();
      expect(
        screen.getByText('Manage installed mods or discover new ones')
      ).toBeInTheDocument();
    });

    it('renders both tab triggers', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods/installed'], queryClient);

      render(<Router />);

      expect(screen.getByRole('tab', { name: /installed/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /browse/i })).toBeInTheDocument();
    });

    it('defaults to Installed tab being active', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/mods/installed'], queryClient);

      render(<Router />);

      await waitFor(() => {
        expect(screen.getByTestId('installed-tab-content')).toBeInTheDocument();
      });

      // Installed tab trigger should be selected
      const installedTabTrigger = screen.getByRole('tab', { name: /installed/i });
      expect(installedTabTrigger).toHaveAttribute('data-state', 'active');
    });
  });
});
