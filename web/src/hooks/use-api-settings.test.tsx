import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { useApiSettings, useUpdateApiSetting } from './use-api-settings';

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

// Mock API settings data (snake_case as returned by API)
const mockApiSettings = {
  status: 'ok',
  data: {
    settings: {
      auto_start_server: false,
      block_env_managed_settings: true,
      enforce_env_on_restart: false,
      mod_list_refresh_interval: 3600,
      server_versions_refresh_interval: 86400,
    },
  },
};

describe('useApiSettings', () => {
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
    it('fetches API settings from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettings),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useApiSettings(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/api',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettings),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useApiSettings(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify camelCase transformation
      expect(result.current.data?.data.settings.autoStartServer).toBe(false);
      expect(result.current.data?.data.settings.blockEnvManagedSettings).toBe(true);
      expect(result.current.data?.data.settings.enforceEnvOnRestart).toBe(false);
      expect(result.current.data?.data.settings.modListRefreshInterval).toBe(3600);
      expect(result.current.data?.data.settings.serverVersionsRefreshInterval).toBe(86400);
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettings),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useApiSettings(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('returns all API settings', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettings),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useApiSettings(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const settings = result.current.data?.data.settings;
      expect(settings).toBeDefined();
      expect(typeof settings?.autoStartServer).toBe('boolean');
      expect(typeof settings?.blockEnvManagedSettings).toBe('boolean');
      expect(typeof settings?.modListRefreshInterval).toBe('number');
    });
  });
});

describe('useUpdateApiSetting', () => {
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
              key: 'auto_start_server',
              value: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useUpdateApiSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'auto_start_server', value: true });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/config/api/settings/auto_start_server',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ value: true }),
        })
      );
    });

    it('performs optimistic update for boolean settings', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          await new Promise((r) => setTimeout(r, 100));
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  key: 'auto_start_server',
                  value: true,
                },
              }),
          };
        }
        return { ok: true, json: () => Promise.resolve(mockApiSettings) };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with initial settings (camelCase as stored)
      queryClient.setQueryData(['config', 'api'], {
        status: 'ok',
        data: {
          settings: {
            autoStartServer: false,
            blockEnvManagedSettings: true,
            enforceEnvOnRestart: false,
            modListRefreshInterval: 3600,
            serverVersionsRefreshInterval: 86400,
          },
        },
      });

      const { result } = renderHook(() => useUpdateApiSetting(), {
        wrapper: createWrapper(queryClient),
      });

      // Start the mutation
      act(() => {
        result.current.mutate({ key: 'auto_start_server', value: true });
      });

      // Check optimistic update happened immediately
      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['config', 'api']) as {
          data: { settings: { autoStartServer: boolean } };
        };
        expect(cachedData.data.settings.autoStartServer).toBe(true);
      });
    });

    it('performs optimistic update for number settings', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          await new Promise((r) => setTimeout(r, 100));
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  key: 'mod_list_refresh_interval',
                  value: 7200,
                },
              }),
          };
        }
        return { ok: true, json: () => Promise.resolve(mockApiSettings) };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache
      queryClient.setQueryData(['config', 'api'], {
        status: 'ok',
        data: {
          settings: {
            autoStartServer: false,
            blockEnvManagedSettings: true,
            enforceEnvOnRestart: false,
            modListRefreshInterval: 3600,
            serverVersionsRefreshInterval: 86400,
          },
        },
      });

      const { result } = renderHook(() => useUpdateApiSetting(), {
        wrapper: createWrapper(queryClient),
      });

      // Start the mutation
      act(() => {
        result.current.mutate({ key: 'mod_list_refresh_interval', value: 7200 });
      });

      // Check optimistic update happened immediately
      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['config', 'api']) as {
          data: { settings: { modListRefreshInterval: number } };
        };
        expect(cachedData.data.settings.modListRefreshInterval).toBe(7200);
      });
    });

    it('invalidates API settings query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'auto_start_server',
              value: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useUpdateApiSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'auto_start_server', value: true });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['config', 'api'],
      });
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
                  code: 'API_SETTING_INVALID',
                  message: 'Invalid value for setting',
                },
              }),
          };
        }
        return { ok: true, json: () => Promise.resolve(mockApiSettings) };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with initial settings
      queryClient.setQueryData(['config', 'api'], {
        status: 'ok',
        data: {
          settings: {
            autoStartServer: false,
            blockEnvManagedSettings: true,
            enforceEnvOnRestart: false,
            modListRefreshInterval: 3600,
            serverVersionsRefreshInterval: 86400,
          },
        },
      });

      const { result } = renderHook(() => useUpdateApiSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'mod_list_refresh_interval', value: -1 });
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      // Check rollback happened
      const cachedData = queryClient.getQueryData(['config', 'api']) as {
        data: { settings: { modListRefreshInterval: number } };
      };
      expect(cachedData.data.settings.modListRefreshInterval).toBe(3600);
    });

    it('encodes special characters in key', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              key: 'some_key',
              value: 'test',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useUpdateApiSetting(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ key: 'some/special key', value: 'test' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/v1alpha1/config/api/settings/some%2Fspecial%20key'),
        expect.any(Object)
      );
    });
  });
});
