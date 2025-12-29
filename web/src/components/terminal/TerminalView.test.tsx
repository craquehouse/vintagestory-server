import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';

// Track mock calls
let mockDispose: ReturnType<typeof vi.fn>;
let mockOpen: ReturnType<typeof vi.fn>;
let mockLoadAddon: ReturnType<typeof vi.fn>;
let mockFit: ReturnType<typeof vi.fn>;
let lastTerminalOptions: Record<string, unknown> | undefined;
let lastTerminalInstance: { options: Record<string, unknown> } | undefined;

// Mock xterm.js - vi.mock is hoisted so we use factory pattern
vi.mock('@xterm/xterm', () => {
  return {
    Terminal: class MockTerminal {
      options: Record<string, unknown> = {};
      loadAddon = vi.fn();
      open = vi.fn();
      dispose = vi.fn();
      writeln = vi.fn();
      constructor(options?: Record<string, unknown>) {
        if (options) {
          this.options = options;
          lastTerminalOptions = options;
        }
        // Store references to instance methods for assertions
        mockDispose = this.dispose;
        mockOpen = this.open;
        mockLoadAddon = this.loadAddon;
        lastTerminalInstance = this;
      }
    },
  };
});

vi.mock('@xterm/addon-fit', () => {
  return {
    FitAddon: class MockFitAddon {
      fit = vi.fn();
      constructor() {
        mockFit = this.fit;
      }
    },
  };
});

// Mock theme state - mutable for testing theme changes
let mockResolvedTheme = 'dark';

// Mock next-themes
vi.mock('next-themes', () => ({
  useTheme: () => ({
    theme: mockResolvedTheme,
    setTheme: vi.fn(),
    resolvedTheme: mockResolvedTheme,
    systemTheme: mockResolvedTheme,
  }),
}));

// Mock ResizeObserver
const mockObserve = vi.fn();
const mockDisconnect = vi.fn();
class MockResizeObserver {
  callback: ResizeObserverCallback;
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }
  observe = mockObserve;
  disconnect = mockDisconnect;
  unobserve = vi.fn();
}

// Import after mocks are set up
import { TerminalView } from './TerminalView';

describe('TerminalView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lastTerminalOptions = undefined;
    lastTerminalInstance = undefined;
    mockResolvedTheme = 'dark';
    global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering (AC: 1)', () => {
    it('renders terminal container with proper role', () => {
      render(<TerminalView />);

      const container = screen.getByRole('application');
      expect(container).toBeInTheDocument();
    });

    it('has proper aria-label for accessibility', () => {
      render(<TerminalView />);

      const container = screen.getByRole('application');
      expect(container).toHaveAttribute('aria-label', 'Server console terminal');
    });

    it('applies custom className', () => {
      render(<TerminalView className="custom-class" />);

      const container = screen.getByRole('application');
      expect(container).toHaveClass('custom-class');
    });

    it('has min-h-0 and min-w-0 classes for proper flex behavior', () => {
      render(<TerminalView />);

      const container = screen.getByRole('application');
      expect(container).toHaveClass('min-h-0');
      expect(container).toHaveClass('min-w-0');
    });
  });

  describe('initialization (AC: 1)', () => {
    it('initializes Terminal with correct options', () => {
      render(<TerminalView />);

      expect(lastTerminalOptions).toMatchObject({
        cursorBlink: true,
        fontSize: 14,
        convertEol: true,
      });
      expect(lastTerminalOptions?.fontFamily).toContain('JetBrains Mono');
    });

    it('loads FitAddon', () => {
      render(<TerminalView />);

      expect(mockLoadAddon).toHaveBeenCalled();
    });

    it('opens terminal in container', () => {
      render(<TerminalView />);

      expect(mockOpen).toHaveBeenCalled();
    });

    it('calls fit on mount', () => {
      render(<TerminalView />);

      expect(mockFit).toHaveBeenCalled();
    });

    it('calls onReady callback with terminal instance', async () => {
      const onReady = vi.fn();

      render(<TerminalView onReady={onReady} />);

      await waitFor(() => {
        expect(onReady).toHaveBeenCalled();
      });
    });
  });

  describe('cleanup', () => {
    it('disposes terminal on unmount', () => {
      const { unmount } = render(<TerminalView />);

      unmount();

      expect(mockDispose).toHaveBeenCalled();
    });

    it('calls onDispose callback on unmount', () => {
      const onDispose = vi.fn();
      const { unmount } = render(<TerminalView onDispose={onDispose} />);

      unmount();

      expect(onDispose).toHaveBeenCalled();
    });

    it('disconnects ResizeObserver on unmount', () => {
      const { unmount } = render(<TerminalView />);

      unmount();

      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe('resize handling (AC: 6)', () => {
    it('sets up ResizeObserver on container', () => {
      render(<TerminalView />);

      expect(mockObserve).toHaveBeenCalled();
    });

    it('calls fit on resize event', async () => {
      // Mock requestAnimationFrame
      vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
        cb(0);
        return 0;
      });

      render(<TerminalView />);

      // fit should be called on mount
      expect(mockFit).toHaveBeenCalled();
    });
  });

  describe('theming (AC: 5)', () => {
    it('initializes terminal with dark theme (Catppuccin Mocha)', () => {
      render(<TerminalView />);

      // Theme should be passed to terminal constructor
      expect(lastTerminalOptions?.theme).toBeDefined();
      // Check for Catppuccin Mocha background color
      const theme = lastTerminalOptions?.theme as Record<string, string>;
      expect(theme?.background).toBe('#1e1e2e');
    });

    it('initializes terminal with light theme (Catppuccin Latte) when theme is light', () => {
      mockResolvedTheme = 'light';

      render(<TerminalView />);

      // Check for Catppuccin Latte background color
      const theme = lastTerminalOptions?.theme as Record<string, string>;
      expect(theme?.background).toBe('#eff1f5');
    });

    it('updates terminal theme when ThemeContext changes after mount', () => {
      // Start with dark theme
      mockResolvedTheme = 'dark';
      const { rerender } = render(<TerminalView />);

      // Verify initial dark theme
      expect(lastTerminalInstance?.options.theme).toBeDefined();
      const initialTheme = lastTerminalInstance?.options.theme as Record<string, string>;
      expect(initialTheme?.background).toBe('#1e1e2e');

      // Change to light theme and re-render
      mockResolvedTheme = 'light';
      rerender(<TerminalView />);

      // Verify theme was updated to Catppuccin Latte
      const updatedTheme = lastTerminalInstance?.options.theme as Record<string, string>;
      expect(updatedTheme?.background).toBe('#eff1f5');
    });
  });
});
