import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { toast } from 'sonner';
import { ApiSettingsPanel } from './ApiSettingsPanel';
import { forgetRememberedDurations } from '@/components/DurationSettingField';

/**
 * Tests for ApiSettingsPanel component.
 */

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
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

// Wrapper component for rendering with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// Mock API settings response (camelCase as transformed by apiClient)
const mockApiSettingsCamelCase = {
  status: 'ok',
  data: {
    settings: {
      autoStartServer: true,
      blockEnvManagedSettings: true,
      enforceEnvOnRestart: true,
      modListRefreshInterval: 300,
      serverVersionsRefreshInterval: 3600,
      metricsCollectionInterval: 10,
      modUpdateWebhookConfigured: true,
      scheduledRestartTimes: [],
      backupKeepCount: 0,
    },
  },
};

// Mock debug status response (VSS-c9o)
const mockDebugStatusEnabled = {
  status: 'ok',
  data: {
    debugEnabled: true,
  },
};

const mockDebugStatusDisabled = {
  status: 'ok',
  data: {
    debugEnabled: false,
  },
};

type FetchCall = [string, RequestInit | undefined];

/**
 * Story 22.5: serve the given settings for every GET and answer every POST with
 * `postResponse` (a successful save by default); returns the fetch mock.
 */
function serveSettings(
  settings: Record<string, unknown>,
  postResponse?: (url: string, saved: Record<string, unknown>) => unknown
) {
  // The server's settings: a successful save changes what the next GET returns
  const saved: Record<string, unknown> = { ...settings };
  const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
    if (options?.method === 'POST') {
      if (postResponse) return postResponse(url, saved);
      const body: { value: unknown } = JSON.parse(String(options.body));
      const key = url.slice(url.lastIndexOf('/') + 1);
      saved[toCamel(key)] = body.value;
      return {
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: { key, value: body.value } }),
      };
    }
    if (url.includes('/debug')) {
      return { ok: true, json: () => Promise.resolve(mockDebugStatusDisabled) };
    }
    return {
      ok: true,
      json: () => Promise.resolve({ status: 'ok', data: { settings: { ...saved } } }),
    };
  });
  globalThis.fetch = mockFetch;
  return mockFetch;
}

function toCamel(key: string): string {
  return key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());
}

function postCalls(mockFetch: ReturnType<typeof vi.fn>): FetchCall[] {
  return mockFetch.mock.calls.filter(
    (call): call is FetchCall => typeof call[0] === 'string' && call[1]?.method === 'POST'
  );
}

async function renderPanel() {
  const queryClient = createTestQueryClient();
  render(<ApiSettingsPanel />, { wrapper: createWrapper(queryClient) });
  await waitFor(() => {
    expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
  });
  return queryClient;
}

