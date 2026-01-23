import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { toast } from 'sonner';
import { ApiSettingsPanel } from './ApiSettingsPanel';

/**
 * Tests for ApiSettingsPanel component.
 */

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
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
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
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

describe('ApiSettingsPanel', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
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
      await new Promise(resolve => setTimeout(resolve, 100));

      // Should not have made any POST calls
      expect(mockFetch.mock.calls.filter(call => call[1]?.method === 'POST')).toHaveLength(0);
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

      // Enter invalid value (too high - 2d > 86400s/1d max)
      const input = screen.getByLabelText('Mod List Refresh');
      fireEvent.change(input, { target: { value: '2d' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText('Must be at most 1d')).toBeInTheDocument();
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

      // Enter invalid value (too high - 8d > 604800s/7d max)
      const input = screen.getByLabelText('Server Versions Refresh');
      fireEvent.change(input, { target: { value: '8d' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText('Must be at most 7d')).toBeInTheDocument();
      });
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

      expect(
        screen.getByText('How often to refresh the installed mods list')
      ).toBeInTheDocument();
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
