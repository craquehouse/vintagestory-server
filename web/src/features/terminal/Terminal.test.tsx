import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';

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
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering (AC: 1)', () => {
    it('renders the terminal page', () => {
      render(<Terminal />);

      expect(screen.getByLabelText('Terminal page')).toBeInTheDocument();
    });

    it('renders the "Server Console" header', () => {
      render(<Terminal />);

      expect(screen.getByText('Server Console')).toBeInTheDocument();
    });

    it('renders the connection status indicator', () => {
      render(<Terminal />);

      // Should show "Connecting..." initially
      expect(screen.getByText('Connecting...')).toBeInTheDocument();
    });

    it('renders the terminal container', () => {
      render(<Terminal />);

      expect(
        screen.getByRole('application', { name: 'Server console terminal' })
      ).toBeInTheDocument();
    });
  });

  describe('connection status (AC: 4)', () => {
    it('shows "Connecting..." initially', () => {
      render(<Terminal />);

      expect(screen.getByText('Connecting...')).toBeInTheDocument();
    });

    it('displays connection status component in header', () => {
      render(<Terminal />);

      // The ConnectionStatus component should be rendered
      const statusElement = screen.getByRole('status');
      expect(statusElement).toBeInTheDocument();
      expect(statusElement).toHaveAttribute('aria-live', 'polite');
    });

    it('renders connection status with correct aria-label for initial state', () => {
      render(<Terminal />);

      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveAttribute(
        'aria-label',
        'Connection status: Connecting...'
      );
    });
  });

  describe('WebSocket connection (AC: 1)', () => {
    it('creates WebSocket connection with correct URL', () => {
      render(<Terminal />);

      expect(MockWebSocket.instances).toHaveLength(1);
      expect(MockWebSocket.instances[0]?.url).toContain('/api/v1alpha1/console/ws');
      expect(MockWebSocket.instances[0]?.url).toContain('api_key=test-api-key');
    });

    it('creates WebSocket with history_lines parameter', () => {
      render(<Terminal />);

      expect(MockWebSocket.instances[0]?.url).toContain('history_lines=100');
    });
  });

  describe('accessibility', () => {
    it('has proper aria-label on terminal container', () => {
      render(<Terminal />);

      const terminalContainer = screen.getByRole('application');
      expect(terminalContainer).toHaveAttribute(
        'aria-label',
        'Server console terminal'
      );
    });

    it('has connection status with ARIA live region', () => {
      render(<Terminal />);

      const statusElement = screen.getByRole('status');
      expect(statusElement).toHaveAttribute('aria-live', 'polite');
    });
  });

  describe('layout', () => {
    it('has proper flex layout for full height', () => {
      render(<Terminal />);

      const container = screen.getByLabelText('Terminal page');
      expect(container).toHaveClass('flex', 'h-full', 'flex-col');
    });
  });
});
