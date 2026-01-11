import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { VersionPage } from './VersionPage';

/**
 * VersionPage Tests - Story 11.2
 *
 * Tests cover:
 * - Loading state
 * - Error state
 * - Not installed state (shows ServerInstallCard)
 * - Installing state (shows ServerInstallCard with progress)
 * - Installed state (shows version info and status)
 * - Update available indicator
 */

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

// Mock server status responses (snake_case as from API)
const mockNotInstalledStatus = {
  status: 'ok',
  data: {
    state: 'not_installed',
    version: null,
    uptime_seconds: null,
    last_exit_code: null,
    available_stable_version: '1.21.6',
    available_unstable_version: '1.22.0-pre.1',
    version_last_checked: '2026-01-10T10:00:00Z',
    disk_space: null,
  },
};

const mockInstalledStatus = {
  status: 'ok',
  data: {
    state: 'installed',
    version: '1.21.5',
    uptime_seconds: null,
    last_exit_code: 0,
    available_stable_version: '1.21.6',
    available_unstable_version: '1.22.0-pre.1',
    version_last_checked: '2026-01-10T10:00:00Z',
    disk_space: {
      total_gb: 100,
      used_gb: 50,
      available_gb: 50,
      usage_percent: 50,
      warning: false,
    },
  },
};

const mockRunningStatus = {
  status: 'ok',
  data: {
    state: 'running',
    version: '1.21.6',
    uptime_seconds: 3600,
    last_exit_code: null,
    available_stable_version: '1.21.6',
    available_unstable_version: '1.22.0-pre.1',
    version_last_checked: '2026-01-10T10:00:00Z',
    disk_space: {
      total_gb: 100,
      used_gb: 50,
      available_gb: 50,
      usage_percent: 50,
      warning: false,
    },
  },
};

const mockInstallingStatus = {
  status: 'ok',
  data: {
    state: 'installing',
    version: null,
    uptime_seconds: null,
    last_exit_code: null,
    available_stable_version: '1.21.6',
    available_unstable_version: '1.22.0-pre.1',
    version_last_checked: '2026-01-10T10:00:00Z',
    disk_space: null,
  },
};

const mockInstallProgress = {
  status: 'ok',
  data: {
    state: 'downloading',
    progress: 45,
    message: 'Downloading VintageStory 1.21.6...',
  },
};

describe('VersionPage', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('loading state', () => {
    it('shows loading state while fetching server status', () => {
      // Make fetch never resolve
      globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('version-page-loading')).toBeInTheDocument();
      expect(screen.getByText('Loading server status...')).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('shows error message on fetch failure', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ detail: 'Server error' }),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-page-error')).toBeInTheDocument();
      });
    });
  });

  describe('not installed state (AC: 1, 5)', () => {
    it('shows "Server Installation" title when not installed', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockNotInstalledStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });

      expect(screen.getByTestId('version-page-title')).toHaveTextContent(
        'Server Installation'
      );
    });

    it('shows ServerInstallCard when server is not installed', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockNotInstalledStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });

      // ServerInstallCard should be rendered
      expect(screen.getByText('Install Server')).toBeInTheDocument();
      expect(
        screen.getByPlaceholderText('e.g., stable, unstable, 1.21.6')
      ).toBeInTheDocument();
    });
  });

  describe('installed state (AC: 2)', () => {
    it('shows "Server Version" title when installed', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockInstalledStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });

      expect(screen.getByTestId('version-page-title')).toHaveTextContent(
        'Server Version'
      );
    });

    it('shows installed version prominently', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockInstalledStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('installed-version-card')).toBeInTheDocument();
      });

      expect(screen.getByTestId('installed-version')).toHaveTextContent('1.21.5');
      expect(screen.getByText('Installed Version')).toBeInTheDocument();
    });

    it('shows server status badge when stopped (installed state)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockInstalledStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('installed-version-card')).toBeInTheDocument();
      });

      // 'installed' state shows as "Stopped" in ServerStatusBadge
      expect(screen.getByText('Stopped')).toBeInTheDocument();
    });

    it('shows server status badge when running', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockRunningStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('installed-version-card')).toBeInTheDocument();
      });

      expect(screen.getByText('Running')).toBeInTheDocument();
    });
  });

  describe('installing state (AC: 3)', () => {
    it('shows ServerInstallCard with progress during installation', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/install/status')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockInstallProgress),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstallingStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });

      // Should show ServerInstallCard in installing mode
      expect(screen.getByText('Installation in progress...')).toBeInTheDocument();

      // Wait for install status to load and show progress
      await waitFor(() => {
        expect(screen.getByText('45%')).toBeInTheDocument();
      });
      expect(screen.getByText('downloading')).toBeInTheDocument();
    });

    it('shows "Server Installation" title during installation', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockInstallingStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });

      expect(screen.getByTestId('version-page-title')).toHaveTextContent(
        'Server Installation'
      );
    });
  });

  describe('update available indicator (AC: 4)', () => {
    it('shows update available banner when newer version exists', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockInstalledStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('installed-version-card')).toBeInTheDocument();
      });

      // mockInstalledStatus has version 1.21.5 and availableStableVersion 1.21.6
      expect(screen.getByTestId('update-available-banner')).toBeInTheDocument();
      expect(screen.getByText('Update Available: 1.21.6')).toBeInTheDocument();
    });

    it('does not show update banner when version is current', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockRunningStatus),
      });

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('installed-version-card')).toBeInTheDocument();
      });

      // mockRunningStatus has version 1.21.6 and availableStableVersion 1.21.6 (same)
      expect(
        screen.queryByTestId('update-available-banner')
      ).not.toBeInTheDocument();
    });
  });
});
