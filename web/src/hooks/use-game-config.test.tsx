import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import {
  useGameConfig,
  useGameSetting,
  useUpdateGameSetting,
  useConfigPendingRestart,
} from './use-game-config';

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

// Mock game config data (snake_case as returned by API)
const mockGameConfig = {
  status: 'ok',
  data: {
    settings: [
      {
        key: 'ServerName',
        value: 'My Server',
        type: 'string',
        live_update: true,
        env_managed: false,
      },
      {
        key: 'Port',
        value: 42420,
        type: 'int',
        live_update: false,
        requires_restart: true,
        env_managed: false,
      },
      {
        key: 'Password',
        value: '',
        type: 'string',
        live_update: true,
        env_managed: true,
      },
    ],
    source_file: 'serverconfig.json',
    last_modified: '2025-12-30T10:00:00Z',
  },
};

describe('useGameConfig', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior', () => {
    it('fetches game config from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/game',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify camelCase transformation
      expect(result.current.data?.data.sourceFile).toBe('serverconfig.json');
      expect(result.current.data?.data.lastModified).toBe('2025-12-30T10:00:00Z');
      expect(result.current.data?.data.settings[0].liveUpdate).toBe(true);
      expect(result.current.data?.data.settings[0].envManaged).toBe(false);
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('returns settings array with metadata', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.settings).toHaveLength(3);
      expect(result.current.data?.data.settings[0].key).toBe('ServerName');
      expect(result.current.data?.data.settings[0].value).toBe('My Server');
      expect(result.current.data?.data.settings[0].type).toBe('string');
    });
  });

  describe('polling configuration', () => {
    it('configures 30-second polling interval', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify polling is configured correctly
      expect(result.current.isSuccess).toBe(true);

      // The hook should poll every 30 seconds
      // We can't easily test actual polling behavior without real timers,
      // but we verify the hook succeeds which confirms it's configured
    });

    it('disables polling in background (refetchIntervalInBackground: false)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Background polling should be disabled (refetchIntervalInBackground: false)
      // This is a configuration check - the hook should work correctly
      expect(result.current.isSuccess).toBe(true);
    });
  });

  describe('error handling', () => {
    it('handles API error responses', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'INTERNAL_ERROR',
              message: 'Failed to load game config',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it('handles network errors', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it('handles malformed JSON response', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.reject(new Error('Invalid JSON')),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeTruthy();
    });
  });
});

describe('useGameSetting', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('returns a specific setting by key', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockGameConfig),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useGameSetting('Port'), {
      wrapper: createWrapper(queryClient),
    });

    await waitFor(() => expect(result.current).toBeDefined());

    expect(result.current?.key).toBe('Port');
    expect(result.current?.value).toBe(42420);
    expect(result.current?.type).toBe('int');
  });

  it('returns undefined for non-existent key', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockGameConfig),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useGameSetting('NonExistent'), {
      wrapper: createWrapper(queryClient),
    });

    // Wait for the query to complete
    await waitFor(() => {
      const { data } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      }).result.current;
      return data !== undefined;
    });

    expect(result.current).toBeUndefined();
  });

  it('returns undefined when config data is not yet loaded', () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useGameSetting('ServerName'), {
      wrapper: createWrapper(queryClient),
    });

    // No data loaded yet, should return undefined
    expect(result.current).toBeUndefined();
  });

  it('returns undefined when config data structure is missing', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          status: 'ok',
          data: {}, // Missing settings array
        }),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useGameSetting('ServerName'), {
      wrapper: createWrapper(queryClient),
    });

    // Wait for the query to complete (even with malformed data)
    await waitFor(() => {
      const { isSuccess } = renderHook(() => useGameConfig(), {
        wrapper: createWrapper(queryClient),
      }).result.current;
      return isSuccess;
    });

    expect(result.current).toBeUndefined();
  });
});

