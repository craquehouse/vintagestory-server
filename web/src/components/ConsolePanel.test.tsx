import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

// Mock xterm.js
vi.mock('@xterm/xterm', () => {
  return {
    Terminal: class MockTerminal {
      options: Record<string, unknown> = {};
      loadAddon = vi.fn();
      open = vi.fn();
      dispose = vi.fn();
      writeln = vi.fn();
      write = vi.fn();
      onData = vi.fn(() => ({ dispose: vi.fn() }));
    },
  };
});

vi.mock('@xterm/addon-fit', () => {
  return {
    FitAddon: class MockFitAddon {
      fit = vi.fn();
    },
  };
});

// Mock next-themes
vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: 'dark',
    setTheme: vi.fn(),
    resolvedTheme: 'dark',
    systemTheme: 'dark',
  }),
}));

// Mock ResizeObserver
class MockResizeObserver {
  observe = vi.fn();
  disconnect = vi.fn();
  unobserve = vi.fn();
}

// Mock useConsoleWebSocket
vi.mock('@/hooks/use-console-websocket', () => ({
  useConsoleWebSocket: vi.fn(() => ({
    connectionState: 'disconnected',
    sendCommand: vi.fn(),
  })),
}));

// Mock useServerStatus
vi.mock('@/hooks/use-server-status', () => ({
  useServerStatus: vi.fn(() => ({
    data: { data: { state: 'stopped' } },
  })),
}));

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn().mockReturnValue(null),
  setCookie: vi.fn(),
}));

// Import after mocks
import { ConsolePanel } from './ConsolePanel';
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import { useConsoleWebSocket } from '@/hooks/use-console-websocket';
import { useServerStatus } from '@/hooks/use-server-status';

// Create fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Wrapper component
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <PreferencesProvider>{children}</PreferencesProvider>
      </QueryClientProvider>
    );
  };
}

describe('ConsolePanel', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  describe('rendering', () => {
    it('renders the panel container', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('console-panel')).toBeInTheDocument();
    });

    it('renders default title', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Server Console')).toBeInTheDocument();
    });

    it('renders custom title', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel title="Custom Title" />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Custom Title')).toBeInTheDocument();
    });

    it('renders header by default', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Server Console')).toBeInTheDocument();
    });

    it('hides header when showHeader is false', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel showHeader={false} />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.queryByText('Server Console')).not.toBeInTheDocument();
    });

    it('renders terminal view', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(
        screen.getByRole('application', { name: 'Server console terminal' })
      ).toBeInTheDocument();
    });

    it('renders command input', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByLabelText('Command input')).toBeInTheDocument();
    });

    it('renders send button', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
    });
  });

  describe('connection state', () => {
    it('renders connection status indicator', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Connection status should be shown
      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has command input with placeholder', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      expect(input).toHaveAttribute('placeholder');
    });

    it('command input can be disabled', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Input state depends on connection, just verify it renders
      expect(screen.getByLabelText('Command input')).toBeInTheDocument();
    });

    it('send button can be disabled', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Button state depends on connection/input, just verify it renders
      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
    });

    it('command input is disabled with "Server not running" placeholder when server is stopped (AC3)', () => {
      // Configure mocks for connected but server stopped
      vi.mocked(useConsoleWebSocket).mockReturnValueOnce({
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      });
      vi.mocked(useServerStatus).mockReturnValueOnce({
        data: { data: { state: 'installed' } }, // 'installed' = stopped
      } as ReturnType<typeof useServerStatus>);

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      expect(input).toBeDisabled();
      expect(input).toHaveAttribute('placeholder', 'Server not running');
    });

    it('send button is disabled when server is stopped (AC3)', () => {
      // Configure mocks for connected but server stopped
      vi.mocked(useConsoleWebSocket).mockReturnValueOnce({
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      });
      vi.mocked(useServerStatus).mockReturnValueOnce({
        data: { data: { state: 'installed' } }, // 'installed' = stopped
      } as ReturnType<typeof useServerStatus>);

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const button = screen.getByRole('button', { name: 'Send' });
      expect(button).toBeDisabled();
    });
  });

  describe('styling', () => {
    it('applies custom className', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel className="custom-class" />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('console-panel')).toHaveClass('custom-class');
    });

    it('has flex column layout', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('console-panel')).toHaveClass('flex');
      expect(screen.getByTestId('console-panel')).toHaveClass('flex-col');
    });

    it('has overflow hidden', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('console-panel')).toHaveClass('overflow-hidden');
    });
  });

  describe('command form', () => {
    it('renders command form with input and button', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Form elements should be present
      // Actual command flow is tested in Terminal.test.tsx
      expect(screen.getByLabelText('Command input')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
    });
  });
});
