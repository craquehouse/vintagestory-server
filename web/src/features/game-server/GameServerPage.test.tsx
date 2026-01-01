import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
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

// Import after mocks
import { GameServerPage } from './GameServerPage';

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
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock game config response
const mockGameConfig = {
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

describe('GameServerPage', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('rendering', () => {
    it('renders the page container', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('game-server-page')).toBeInTheDocument();
    });

    it('renders GameConfigPanel', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Shows loading initially, then content
      expect(
        screen.getByTestId('game-config-loading') ||
          screen.getByTestId('game-config-panel')
      ).toBeInTheDocument();
    });

    it('renders ConsolePanel', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByTestId('console-panel')).toBeInTheDocument();
    });

    it('renders both panels simultaneously', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Both panels should be present (GameConfig may be loading)
      expect(screen.getByTestId('console-panel')).toBeInTheDocument();
      expect(
        screen.getByTestId('game-config-loading') ||
          screen.getByTestId('game-config-panel')
      ).toBeInTheDocument();
    });
  });

  describe('layout structure', () => {
    it('has flex container with gap', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const container = screen.getByTestId('game-server-page');
      expect(container).toHaveClass('flex');
      expect(container).toHaveClass('gap-4');
    });

    it('has flex-col for mobile layout', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const container = screen.getByTestId('game-server-page');
      expect(container).toHaveClass('flex-col');
    });

    it('has lg:flex-row for desktop layout', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const container = screen.getByTestId('game-server-page');
      expect(container).toHaveClass('lg:flex-row');
    });

    it('fills available height', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const container = screen.getByTestId('game-server-page');
      expect(container).toHaveClass('h-full');
    });
  });

  describe('panel ordering', () => {
    it('GameConfigPanel is order-2 on mobile (bottom)', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      // Find the wrapper div containing GameConfigPanel
      const gameConfigLoading = screen.queryByTestId('game-config-loading');
      const gameConfigPanel = screen.queryByTestId('game-config-panel');
      const wrapper = (gameConfigLoading || gameConfigPanel)?.parentElement;

      expect(wrapper).toHaveClass('order-2');
    });

    it('GameConfigPanel is lg:order-1 on desktop (left)', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const gameConfigLoading = screen.queryByTestId('game-config-loading');
      const gameConfigPanel = screen.queryByTestId('game-config-panel');
      const wrapper = (gameConfigLoading || gameConfigPanel)?.parentElement;

      expect(wrapper).toHaveClass('lg:order-1');
    });

    it('ConsolePanel is order-1 on mobile (top)', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const consolePanel = screen.getByTestId('console-panel');
      const wrapper = consolePanel.parentElement;

      expect(wrapper).toHaveClass('order-1');
    });

    it('ConsolePanel is lg:order-2 on desktop (right)', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const consolePanel = screen.getByTestId('console-panel');
      const wrapper = consolePanel.parentElement;

      expect(wrapper).toHaveClass('lg:order-2');
    });
  });

  describe('panel sizing', () => {
    it('GameConfigPanel takes half width on desktop', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const gameConfigLoading = screen.queryByTestId('game-config-loading');
      const gameConfigPanel = screen.queryByTestId('game-config-panel');
      const wrapper = (gameConfigLoading || gameConfigPanel)?.parentElement;

      expect(wrapper).toHaveClass('lg:w-1/2');
    });

    it('ConsolePanel takes half width on desktop', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const consolePanel = screen.getByTestId('console-panel');
      const wrapper = consolePanel.parentElement;

      expect(wrapper).toHaveClass('lg:w-1/2');
    });

    it('GameConfigPanel is scrollable', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const gameConfigLoading = screen.queryByTestId('game-config-loading');
      const gameConfigPanel = screen.queryByTestId('game-config-panel');
      const wrapper = (gameConfigLoading || gameConfigPanel)?.parentElement;

      expect(wrapper).toHaveClass('overflow-auto');
    });

    it('ConsolePanel has minimum height on mobile', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const consolePanel = screen.getByTestId('console-panel');
      const wrapper = consolePanel.parentElement;

      expect(wrapper).toHaveClass('min-h-[300px]');
    });
  });

  describe('accessibility', () => {
    it('has aria-label on container', () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockGameConfig),
      });

      const queryClient = createTestQueryClient();
      render(<GameServerPage />, {
        wrapper: createWrapper(queryClient),
      });

      const container = screen.getByTestId('game-server-page');
      expect(container).toHaveAttribute('aria-label', 'Game Server page');
    });
  });
});