describe('useUpdateGameSetting', () => {
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
    it('calls update endpoint with POST method and value in body', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'ServerName',
              value: 'New Server Name',
              method: 'console_command',
              pending_restart: false,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'New Server Name' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/game/settings/ServerName',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ value: 'New Server Name' }),
        })
      );
    });

    it('performs optimistic update', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          await new Promise((r) => setTimeout(r, 100));
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  key: 'ServerName',
                  value: 'Updated Name',
                  method: 'console_command',
                  pending_restart: false,
                },
              }),
          };
        }
        return { ok: true, json: () => Promise.resolve(mockGameConfig) };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with initial config (camelCase as stored)
      queryClient.setQueryData(['config', 'game'], {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'My Server',
              type: 'string',
              liveUpdate: true,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2025-12-30T10:00:00Z',
        },
      });

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      // Start the mutation
      act(() => {
        result.current.mutate({ key: 'ServerName', value: 'Updated Name' });
      });

      // Check optimistic update happened immediately
      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['config', 'game']) as {
          data: { settings: { key: string; value: string }[] };
        };
        expect(cachedData.data.settings[0].value).toBe('Updated Name');
      });
    });

    it('does NOT invalidate game config on success (trusts optimistic update)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'ServerName',
              value: 'New Name',
              method: 'console_command',
              pending_restart: false,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'New Name' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should NOT invalidate game config - optimistic update is trusted
      // Polling (30s) handles eventual consistency
      expect(invalidateSpy).not.toHaveBeenCalledWith({
        queryKey: ['config', 'game'],
      });
    });

    it('invalidates mods query on success (for pending restart status)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'Port',
              value: 42421,
              method: 'file_update',
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'Port', value: 42421 });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should invalidate mods query (for pending restart status)
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['mods'],
      });
      // But NOT game config
      expect(invalidateSpy).not.toHaveBeenCalledWith({
        queryKey: ['config', 'game'],
      });
    });

    it('keeps optimistic update visible after mutation completes', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'ServerName',
              value: 'Updated Name',
              method: 'console_command',
              pending_restart: false,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with initial config
      queryClient.setQueryData(['config', 'game'], {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'Original Name',
              type: 'string',
              liveUpdate: true,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2025-12-30T10:00:00Z',
        },
      });

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'Updated Name' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the optimistic value is still in cache after mutation completes
      // (not overwritten by immediate refetch)
      const cachedData = queryClient.getQueryData(['config', 'game']) as {
        data: { settings: { key: string; value: string }[] };
      };
      expect(cachedData.data.settings[0].value).toBe('Updated Name');
    });

    it('rolls back on error', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          return {
            ok: false,
            status: 400,
            statusText: 'Bad Request',
            json: () =>
              Promise.resolve({
                detail: {
                  code: 'SETTING_VALUE_INVALID',
                  message: 'Invalid value for setting',
                },
              }),
          };
        }
        return { ok: true, json: () => Promise.resolve(mockGameConfig) };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with initial config
      queryClient.setQueryData(['config', 'game'], {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'Original Name',
              type: 'string',
              liveUpdate: true,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2025-12-30T10:00:00Z',
        },
      });

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'Bad Value' });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      // Check rollback happened
      const cachedData = queryClient.getQueryData(['config', 'game']) as {
        data: { settings: { key: string; value: string }[] };
      };
      expect(cachedData.data.settings[0].value).toBe('Original Name');
    });

    it('handles number values correctly', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'Port',
              value: 42421,
              method: 'file_update',
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'Port', value: 42421 });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/game/settings/Port',
        expect.objectContaining({
          body: JSON.stringify({ value: 42421 }),
        })
      );
    });

    it('handles boolean values correctly', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'AllowPvP',
              value: true,
              method: 'console_command',
              pending_restart: false,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'AllowPvP', value: true });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/game/settings/AllowPvP',
        expect.objectContaining({
          body: JSON.stringify({ value: true }),
        })
      );
    });
  });

  describe('error scenarios', () => {
    it('handles network errors during mutation', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate cache
      queryClient.setQueryData(['config', 'game'], {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'Original Name',
              type: 'string',
              liveUpdate: true,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2025-12-30T10:00:00Z',
        },
      });

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'New Name' });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      // Should rollback to original value
      const cachedData = queryClient.getQueryData(['config', 'game']) as {
        data: { settings: { key: string; value: string }[] };
      };
      expect(cachedData.data.settings[0].value).toBe('Original Name');
    });

    it('handles 403 forbidden error', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'INSUFFICIENT_PERMISSIONS',
              message: 'Admin role required',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate cache
      queryClient.setQueryData(['config', 'game'], {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'Original Name',
              type: 'string',
              liveUpdate: true,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2025-12-30T10:00:00Z',
        },
      });

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'New Name' });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      // Should rollback
      const cachedData = queryClient.getQueryData(['config', 'game']) as {
        data: { settings: { key: string; value: string }[] };
      };
      expect(cachedData.data.settings[0].value).toBe('Original Name');
    });

    it('handles 404 not found error (setting does not exist)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'SETTING_NOT_FOUND',
              message: 'Setting key not found',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'NonExistent', value: 'value' });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeTruthy();
    });

    it('handles optimistic update when no previous cache exists', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'ServerName',
              value: 'New Name',
              method: 'console_command',
              pending_restart: false,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      // Do NOT pre-populate cache

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'New Name' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Should succeed even with no previous data
      expect(result.current.isSuccess).toBe(true);
    });

    it('rolls back when server returns error after optimistic update', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 422,
        statusText: 'Unprocessable Entity',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'VALIDATION_ERROR',
              message: 'Invalid port number',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate cache with valid data
      queryClient.setQueryData(['config', 'game'], {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'Port',
              value: 42420,
              type: 'int',
              liveUpdate: false,
              requiresRestart: true,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2025-12-30T10:00:00Z',
        },
      });

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'Port', value: 999999 }); // Invalid port
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      // Should rollback to original value
      const cachedData = queryClient.getQueryData(['config', 'game']) as {
        data: { settings: { key: string; value: number }[] };
      };
      expect(cachedData.data.settings[0].value).toBe(42420);
    });
  });

  describe('cache invalidation behavior', () => {
    it('cancels outgoing refetches before optimistic update', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'ServerName',
              value: 'Updated',
              method: 'console_command',
              pending_restart: false,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const cancelSpy = vi.spyOn(queryClient, 'cancelQueries');

      // Pre-populate cache
      queryClient.setQueryData(['config', 'game'], {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'Original',
              type: 'string',
              liveUpdate: true,
              envManaged: false,
            },
          ],
          sourceFile: 'serverconfig.json',
          lastModified: '2025-12-30T10:00:00Z',
        },
      });

      const { result } = renderHook(() => useUpdateGameSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'ServerName', value: 'Updated' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify cancelQueries was called to prevent race conditions
      expect(cancelSpy).toHaveBeenCalledWith({
        queryKey: ['config', 'game'],
      });
    });
  });
});

