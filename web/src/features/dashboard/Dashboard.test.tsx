/**
 * Tests for Dashboard component.
 *
 * Story 12.4: Dashboard Stats Cards
 * Story 11.6: Dashboard & Navigation Cleanup
 * Story 12.5: Dashboard Time-Series Charts
 *
 * Tests verify the Dashboard shows:
 * - Empty state with link to Installation page when server not installed
 * - Installing state with spinner and link to view progress
 * - Stat cards grid with server status, memory, disk, and uptime when installed
 * - Time-series chart with time range selector when installed (Story 12.5)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { type ReactNode } from 'react';
import { Dashboard } from './Dashboard';
import type { ServerStatus, MetricsSnapshot } from '@/api/types';

// Mock ResizeObserver for Recharts ResponsiveContainer
class MockResizeObserver {
  observe = vi.fn();
  unobserve = vi.fn();
  disconnect = vi.fn();
}
globalThis.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;

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

// Mock metrics history response (Story 12.5)
function mockMetricsHistory(metrics: MetricsSnapshot[]) {
  return {
    ok: true,
    json: () =>
      Promise.resolve({
        status: 'ok',
        data: {
          metrics,
          count: metrics.length,
        },
      }),
  };
}

// Sample metrics data for chart tests
const sampleMetrics: MetricsSnapshot[] = [
  {
    timestamp: '2026-01-17T10:00:00Z',
    apiMemoryMb: 100,
    apiCpuPercent: 2.0,
    gameMemoryMb: 500,
    gameCpuPercent: 15.0,
  },
  {
    timestamp: '2026-01-17T10:10:00Z',
    apiMemoryMb: 105,
    apiCpuPercent: 2.2,
    gameMemoryMb: 510,
    gameCpuPercent: 15.5,
  },
];

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
        // Look for the badge specifically (it has the role="status" aria attribute)
        expect(screen.getByRole('status')).toHaveTextContent('Stopped');
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

    it('displays server version when running', async () => {
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

  describe('stat cards grid (Story 12.4)', () => {
    it('renders stats grid with 4 cards when server is installed (AC: 1)', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
          diskSpace: {
            totalGb: 100,
            usedGb: 55,
            availableGb: 45,
            usagePercent: 55,
            warning: false,
          },
        }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-stats-grid')).toBeInTheDocument();
      });

      // Verify all 4 stat cards are present
      expect(screen.getByTestId('server-status-card')).toBeInTheDocument();
      expect(screen.getByTestId('memory-card')).toBeInTheDocument();
      expect(screen.getByTestId('disk-card')).toBeInTheDocument();
      expect(screen.getByTestId('uptime-card')).toBeInTheDocument();
    });

    it('shows responsive grid layout (AC: 5)', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({
          state: 'installed',
          version: '1.21.3',
        }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-stats-grid')).toBeInTheDocument();
      });

      const grid = screen.getByTestId('dashboard-stats-grid');
      // Check for responsive grid classes (sm breakpoint at 640px)
      expect(grid.className).toContain('grid');
      expect(grid.className).toContain('sm:grid-cols-2');
    });

    it('does not show stats grid when server not installed', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'not_installed' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-empty')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('dashboard-stats-grid')).not.toBeInTheDocument();
    });
  });

  describe('metrics chart (Story 12.5)', () => {
    it('renders chart card when server is installed (AC: 1)', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/server/status')) {
          return Promise.resolve(
            mockServerStatus(createServerStatus({ state: 'running', version: '1.21.3' }))
          );
        }
        if (url.includes('/metrics/history')) {
          return Promise.resolve(mockMetricsHistory(sampleMetrics));
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('metrics-chart-card')).toBeInTheDocument();
      });

      // Should show chart title
      expect(screen.getByText('Memory Usage Over Time')).toBeInTheDocument();
    });

    it('renders time range selector with all options (AC: 3)', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/server/status')) {
          return Promise.resolve(
            mockServerStatus(createServerStatus({ state: 'installed', version: '1.21.3' }))
          );
        }
        if (url.includes('/metrics/history')) {
          return Promise.resolve(mockMetricsHistory([]));
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('time-range-selector')).toBeInTheDocument();
      });

      // Should have all time range options
      expect(screen.getByText('15m')).toBeInTheDocument();
      expect(screen.getByText('1h')).toBeInTheDocument();
      expect(screen.getByText('6h')).toBeInTheDocument();
      expect(screen.getByText('24h')).toBeInTheDocument();
    });

    it('defaults to 1h time range selected (AC: 3)', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/server/status')) {
          return Promise.resolve(
            mockServerStatus(createServerStatus({ state: 'installed', version: '1.21.3' }))
          );
        }
        if (url.includes('/metrics/history')) {
          return Promise.resolve(mockMetricsHistory([]));
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('time-range-60')).toHaveAttribute('aria-pressed', 'true');
      });
    });

    it('changes time range when clicking selector (AC: 3)', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/server/status')) {
          return Promise.resolve(
            mockServerStatus(createServerStatus({ state: 'installed', version: '1.21.3' }))
          );
        }
        if (url.includes('/metrics/history')) {
          return Promise.resolve(mockMetricsHistory([]));
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('time-range-selector')).toBeInTheDocument();
      });

      // Click 6h option
      await user.click(screen.getByText('6h'));

      // Should now be selected
      expect(screen.getByTestId('time-range-360')).toHaveAttribute('aria-pressed', 'true');
      expect(screen.getByTestId('time-range-60')).toHaveAttribute('aria-pressed', 'false');
    });

    it('shows loading state for chart while fetching (AC: 1)', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/server/status')) {
          return Promise.resolve(
            mockServerStatus(createServerStatus({ state: 'running', version: '1.21.3' }))
          );
        }
        if (url.includes('/metrics/history')) {
          // Never resolve to keep loading
          return new Promise(() => {});
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('metrics-chart-loading')).toBeInTheDocument();
      });

      expect(screen.getByText('Loading chart...')).toBeInTheDocument();
    });

    it('renders chart with data when loaded (AC: 1, 2)', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/server/status')) {
          return Promise.resolve(
            mockServerStatus(createServerStatus({ state: 'running', version: '1.21.3' }))
          );
        }
        if (url.includes('/metrics/history')) {
          return Promise.resolve(mockMetricsHistory(sampleMetrics));
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('metrics-chart')).toBeInTheDocument();
      });
    });

    it('shows empty state when no metrics data (AC: 1)', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/server/status')) {
          return Promise.resolve(
            mockServerStatus(createServerStatus({ state: 'installed', version: '1.21.3' }))
          );
        }
        if (url.includes('/metrics/history')) {
          return Promise.resolve(mockMetricsHistory([]));
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('metrics-chart-empty')).toBeInTheDocument();
      });

      expect(screen.getByText('No metrics data available')).toBeInTheDocument();
    });

    it('does not show chart when server not installed', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus(createServerStatus({ state: 'not_installed' }))
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('dashboard-empty')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('metrics-chart-card')).not.toBeInTheDocument();
    });
  });
});
