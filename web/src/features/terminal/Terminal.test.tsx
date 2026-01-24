import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';

// WebSocket constants
const WS_CONNECTING = 0;
const WS_OPEN = 1;
const WS_CLOSED = 3;

// Mock WebSocket
class MockWebSocket {
  static instances: MockWebSocket[] = [];
  static readonly CONNECTING = WS_CONNECTING;
  static readonly OPEN = WS_OPEN;
  static readonly CLOSED = WS_CLOSED;

  url: string;
  readyState: number = WS_CONNECTING;
  onopen: ((ev: Event) => void) | null = null;
  onclose: ((ev: CloseEvent) => void) | null = null;
  onmessage: ((ev: MessageEvent) => void) | null = null;
  onerror: ((ev: Event) => void) | null = null;
  send = vi.fn();
  close = vi.fn();

  constructor(url: string) {
    this.url = url;
    MockWebSocket.instances.push(this);
  }

  simulateOpen() {
    this.readyState = WS_OPEN;
    if (this.onopen) {
      this.onopen(new Event('open'));
    }
  }

  simulateClose(code: number = 1000) {
    this.readyState = WS_CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close', { code, wasClean: true }));
    }
  }

  simulateMessage(data: string) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', { data }));
    }
  }
}

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

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn().mockReturnValue(null),
  setCookie: vi.fn(),
}));

// Mock ws-token module for Story 9.1
vi.mock('@/api/ws-token', () => ({
  requestWebSocketToken: vi.fn().mockResolvedValue({
    token: 'mock-token-123',
    expiresAt: '2026-01-03T12:05:00Z',
    expiresInSeconds: 300,
  }),
  WebSocketTokenError: class WebSocketTokenError extends Error {
    constructor(message: string) {
      super(message);
      this.name = 'WebSocketTokenError';
    }
  },
}));

// Import after mocks
import { Terminal } from './Terminal';
import { PreferencesProvider } from '@/contexts/PreferencesContext';

// Create a wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <PreferencesProvider>{children}</PreferencesProvider>
      </QueryClientProvider>
    );
  };
}

// Helper to render with providers
function renderTerminal() {
  return render(<Terminal />, { wrapper: createWrapper() });
}

