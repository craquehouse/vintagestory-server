import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { GameConfigPanel } from './GameConfigPanel';
import { PAGE_CONTENT_WIDTH } from '@/components/layout/content-width';
import { queryKeys } from '@/api/query-keys';
import type { ApiResponse, GameConfigData } from '@/api/types';

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Create a fresh QueryClient for each test, without a known role
function createUnseededQueryClient() {
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

// Story 23.3: the fields are editable only for an Admin key, so the existing tests start
// with the Admin role known (useAuthMe's staleTime is Infinity: no request is made)
function createTestQueryClient(role = 'admin') {
  const queryClient = createUnseededQueryClient();
  queryClient.setQueryData(queryKeys.auth.me, { status: 'ok', data: { role } });
  return queryClient;
}

// Wrapper component for rendering with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
  };
}

// Mock game config response (snake_case as from API)
const mockGameConfig = {
  status: 'ok',
  data: {
    settings: [
      {
        key: 'ServerName',
        value: 'My Test Server',
        type: 'string',
        live_update: true,
        env_managed: false,
      },
      {
        key: 'ServerDescription',
        value: 'A test server',
        type: 'string',
        live_update: true,
        env_managed: false,
      },
      {
        key: 'Password',
        value: '',
        type: 'string',
        live_update: true,
        env_managed: true,
      },
      {
        key: 'MaxClients',
        value: 16,
        type: 'int',
        live_update: true,
        env_managed: false,
      },
      {
        key: 'AllowPvP',
        value: false,
        type: 'bool',
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
    ],
    source_file: 'serverconfig.json',
    last_modified: '2025-12-30T10:00:00Z',
  },
};

describe('GameConfigPanel', () => {
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
    it('shows skeleton loader while loading', () => {
      // Make fetch never resolve
      globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('game-config-loading')).toBeInTheDocument();
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
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-error')).toBeInTheDocument();
      });

      expect(screen.getByText('Failed to load settings')).toBeInTheDocument();
    });
  });

  describe('rendering settings', () => {
    it('renders setting groups when loaded', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Check for group titles
      expect(screen.getByText('Server Info')).toBeInTheDocument();
      expect(screen.getByText('Player Settings')).toBeInTheDocument();
    });

    it('skips rendering settings not available in API response', async () => {
      // Mock config with only ServerName, missing other settings
      const partialConfig = {
        status: 'ok',
        data: {
          settings: [
            {
              key: 'ServerName',
              value: 'Test Server',
              type: 'string',
              live_update: true,
              env_managed: false,
            },
          ],
          source_file: 'serverconfig.json',
          last_modified: '2025-12-30T10:00:00Z',
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(partialConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // ServerName should render
      expect(screen.getByLabelText('Server Name')).toBeInTheDocument();

      // ServerDescription, Password, etc. should not render
      expect(screen.queryByLabelText('Description')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Password')).not.toBeInTheDocument();
      expect(screen.queryByLabelText('Max Players')).not.toBeInTheDocument();
    });

    it('skips rendering entire groups when no settings are available', async () => {
      // Mock config with no settings at all
      const emptyConfig = {
        status: 'ok',
        data: {
          settings: [],
          source_file: 'serverconfig.json',
          last_modified: '2025-12-30T10:00:00Z',
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(emptyConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // No groups should render
      expect(screen.queryByText('Server Info')).not.toBeInTheDocument();
      expect(screen.queryByText('Player Settings')).not.toBeInTheDocument();
      expect(screen.queryByText('World Settings')).not.toBeInTheDocument();
      expect(screen.queryByText('Network')).not.toBeInTheDocument();
    });

    it('renders individual settings with correct values', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Check for setting labels and values
      expect(screen.getByLabelText('Server Name')).toHaveValue('My Test Server');
      expect(screen.getByLabelText('Max Players')).toHaveValue(16);
    });

    it('shows env badge for env-managed settings', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Password is env_managed
      expect(screen.getByText(/Env:/)).toBeInTheDocument();
    });

    it('disables env-managed inputs', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Password input should be disabled
      expect(screen.getByLabelText('Password')).toBeDisabled();
    });
  });

  describe('updating settings', () => {
    it('calls API on field blur with changed value', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          return {
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
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockGameConfig),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Change server name
      const input = screen.getByLabelText('Server Name');
      fireEvent.change(input, { target: { value: 'New Server Name' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/config/game/settings/ServerName'),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    it('shows validation error for invalid values', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Clear server name (required field)
      const input = screen.getByLabelText('Server Name');
      fireEvent.change(input, { target: { value: '' } });
      fireEvent.blur(input);

      await waitFor(() => {
        expect(screen.getByText('Server name is required')).toBeInTheDocument();
      });
    });

    it('handles API errors with Error objects', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          return {
            ok: false,
            status: 500,
            statusText: 'Internal Server Error',
            json: () => Promise.resolve({ detail: 'Server error' }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockGameConfig),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Change server name to trigger save
      const input = screen.getByLabelText('Server Name');
      fireEvent.change(input, { target: { value: 'New Server Name' } });
      fireEvent.blur(input);

      // Wait for error to be shown
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/config/game/settings/ServerName'),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    it('handles non-Error exceptions with default message', async () => {
      // Create a mock mutation that throws a non-Error object
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          // Simulate a non-Error exception (e.g., network error, string, etc.)
          throw 'Network connection failed'; // Not an Error instance
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockGameConfig),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Change server name to trigger save
      const input = screen.getByLabelText('Server Name');
      fireEvent.change(input, { target: { value: 'New Server Name' } });
      fireEvent.blur(input);

      // Wait for the fetch to be called
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          expect.stringContaining('/config/game/settings/ServerName'),
          expect.objectContaining({
            method: 'POST',
          })
        );
      });
    });

    it("keeps a failed save's message under the field through the rollback (Story 22.6 review)", async () => {
      const refused = 'Server name is too long';
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/settings/')) {
          // The optimistic value reaches the field before the save fails
          await new Promise((resolve) => setTimeout(resolve, 20));
          return {
            ok: false,
            status: 400,
            statusText: 'Bad Request',
            json: () => Promise.resolve({ detail: { code: 'CONFIG_INVALID', message: refused } }),
          };
        }
        return {
          ok: true,
          json: () => Promise.resolve(mockGameConfig),
        };
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      const input = screen.getByLabelText('Server Name');
      fireEvent.change(input, { target: { value: 'New Server Name' } });
      fireEvent.blur(input);

      await waitFor(() => expect(screen.getByRole('alert')).toHaveTextContent(refused));
      // Let the rollback reach the field
      await new Promise((resolve) => setTimeout(resolve, 50));
      const cached = queryClient.getQueryData<ApiResponse<GameConfigData>>(queryKeys.config.game);
      expect(cached?.data.settings.find((s) => s.key === 'ServerName')?.value).toBe(
        'My Test Server'
      );
      expect(screen.getByRole('alert')).toHaveTextContent(refused);
      expect(input).toHaveValue('My Test Server');
    });
  });

  describe('collapsible groups', () => {
    it('renders collapsible groups for World Settings and Network', async () => {
      // Add world settings to mock
      const configWithWorld = {
        ...mockGameConfig,
        data: {
          ...mockGameConfig.data,
          settings: [
            ...mockGameConfig.data.settings,
            {
              key: 'MaxChunkRadius',
              value: 8,
              type: 'int',
              live_update: true,
              env_managed: false,
            },
          ],
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(configWithWorld),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // World Settings should be collapsible
      const worldHeader = screen.getByText('World Settings').closest('[data-slot="card-header"]');
      expect(worldHeader).toHaveAttribute('role', 'button');
    });
  });

  describe('accessibility', () => {
    it('labels are properly associated with inputs', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });

      // Check that inputs can be found by label
      expect(screen.getByLabelText('Server Name')).toBeInTheDocument();
      expect(screen.getByLabelText('Max Players')).toBeInTheDocument();
      expect(screen.getByLabelText('Allow PvP')).toBeInTheDocument();
    });
  });

  describe('custom className', () => {
    it('applies custom className', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel className="custom-class" />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toHaveClass('custom-class');
      });
    });
  });
  describe('Story 16.8: settings with no value and the password', () => {
    const configWithNulls = {
      ...mockGameConfig,
      data: {
        ...mockGameConfig.data,
        settings: [
          ...mockGameConfig.data.settings.map((setting) =>
            setting.key === 'ServerDescription' || setting.key === 'Password'
              ? { ...setting, value: null, env_managed: false }
              : setting
          ),
          {
            key: 'Ip',
            value: null,
            type: 'string',
            live_update: false,
            requires_restart: true,
            env_managed: false,
          },
        ],
      },
    };

    it('shows Description, Password and IP Address with no value as empty fields', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(configWithNulls),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByLabelText('Description')).toBeInTheDocument();
      });

      expect(screen.getByLabelText('Description')).toHaveValue('');
      expect(screen.getByLabelText('Password')).toHaveValue('');
      expect(screen.getByLabelText('IP Address')).toHaveValue('');
      expect(screen.queryByDisplayValue('null')).not.toBeInTheDocument();
    });

    it('masks the password and not the server name', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(configWithNulls),
      });

      const queryClient = createTestQueryClient();
      render(<GameConfigPanel />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByLabelText('Password')).toBeInTheDocument();
      });

      expect(screen.getByLabelText('Password')).toHaveAttribute('type', 'password');
      expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument();
      expect(screen.getByLabelText('Server Name')).toHaveAttribute('type', 'text');
      expect(screen.getByLabelText('Description')).toHaveAttribute('type', 'text');
    });
  });

  describe('Story 17.5: secret settings', () => {
    // The API's Password setting, with everything else as in mockGameConfig
    const configWithPassword = (password: Record<string, unknown>) => ({
      ...mockGameConfig,
      data: {
        ...mockGameConfig.data,
        settings: mockGameConfig.data.settings.map((setting) =>
          setting.key === 'Password' ? { ...setting, env_managed: false, ...password } : setting
        ),
      },
    });

    async function renderWith(config: unknown) {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(config),
      });
      render(<GameConfigPanel />, { wrapper: createWrapper(createTestQueryClient()) });
      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });
    }

    function expectOtherSettingsAsFields() {
      expect(screen.getByLabelText('Server Name')).toHaveValue('My Test Server');
      expect(screen.getByLabelText('Description')).toHaveValue('A test server');
      expect(screen.getByLabelText('Max Players')).toBeInTheDocument();
      expect(screen.getByRole('switch', { name: 'Allow PvP' })).toBeInTheDocument();
    }

    it('with a Monitor response, shows "Set" and no password field', async () => {
      await renderWith(configWithPassword({ value: null, secret: true, configured: true }));

      expect(screen.getByTestId('secret-setting-status-Password')).toHaveTextContent('Set');
      expect(document.getElementById('Password')).toBeNull();
      expect(screen.queryByRole('button', { name: 'Show password' })).not.toBeInTheDocument();
      expectOtherSettingsAsFields();
    });

    it('with a Monitor response and no password, shows "Not set"', async () => {
      await renderWith(configWithPassword({ value: null, secret: true, configured: false }));

      expect(screen.getByTestId('secret-setting-status-Password')).toHaveTextContent('Not set');
      expect(document.getElementById('Password')).toBeNull();
      expect(screen.queryByRole('button', { name: 'Show password' })).not.toBeInTheDocument();
      expectOtherSettingsAsFields();
    });

    it('with an Admin response, keeps the masked field with its value', async () => {
      await renderWith(configWithPassword({ value: 'admin-sees-this', secret: true }));

      const input = screen.getByLabelText('Password');
      expect(input).toHaveAttribute('type', 'password');
      expect(input).toHaveValue('admin-sees-this');
      expect(screen.getByRole('button', { name: 'Show password' })).toBeInTheDocument();
      expect(screen.queryByTestId('secret-setting-Password')).not.toBeInTheDocument();
      expectOtherSettingsAsFields();
    });

    it('with an Admin response and no password, shows an empty masked field', async () => {
      await renderWith(configWithPassword({ value: null, secret: true }));

      const input = screen.getByLabelText('Password');
      expect(input).toHaveAttribute('type', 'password');
      expect(input).toHaveValue('');
      expect(screen.queryByText('Not set')).not.toBeInTheDocument();
      expect(screen.queryByTestId('secret-setting-Password')).not.toBeInTheDocument();
      expectOtherSettingsAsFields();
    });
  });

  describe('Story 17.6: booleans with no value', () => {
    const withSettings = (
      extra: Record<string, unknown>[],
      password?: Record<string, unknown>
    ) => ({
      ...mockGameConfig,
      data: {
        ...mockGameConfig.data,
        settings: [
          ...mockGameConfig.data.settings.map((setting) => {
            if (setting.key === 'AllowPvP') return { ...setting, value: null };
            if (setting.key === 'Password' && password) {
              return { ...setting, env_managed: false, ...password };
            }
            return setting;
          }),
          ...extra,
        ],
      },
    });
    const entitySpawning = {
      key: 'EntitySpawning',
      value: null,
      default: true,
      type: 'bool',
      live_update: true,
      env_managed: false,
    };

    async function renderWith(config: unknown) {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(config),
      });
      render(<GameConfigPanel />, { wrapper: createWrapper(createTestQueryClient()) });
      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });
    }

    it('shows the known default and "Not set" for a boolean without one', async () => {
      await renderWith(withSettings([entitySpawning]));

      expect(screen.getByTestId('setting-state-EntitySpawning')).toHaveTextContent(
        'Enabled (default)'
      );
      expect(screen.getByRole('switch', { name: 'Entity Spawning' })).toBeChecked();
      expect(screen.getByTestId('setting-state-AllowPvP')).toHaveTextContent(/^Not set$/);
      expect(screen.getByRole('switch', { name: 'Allow PvP' })).not.toBeChecked();
    });

    it('leaves a withheld secret to Story 17.5 (the two do not interfere)', async () => {
      await renderWith(
        withSettings([entitySpawning], { value: null, secret: true, configured: true })
      );

      expect(screen.getByTestId('secret-setting-status-Password')).toHaveTextContent('Set');
      expect(document.getElementById('Password')).toBeNull();
      expect(screen.queryByTestId('setting-state-Password')).not.toBeInTheDocument();
      expect(screen.getByTestId('setting-state-EntitySpawning')).toHaveTextContent(
        'Enabled (default)'
      );
      expect(screen.getByTestId('setting-state-AllowPvP')).toHaveTextContent(/^Not set$/);
    });
  });

  describe('Story 16.6: desktop layout', () => {
    const setting = (key: string, value: string | number | boolean, type: string) => ({
      key,
      value,
      type,
      live_update: true,
      env_managed: false,
    });

    // Every setting the panel shows, so all four groups render
    const fullConfig = {
      status: 'ok',
      data: {
        settings: [
          setting('ServerName', 'My Test Server', 'string'),
          setting('ServerDescription', 'A test server', 'string'),
          setting('WelcomeMessage', 'Welcome', 'string'),
          setting('Password', '', 'string'),
          setting('MaxClients', 16, 'int'),
          setting('AllowPvP', true, 'bool'),
          setting('MaxChunkRadius', 12, 'int'),
          setting('AllowFireSpread', true, 'bool'),
          setting('AllowFallingBlocks', true, 'bool'),
          setting('EntitySpawning', true, 'bool'),
          setting('PassTimeWhenEmpty', false, 'bool'),
          setting('Port', 42420, 'int'),
          setting('Ip', '', 'string'),
          setting('AdvertiseServer', false, 'bool'),
          setting('Upnp', false, 'bool'),
        ],
        source_file: 'serverconfig.json',
        last_modified: '2025-12-30T10:00:00Z',
      },
    };

    async function renderFull() {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(fullConfig),
      });
      render(<GameConfigPanel />, { wrapper: createWrapper(createTestQueryClient()) });
      await waitFor(() => {
        expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
      });
    }

    const card = (title: string) =>
      screen.getByText(title).closest('[data-slot="card"]') as HTMLElement;

    it('limits the panel to 1280px and centers it', async () => {
      await renderFull();

      expect(screen.getByTestId('game-config-layout')).toHaveClass(
        ...PAGE_CONTENT_WIDTH.split(' ')
      );
    });

    it('puts Server Info above the columns with its fields in two columns from xl', async () => {
      await renderFull();

      const serverInfo = card('Server Info');
      expect(screen.getByTestId('game-config-columns')).not.toContainElement(serverInfo);

      const content = serverInfo.querySelector('[data-slot="card-content"]');
      expect(content).toHaveClass('xl:grid', 'xl:grid-cols-2', 'xl:space-y-0');
      const ids = [...(content?.querySelectorAll('input') ?? [])].map((input) => input.id);
      expect(ids).toEqual(['ServerName', 'ServerDescription', 'WelcomeMessage', 'Password']);
    });

    it('stacks Player Settings then Network on the left and World Settings on the right', async () => {
      await renderFull();

      const columns = screen.getByTestId('game-config-columns');
      expect(columns).toHaveClass('grid', 'xl:grid-cols-2', 'xl:items-start');

      const left = screen.getByTestId('game-config-column-left');
      const right = screen.getByTestId('game-config-column-right');
      expect([...columns.children]).toEqual([left, right]);
      expect([...left.children]).toEqual([card('Player Settings'), card('Network')]);
      expect([...right.children]).toEqual([card('World Settings')]);
    });

    it('collapsing World Settings leaves the left column as it was', async () => {
      await renderFull();

      fireEvent.click(screen.getByRole('button', { name: /World Settings/ }));

      expect(screen.queryByLabelText('Max Chunk Radius')).not.toBeInTheDocument();
      const left = screen.getByTestId('game-config-column-left');
      expect([...left.children]).toEqual([card('Player Settings'), card('Network')]);
      expect(screen.getByLabelText('Max Players')).toBeInTheDocument();
      expect(screen.getByLabelText('Port')).toBeInTheDocument();
    });

    it('collapsing Network leaves World Settings as it was', async () => {
      await renderFull();

      fireEvent.click(screen.getByRole('button', { name: /Network/ }));

      expect(screen.queryByLabelText('Port')).not.toBeInTheDocument();
      const right = screen.getByTestId('game-config-column-right');
      expect([...right.children]).toEqual([card('World Settings')]);
      expect(screen.getByLabelText('Max Chunk Radius')).toBeInTheDocument();
    });

    it('keeps number inputs narrow and lets text inputs fill their column', async () => {
      await renderFull();

      expect(screen.getByLabelText('Max Players')).toHaveClass('max-w-xs');
      expect(screen.getByLabelText('Max Chunk Radius')).toHaveClass('max-w-xs');
      expect(screen.getByLabelText('Port')).toHaveClass('max-w-xs');
      expect(screen.getByLabelText('Server Name')).not.toHaveClass('max-w-xs');
      expect(screen.getByLabelText('IP Address')).not.toHaveClass('max-w-xs');
    });

    it('limits the error message to the same width', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error',
        json: () => Promise.resolve({ detail: 'Server error' }),
      });
      render(<GameConfigPanel />, { wrapper: createWrapper(createTestQueryClient()) });

      await waitFor(() => {
        expect(screen.getByTestId('game-config-error')).toBeInTheDocument();
      });
      const message = screen.getByTestId('game-config-error').firstElementChild;
      expect(message).toHaveClass(...PAGE_CONTENT_WIDTH.split(' '));
    });

    it('limits the loading skeleton to the same width', () => {
      globalThis.fetch = vi.fn().mockReturnValue(new Promise(() => {}));
      render(<GameConfigPanel />, { wrapper: createWrapper(createTestQueryClient()) });

      const skeletons = screen.getByTestId('game-config-loading').firstElementChild;
      expect(skeletons).toHaveClass(...PAGE_CONTENT_WIDTH.split(' '));
    });
  });

  // Story 23.3 (FR313, Epic 23 ADR-6)
  describe('read-only for keys that are not Admin', () => {
    function respondWithConfig(authMe?: () => Promise<unknown>) {
      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/auth/me') && authMe) {
          return authMe();
        }
        return { ok: true, json: () => Promise.resolve(mockGameConfig) };
      });
    }

    it('disables every field and shows the note for a Monitor key', async () => {
      respondWithConfig();
      render(<GameConfigPanel />, { wrapper: createWrapper(createTestQueryClient('monitor')) });

      await waitFor(() => expect(screen.getByTestId('game-config-panel')).toBeInTheDocument());
      expect(screen.getByTestId('game-config-read-only-note')).toHaveTextContent(
        'Only an Admin key can change settings.'
      );
      expect(screen.getByLabelText('Server Name')).toBeDisabled();
      expect(screen.getByLabelText('Server Name').getAttribute('aria-describedby')).toContain(
        'game-config-read-only-note'
      );
      expect(screen.getByLabelText('Port')).toBeDisabled();
      for (const control of screen.queryAllByRole('switch')) {
        expect(control).toBeDisabled();
      }

      fireEvent.change(screen.getByLabelText('Server Name'), { target: { value: 'X' } });
      fireEvent.blur(screen.getByLabelText('Server Name'));
      const posts = vi
        .mocked(globalThis.fetch)
        .mock.calls.filter(([, init]) => (init as RequestInit | undefined)?.method === 'POST');
      expect(posts).toHaveLength(0);
    });

    it('enables the fields and shows no note for an Admin key', async () => {
      respondWithConfig();
      render(<GameConfigPanel />, { wrapper: createWrapper(createTestQueryClient('admin')) });

      await waitFor(() => expect(screen.getByTestId('game-config-panel')).toBeInTheDocument());
      expect(screen.queryByTestId('game-config-read-only-note')).not.toBeInTheDocument();
      expect(screen.getByLabelText('Server Name')).toBeEnabled();
    });

    it('disables the fields without a note while the role loads', async () => {
      respondWithConfig(() => new Promise(() => {}));
      render(<GameConfigPanel />, { wrapper: createWrapper(createUnseededQueryClient()) });

      await waitFor(() => expect(screen.getByTestId('game-config-panel')).toBeInTheDocument());
      expect(screen.getByLabelText('Server Name')).toBeDisabled();
      expect(screen.queryByTestId('game-config-read-only-note')).not.toBeInTheDocument();
    });

    it('disables the fields and says why when the role cannot be loaded', async () => {
      respondWithConfig(async () => ({
        ok: false,
        status: 500,
        json: () => Promise.resolve({ detail: { code: 'INTERNAL_ERROR', message: 'boom' } }),
      }));
      render(<GameConfigPanel />, { wrapper: createWrapper(createUnseededQueryClient()) });

      await waitFor(() =>
        expect(screen.getByTestId('game-config-read-only-note')).toHaveTextContent(
          "Could not check this key's role; settings cannot be changed until it loads."
        )
      );
      expect(screen.getByLabelText('Server Name')).toBeDisabled();
    });
  });
});
