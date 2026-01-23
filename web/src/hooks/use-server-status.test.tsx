import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { toast } from 'sonner';
import {
  useServerStatus,
  useStartServer,
  useStopServer,
  useRestartServer,
  useInstallServer,
  useUninstallServer,
  useServerStateToasts,
} from './use-server-status';
import type { ServerState } from '../api/types';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
  },
}));

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

// Wrapper component for rendering hooks with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('useServerStatus', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior (AC: 6)', () => {
    it('fetches server status from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              state: 'running',
              version: '1.21.3',
              uptime_seconds: 3600,
              last_exit_code: null,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useServerStatus(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/server/status',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              state: 'running',
              version: '1.21.3',
              uptime_seconds: 7200,
              last_exit_code: null,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useServerStatus(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify camelCase transformation
      expect(result.current.data?.data.uptimeSeconds).toBe(7200);
      expect(result.current.data?.data.lastExitCode).toBe(null);
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { state: 'installed', version: null, uptime_seconds: null, last_exit_code: null },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useServerStatus(), {
        wrapper: createWrapper(queryClient),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });
  });
});

describe('useStartServer', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior (AC: 5)', () => {
    it('calls start endpoint with POST method', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server starting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useStartServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/server/start',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('provides pending state during mutation', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      const mockFetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve({ status: 'ok', data: { message: 'Started' } }),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useStartServer(), {
        wrapper: createWrapper(queryClient),
      });

      // Start mutation
      act(() => {
        result.current.mutate();
      });

      // Should be pending
      await waitFor(() => expect(result.current.isPending).toBe(true));

      // Resolve the promise
      await act(async () => {
        resolvePromise!();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isPending).toBe(false);
    });

    it('invalidates server status query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server starting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useStartServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['server', 'status'],
      });
    });

    it('optimistically updates state to starting when valid data exists', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server starting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Set initial valid query data
      queryClient.setQueryData(['server', 'status'], {
        status: 'ok',
        data: {
          state: 'installed',
          version: '1.21.3',
          uptimeSeconds: null,
          lastExitCode: null,
        },
      });

      const { result } = renderHook(() => useStartServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.isSuccess).toBe(true);
    });

    it('handles optimistic update with no prior query data', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server starting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useStartServer(), {
        wrapper: createWrapper(queryClient),
      });

      // Don't set any prior query data
      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should complete successfully even without prior data
      expect(result.current.isSuccess).toBe(true);
    });

    it('handles optimistic update with malformed query data', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server starting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Set malformed data (no 'data' property)
      queryClient.setQueryData(['server', 'status'], { status: 'ok' });

      const { result } = renderHook(() => useStartServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should complete successfully even with malformed data
      expect(result.current.isSuccess).toBe(true);
    });

    it('rolls back optimistic update on error', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Set initial query data
      const initialData = {
        status: 'ok',
        data: {
          state: 'installed',
          version: '1.21.3',
          uptimeSeconds: null,
          lastExitCode: null,
        },
      };
      queryClient.setQueryData(['server', 'status'], initialData);

      const { result } = renderHook(() => useStartServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      // Query data should be rolled back to initial state
      const queryData = queryClient.getQueryData(['server', 'status']);
      expect(queryData).toEqual(initialData);
    });
  });
});

describe('useStopServer', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior (AC: 5)', () => {
    it('calls stop endpoint with POST method', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server stopping' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useStopServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/server/stop',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('optimistically updates state to stopping when valid data exists', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server stopping' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Set initial valid query data
      queryClient.setQueryData(['server', 'status'], {
        status: 'ok',
        data: {
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
          lastExitCode: null,
        },
      });

      const { result } = renderHook(() => useStopServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.isSuccess).toBe(true);
    });

    it('handles optimistic update with no prior query data', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server stopping' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useStopServer(), {
        wrapper: createWrapper(queryClient),
      });

      // Don't set any prior query data
      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should complete successfully even without prior data
      expect(result.current.isSuccess).toBe(true);
    });

    it('handles optimistic update with malformed query data', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server stopping' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Set malformed data (no 'data' property)
      queryClient.setQueryData(['server', 'status'], { status: 'ok' });

      const { result } = renderHook(() => useStopServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should complete successfully even with malformed data
      expect(result.current.isSuccess).toBe(true);
    });

    it('rolls back optimistic update on error', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Set initial query data
      const initialData = {
        status: 'ok',
        data: {
          state: 'running',
          version: '1.21.3',
          uptimeSeconds: 3600,
          lastExitCode: null,
        },
      };
      queryClient.setQueryData(['server', 'status'], initialData);

      const { result } = renderHook(() => useStopServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      // Query data should be rolled back to initial state
      const queryData = queryClient.getQueryData(['server', 'status']);
      expect(queryData).toEqual(initialData);
    });

    it('invalidates server status query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server stopping' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useStopServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['server', 'status'],
      });
    });
  });
});

