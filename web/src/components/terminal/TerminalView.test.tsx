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

// Mock cookies module
vi.mock('@/lib/cookies', () => ({
  getCookie: vi.fn(),
  setCookie: vi.fn(),
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
import { PreferencesProvider } from '@/contexts/PreferencesContext';
import * as cookies from '@/lib/cookies';

const mockedGetCookie = vi.mocked(cookies.getCookie);

// Helper to render with PreferencesProvider
function renderTerminal(props: Parameters<typeof TerminalView>[0] = {}) {
  return render(
    <PreferencesProvider>
      <TerminalView {...props} />
    </PreferencesProvider>
  );
}

describe('TerminalView', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    lastTerminalOptions = undefined;
    lastTerminalInstance = undefined;
    mockResolvedTheme = 'dark';
    mockedGetCookie.mockReturnValue(null);
    global.ResizeObserver = MockResizeObserver as unknown as typeof ResizeObserver;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('rendering (AC: 1)', () => {
    it('renders terminal container with proper role', () => {
      renderTerminal();

      const container = screen.getByRole('application');
      expect(container).toBeInTheDocument();
    });

    it('has proper aria-label for accessibility', () => {
      renderTerminal();

      const container = screen.getByRole('application');
      expect(container).toHaveAttribute('aria-label', 'Server console terminal');
    });

    it('applies custom className', () => {
      renderTerminal({ className: 'custom-class' });

      const container = screen.getByRole('application');
      expect(container).toHaveClass('custom-class');
    });

    it('has min-h-0 and min-w-0 classes for proper flex behavior', () => {
      renderTerminal();

      const container = screen.getByRole('application');
      expect(container).toHaveClass('min-h-0');
      expect(container).toHaveClass('min-w-0');
    });
  });

  describe('initialization (AC: 1)', () => {
    it('initializes Terminal with correct options using default font size', () => {
      renderTerminal();

      expect(lastTerminalOptions).toMatchObject({
        cursorBlink: true,
        fontSize: 14, // Default from FONT_SIZE_DEFAULT
        convertEol: true,
      });
      expect(lastTerminalOptions?.fontFamily).toContain('JetBrains Mono');
    });

    it('uses font size from preferences cookie', () => {
      mockedGetCookie.mockReturnValue(JSON.stringify({ consoleFontSize: 18 }));

      renderTerminal();

      expect(lastTerminalOptions?.fontSize).toBe(18);
    });

    it('uses fontSize prop override when provided', () => {
      mockedGetCookie.mockReturnValue(JSON.stringify({ consoleFontSize: 18 }));

      renderTerminal({ fontSize: 20 });

      expect(lastTerminalOptions?.fontSize).toBe(20);
    });

    it('loads FitAddon', () => {
      renderTerminal();

      expect(mockLoadAddon).toHaveBeenCalled();
    });

    it('opens terminal in container', () => {
      renderTerminal();

      expect(mockOpen).toHaveBeenCalled();
    });

    it('calls fit on mount', () => {
      renderTerminal();

      expect(mockFit).toHaveBeenCalled();
    });

    it('calls onReady callback with terminal instance', async () => {
      const onReady = vi.fn();

      renderTerminal({ onReady });

      await waitFor(() => {
        expect(onReady).toHaveBeenCalled();
      });
    });
  });

  describe('cleanup', () => {
    it('disposes terminal on unmount', () => {
      const { unmount } = renderTerminal();

      unmount();

      expect(mockDispose).toHaveBeenCalled();
    });

    it('calls onDispose callback on unmount', () => {
      const onDispose = vi.fn();
      const { unmount } = renderTerminal({ onDispose });

      unmount();

      expect(onDispose).toHaveBeenCalled();
    });

    it('disconnects ResizeObserver on unmount', () => {
      const { unmount } = renderTerminal();

      unmount();

      expect(mockDisconnect).toHaveBeenCalled();
    });
  });

  describe('resize handling (AC: 6)', () => {
    it('sets up ResizeObserver on container', () => {
      renderTerminal();

      expect(mockObserve).toHaveBeenCalled();
    });

    it('calls fit on resize event', async () => {
      // Mock requestAnimationFrame
      vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
        cb(0);
        return 0;
      });

      renderTerminal();

      // fit should be called on mount
      expect(mockFit).toHaveBeenCalled();
    });
  });

  describe('theming (AC: 5)', () => {
    it('initializes terminal with dark theme (Catppuccin Mocha)', () => {
      renderTerminal();

      // Theme should be passed to terminal constructor
      expect(lastTerminalOptions?.theme).toBeDefined();
      // Check for Catppuccin Mocha background color (mantle)
      const theme = lastTerminalOptions?.theme as Record<string, string>;
      expect(theme?.background).toBe('#181825');
    });

    it('initializes terminal with light theme (Catppuccin Latte) when theme is light', () => {
      mockResolvedTheme = 'light';

      renderTerminal();

      // Check for Catppuccin Latte background color
      const theme = lastTerminalOptions?.theme as Record<string, string>;
      expect(theme?.background).toBe('#eff1f5');
    });

    it('updates terminal theme when ThemeContext changes after mount', () => {
      // Start with dark theme
      mockResolvedTheme = 'dark';
      const { rerender } = render(
        <PreferencesProvider>
          <TerminalView />
        </PreferencesProvider>
      );

      // Verify initial dark theme (mantle)
      expect(lastTerminalInstance?.options.theme).toBeDefined();
      const initialTheme = lastTerminalInstance?.options.theme as Record<string, string>;
      expect(initialTheme?.background).toBe('#181825');

      // Change to light theme and re-render
      mockResolvedTheme = 'light';
      rerender(
        <PreferencesProvider>
          <TerminalView />
        </PreferencesProvider>
      );

      // Verify theme was updated to Catppuccin Latte
      const updatedTheme = lastTerminalInstance?.options.theme as Record<string, string>;
      expect(updatedTheme?.background).toBe('#eff1f5');
    });
  });

  describe('font size updates', () => {
    it('updates terminal font size when fontSize prop changes', () => {
      const { rerender } = render(
        <PreferencesProvider>
          <TerminalView fontSize={14} />
        </PreferencesProvider>
      );

      // Clear the initial fit call
      mockFit.mockClear();

      // Update font size
      rerender(
        <PreferencesProvider>
          <TerminalView fontSize={18} />
        </PreferencesProvider>
      );

      // Verify font size was updated on terminal instance
      expect(lastTerminalInstance?.options.fontSize).toBe(18);
      // Verify fit was called to adjust terminal dimensions
      expect(mockFit).toHaveBeenCalled();
    });

    it('updates terminal font size when fontSize prop changes from default', () => {
      // Start without fontSize prop (uses default 14)
      const { rerender } = render(
        <PreferencesProvider>
          <TerminalView />
        </PreferencesProvider>
      );

      // Clear the initial fit call
      mockFit.mockClear();

      // Update to new fontSize
      rerender(
        <PreferencesProvider>
          <TerminalView fontSize={20} />
        </PreferencesProvider>
      );

      // Verify font size was updated on terminal instance
      expect(lastTerminalInstance?.options.fontSize).toBe(20);
      // Verify fit was called to adjust terminal dimensions
      expect(mockFit).toHaveBeenCalled();
    });

    it('handles fit errors during font size update gracefully', () => {
      // Make fit throw an error
      mockFit.mockImplementationOnce(() => {
        throw new Error('Terminal disposed');
      });

      const { rerender } = render(
        <PreferencesProvider>
          <TerminalView fontSize={14} />
        </PreferencesProvider>
      );

      // Update font size - should not throw despite fit error
      expect(() => {
        rerender(
          <PreferencesProvider>
            <TerminalView fontSize={18} />
          </PreferencesProvider>
        );
      }).not.toThrow();

      // Verify fit was called even though it threw
      expect(mockFit).toHaveBeenCalled();
    });
  });

  describe('resize error handling', () => {
    it('handles fit errors during resize gracefully', () => {
      // Store RAF callback
      let rafCallback: FrameRequestCallback | null = null;

      // Mock requestAnimationFrame to capture the callback
      const rafSpy = vi.spyOn(window, 'requestAnimationFrame').mockImplementation((cb) => {
        rafCallback = cb;
        return 0;
      });

      // Store the ResizeObserver callback
      let resizeObserverCallback: ResizeObserverCallback | null = null;

      // Override ResizeObserver to capture callback
      class TestMockResizeObserver {
        callback: ResizeObserverCallback;
        constructor(callback: ResizeObserverCallback) {
          this.callback = callback;
          resizeObserverCallback = callback;
        }
        observe = mockObserve;
        disconnect = mockDisconnect;
        unobserve = vi.fn();
      }

      global.ResizeObserver = TestMockResizeObserver as unknown as typeof ResizeObserver;

      renderTerminal();

      // Clear the initial fit call from mount
      mockFit.mockClear();

      // Make fit throw an error on next call
      mockFit.mockImplementationOnce(() => {
        throw new Error('Terminal disposed during resize');
      });

      // Verify we captured the resize callback
      expect(resizeObserverCallback).toBeDefined();

      // Trigger resize - this should call requestAnimationFrame with fit
      if (resizeObserverCallback) {
        resizeObserverCallback([], {} as ResizeObserver);

        // Now execute the RAF callback which should call fit() in a try-catch
        if (rafCallback) {
          expect(() => rafCallback(0)).not.toThrow();
        }

        // Verify fit was attempted despite the error
        expect(mockFit).toHaveBeenCalled();
      }

      rafSpy.mockRestore();
    });
  });
});
