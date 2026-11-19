import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

// Story 21.4: the webhook test counts error toasts
vi.mock('sonner', () => ({
  toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() },
}));

import { toast } from 'sonner';
import { useApiSettings, useUpdateApiSetting, useSetModUpdateWebhook } from './use-api-settings';
import { handleApiError } from '@/api/error-handler';
import type { ApiResponse, ApiSettingsData } from '@/api/types';

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
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
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

describe('useUpdateApiSetting with a secret key (Story 14.6)', () => {
  const originalFetch = globalThis.fetch;

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('never writes the webhook URL into the cached settings', async () => {
    const mockFetch = vi.fn();
    globalThis.fetch = mockFetch;
    const queryClient = createTestQueryClient();
    queryClient.setQueryData(['config', 'api'], {
      status: 'ok',
      data: { settings: { autoStartServer: false, modUpdateWebhookConfigured: false } },
    });
    const { result } = renderHook(() => useUpdateApiSetting(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate({
        key: 'mod_update_webhook_url',
        value: 'https://discord.com/api/webhooks/1/cache-token',
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(JSON.stringify(queryClient.getQueryData(['config', 'api']))).not.toContain(
      'cache-token'
    );
    expect(mockFetch).not.toHaveBeenCalled();
  });
});

describe('useUpdateApiSetting and Scheduled Jobs (Story 17.6)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  function okFetch(key: string, value: number | boolean) {
    return vi.fn().mockResolvedValue({
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: { key, value } }),
    });
  }

  async function save(
    queryClient: QueryClient,
    key: string,
    value: number | boolean
  ): Promise<void> {
    const { result } = renderHook(() => useUpdateApiSetting(), {
      wrapper: createWrapper(queryClient),
    });
    await act(async () => {
      result.current.mutate({ key, value });
    });
    await waitFor(() => expect(result.current.isSuccess || result.current.isError).toBe(true));
  }

  it.each([
    'mod_list_refresh_interval',
    'server_versions_refresh_interval',
    'metrics_collection_interval',
  ])('invalidates the jobs query after saving %s', async (key) => {
    globalThis.fetch = okFetch(key, 600);
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    await save(queryClient, key, 600);

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['jobs'] });
    });
  });

  it('invalidates the jobs query when the save fails too (a not-applied save)', async () => {
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: () =>
        Promise.resolve({
          detail: {
            code: 'API_SETTING_NOT_APPLIED',
            message: 'Saved, but its job could not be rescheduled',
          },
        }),
    });
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    await save(queryClient, 'mod_list_refresh_interval', 600);

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['jobs'] });
    });
  });

  // Story 22.5: a not-applied save did save the value, so the cache keeps it
  it('keeps the saved value in the cache after API_SETTING_NOT_APPLIED', async () => {
    globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
      if (url.includes('/settings/')) {
        return {
          ok: false,
          status: 500,
          statusText: 'Internal Server Error',
          json: () =>
            Promise.resolve({
              detail: {
                code: 'API_SETTING_NOT_APPLIED',
                message: 'Saved, but its job could not be rescheduled',
              },
            }),
        };
      }
      // The refetch is held, so only onError can change the cache
      return new Promise(() => {});
    });
    const queryClient = createTestQueryClient();
    queryClient.setQueryData<ApiResponse<ApiSettingsData>>(['config', 'api'], {
      status: 'ok',
      data: {
        settings: {
          autoStartServer: false,
          blockEnvManagedSettings: true,
          enforceEnvOnRestart: false,
          modListRefreshInterval: 3600,
          serverVersionsRefreshInterval: 86400,
          metricsCollectionInterval: 10,
          modUpdateWebhookConfigured: false,
        },
      },
    });

    await save(queryClient, 'mod_list_refresh_interval', 0);

    const cached = queryClient.getQueryData<ApiResponse<ApiSettingsData>>(['config', 'api']);
    expect(cached?.data.settings.modListRefreshInterval).toBe(0);
  });

  it('does not invalidate the jobs query after saving auto_start_server', async () => {
    globalThis.fetch = okFetch('auto_start_server', true);
    const queryClient = createTestQueryClient();
    const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

    await save(queryClient, 'auto_start_server', true);

    await waitFor(() => {
      expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['config', 'api'] });
    });
    expect(invalidateSpy).not.toHaveBeenCalledWith({ queryKey: ['jobs'] });
  });
});

describe('useSetModUpdateWebhook reports errors once (Story 21.4)', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  it('shows only the caller toast for a refused webhook', async () => {
    const message = 'The webhook URL must be a Discord webhook.';
    globalThis.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: () => Promise.resolve({ detail: { code: 'INVALID_WEBHOOK_URL', message } }),
    });
    // Built like the app's query client: its default mutation onError shows a toast
    const queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
        mutations: { retry: false, onError: (error) => handleApiError(error) },
      },
    });
    const { result } = renderHook(() => useSetModUpdateWebhook(), {
      wrapper: createWrapper(queryClient),
    });

    await act(async () => {
      result.current.mutate('https://example.invalid/hook', {
        onError: (error) => {
          toast.error('Update failed', { description: error.message });
        },
      });
    });

    await waitFor(() => expect(result.current.isError).toBe(true));
    expect(toast.error).toHaveBeenCalledTimes(1);
    expect(toast.error).toHaveBeenCalledWith('Update failed', { description: message });
  });
});
