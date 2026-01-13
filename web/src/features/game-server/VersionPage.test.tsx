import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
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

// Story 13.3: Mock versions list response
const mockVersionsList = {
  status: 'ok',
  data: {
    versions: [
      {
        version: '1.21.6',
        filename: 'vs_server_linux-x64_1.21.6.tar.gz',
        filesize: '45.2 MB',
        md5: 'abc123',
        cdn_url: 'https://cdn.example.com/1.21.6',
        local_url: '/local/1.21.6',
        is_latest: true,
        channel: 'stable',
      },
      {
        version: '1.21.5',
        filename: 'vs_server_linux-x64_1.21.5.tar.gz',
        filesize: '44.8 MB',
        md5: 'def456',
        cdn_url: 'https://cdn.example.com/1.21.5',
        local_url: '/local/1.21.5',
        is_latest: false,
        channel: 'stable',
      },
      {
        version: '1.22.0-pre.1',
        filename: 'vs_server_linux-x64_1.22.0-pre.1.tar.gz',
        filesize: '46.1 MB',
        md5: 'ghi789',
        cdn_url: 'https://cdn.example.com/1.22.0-pre.1',
        local_url: '/local/1.22.0-pre.1',
        is_latest: true,
        channel: 'unstable',
      },
    ],
    total: 3,
    cached: true,
    cached_at: '2026-01-13T10:00:00Z',
  },
};

