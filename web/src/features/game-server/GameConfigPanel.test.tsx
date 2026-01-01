import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { GameConfigPanel } from './GameConfigPanel';

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
});
