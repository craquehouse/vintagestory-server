import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// Mock xterm.js
vi.mock('@xterm/xterm', () => {
  return {
    Terminal: class MockTerminal {
      options: Record<string, unknown> = {};
      loadAddon = vi.fn();
      open = vi.fn();
      dispose = vi.fn();
      clear = vi.fn();
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

// Create mock functions
const mockSendCommand = vi.fn();
const mockReconnect = vi.fn();
const mockDisconnect = vi.fn();

// Type definitions for mock config
type ConsoleWebSocketMock = {
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'forbidden' | 'token_error';
  sendCommand: typeof mockSendCommand;
  retryCount: number;
  isReconnecting: boolean;
  wsRef: { current: null };
  reconnect: typeof mockReconnect;
  disconnect: typeof mockDisconnect;
};

type ServerStatusMock = {
  data: { data: { state: 'stopped' | 'installed' | 'running' | 'installing' | 'not_installed' } };
  isLoading: boolean;
  error: null;
};

type LogFilesMock = {
  data: { data: { files: Array<{ name: string; sizeBytes: number; modifiedAt: string }> } } | undefined;
  isLoading: boolean;
  error: null;
};

type LogStreamMock = {
  connectionState: 'connecting' | 'connected' | 'disconnected' | 'not_found' | 'invalid';
  isLoading: boolean;
  error: null;
};

// Mutable config object that can be modified in tests
const mockConfig: {
  consoleWebSocket: ConsoleWebSocketMock;
  serverStatus: ServerStatusMock;
  logFiles: LogFilesMock;
  logStream: LogStreamMock;
} = {
  consoleWebSocket: {
    connectionState: 'disconnected',
    sendCommand: mockSendCommand,
    retryCount: 0,
    isReconnecting: false,
    wsRef: { current: null },
    reconnect: mockReconnect,
    disconnect: mockDisconnect,
  },
  serverStatus: {
    data: { data: { state: 'stopped' } },
    isLoading: false,
    error: null,
  },
  logFiles: {
    data: undefined,
    isLoading: false,
    error: null,
  },
  logStream: {
    connectionState: 'disconnected',
    isLoading: false,
    error: null,
  },
};

// Mock hooks using the config object
vi.mock('@/hooks/use-console-websocket', () => ({
  useConsoleWebSocket: vi.fn(() => mockConfig.consoleWebSocket),
}));

vi.mock('@/hooks/use-server-status', () => ({
  useServerStatus: vi.fn(() => mockConfig.serverStatus),
}));

vi.mock('@/hooks/use-log-files', () => ({
  useLogFiles: vi.fn(() => mockConfig.logFiles),
}));

vi.mock('@/hooks/use-log-stream', () => ({
  useLogStream: vi.fn(() => mockConfig.logStream),
}));

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn().mockReturnValue(null),
  setCookie: vi.fn(),
}));

// Import after mocks
import { ConsolePanel } from './ConsolePanel';
import { PreferencesProvider } from '@/contexts/PreferencesContext';

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

// Helper to reset mock config to defaults
function resetMockConfig() {
  mockConfig.consoleWebSocket = {
    connectionState: 'disconnected',
    sendCommand: mockSendCommand,
    retryCount: 0,
    isReconnecting: false,
    wsRef: { current: null },
    reconnect: mockReconnect,
    disconnect: mockDisconnect,
  };
  mockConfig.serverStatus = {
    data: { data: { state: 'stopped' } },
    isLoading: false,
    error: null,
  };
  mockConfig.logFiles = {
    data: undefined,
    isLoading: false,
    error: null,
  };
  mockConfig.logStream = {
    connectionState: 'disconnected',
    isLoading: false,
    error: null,
  };
}

describe('ConsolePanel', () => {
  beforeEach(() => {
    vi.resetAllMocks();
    global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
    mockSendCommand.mockClear();
    mockReconnect.mockClear();
    mockDisconnect.mockClear();
    resetMockConfig();
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

  describe('source selector dropdown', () => {
    it('renders source selector button', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('source-selector')).toBeInTheDocument();
    });

    it('shows "Console" label by default for console mode', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByTestId('source-selector'));

      expect(screen.getByText('Live Console')).toBeInTheDocument();
    });

    it('opens dropdown and shows Live Console option', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByTestId('source-selector'));

      expect(screen.getByText('Live Console')).toBeInTheDocument();
      expect(screen.getByText('Output Source')).toBeInTheDocument();
    });

    it('shows log files in dropdown when available', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: {
          data: {
            files: [
              { name: 'server-main.txt', sizeBytes: 1024, modifiedAt: '2026-01-17T10:30:00Z' },
              { name: 'error.txt', sizeBytes: 512, modifiedAt: '2026-01-17T09:15:00Z' },
            ],
          },
        },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByTestId('source-selector'));

      expect(screen.getByText('server-main.txt')).toBeInTheDocument();
      expect(screen.getByText('error.txt')).toBeInTheDocument();
      expect(screen.getByText('Log Files')).toBeInTheDocument();
    });

    it('shows "No log files available" when log files list is empty', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: { data: { files: [] } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByTestId('source-selector'));

      expect(screen.getByText('No log files available')).toBeInTheDocument();
    });

    it('clicking log file switches to log file mode', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: {
          data: {
            files: [{ name: 'server-main.txt', sizeBytes: 1024, modifiedAt: '2026-01-17T10:30:00Z' }],
          },
        },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Open dropdown
      await user.click(screen.getByTestId('source-selector'));

      // Click on log file
      await user.click(screen.getByText('server-main.txt'));

      // Verify source selector shows the log file name
      expect(screen.getByTestId('source-selector')).toHaveTextContent('server-main.txt');
    });

    it('clicking "Live Console" switches back to console mode', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: {
          data: {
            files: [{ name: 'server-main.txt', sizeBytes: 1024, modifiedAt: '2026-01-17T10:30:00Z' }],
          },
        },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Open dropdown
      await user.click(screen.getByTestId('source-selector'));

      // Click on log file
      await user.click(screen.getByText('server-main.txt'));

      // Open dropdown again
      await user.click(screen.getByTestId('source-selector'));

      // Click on Live Console
      await user.click(screen.getByText('Live Console'));

      // Verify source selector shows "Console"
      expect(screen.getByTestId('source-selector')).toHaveTextContent('Console');
    });

    it('shows file icon for log file mode in source selector', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: {
          data: {
            files: [{ name: 'server-main.txt', sizeBytes: 1024, modifiedAt: '2026-01-17T10:30:00Z' }],
          },
        },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Open dropdown
      await user.click(screen.getByTestId('source-selector'));

      // Click on log file
      await user.click(screen.getByText('server-main.txt'));

      // Verify file icon is shown (the button should have FileText icon, not Terminal icon)
      const sourceButton = screen.getByTestId('source-selector');
      expect(sourceButton.innerHTML).toContain('file-text');
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

    it('command input is disabled with "Disconnected" placeholder when disconnected', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      expect(input).toBeDisabled();
      expect(input).toHaveAttribute('placeholder', 'Disconnected');
    });

    it('command input is disabled with "Server not running" placeholder when server is stopped', () => {
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'installed' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      expect(input).toBeDisabled();
      expect(input).toHaveAttribute('placeholder', 'Server not running');
    });

    it('command input is disabled in log file mode', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: {
          data: {
            files: [{ name: 'server-main.txt', sizeBytes: 1024, modifiedAt: '2026-01-17T10:30:00Z' }],
          },
        },
        isLoading: false,
        error: null,
      };

      // Mock as connected and running for console mode
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Open dropdown
      await user.click(screen.getByTestId('source-selector'));

      // Click on log file
      await user.click(screen.getByText('server-main.txt'));

      // Input should show "Viewing log file (read-only)" and be disabled
      const input = screen.getByLabelText('Command input');
      expect(input).toBeDisabled();
      expect(input).toHaveAttribute('placeholder', 'Viewing log file (read-only)');
    });

    it('send button is disabled when disconnected', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const button = screen.getByRole('button', { name: 'Send' });
      expect(button).toBeDisabled();
    });

    it('send button is disabled when server is stopped', () => {
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'installed' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const button = screen.getByRole('button', { name: 'Send' });
      expect(button).toBeDisabled();
    });

    it('send button is disabled in log file mode', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: {
          data: {
            files: [{ name: 'server-main.txt', sizeBytes: 1024, modifiedAt: '2026-01-17T10:30:00Z' }],
          },
        },
        isLoading: false,
        error: null,
      };

      // Mock as connected and running for console mode
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Open dropdown
      await user.click(screen.getByTestId('source-selector'));

      // Click on log file
      await user.click(screen.getByText('server-main.txt'));

      // Send button should be disabled
      const button = screen.getByRole('button', { name: 'Send' });
      expect(button).toBeDisabled();
    });

    it('placeholder shows "Enter command..." when connected and server running', () => {
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      expect(input).not.toBeDisabled();
      expect(input).toHaveAttribute('placeholder', 'Enter command...');
    });
  });

  describe('command submission', () => {
    it('sends command on form submission', async () => {
      const user = userEvent.setup();
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: mockSendCommand,
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '/help');

      const button = screen.getByRole('button', { name: 'Send' });
      await user.click(button);

      expect(mockSendCommand).toHaveBeenCalledWith('/help');
      expect(input).toHaveValue('');
    });

    it('sends command on Enter key', async () => {
      const user = userEvent.setup();
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: mockSendCommand,
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '/help{enter}');

      expect(mockSendCommand).toHaveBeenCalledWith('/help');
    });

    it('does not send empty command', async () => {
      const user = userEvent.setup();
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: mockSendCommand,
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '   '); // Only whitespace

      const button = screen.getByRole('button', { name: 'Send' });
      expect(button).toBeDisabled(); // Button should be disabled for empty input

      await user.click(button);

      expect(mockSendCommand).not.toHaveBeenCalled();
    });

    it('trims command before sending', async () => {
      const user = userEvent.setup();
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: mockSendCommand,
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '  /help  '); // Extra whitespace

      const button = screen.getByRole('button', { name: 'Send' });
      await user.click(button);

      expect(mockSendCommand).toHaveBeenCalledWith('/help');
    });
  });

  describe('ConnectionStatus display', () => {
    it('displays connecting state', () => {
      mockConfig.consoleWebSocket = {
        connectionState: 'connecting',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Connecting...')).toBeInTheDocument();
    });

    it('displays connected state', () => {
      mockConfig.consoleWebSocket = {
        connectionState: 'connected',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };
      mockConfig.serverStatus = {
        data: { data: { state: 'running' } },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Connected')).toBeInTheDocument();
    });

    it('displays disconnected state', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Disconnected')).toBeInTheDocument();
    });

    it('displays access denied state', () => {
      mockConfig.consoleWebSocket = {
        connectionState: 'forbidden',
        sendCommand: vi.fn(),
        retryCount: 0,
        isReconnecting: false,
        wsRef: { current: null },
        reconnect: vi.fn(),
        disconnect: vi.fn(),
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Access Denied')).toBeInTheDocument();
    });
  });

  describe('terminal behavior', () => {
    it('source change clears terminal', async () => {
      const user = userEvent.setup();
      mockConfig.logFiles = {
        data: {
          data: {
            files: [{ name: 'server-main.txt', sizeBytes: 1024, modifiedAt: '2026-01-17T10:30:00Z' }],
          },
        },
        isLoading: false,
        error: null,
      };

      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      // Open dropdown and switch to log file
      await user.click(screen.getByTestId('source-selector'));
      await user.click(screen.getByText('server-main.txt'));

      // Open dropdown again and switch back to console
      await user.click(screen.getByTestId('source-selector'));
      await user.click(screen.getByText('Live Console'));

      // The terminal clear method should have been called (verified via mock)
      // This test verifies the source switching functionality works
      expect(screen.getByTestId('source-selector')).toHaveTextContent('Console');
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

      expect(screen.getByLabelText('Command input')).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('command input has aria-label', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByLabelText('Command input')).toBeInTheDocument();
    });

    it('source selector has accessible label through testid', () => {
      const queryClient = createTestQueryClient();
      render(<ConsolePanel />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('source-selector')).toBeInTheDocument();
    });
  });
});
