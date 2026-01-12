/**
 * Tests for Dashboard component.
 *
 * Story 11.6: Dashboard & Navigation Cleanup
 *
 * Tests verify the Dashboard shows:
 * - Empty state with link to Installation page when server not installed
 * - Installing state with spinner and link to view progress
 * - Server status card with controls when server is installed
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { type ReactNode } from 'react';
import { Dashboard } from './Dashboard';
import type { ServerStatus } from '@/api/types';

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

// Wrapper component for rendering with providers (includes MemoryRouter for Link)
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter>{children}</MemoryRouter>
      </QueryClientProvider>
    );
  };
}

// Create a full ServerStatus with defaults for optional fields
function createServerStatus(
  overrides: Partial<ServerStatus> & Pick<ServerStatus, 'state'>
): ServerStatus {
  return {
    state: overrides.state,
    version: overrides.version ?? null,
    uptimeSeconds: overrides.uptimeSeconds ?? null,
    lastExitCode: overrides.lastExitCode ?? null,
    availableStableVersion: overrides.availableStableVersion ?? null,
    availableUnstableVersion: overrides.availableUnstableVersion ?? null,
    versionLastChecked: overrides.versionLastChecked ?? null,
    diskSpace: overrides.diskSpace ?? null,
  };
}

// Mock server status responses
function mockServerStatus(status: ServerStatus) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'ok',
        data: status,
      }),
  };
}

describe('Dashboard', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('not installed state (AC: 1, 2)', () => {
    it('shows empty state card when server is not installed', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'not_installed' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-empty')).toBeInTheDocument();
      });

      // Should show "Server Not Installed" message
      expect(screen.getByText(/server not installed/i)).toBeInTheDocument();
    });

    it('shows link to Installation page in empty state', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'not_installed' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-empty')).toBeInTheDocument();
      });

      // Should have link to Installation page
      const installLink = screen.getByRole('link', { name: /installation/i });
      expect(installLink).toBeInTheDocument();
      expect(installLink).toHaveAttribute('href', '/game-server/version');
    });

    it('does not show server controls in empty state', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'not_installed' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-empty')).toBeInTheDocument();
      });

      // Control buttons should not be visible
      expect(screen.queryByRole('button', { name: 'Start server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Stop server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Restart server' })).not.toBeInTheDocument();
    });
  });

  describe('installing state (AC: 1, 2)', () => {
    it('shows installing state with spinner and progress link', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'installing' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-empty')).toBeInTheDocument();
      });

      // Should show "Installation in Progress" message
      expect(screen.getByText(/installation in progress/i)).toBeInTheDocument();

      // Should have link to view installation progress
      const progressLink = screen.getByRole('link', { name: /view installation progress/i });
      expect(progressLink).toBeInTheDocument();
      expect(progressLink).toHaveAttribute('href', '/game-server/version');
    });

    it('does not show server controls during installation', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'installing' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-empty')).toBeInTheDocument();
      });

      // Control buttons should not be visible
      expect(screen.queryByRole('button', { name: 'Start server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Stop server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Restart server' })).not.toBeInTheDocument();
    });
  });

  describe('stopped state (AC: 3)', () => {
    it('shows ServerStatusBadge with Stopped status', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'installed', version: '1.21.3' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Stopped')).toBeInTheDocument();
      });
    });

    it('displays server version when stopped', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'installed', version: '1.21.3' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Version 1.21.3')).toBeInTheDocument();
      });
    });

    it('enables Start button and disables Stop/Restart when stopped', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'installed', version: '1.21.3' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Start server' })).not.toBeDisabled();
      });

      expect(screen.getByRole('button', { name: 'Stop server' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Restart server' })).toBeDisabled();
    });
  });

  describe('running state (AC: 4)', () => {
    it('shows ServerStatusBadge with Running status', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
        }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Running')).toBeInTheDocument();
      });
    });

    it('displays server version and uptime when running', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3660, // 1 hour, 1 minute
        }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Version 1.21.3')).toBeInTheDocument();
        expect(screen.getByText('Uptime: 1 hour, 1 minute')).toBeInTheDocument();
      });
    });

    it('enables Stop/Restart buttons and disables Start when running', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
        }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByRole('button', { name: 'Stop server' })).not.toBeDisabled();
      });

      expect(screen.getByRole('button', { name: 'Restart server' })).not.toBeDisabled();
      expect(screen.getByRole('button', { name: 'Start server' })).toBeDisabled();
    });
  });

  describe('auto-refresh (AC: 6)', () => {
    it('polls server status using TanStack Query', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
        }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Running')).toBeInTheDocument();
      });

      // The hook uses useQuery which enables polling
      // We verify the query was made with the correct endpoint
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/server/status',
        expect.anything()
      );
    });
  });

  describe('loading state', () => {
    it('shows loading message while fetching status', () => {
      // Don't resolve the fetch immediately
      const mockFetch = vi.fn().mockImplementation(() => new Promise(() => {}));
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByText('Loading server status...')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message when status fetch fails', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Error Loading Status')).toBeInTheDocument();
      });
    });
  });
});
