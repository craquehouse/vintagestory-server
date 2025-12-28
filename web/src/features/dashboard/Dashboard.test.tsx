import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { Dashboard } from './Dashboard';
import type { ServerStatus, InstallStatus } from '@/api/types';

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

// Wrapper component for rendering with providers
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
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
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8000';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('not installed state (AC: 1)', () => {
    it('shows ServerInstallCard when server is not installed', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus({
          state: 'not_installed',
          version: null,
          uptimeSeconds: null,
          lastExitCode: null,
        })
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Install Server')).toBeInTheDocument();
      });

      // Should show version input and install button
      expect(screen.getByRole('textbox', { name: /server version/i })).toBeInTheDocument();
    });

    it('hides server control buttons when not installed', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus({
          state: 'not_installed',
          version: null,
          uptimeSeconds: null,
          lastExitCode: null,
        })
      );
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Install Server')).toBeInTheDocument();
      });

      // Control buttons should not be visible
      expect(screen.queryByRole('button', { name: 'Start server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Stop server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Restart server' })).not.toBeInTheDocument();
    });
  });

  describe('installing state (AC: 2)', () => {
    it('shows progress indicator during installation', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/status') && !url.includes('/install/status')) {
          return Promise.resolve(
            mockServerStatus({
              state: 'installing',
              version: null,
              uptimeSeconds: null,
              lastExitCode: null,
            })
          );
        }
        if (url.includes('/install/status')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  state: 'downloading',
                  progress: 50,
                  message: 'Downloading...',
                } as InstallStatus,
              }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByRole('status', { name: /installation progress/i })).toBeInTheDocument();
      });
    });

    it('disables install button during installation', async () => {
      const mockFetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/status') && !url.includes('/install/status')) {
          return Promise.resolve(
            mockServerStatus({
              state: 'installing',
              version: null,
              uptimeSeconds: null,
              lastExitCode: null,
            })
          );
        }
        if (url.includes('/install/status')) {
          return Promise.resolve({
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  state: 'downloading',
                  progress: 50,
                  message: 'Downloading...',
                } as InstallStatus,
              }),
          });
        }
        return Promise.reject(new Error('Unknown URL'));
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<Dashboard />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByRole('status', { name: /installation progress/i })).toBeInTheDocument();
      });

      // Install button should not be visible during installation (progress is shown instead)
      expect(screen.queryByRole('button', { name: /install server/i })).not.toBeInTheDocument();
    });
  });

  describe('stopped state (AC: 3)', () => {
    it('shows ServerStatusBadge with Stopped status', async () => {
      const mockFetch = vi.fn().mockResolvedValue(
        mockServerStatus({
          state: 'installed',
          version: '1.21.3',
          uptimeSeconds: null,
          lastExitCode: null,
        })
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
        mockServerStatus({
          state: 'installed',
          version: '1.21.3',
          uptimeSeconds: null,
          lastExitCode: null,
        })
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
        mockServerStatus({
          state: 'installed',
          version: '1.21.3',
          uptimeSeconds: null,
          lastExitCode: null,
        })
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
        mockServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
          lastExitCode: null,
        })
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
        mockServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3660, // 1 hour, 1 minute
          lastExitCode: null,
        })
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
        mockServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
          lastExitCode: null,
        })
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
        mockServerStatus({
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
          lastExitCode: null,
        })
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
        'http://localhost:8000/api/v1alpha1/server/status',
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