const mockStableVersionsList = {
  status: 'ok',
  data: {
    versions: [
      {
        version: '1.21.6',
        filename: 'vs_server_linux-x64_1.21.6.tar.gz',
        filesize: '45.2 MB',
        md5: 'abc123',
        cdn_url: 'https://cdn.example.com/1.21.6',
        local_url: '/local/1.21.6',
        is_latest: true,
        channel: 'stable',
      },
      {
        version: '1.21.5',
        filename: 'vs_server_linux-x64_1.21.5.tar.gz',
        filesize: '44.8 MB',
        md5: 'def456',
        cdn_url: 'https://cdn.example.com/1.21.5',
        local_url: '/local/1.21.5',
        is_latest: false,
        channel: 'stable',
      },
    ],
    total: 2,
    cached: true,
    cached_at: '2026-01-13T10:00:00Z',
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

  /**
   * Story 13.5: Not installed state now shows version browser instead of ServerInstallCard
   */
  describe('not installed state (AC: 1, Story 13.5)', () => {
    it('shows "Server Installation" title when not installed', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockNotInstalledStatus),
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

      expect(screen.getByTestId('version-page-title')).toHaveTextContent(
        'Server Installation'
      );
    });

    it('shows version browser instead of ServerInstallCard when not installed', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockNotInstalledStatus),
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

      // Should NOT show ServerInstallCard anymore
      expect(screen.queryByText('Install Server')).not.toBeInTheDocument();
      expect(screen.queryByPlaceholderText('e.g., stable, unstable, 1.21.6')).not.toBeInTheDocument();

      // Should show version browser components
      await waitFor(() => {
        expect(screen.getByTestId('version-grid')).toBeInTheDocument();
      });
      expect(screen.getByTestId('channel-filter')).toBeInTheDocument();
      expect(screen.getByText('Available Versions')).toBeInTheDocument();
    });

    it('shows VersionGrid with versions when not installed', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockNotInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-grid')).toBeInTheDocument();
      });

      // Should show all versions
      expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      expect(screen.getByTestId('version-card-1.21.5')).toBeInTheDocument();
      expect(screen.getByTestId('version-card-1.22.0-pre.1')).toBeInTheDocument();
    });

    it('opens InstallVersionDialog on card click when not installed', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockNotInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Wait for versions to load
      await waitFor(() => {
        expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      });

      // Click a version card
      await user.click(screen.getByTestId('version-card-1.21.6'));

      // Dialog should open showing "Install" action (since not installed)
      await waitFor(() => {
        expect(screen.getByTestId('install-version-dialog')).toBeInTheDocument();
      });
      expect(screen.getByTestId('dialog-title')).toHaveTextContent('Install Server Version');
    });

    it('enables channel filter when not installed', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions?channel=stable')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockStableVersionsList),
          };
        }
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockNotInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('channel-filter')).toBeInTheDocument();
      });

      // Initially shows all versions including unstable
      await waitFor(() => {
        expect(screen.getByTestId('version-card-1.22.0-pre.1')).toBeInTheDocument();
      });

      // Click Stable tab
      await user.click(screen.getByTestId('channel-filter-stable'));

      // Wait for filtered results - unstable should be removed
      await waitFor(() => {
        expect(screen.queryByTestId('version-card-1.22.0-pre.1')).not.toBeInTheDocument();
      });

      // Stable versions should still be present
      expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      expect(screen.getByTestId('version-card-1.21.5')).toBeInTheDocument();
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

  /**
   * Story 13.3: Version List Section Tests
   *
   * AC 1: Available Versions section shown when installed
   * AC 2: Channel filter with All, Stable, Unstable tabs
   * AC 3: Filtering by channel works
   * AC 4: Versions sorted by version number (newest first - handled by API)
   */
  describe('version list section (Story 13.3)', () => {
    it('shows Available Versions section when installed (AC: 1)', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('available-versions-section')).toBeInTheDocument();
      });

      expect(screen.getByText('Available Versions')).toBeInTheDocument();
    });

    // Story 13.5: Now shows version browser when not installed too
    it('shows Available Versions section when not installed (Story 13.5)', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockNotInstalledStatus),
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

      // Story 13.5: Now shows available versions section even when not installed
      await waitFor(() => {
        expect(screen.getByTestId('available-versions-section')).toBeInTheDocument();
      });
    });

    it('renders ChannelFilter with All, Stable, Unstable tabs (AC: 2)', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('channel-filter')).toBeInTheDocument();
      });

      expect(screen.getByTestId('channel-filter-all')).toBeInTheDocument();
      expect(screen.getByTestId('channel-filter-stable')).toBeInTheDocument();
      expect(screen.getByTestId('channel-filter-unstable')).toBeInTheDocument();
    });

    it('renders VersionGrid with versions (AC: 4)', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-grid')).toBeInTheDocument();
      });

      // Should show all three versions
      expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      expect(screen.getByTestId('version-card-1.21.5')).toBeInTheDocument();
      expect(screen.getByTestId('version-card-1.22.0-pre.1')).toBeInTheDocument();
    });

    it('shows installed badge on current version', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-grid')).toBeInTheDocument();
      });

      // mockInstalledStatus has version 1.21.5 installed
      expect(screen.getByTestId('version-card-installed-1.21.5')).toBeInTheDocument();
      // Other versions should not show installed
      expect(screen.queryByTestId('version-card-installed-1.21.6')).not.toBeInTheDocument();
    });

    it('filters by channel when tab clicked (AC: 3)', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions?channel=stable')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockStableVersionsList),
          };
        }
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Wait for initial load
      await waitFor(() => {
        expect(screen.getByTestId('version-grid')).toBeInTheDocument();
      });

      // Initially shows all versions including unstable
      expect(screen.getByTestId('version-card-1.22.0-pre.1')).toBeInTheDocument();

      // Click Stable tab
      await user.click(screen.getByTestId('channel-filter-stable'));

      // Wait for filtered results - unstable should be removed
      await waitFor(() => {
        expect(screen.queryByTestId('version-card-1.22.0-pre.1')).not.toBeInTheDocument();
      });

      // Stable versions should still be present
      expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      expect(screen.getByTestId('version-card-1.21.5')).toBeInTheDocument();
    });

    it('shows loading skeleton while fetching versions', async () => {
      // Make versions request hang
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return new Promise(() => {}); // Never resolves
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('available-versions-section')).toBeInTheDocument();
      });

      // Should show loading state
      expect(screen.getByTestId('version-grid-loading')).toBeInTheDocument();
    });
  });

  /**
   * Story 13.4: Install/Upgrade Dialog Integration Tests
   *
   * AC 1: Dialog opens when clicking version card
   * AC 2: Dialog shows correct action type (upgrade/reinstall/downgrade)
   * AC 3: Dialog closes on cancel
   */
  describe('install/upgrade dialog (Story 13.4)', () => {
    it('opens dialog when clicking a version card (AC: 1)', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Wait for versions to load
      await waitFor(() => {
        expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      });

      // Click a version card
      await user.click(screen.getByTestId('version-card-1.21.6'));

      // Dialog should open
      await waitFor(() => {
        expect(screen.getByTestId('install-version-dialog')).toBeInTheDocument();
      });
    });

    it('shows upgrade dialog when selecting newer version (AC: 2)', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus), // version 1.21.5
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      });

      // Click newer version (1.21.6 vs installed 1.21.5)
      await user.click(screen.getByTestId('version-card-1.21.6'));

      await waitFor(() => {
        expect(screen.getByTestId('dialog-title')).toHaveTextContent('Upgrade Server Version');
      });
    });

    it('shows reinstall dialog when selecting same version (AC: 2)', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus), // version 1.21.5
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-card-1.21.5')).toBeInTheDocument();
      });

      // Click same version (1.21.5)
      await user.click(screen.getByTestId('version-card-1.21.5'));

      await waitFor(() => {
        expect(screen.getByTestId('dialog-title')).toHaveTextContent('Reinstall Server Version');
      });
    });

    it('closes dialog when cancel is clicked (AC: 3)', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
      });

      // Open dialog
      await user.click(screen.getByTestId('version-card-1.21.6'));

      await waitFor(() => {
        expect(screen.getByTestId('install-version-dialog')).toBeInTheDocument();
      });

      // Click cancel
      await user.click(screen.getByTestId('cancel-button'));

      // Dialog should close
      await waitFor(() => {
        expect(screen.queryByTestId('install-version-dialog')).not.toBeInTheDocument();
      });
    });

    it('shows server running warning when server is running', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockRunningStatus), // Server is running
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('version-card-1.21.5')).toBeInTheDocument();
      });

      // Click a different version
      await user.click(screen.getByTestId('version-card-1.21.5'));

      await waitFor(() => {
        expect(screen.getByTestId('server-running-warning')).toBeInTheDocument();
      });
    });
  });

  /**
   * Story 13.5: Quick Install Button Tests
   *
   * AC 4: Quick action buttons for install/update
   */
  describe('quick install button (Story 13.5)', () => {
    it('shows "Install Latest Stable" button when not installed', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockNotInstalledStatus),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('quick-install-button')).toBeInTheDocument();
      });

      // Check button contains the expected text
      const button = screen.getByTestId('quick-install-button');
      expect(button).toHaveTextContent(/Install Latest Stable/);
      expect(button).toHaveTextContent(/1\.21\.6/);
    });

    it('shows "Update to" button when update available', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockInstalledStatus), // version 1.21.5
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('quick-install-button')).toBeInTheDocument();
      });

      // Check button contains the expected text
      const button = screen.getByTestId('quick-install-button');
      expect(button).toHaveTextContent(/Update to/);
      expect(button).toHaveTextContent(/1\.21\.6/);
    });

    it('does not show button when version is current', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/versions')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockVersionsList),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockRunningStatus), // version 1.21.6 (current)
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<VersionPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Wait for page to load
      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });

      // Wait for versions to load
      await waitFor(() => {
        expect(screen.getByTestId('version-grid')).toBeInTheDocument();
      });

      // Button should not be present when up to date
      expect(screen.queryByTestId('quick-install-button')).not.toBeInTheDocument();
    });
  });
});