describe('Terminal Page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    MockWebSocket.instances = [];
    // @ts-expect-error - Mocking global WebSocket
    global.WebSocket = MockWebSocket;
    global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
    import.meta.env.VITE_API_KEY = 'test-api-key';
    Object.defineProperty(window, 'location', {
      value: { protocol: 'http:', host: 'localhost:8080' },
      writable: true,
    });

    // Mock fetch for server status endpoint
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: () =>
        Promise.resolve({
          status: 'ok',
          data: { state: 'running', version: '1.21.3', uptime_seconds: 100 },
        }),
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering (AC: 1)', () => {
    it('renders the terminal page', () => {
      renderTerminal();

      expect(screen.getByLabelText('Terminal page')).toBeInTheDocument();
    });

    it('renders the "Server Console" header', () => {
      renderTerminal();

      expect(screen.getByText('Server Console')).toBeInTheDocument();
    });

    it('renders the connection status indicator', () => {
      renderTerminal();

      // Should show "Connecting..." initially
      expect(screen.getByText('Connecting...')).toBeInTheDocument();
    });

    it('renders the terminal container', () => {
      renderTerminal();

      expect(
        screen.getByRole('application', { name: 'Server console terminal' })
      ).toBeInTheDocument();
    });

    it('renders the command input field', () => {
      renderTerminal();

      expect(screen.getByLabelText('Command input')).toBeInTheDocument();
    });

    it('renders the send button', () => {
      renderTerminal();

      expect(screen.getByRole('button', { name: 'Send' })).toBeInTheDocument();
    });
  });

  describe('connection status (AC: 4)', () => {
    it('shows "Connecting..." initially', () => {
      renderTerminal();

      expect(screen.getByText('Connecting...')).toBeInTheDocument();
    });

    it('displays connection status component in header', () => {
      renderTerminal();

      // The ConnectionStatus component should be rendered
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
      expect(statusElement).toHaveAttribute('aria-live', 'polite');
    });

    it('renders connection status with correct aria-label for initial state', () => {
      renderTerminal();

      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveAttribute(
        'aria-label',
        'Connection status: Connecting...'
      );
    });
  });

  describe('WebSocket connection (AC: 1)', () => {
    it('creates WebSocket connection with correct URL', async () => {
      renderTerminal();

      // Wait for token request and WebSocket creation
      await waitFor(() => {
        expect(MockWebSocket.instances).toHaveLength(1);
      });
      expect(MockWebSocket.instances[0]?.url).toContain('/api/v1alpha1/console/ws');
      expect(MockWebSocket.instances[0]?.url).toContain('token=mock-token-123');
    });

    it('creates WebSocket with history_lines parameter', async () => {
      renderTerminal();

      // Wait for token request and WebSocket creation
      await waitFor(() => {
        expect(MockWebSocket.instances).toHaveLength(1);
      });
      expect(MockWebSocket.instances[0]?.url).toContain('history_lines=100');
    });
  });

  describe('command input (AC: 3)', () => {
    it('disables input when not connected', () => {
      renderTerminal();

      const input = screen.getByLabelText('Command input');
      expect(input).toBeDisabled();
    });

    it('enables input when connected', async () => {
      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      // Simulate connection
      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        const input = screen.getByLabelText('Command input');
        expect(input).not.toBeDisabled();
      });
    });

    it('disables send button when input is empty', async () => {
      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        const button = screen.getByRole('button', { name: 'Send' });
        expect(button).toBeDisabled();
      });
    });

    it('enables send button when input has content', async () => {
      const user = userEvent.setup();
      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(screen.getByLabelText('Command input')).not.toBeDisabled();
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '/help');

      const button = screen.getByRole('button', { name: 'Send' });
      expect(button).not.toBeDisabled();
    });

    it('sends command when form is submitted', async () => {
      const user = userEvent.setup();
      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(screen.getByLabelText('Command input')).not.toBeDisabled();
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '/help');

      const button = screen.getByRole('button', { name: 'Send' });
      await user.click(button);

      expect(MockWebSocket.instances[0]?.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'command', content: '/help' })
      );
    });

    it('clears input after sending command', async () => {
      const user = userEvent.setup();
      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(screen.getByLabelText('Command input')).not.toBeDisabled();
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '/help');
      await user.click(screen.getByRole('button', { name: 'Send' }));

      expect(input).toHaveValue('');
    });

    it('does not send command when input is whitespace only', async () => {
      const user = userEvent.setup();
      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(screen.getByLabelText('Command input')).not.toBeDisabled();
      });

      const input = screen.getByLabelText('Command input');
      // Type only whitespace
      await user.type(input, '   ');
      await user.click(screen.getByRole('button', { name: 'Send' }));

      // Should not have sent any command
      expect(MockWebSocket.instances[0]?.send).not.toHaveBeenCalled();
      // Input should still contain the whitespace (not cleared)
      expect(input).toHaveValue('   ');
    });

    it('does not send command when server is not running even if connected', async () => {
      const user = userEvent.setup();

      // Mock server status as stopped
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { state: 'stopped', version: '1.21.3', uptime_seconds: 0 },
          }),
      });

      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      // Simulate connection
      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      // Input should be disabled when server is not running
      await waitFor(() => {
        const input = screen.getByLabelText('Command input');
        expect(input).toBeDisabled();
      });

      const input = screen.getByLabelText('Command input');
      const button = screen.getByRole('button', { name: 'Send' });

      // Button should be disabled
      expect(button).toBeDisabled();

      // Try to submit anyway by triggering the form
      const form = button.closest('form');
      if (form) {
        act(() => {
          form.dispatchEvent(
            new Event('submit', { bubbles: true, cancelable: true })
          );
        });
      }

      // Should not have sent any command
      expect(MockWebSocket.instances[0]?.send).not.toHaveBeenCalled();
    });

    it('sends command on Enter key', async () => {
      const user = userEvent.setup();
      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(screen.getByLabelText('Command input')).not.toBeDisabled();
      });

      const input = screen.getByLabelText('Command input');
      await user.type(input, '/help{enter}');

      expect(MockWebSocket.instances[0]?.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'command', content: '/help' })
      );
    });

    it('shows placeholder based on connection state', async () => {
      renderTerminal();

      const input = screen.getByLabelText('Command input');
      expect(input).toHaveAttribute('placeholder', 'Disconnected');

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(input).toHaveAttribute('placeholder', 'Enter command...');
      });
    });

    it('shows "Server not running" placeholder when connected but server is stopped', async () => {
      // Mock server status as stopped
      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { state: 'stopped', version: '1.21.3', uptime_seconds: 0 },
          }),
      });

      renderTerminal();

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      // Simulate connection
      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      // Wait for server status to be fetched
      await waitFor(() => {
        const input = screen.getByLabelText('Command input');
        expect(input).toHaveAttribute('placeholder', 'Server not running');
      });
    });
  });

  describe('accessibility', () => {
    it('has proper aria-label on terminal container', () => {
      renderTerminal();

      const terminalContainer = screen.getByRole('application');
      expect(terminalContainer).toHaveAttribute(
        'aria-label',
        'Server console terminal'
      );
    });

    it('has connection status with ARIA live region', () => {
      renderTerminal();

      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveAttribute('aria-live', 'polite');
    });

    it('has aria-label on command input', () => {
      renderTerminal();

      expect(screen.getByLabelText('Command input')).toBeInTheDocument();
    });
  });

  describe('layout', () => {
    it('has proper flex layout for full height', () => {
      renderTerminal();

      const container = screen.getByLabelText('Terminal page');
      expect(container).toHaveClass('flex', 'h-full', 'flex-col');
    });
  });

  describe('message queuing before terminal ready', () => {
    it('queues messages received before terminal initialization and flushes them when ready', async () => {
      // This test verifies lines 34-38 (queuing) and lines 52-55 (flushing)
      //
      // Strategy: Use React's component lifecycle to create a race condition
      // where WebSocket messages arrive before the TerminalView calls onReady.
      // We'll control this by mocking TerminalView to delay onReady.

      let capturedOnReady: ((terminal: any) => void) | undefined;
      const { Terminal: MockTerminalClass } = await import('@xterm/xterm');

      // Create a custom TerminalView mock that delays calling onReady
      const DelayedTerminalView = ({
        onReady,
        onDispose,
        className,
      }: {
        onReady?: (terminal: any) => void;
        onDispose?: () => void;
        className?: string;
      }) => {
        // Capture the callback but don't call it yet
        capturedOnReady = onReady;
        return (
          <div
            className={className}
            role="application"
            aria-label="Server console terminal"
            data-testid="delayed-terminal"
          />
        );
      };

      // Temporarily mock the TerminalView module
      vi.doMock('@/components/terminal/TerminalView', () => ({
        TerminalView: DelayedTerminalView,
      }));

      // Need to re-import Terminal to pick up the new mock
      vi.resetModules();
      const { Terminal: TestTerminal } = await import('./Terminal');

      // Render with the mocked TerminalView
      const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
      const PreferencesProvider = (await import('@/contexts/PreferencesContext'))
        .PreferencesProvider;

      render(
        <QueryClientProvider client={queryClient}>
          <PreferencesProvider>
            <TestTerminal />
          </PreferencesProvider>
        </QueryClientProvider>
      );

      // Wait for WebSocket to be created
      await waitFor(() => {
        expect(MockWebSocket.instances.length).toBeGreaterThan(0);
      });

      // Simulate WebSocket opening
      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      // Send messages while terminal is NOT ready - should be queued (lines 34-38)
      act(() => {
        MockWebSocket.instances[0]?.simulateMessage('Queued message 1');
        MockWebSocket.instances[0]?.simulateMessage('Queued message 2');
        MockWebSocket.instances[0]?.simulateMessage('Queued message 3');
      });

      // Create mock terminal and trigger onReady
      const mockTerminalInstance = new MockTerminalClass();

      // Now call onReady - should flush queued messages (lines 52-55)
      expect(capturedOnReady).toBeDefined();
      act(() => {
        capturedOnReady!(mockTerminalInstance);
      });

      // Verify all queued messages were flushed
      expect(mockTerminalInstance.writeln).toHaveBeenCalledTimes(3);
      expect(mockTerminalInstance.writeln).toHaveBeenNthCalledWith(1, 'Queued message 1');
      expect(mockTerminalInstance.writeln).toHaveBeenNthCalledWith(2, 'Queued message 2');
      expect(mockTerminalInstance.writeln).toHaveBeenNthCalledWith(3, 'Queued message 3');

      // Send another message after terminal is ready
      act(() => {
        MockWebSocket.instances[0]?.simulateMessage('Direct message');
      });

      // Should be written directly (4th call)
      expect(mockTerminalInstance.writeln).toHaveBeenCalledTimes(4);
      expect(mockTerminalInstance.writeln).toHaveBeenNthCalledWith(4, 'Direct message');

      // Cleanup
      vi.doUnmock('@/components/terminal/TerminalView');
      vi.resetModules();
    });
  });

});
