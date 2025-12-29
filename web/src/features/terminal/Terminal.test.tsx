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

// Import after mocks
import { Terminal } from './Terminal';

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
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
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
      value: { protocol: 'http:', host: 'localhost:8000' },
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
    it('creates WebSocket connection with correct URL', () => {
      renderTerminal();

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(MockWebSocket.instances[0]?.url).toContain('/api/v1alpha1/console/ws');
      expect(MockWebSocket.instances[0]?.url).toContain('api_key=test-api-key');
    });

    it('creates WebSocket with history_lines parameter', () => {
      renderTerminal();

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

    it('sends command on Enter key', async () => {
      const user = userEvent.setup();
      renderTerminal();
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

      act(() => {
        MockWebSocket.instances[0]?.simulateOpen();
      });

      await waitFor(() => {
        expect(input).toHaveAttribute('placeholder', 'Enter command...');
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
});