describe('ApiSettingsPanel', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    forgetRememberedDurations();
  });

  describe('loading state', () => {
    it('shows skeleton loader while loading', () => {
      // Make fetch never resolve
      globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('api-settings-loading')).toBeInTheDocument();
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
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Failed to load settings')).toBeInTheDocument();
    });

    it('shows fallback error message when error.message is empty', async () => {
      // Mock an error without a statusText to create an error with empty message
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: '',
        json: () => Promise.resolve({}),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Unable to load API settings')).toBeInTheDocument();
    });
  });

  describe('rendering settings', () => {
    it('renders all setting groups when loaded', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Check for group titles
      expect(screen.getByText('Server Behavior')).toBeInTheDocument();
      expect(screen.getByText('Environment Variables')).toBeInTheDocument();
      expect(screen.getByText('Refresh Intervals')).toBeInTheDocument();
    });

    it('uses default values when settings are undefined', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: {
                settings: {
                  // All settings are undefined
                },
              },
            }),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // auto_start_server should default to false
      const autoStartToggle = screen.getByLabelText('Auto-Start Server');
      expect(autoStartToggle).toHaveAttribute('data-state', 'unchecked');

      // block_env_managed_settings should default to true
      const blockEnvToggle = screen.getByLabelText('Block Env-Managed Settings');
      expect(blockEnvToggle).toHaveAttribute('data-state', 'checked');

      // Story 22.5: enforce_env_on_restart defaults to false, as in the API
      const enforceEnvToggle = screen.getByLabelText('Enforce Env on Restart');
      expect(enforceEnvToggle).toHaveAttribute('data-state', 'unchecked');

      // mod_list_refresh_interval should default to 14400 (4h)
      expect(screen.getByLabelText('Mod List Refresh')).toHaveValue('4h');

      // Story 22.5: server_versions_refresh_interval defaults to 86400 (1d), as in the API
      expect(screen.getByLabelText('Server Versions Refresh')).toHaveValue('1d');
    });

    it('renders the Update Alerts group with the webhook status (Story 14.6)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      render(<ApiSettingsPanel />, { wrapper: createWrapper(createTestQueryClient()) });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });
      expect(screen.getByText('Update Alerts')).toBeInTheDocument();
      expect(screen.getByTestId('mod-update-webhook-status')).toHaveTextContent('Configured');
    });

    it('renders auto_start_server toggle', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      expect(screen.getByLabelText('Auto-Start Server')).toBeInTheDocument();
    });

    it('renders block_env_managed_settings toggle', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      expect(screen.getByLabelText('Block Env-Managed Settings')).toBeInTheDocument();
    });

    it('renders enforce_env_on_restart toggle', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      expect(screen.getByLabelText('Enforce Env on Restart')).toBeInTheDocument();
    });

    it('renders mod_list_refresh_interval input', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // VSS-s9s: Now displays human-readable duration (5m = 300s)
      expect(screen.getByLabelText('Mod List Refresh')).toHaveValue('5m');
    });

    it('renders server_versions_refresh_interval input', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // VSS-s9s: Now displays human-readable duration (1h = 3600s)
      expect(screen.getByLabelText('Server Versions Refresh')).toHaveValue('1h');
    });
  });

  describe('updating settings', () => {
    it('calls API on toggle change', async () => {
      const mockFetch = vi.fn().mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  key: 'auto_start_server',
                  value: false,
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Click the auto-start toggle
      const toggle = screen.getByLabelText('Auto-Start Server');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/config/api/settings/auto_start_server'),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    it('shows success toast on successful toggle update', async () => {
      const mockFetch = vi.fn().mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  key: 'auto_start_server',
                  value: false,
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Click the auto-start toggle
      const toggle = screen.getByLabelText('Auto-Start Server');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('auto_start_server updated');
      });
    });

    it('shows error toast on failed toggle update', async () => {
      const mockFetch = vi.fn().mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return {
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            json: () => Promise.resolve({ detail: 'Database connection failed' }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Click the auto-start toggle
      const toggle = screen.getByLabelText('Auto-Start Server');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Update failed',
          expect.objectContaining({
            description: 'Database connection failed',
          })
        );
      });
    });

    it('shows fallback error toast when update fails with non-Error object', async () => {
      const mockFetch = vi.fn().mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          // Reject with a non-Error object
          return Promise.reject('Network timeout');
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Click the auto-start toggle
      const toggle = screen.getByLabelText('Auto-Start Server');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Update failed',
          expect.objectContaining({
            description: 'Failed to update setting',
          })
        );
      });
    });

    it('shows a warning toast, not "Update failed", when the save is not applied (Story 17.6)', async () => {
      const notApplied =
        "Saved 'mod_list_refresh_interval', but its job could not be rescheduled: boom. " +
        'The saved value applies when the API restarts.';
      const mockFetch = vi.fn().mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return {
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            json: () =>
              Promise.resolve({
                detail: { code: 'API_SETTING_NOT_APPLIED', message: notApplied },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      const input = screen.getByLabelText('Mod List Refresh');
      fireEvent.change(input, { target: { value: '10m' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(toast.warning).toHaveBeenCalledWith('Saved, not applied yet', {
          description: notApplied,
        });
      });
      expect(toast.warning).toHaveBeenCalledTimes(1);
      expect(toast.error).not.toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
    });

    it('calls API on duration field blur with changed value', async () => {
      const mockFetch = vi.fn().mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  key: 'mod_list_refresh_interval',
                  value: 600,
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Change the mod list refresh interval
      const input = screen.getByLabelText('Mod List Refresh');
      fireEvent.change(input, { target: { value: '10m' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/config/api/settings/mod_list_refresh_interval'),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    it('shows success toast on successful duration field update', async () => {
      const mockFetch = vi.fn().mockImplementation(async (_url: string, options?: RequestInit) => {
        if (options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  key: 'mod_list_refresh_interval',
                  value: 600,
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Change the mod list refresh interval
      const input = screen.getByLabelText('Mod List Refresh');
      fireEvent.change(input, { target: { value: '10m' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('mod_list_refresh_interval updated');
      });
    });

    it('does not call API on blur without value change', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Focus and blur without changing value
      const input = screen.getByLabelText('Mod List Refresh');
      fireEvent.focus(input);
      fireEvent.blur(input);

      // Wait a bit to ensure no additional calls
      await new Promise((resolve) => setTimeout(resolve, 100));

      // Should not have made any POST calls
      expect(mockFetch.mock.calls.filter((call) => call[1]?.method === 'POST')).toHaveLength(0);
    });
  });

  describe('validation', () => {
    it('shows validation error for mod_list_refresh_interval below minimum', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // VSS-s9s: Enter invalid value (too low - 5s is less than min of 60s/1m)
      const input = screen.getByLabelText('Mod List Refresh');
      fireEvent.change(input, { target: { value: '5s' } });
      fireEvent.blur(input);

      await waitFor(() => {
        // New error message uses human-readable format
        expect(screen.getByText('Must be at least 1m')).toBeInTheDocument();
      });
    });

    it('shows validation error for mod_list_refresh_interval above maximum', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Story 22.5: too high - 400d > 365d, the API's maximum
      const input = screen.getByLabelText('Mod List Refresh');
      fireEvent.change(input, { target: { value: '400d' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText('Must be at most 365d')).toBeInTheDocument();
      });
    });

    it('shows validation error for server_versions_refresh_interval out of range', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Story 22.5: too high - 400d > 365d, the API's maximum
      const input = screen.getByLabelText('Server Versions Refresh');
      fireEvent.change(input, { target: { value: '400d' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText('Must be at most 365d')).toBeInTheDocument();
      });
    });
  });

  describe('refresh bounds and defaults (Story 22.5)', () => {
    const loaded = { ...mockApiSettingsCamelCase.data.settings };

    for (const label of ['Mod List Refresh', 'Server Versions Refresh']) {
      it(`${label}: refuses 30s with the min message and saves nothing`, async () => {
        const mockFetch = serveSettings(loaded);
        await renderPanel();

        const input = screen.getByLabelText(label);
        fireEvent.change(input, { target: { value: '30s' } });
        fireEvent.blur(input);

        await waitFor(() => {
          expect(screen.getByText('Must be at least 1m')).toBeInTheDocument();
        });
        expect(postCalls(mockFetch)).toHaveLength(0);
      });

      it(`${label}: refuses 400d with the max message and saves nothing`, async () => {
        const mockFetch = serveSettings(loaded);
        await renderPanel();

        const input = screen.getByLabelText(label);
        fireEvent.change(input, { target: { value: '400d' } });
        fireEvent.blur(input);

        await waitFor(() => {
          expect(screen.getByText('Must be at most 365d')).toBeInTheDocument();
        });
        expect(postCalls(mockFetch)).toHaveLength(0);
      });

      it(`${label}: saves 2d`, async () => {
        const mockFetch = serveSettings(loaded);
        await renderPanel();

        const input = screen.getByLabelText(label);
        fireEvent.change(input, { target: { value: '2d' } });
        fireEvent.blur(input);

        await waitFor(() => {
          expect(toast.success).toHaveBeenCalledTimes(1);
        });
        const posts = postCalls(mockFetch);
        expect(posts).toHaveLength(1);
        expect(JSON.parse(String(posts[0][1]?.body))).toEqual({ value: 172800 });
      });
    }

    it('shows the API defaults when the settings are missing', async () => {
      serveSettings({});
      await renderPanel();

      expect(screen.getByLabelText('Server Versions Refresh')).toHaveValue('1d');
      expect(screen.getByLabelText('Enforce Env on Restart')).toHaveAttribute(
        'data-state',
        'unchecked'
      );
      expect(screen.getByLabelText('Mod List Refresh')).toHaveValue('4h');
      expect(screen.getByLabelText('Auto-Start Server')).toHaveAttribute('data-state', 'unchecked');
      expect(screen.getByLabelText('Block Env-Managed Settings')).toHaveAttribute(
        'data-state',
        'checked'
      );
    });
  });

  describe('interval switches (Story 22.5)', () => {
    const loaded = { ...mockApiSettingsCamelCase.data.settings };
    const switches = [
      ['Mod List Refresh', 'mod_list_refresh_interval'],
      ['Server Versions Refresh', 'server_versions_refresh_interval'],
      ['Metrics Collection', 'metrics_collection_interval'],
    ] as const;

    function failWith(code: string | null, message: string) {
      return {
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ detail: code ? { code, message } : { message } }),
      };
    }

    it('shows an On switch per interval, checked with the loaded values', async () => {
      serveSettings(loaded);
      await renderPanel();

      for (const [label] of switches) {
        expect(screen.getByRole('switch', { name: `${label} On` })).toHaveAttribute(
          'aria-checked',
          'true'
        );
      }
    });

    it('describes each switch by its help text', async () => {
      serveSettings(loaded);
      await renderPanel();

      for (const [label, key] of switches) {
        expect(screen.getByRole('switch', { name: `${label} On` })).toHaveAttribute(
          'aria-describedby',
          `${key}-desc`
        );
      }
    });

    it('shows Metrics Collection from the settings', async () => {
      serveSettings({ ...loaded, metricsCollectionInterval: 30 });
      await renderPanel();
      expect(screen.getByLabelText('Metrics Collection')).toHaveValue('30s');
    });

    it('shows Metrics Collection at 10s when the setting is missing', async () => {
      serveSettings({});
      await renderPanel();
      expect(screen.getByLabelText('Metrics Collection')).toHaveValue('10s');
    });

    it('says what stops and what keeps working when Metrics Collection is off', async () => {
      serveSettings(loaded);
      await renderPanel();

      expect(
        screen.getByText(/charts and its memory and players cards stop updating/)
      ).toBeInTheDocument();
      expect(screen.getByText(/\/metrics is read live and keeps working/)).toBeInTheDocument();
    });

    it.each([
      ['0', 'Must be at least 1s'],
      ['2h', 'Must be at most 1h'],
    ])('Metrics Collection refuses %s and saves nothing', async (typed, message) => {
      const mockFetch = serveSettings(loaded);
      await renderPanel();

      const input = screen.getByLabelText('Metrics Collection');
      fireEvent.change(input, { target: { value: typed } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText(message)).toBeInTheDocument();
      });
      expect(postCalls(mockFetch)).toHaveLength(0);
    });

    it('Metrics Collection saves 30s', async () => {
      const mockFetch = serveSettings(loaded);
      await renderPanel();

      const input = screen.getByLabelText('Metrics Collection');
      fireEvent.change(input, { target: { value: '30s' } });
      fireEvent.blur(input);

      await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
      const posts = postCalls(mockFetch);
      expect(posts).toHaveLength(1);
      expect(posts[0][0]).toMatch(/\/config\/api\/settings\/metrics_collection_interval$/);
      expect(JSON.parse(String(posts[0][1]?.body))).toEqual({ value: 30 });
    });

    it('turning Mod List Refresh off saves 0 with one success toast and shows Off', async () => {
      const mockFetch = serveSettings(loaded);
      await renderPanel();

      fireEvent.click(screen.getByRole('switch', { name: 'Mod List Refresh On' }));

      await waitFor(() => {
        expect(screen.getByTestId('mod_list_refresh_interval-off')).toHaveTextContent('Off');
      });
      await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
      expect(toast.success).toHaveBeenCalledWith('mod_list_refresh_interval updated');
      expect(toast.error).not.toHaveBeenCalled();
      const posts = postCalls(mockFetch);
      expect(posts).toHaveLength(1);
      expect(posts[0][0]).toMatch(/\/config\/api\/settings\/mod_list_refresh_interval$/);
      expect(posts[0][1]?.body).toBe('{"value":0}');
      expect(screen.queryByLabelText('Mod List Refresh')).not.toBeInTheDocument();
    });

    it.each([
      ['Mod List Refresh', 'mod_list_refresh_interval', 'modListRefreshInterval', 14400, '4h'],
      [
        'Server Versions Refresh',
        'server_versions_refresh_interval',
        'serverVersionsRefreshInterval',
        86400,
        '1d',
      ],
      ['Metrics Collection', 'metrics_collection_interval', 'metricsCollectionInterval', 10, '10s'],
    ])(
      '%s loaded off shows Off, and turning it on saves the API default',
      async (label, key, camelKey, seconds, shown) => {
        const mockFetch = serveSettings({ ...loaded, [camelKey]: 0 });
        await renderPanel();

        const toggle = screen.getByRole('switch', { name: `${label} On` });
        expect(toggle).toHaveAttribute('aria-checked', 'false');
        expect(screen.getByTestId(`${key}-off`)).toHaveTextContent('Off');

        fireEvent.click(toggle);

        await waitFor(() => expect(screen.getByLabelText(label)).toHaveValue(shown));
        const posts = postCalls(mockFetch);
        expect(posts).toHaveLength(1);
        expect(JSON.parse(String(posts[0][1]?.body))).toEqual({ value: seconds });
      }
    );

    it('a failed switch save shows one error toast and puts the switch back', async () => {
      serveSettings(loaded, () => failWith(null, 'Server exploded'));
      await renderPanel();

      const toggle = screen.getByRole('switch', { name: 'Mod List Refresh On' });
      fireEvent.click(toggle);

      await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
      expect(toast.error).toHaveBeenCalledWith('Update failed', expect.anything());
      expect(toast.success).not.toHaveBeenCalled();
      await waitFor(() => expect(toggle).toHaveAttribute('aria-checked', 'true'));
      expect(screen.getByLabelText('Mod List Refresh')).toHaveValue('5m');
    });

    // TanStack Query notifies listeners with setTimeout(0), so a save's optimistic value
    // reaches the panel after a round trip of a timer tick, but after the answer when the
    // answer comes at once, as it may on localhost (Story 22.5 review)
    it.each([
      ['a 0 ms round trip', true],
      ['an answer that comes at once', false],
    ])('a not-applied switch save shows one warning and stays Off, after %s', async (_, wait) => {
      const notApplied = 'Saved, but its job could not be rescheduled';
      serveSettings(loaded, async (_url, saved) => {
        if (wait) await new Promise((resolve) => setTimeout(resolve, 0));
        saved.modListRefreshInterval = 0;
        return failWith('API_SETTING_NOT_APPLIED', notApplied);
      });
      await renderPanel();

      const toggle = screen.getByRole('switch', { name: 'Mod List Refresh On' });
      const states: (string | null)[] = [];
      const observer = new MutationObserver(() => {
        states.push(toggle.getAttribute('aria-checked'));
      });
      observer.observe(toggle, { attributes: true, attributeFilter: ['aria-checked'] });

      fireEvent.click(toggle);

      await waitFor(() => expect(toast.warning).toHaveBeenCalledTimes(1));
      expect(toast.warning).toHaveBeenCalledWith('Saved, not applied yet', {
        description: notApplied,
      });
      await waitFor(() => {
        expect(screen.getByTestId('mod_list_refresh_interval-off')).toHaveTextContent('Off');
      });
      // Let the refetch land
      await new Promise((resolve) => setTimeout(resolve, 50));
      observer.disconnect();

      expect(toggle).toHaveAttribute('aria-checked', 'false');
      expect(states[0]).toBe('false');
      expect(states).not.toContain('true');
      expect(toast.error).not.toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
      expect(screen.getByRole('alert')).toHaveTextContent(notApplied);
    });

    it('turning a job back on restores the value shown before it was turned off', async () => {
      const mockFetch = serveSettings({ ...loaded, modListRefreshInterval: 7200 });
      await renderPanel();

      const toggle = screen.getByRole('switch', { name: 'Mod List Refresh On' });
      fireEvent.click(toggle);
      await waitFor(() => {
        expect(screen.getByTestId('mod_list_refresh_interval-off')).toBeInTheDocument();
      });
      await waitFor(() => expect(toggle).not.toBeDisabled());
      fireEvent.click(toggle);

      await waitFor(() => expect(screen.getByLabelText('Mod List Refresh')).toHaveValue('2h'));
      const bodies = postCalls(mockFetch).map((call) => JSON.parse(String(call[1]?.body)));
      expect(bodies).toEqual([{ value: 0 }, { value: 7200 }]);
    });
  });

  describe('collapsible groups', () => {
    it('Refresh Intervals group is collapsible', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Find the Refresh Intervals header
      const header = screen.getByText('Refresh Intervals').closest('[data-slot="card-header"]');
      expect(header).toHaveAttribute('role', 'button');
    });
  });

  describe('styling', () => {
    it('applies custom className', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel className="custom-class" />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toHaveClass('custom-class');
      });
    });
  });

  describe('debug logging toggle (VSS-c9o)', () => {
    it('renders Debug Logging group when loaded', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      expect(screen.getByText('Debug Logging')).toBeInTheDocument();
    });

    it('renders debug toggle with correct initial state (disabled)', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      expect(toggle).toHaveAttribute('data-state', 'unchecked');
      // Check the status text next to the toggle (sibling span)
      const statusText = toggle.nextElementSibling;
      expect(statusText).toHaveTextContent('Disabled');
    });

    it('renders debug toggle with correct initial state (enabled)', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusEnabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      expect(toggle).toHaveAttribute('data-state', 'checked');
      // Check the status text next to the toggle (sibling span)
      const statusText = toggle.nextElementSibling;
      expect(statusText).toHaveTextContent('Enabled');
    });

    it('calls debug enable API when toggling on', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/enable') && options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { debugEnabled: true, changed: true },
              }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/debug/enable'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('calls debug disable API when toggling off', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/disable') && options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { debugEnabled: false, changed: true },
              }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusEnabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/debug/disable'),
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('shows error message when debug status fetch fails', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          return {
            ok: false,
            status: 403,
            statusText: 'Forbidden',
            json: () => Promise.resolve({ detail: 'Admin required' }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      await waitFor(() => {
        expect(screen.getByText('Unable to load debug status')).toBeInTheDocument();
      });
    });

    it('shows success toast when enabling debug logging', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/enable') && options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { debugEnabled: true, changed: true },
              }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Debug logging enabled');
      });
    });

    it('shows success toast when disabling debug logging', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/disable') && options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { debugEnabled: false, changed: true },
              }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusEnabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.success).toHaveBeenCalledWith('Debug logging disabled');
      });
    });

    it('shows info toast when debug logging already in desired state', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/enable') && options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { debugEnabled: true, changed: false },
              }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.info).toHaveBeenCalledWith('Debug logging was already enabled');
      });
    });

    it('shows info toast when debug logging already disabled', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/disable') && options?.method === 'POST') {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { debugEnabled: false, changed: false },
              }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusEnabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.info).toHaveBeenCalledWith('Debug logging was already disabled');
      });
    });

    it('shows error toast when debug toggle fails', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/enable') && options?.method === 'POST') {
          return {
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            json: () => Promise.resolve({ detail: 'Failed to update logging config' }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Update failed',
          expect.objectContaining({
            description: 'Failed to update logging config',
          })
        );
      });

      // Wait for all mutations to settle to prevent unhandled rejection warnings
      await waitFor(() => {
        expect(queryClient.isMutating()).toBe(0);
      });
    });

    it('shows fallback error toast when debug toggle fails with non-Error object', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/enable') && options?.method === 'POST') {
          // Reject with a non-Error object
          return Promise.reject('Connection lost');
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith(
          'Update failed',
          expect.objectContaining({
            description: 'Failed to toggle debug logging',
          })
        );
      });

      // Wait for all mutations to settle to prevent unhandled rejection warnings
      await waitFor(() => {
        expect(queryClient.isMutating()).toBe(0);
      });
    });

    it('disables debug toggle while update is pending', async () => {
      let resolvePromise: (value: unknown) => void;
      const pendingPromise = new Promise((resolve) => {
        resolvePromise = resolve;
      });

      const mockFetch = vi.fn().mockImplementation(async (url: string, options?: RequestInit) => {
        if (url.includes('/debug/enable') && options?.method === 'POST') {
          await pendingPromise;
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { debugEnabled: true, changed: true },
              }),
          };
        }
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { container } = render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      expect(toggle).not.toBeDisabled();

      fireEvent.click(toggle);

      // Toggle should be disabled while pending
      await waitFor(() => {
        expect(toggle).toBeDisabled();
      });

      // Should show loading spinner while pending (Loader2 icon with animate-spin class)
      await waitFor(() => {
        const spinner = container.querySelector('.animate-spin');
        expect(spinner).toBeInTheDocument();
      });

      // Resolve the pending promise
      resolvePromise!({});

      // Wait for toggle to be enabled again
      await waitFor(() => {
        expect(toggle).not.toBeDisabled();
      });
    });

    it('shows skeleton while debug status is loading', async () => {
      let resolveDebugPromise: (value: unknown) => void;
      const pendingDebugPromise = new Promise((resolve) => {
        resolveDebugPromise = resolve;
      });

      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          await pendingDebugPromise;
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      // Debug toggle should not be present yet, skeleton should be shown
      await waitFor(() => {
        expect(screen.queryByTestId('debug-logging-toggle')).not.toBeInTheDocument();
      });

      // Resolve the debug promise
      resolveDebugPromise!({});

      // Wait for toggle to appear
      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });
    });

    it('displays undefined debugEnabled status as disabled', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: {
                  // debugEnabled is missing
                },
              }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('debug-logging-toggle')).toBeInTheDocument();
      });

      const toggle = screen.getByTestId('debug-logging-toggle');
      expect(toggle).toHaveAttribute('data-state', 'unchecked');
      // Check the status text - should show "Disabled" when debugEnabled is undefined
      const statusText = toggle.nextElementSibling;
      expect(statusText).toHaveTextContent('Disabled');
    });
  });

  describe('Scheduled Restarts (Story 22.6)', () => {
    const loaded = { ...mockApiSettingsCamelCase.data.settings };
    const refused =
      "Invalid value for 'scheduled_restart_times': '04:00' and '04:10' are 10 minutes apart; " +
      'restart times must be at least 16 minutes apart';

    function answerWith(status: number, code: string, message: string) {
      return {
        ok: false,
        status,
        statusText: status === 400 ? 'Bad Request' : 'Internal Server Error',
        json: () => Promise.resolve({ detail: { code, message } }),
      };
    }

    function titles(): string[] {
      return screen
        .getAllByText(/^(Server Behavior|Scheduled Restarts|Environment Variables|Backup Cleanup)$/)
        .map((el) => el.textContent ?? '');
    }

    async function addRestartTime(value: string) {
      fireEvent.click(screen.getByTestId('add-restart-time'));
      const inputs = screen.getAllByLabelText(/^Restart time \d+$/);
      const input = inputs[inputs.length - 1];
      fireEvent.change(input, { target: { value } });
      fireEvent.blur(input);
    }

    function restartTimesShown(): string[] {
      return screen
        .queryAllByLabelText(/^Restart time \d+$/)
        .map((el) => (el instanceof HTMLInputElement ? el.value : ''));
    }

    it('is shown after Server Behavior and before Environment Variables', async () => {
      serveSettings(loaded);
      await renderPanel();

      const shown = titles();
      expect(shown.indexOf('Scheduled Restarts')).toBe(shown.indexOf('Server Behavior') + 1);
      expect(shown.indexOf('Environment Variables')).toBeGreaterThan(
        shown.indexOf('Scheduled Restarts')
      );
      expect(screen.getByText('Restart the game server every day at these times')).toBeVisible();
    });

    it('shows loaded times sorted', async () => {
      serveSettings({ ...loaded, scheduledRestartTimes: ['16:00', '04:00'] });
      await renderPanel();

      expect(restartTimesShown()).toEqual(['04:00', '16:00']);
    });

    it('says no restart is scheduled when the setting is missing', async () => {
      serveSettings({});
      await renderPanel();

      expect(screen.getByTestId('scheduled-restarts-empty')).toHaveTextContent(
        'No restart is scheduled.'
      );
    });

    it('saves an added time with one POST and one success toast', async () => {
      const mockFetch = serveSettings(loaded);
      await renderPanel();

      await addRestartTime('04:00');

      await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
      expect(toast.success).toHaveBeenCalledWith('scheduled_restart_times updated');
      expect(toast.error).not.toHaveBeenCalled();
      const posts = postCalls(mockFetch);
      expect(posts).toHaveLength(1);
      expect(posts[0][0]).toMatch(/\/config\/api\/settings\/scheduled_restart_times$/);
      expect(posts[0][1]?.body).toBe('{"value":["04:00"]}');
      await waitFor(() => expect(restartTimesShown()).toEqual(['04:00']));
    });

    it("a 400 shows one error toast and the API's message under the list", async () => {
      // The client would refuse 04:00 with 04:10; the stub refuses a list it lets through
      serveSettings({ ...loaded, scheduledRestartTimes: ['08:00'] }, async () => {
        await new Promise((resolve) => setTimeout(resolve, 20));
        return answerWith(400, 'API_SETTING_INVALID', refused);
      });
      await renderPanel();

      await addRestartTime('04:00');

      await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
      expect(toast.error).toHaveBeenCalledWith('Update failed', { description: refused });
      expect(toast.success).not.toHaveBeenCalled();
      await waitFor(() => {
        expect(screen.getByRole('alert')).toHaveTextContent(refused);
      });
      // Let the refetch land
      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(restartTimesShown()).toEqual(['08:00', '04:00']);
      expect(toast.error).toHaveBeenCalledTimes(1);
    });

    it('a 500 not applied shows one warning toast', async () => {
      const notApplied = 'Saved, but the restart jobs could not be applied';
      serveSettings(loaded, async (_url, saved) => {
        await new Promise((resolve) => setTimeout(resolve, 20));
        saved.scheduledRestartTimes = ['04:00'];
        return answerWith(500, 'API_SETTING_NOT_APPLIED', notApplied);
      });
      await renderPanel();

      await addRestartTime('04:00');

      await waitFor(() => expect(toast.warning).toHaveBeenCalledTimes(1));
      expect(toast.warning).toHaveBeenCalledWith('Saved, not applied yet', {
        description: notApplied,
      });
      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(toast.error).not.toHaveBeenCalled();
      expect(toast.success).not.toHaveBeenCalled();
      expect(screen.getByRole('alert')).toHaveTextContent(notApplied);
      expect(restartTimesShown()).toEqual(['04:00']);
    });
  });

  describe('Backup Cleanup (Story 22.6)', () => {
    const loaded = { ...mockApiSettingsCamelCase.data.settings, backupKeepCount: 7 };

    function titles(): string[] {
      return screen
        .getAllByText(/^(Scheduled Restarts|Environment Variables|Backup Cleanup)$/)
        .map((el) => el.textContent ?? '');
    }

    it('is shown directly after Scheduled Restarts', async () => {
      serveSettings(loaded);
      await renderPanel();

      const shown = titles();
      expect(shown.indexOf('Backup Cleanup')).toBe(shown.indexOf('Scheduled Restarts') + 1);
      expect(screen.getByText('Delete old backup files every day')).toBeInTheDocument();
    });

    it('has one number field, Backups kept, with the loaded value', async () => {
      serveSettings(loaded);
      await renderPanel();

      const input = screen.getByLabelText('Backups kept');
      expect(input).toHaveAttribute('type', 'number');
      expect(input).toHaveValue(7);
    });

    it('shows 0 when the setting is missing', async () => {
      serveSettings({});
      await renderPanel();

      expect(screen.getByLabelText('Backups kept')).toHaveValue(0);
    });

    it('has no field for log archives', async () => {
      serveSettings(loaded);
      await renderPanel();

      expect(screen.getByTestId('api-settings-panel')).not.toHaveTextContent(/log archive/i);
    });

    it.each([
      ['0 keeps all', /0 keeps all/],
      ['deleted permanently', /deleted permanently/],
      ['03:00 server time, TZ', /03:00 server time \(TZ, UTC unless set\)/],
      ['only serverdata/Backups', /serverdata\/Backups/],
      ['BackupSaves never', /BackupSaves and the world are never touched/],
    ])('help text: %s', async (_fact, pattern) => {
      serveSettings(loaded);
      await renderPanel();

      expect(screen.getByText(pattern)).toBeInTheDocument();
    });

    it('saves 3 with one POST and one success toast', async () => {
      const mockFetch = serveSettings(loaded);
      await renderPanel();

      const input = screen.getByLabelText('Backups kept');
      fireEvent.change(input, { target: { value: '3' } });
      fireEvent.blur(input);

      await waitFor(() => expect(toast.success).toHaveBeenCalledTimes(1));
      expect(toast.success).toHaveBeenCalledWith('backup_keep_count updated');
      const posts = postCalls(mockFetch);
      expect(posts).toHaveLength(1);
      expect(posts[0][0]).toMatch(/\/config\/api\/settings\/backup_keep_count$/);
      expect(JSON.parse(String(posts[0][1]?.body))).toEqual({ value: 3 });
    });

    it.each(['-1', '1001'])('refuses %s before sending', async (value) => {
      const mockFetch = serveSettings(loaded);
      await renderPanel();

      const input = screen.getByLabelText('Backups kept');
      fireEvent.change(input, { target: { value } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText('Must be between 0 and 1000')).toBeInTheDocument();
      });
      expect(postCalls(mockFetch)).toHaveLength(0);
      expect(toast.success).not.toHaveBeenCalled();
      expect(toast.error).not.toHaveBeenCalled();
    });

    it("a 400 shows one error toast and the API's message under the field", async () => {
      const refused =
        "Invalid value for 'backup_keep_count': Input should be less than or equal to 1000";
      serveSettings(loaded, async () => {
        await new Promise((resolve) => setTimeout(resolve, 20));
        return {
          ok: false,
          status: 400,
          statusText: 'Bad Request',
          json: () =>
            Promise.resolve({ detail: { code: 'API_SETTING_INVALID', message: refused } }),
        };
      });
      await renderPanel();

      const input = screen.getByLabelText('Backups kept');
      fireEvent.change(input, { target: { value: '5' } });
      fireEvent.blur(input);

      await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1));
      expect(toast.error).toHaveBeenCalledWith('Update failed', { description: refused });
      expect(toast.success).not.toHaveBeenCalled();
      await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(refused));
      await new Promise((resolve) => setTimeout(resolve, 50));
      expect(toast.error).toHaveBeenCalledTimes(1);
    });
  });

  describe('field descriptions', () => {
    it('shows description for boolean fields', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      expect(
        screen.getByText('Automatically start the game server when the API starts')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Prevent changes to settings managed by environment variables')
      ).toBeInTheDocument();
      expect(
        screen.getByText('Re-apply environment variable values when the server restarts')
      ).toBeInTheDocument();
    });

    it('shows description for duration fields', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockApiSettingsCamelCase),
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      expect(screen.getByText('How often to refresh the installed mods list')).toBeInTheDocument();
      expect(
        screen.getByText('How often to check for new game server versions')
      ).toBeInTheDocument();
    });

    it('shows description for debug logging toggle', async () => {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/debug')) {
          return {
            ok: true,
            json: () => Promise.resolve(mockDebugStatusDisabled),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockApiSettingsCamelCase),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ApiSettingsPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('api-settings-panel')).toBeInTheDocument();
      });

      expect(
        screen.getByText('Enable DEBUG-level logging at runtime without server restart')
      ).toBeInTheDocument();
    });
  });
});