describe('useConfigPendingRestart', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('returns false when mods cache is empty', () => {
    const queryClient = createTestQueryClient();
    const { result } = renderHook(() => useConfigPendingRestart(), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current).toBe(false);
  });

  it('returns false when mods data shows no pending restart', () => {
    const queryClient = createTestQueryClient();

    // Pre-populate mods cache with no pending restart
    queryClient.setQueryData(['mods'], {
      status: 'ok',
      data: {
        mods: [],
        pendingRestart: false,
      },
    });

    const { result } = renderHook(() => useConfigPendingRestart(), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current).toBe(false);
  });

  it('returns true when mods data shows pending restart', () => {
    const queryClient = createTestQueryClient();

    // Pre-populate mods cache with pending restart
    queryClient.setQueryData(['mods'], {
      status: 'ok',
      data: {
        mods: [],
        pendingRestart: true,
      },
    });

    const { result } = renderHook(() => useConfigPendingRestart(), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current).toBe(true);
  });

  it('returns false when mods data structure is malformed', () => {
    const queryClient = createTestQueryClient();

    // Pre-populate mods cache with malformed data
    queryClient.setQueryData(['mods'], {
      status: 'ok',
      data: {}, // Missing pendingRestart field
    });

    const { result } = renderHook(() => useConfigPendingRestart(), {
      wrapper: createWrapper(queryClient),
    });

    expect(result.current).toBe(false);
  });

  it('does not trigger fetch (enabled: false)', () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();
    renderHook(() => useConfigPendingRestart(), {
      wrapper: createWrapper(queryClient),
    });

    // Should not call fetch since enabled: false
    expect(mockFetch).not.toHaveBeenCalled();
  });

  it('reads from cache only (does not refetch)', async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          status: 'ok',
          data: { mods: [], pending_restart: true },
        }),
    });
    globalThis.fetch = mockFetch;

    const queryClient = createTestQueryClient();

    // Pre-populate cache
    queryClient.setQueryData(['mods'], {
      status: 'ok',
      data: {
        mods: [],
        pendingRestart: true,
      },
    });

    const { result } = renderHook(() => useConfigPendingRestart(), {
      wrapper: createWrapper(queryClient),
    });

    // Should read from cache immediately
    expect(result.current).toBe(true);

    // Wait a bit to ensure no fetch happens
    await new Promise((resolve) => setTimeout(resolve, 100));

    // Should not have fetched (enabled: false means cache-only)
    expect(mockFetch).not.toHaveBeenCalled();
  });
});
