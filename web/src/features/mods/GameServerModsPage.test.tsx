/**
 * Tests for GameServerModsPage empty state.
 *
 * Story 11.4: AC4 - Empty state when server is not installed
 *
 * These tests verify the wrapper component behavior that shows
 * an empty state when the server is not installed.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route, Navigate, Link } from 'react-router';
import { ServerOff, Loader2 } from 'lucide-react';

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
import { Button } from '@/components/ui/button';
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import type { ServerState } from '@/api/types';

// Mock the server status hook
const mockUseServerStatus = vi.fn();
vi.mock('@/hooks/use-server-status', () => ({
  useServerStatus: () => mockUseServerStatus(),
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

/**
 * Determines if the server is in an "installed" state (mirrors App.tsx).
 */
function isServerInstalled(state: ServerState): boolean {
  return state !== 'not_installed' && state !== 'installing';
}

/**
 * GameServerModsPage component for testing (mirrors App.tsx implementation).
 */
function GameServerModsPage() {
  const { data: statusResponse, isLoading } = mockUseServerStatus();
  const serverStatus = statusResponse?.data;
  const serverState = serverStatus?.state ?? 'not_installed';
  const isInstalled = isServerInstalled(serverState);
  const isInstalling = serverState === 'installing';

  if (isLoading) {
    return (
      <div className="p-4" data-testid="mods-page-loading">
        <h1 className="text-2xl font-bold">Mods</h1>
        <p className="text-muted-foreground mt-4">Loading server status...</p>
      </div>
    );
  }

  if (!isInstalled) {
    return (
      <div className="p-4" data-testid="mods-page-empty">
        <h1 className="text-2xl font-bold mb-6">Mods</h1>
        <div className="flex flex-col items-center justify-center h-64 text-center">
          {isInstalling ? (
            <>
              <Loader2 className="h-12 w-12 text-muted-foreground mb-4 animate-spin" />
              <p className="text-lg font-medium">Installation in Progress</p>
              <p className="text-muted-foreground mb-4">
                Mod management will be available once installation completes.
              </p>
              <Link to="/game-server/version">
                <Button variant="outline">View Installation Progress</Button>
              </Link>
            </>
          ) : (
            <>
              <ServerOff className="h-12 w-12 text-muted-foreground mb-4" />
              <p className="text-lg font-medium">Server Not Installed</p>
              <p className="text-muted-foreground mb-4">
                Install a VintageStory server to manage mods.
                Compatibility checking requires a server version to compare against.
              </p>
              <Link to="/game-server/version">
                <Button variant="default">Go to Installation</Button>
              </Link>
            </>
          )}
        </div>
      </div>
    );
  }

  return <ModsPage />;
}

// Wrapper component with providers
function renderWithProviders(
  initialEntries: string[] = ['/game-server/mods']
) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <PreferencesProvider>
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            <Route path="/game-server/mods" element={<GameServerModsPage />}>
              <Route index element={<Navigate to="installed" replace />} />
              <Route path="installed" element={<InstalledTab />} />
              <Route path="browse" element={<BrowseTab />} />
            </Route>
            <Route path="/game-server/version" element={<div data-testid="version-page">Version Page</div>} />
          </Routes>
        </MemoryRouter>
      </PreferencesProvider>
    </QueryClientProvider>
  );
}

describe('GameServerModsPage empty state (Story 11.4 AC4)', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';

    // Mock fetch for ModsPage child components
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: { mods: [], pendingRestart: false } }),
    });
  });

  describe('loading state', () => {
    it('renders loading state while checking server status', () => {
      mockUseServerStatus.mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      });

      renderWithProviders();

      expect(screen.getByTestId('mods-page-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading server status/i)).toBeInTheDocument();
    });
  });

  describe('not installed state', () => {
    it('renders empty state when server is not installed', () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      });

      renderWithProviders();

      expect(screen.getByTestId('mods-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/server not installed/i)).toBeInTheDocument();
    });

    it('shows message about compatibility checking', () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      });

      renderWithProviders();

      expect(screen.getByText(/compatibility checking requires a server version/i)).toBeInTheDocument();
    });

    it('shows link to Installation page', () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      });

      renderWithProviders();

      const installLink = screen.getByRole('link', { name: /go to installation/i });
      expect(installLink).toBeInTheDocument();
      expect(installLink).toHaveAttribute('href', '/game-server/version');
    });

    it('does not render ModsPage content when not installed', () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      });

      renderWithProviders();

      expect(screen.queryByTestId('mods-page')).not.toBeInTheDocument();
    });
  });

  describe('installing state', () => {
    it('shows installation in progress message', () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'installing', version: null } },
        isLoading: false,
        error: null,
      });

      renderWithProviders();

      expect(screen.getByTestId('mods-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/installation in progress/i)).toBeInTheDocument();
    });

    it('shows link to view installation progress', () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'installing', version: null } },
        isLoading: false,
        error: null,
      });

      renderWithProviders();

      const progressLink = screen.getByRole('link', { name: /view installation progress/i });
      expect(progressLink).toBeInTheDocument();
      expect(progressLink).toHaveAttribute('href', '/game-server/version');
    });
  });

  describe('installed state', () => {
    it('renders ModsPage when server is installed (stopped)', async () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'installed', version: '1.21.3' } },
        isLoading: false,
        error: null,
      });

      renderWithProviders(['/game-server/mods/installed']);

      // Should show ModsPage content, not empty state
      expect(screen.queryByTestId('mods-page-empty')).not.toBeInTheDocument();
      expect(screen.getByTestId('mods-page')).toBeInTheDocument();
    });

    it('renders ModsPage when server is running', async () => {
      mockUseServerStatus.mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      });

      renderWithProviders(['/game-server/mods/installed']);

      expect(screen.queryByTestId('mods-page-empty')).not.toBeInTheDocument();
      expect(screen.getByTestId('mods-page')).toBeInTheDocument();
    });
  });
});
