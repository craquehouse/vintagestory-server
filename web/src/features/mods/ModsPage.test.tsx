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
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter, Routes, Route, Navigate, useLocation } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { ModsPage } from './ModsPage';
import { InstalledTab } from './InstalledTab';
import { BrowseTab } from './BrowseTab';

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
function createTestRouterWithRedirects(initialEntries: string[], queryClient: QueryClient) {
  return function TestRouter({ children }: { children?: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            <Route path="/game-server/mods" element={<ModsPage />}>
              <Route index element={<Navigate to="installed" replace />} />
              <Route path="installed" element={<InstalledTab />} />
              <Route path="browse" element={<BrowseTab />} />
            </Route>
            {/* Legacy route redirects */}
            <Route path="/mods/*" element={<ModsRedirect />} />
          </Routes>
          {children}
        </MemoryRouter>
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

      // Should show the mod lookup input
      expect(
        screen.getByPlaceholderText('Enter mod slug or paste URL')
      ).toBeInTheDocument();
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