describe('useRestartServer', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior (AC: 5)', () => {
    it('calls restart endpoint with POST method', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server restarting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useRestartServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/server/restart',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('invalidates server status query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server restarting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useRestartServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['server', 'status'],
      });
    });
  });
});

describe('useInstallServer', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior', () => {
    it('calls install endpoint with POST method and version in body', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Installation started' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useInstallServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('1.21.3');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/server/install',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ version: '1.21.3' }),
        })
      );
    });

    it('provides pending state during mutation', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      const mockFetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve({ status: 'ok', data: { message: 'Started' } }),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useInstallServer(), {
        wrapper: createWrapper(queryClient),
      });

      // Start mutation
      act(() => {
        result.current.mutate('1.21.3');
      });

      // Should be pending
      await waitFor(() => expect(result.current.isPending).toBe(true));

      // Resolve the promise
      await act(async () => {
        resolvePromise!();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isPending).toBe(false);
    });

    it('invalidates server status query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Installation started' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useInstallServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('1.21.3');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['server', 'status'],
      });
    });

    // Story 13.4: Test versions query invalidation
    it('invalidates versions query on success (Story 13.4)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Installation started' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useInstallServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('1.21.3');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify both server.status and versions are invalidated
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['server', 'status'],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['versions'],
      });
    });
  });
});

/**
 * Story 13.7: useUninstallServer Tests
 */
describe('useUninstallServer', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior (Story 13.7)', () => {
    it('calls DELETE /api/v1alpha1/server endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { state: 'not_installed' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useUninstallServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/server',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('invalidates server status query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { state: 'not_installed' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUninstallServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['server', 'status'],
      });
    });

    it('invalidates versions query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { state: 'not_installed' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUninstallServer(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate();
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify both server.status and versions are invalidated
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['server', 'status'],
      });
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['versions'],
      });
    });
  });
});

describe('useServerStateToasts', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('server started toast (UI-004)', () => {
    it('shows toast when transitioning from starting to running', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: 'starting' as ServerState } }
      );

      // Transition to running
      rerender({ state: 'running' as ServerState });

      expect(toast.success).toHaveBeenCalledWith('Server started', {
        description: 'The server is now running.',
      });
    });

    it('does not show toast when running without prior starting state', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: 'installed' as ServerState } }
      );

      // Transition directly to running (shouldn't happen normally, but tests the guard)
      rerender({ state: 'running' as ServerState });

      expect(toast.success).not.toHaveBeenCalled();
    });
  });

  describe('server stopped toast (UI-004)', () => {
    it('shows toast when transitioning from stopping to installed', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: 'stopping' as ServerState } }
      );

      // Transition to installed (stopped)
      rerender({ state: 'installed' as ServerState });

      expect(toast.success).toHaveBeenCalledWith('Server stopped', {
        description: 'The server has stopped.',
      });
    });

    it('does not show toast when installed without prior stopping state', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: 'running' as ServerState } }
      );

      // Transition directly to installed (shouldn't happen normally)
      rerender({ state: 'installed' as ServerState });

      expect(toast.success).not.toHaveBeenCalled();
    });
  });

  // Story 13.4: Installation complete toast
  describe('installation complete toast (Story 13.4)', () => {
    it('shows toast when transitioning from installing to installed', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: 'installing' as ServerState } }
      );

      // Transition to installed (installation complete)
      rerender({ state: 'installed' as ServerState });

      expect(toast.success).toHaveBeenCalledWith('Installation complete', {
        description: 'The server has been installed successfully.',
      });
    });

    it('does not show toast when installed without prior installing state', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: 'not_installed' as ServerState } }
      );

      // Transition directly to installed (shouldn't happen normally)
      rerender({ state: 'installed' as ServerState });

      expect(toast.success).not.toHaveBeenCalled();
    });
  });

  describe('edge cases', () => {
    it('does not show toast on initial render', () => {
      renderHook(() => useServerStateToasts('running'));

      expect(toast.success).not.toHaveBeenCalled();
    });

    it('handles undefined state gracefully', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: undefined as ServerState | undefined } }
      );

      rerender({ state: 'running' as ServerState });

      expect(toast.success).not.toHaveBeenCalled();
    });

    it('handles transition from undefined to starting without toast', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: undefined as ServerState | undefined } }
      );

      rerender({ state: 'starting' as ServerState });

      expect(toast.success).not.toHaveBeenCalled();
    });

    it('does not show toast for other state transitions', () => {
      const { rerender } = renderHook(
        ({ state }) => useServerStateToasts(state),
        { initialProps: { state: 'installed' as ServerState } }
      );

      // installed -> starting
      rerender({ state: 'starting' as ServerState });
      expect(toast.success).not.toHaveBeenCalled();

      // starting -> stopping (error case)
      rerender({ state: 'stopping' as ServerState });
      expect(toast.success).not.toHaveBeenCalled();
    });
  });
});
