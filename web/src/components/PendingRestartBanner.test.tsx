import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { PendingRestartBanner } from './PendingRestartBanner';

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

// Mock responses
const mockModsWithPendingRestart = {
  status: 'ok',
  data: {
    mods: [],
    pendingRestart: true,
  },
};

const mockModsNoPendingRestart = {
  status: 'ok',
  data: {
    mods: [],
    pendingRestart: false,
  },
};

describe('PendingRestartBanner', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('visibility (AC: 9)', () => {
    it('shows banner when pendingRestart is true', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('pending-restart-banner')).toBeInTheDocument();
      });
    });

    it('hides banner when pendingRestart is false', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsNoPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      // Wait for the query to settle
      await waitFor(() => {
        expect(globalThis.fetch).toHaveBeenCalled();
      });

      // Give component time to render (or not render)
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(screen.queryByTestId('pending-restart-banner')).not.toBeInTheDocument();
    });
  });

  describe('content', () => {
    it('displays restart icon', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('restart-icon')).toBeInTheDocument();
      });
    });

    it('displays "Restart required" text', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Restart required')).toBeInTheDocument();
      });
    });

    it('displays "Restart Now" button', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
        expect(screen.getByText('Restart Now')).toBeInTheDocument();
      });
    });
  });

  describe('restart functionality', () => {
    it('calls restart API when button is clicked', async () => {
      const restartFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server restarting' },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options) => {
        if (options?.method === 'POST' && url.includes('/restart')) {
          return restartFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsWithPendingRestart),
        });
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('restart-button'));
      });

      await waitFor(() => {
        expect(restartFetch).toHaveBeenCalled();
      });
    });

    it('calls onRestart callback after successful restart', async () => {
      const restartFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server restarting' },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options) => {
        if (options?.method === 'POST' && url.includes('/restart')) {
          return restartFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsWithPendingRestart),
        });
      });

      const onRestart = vi.fn();
      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner onRestart={onRestart} />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('restart-button'));
      });

      await waitFor(() => {
        expect(onRestart).toHaveBeenCalled();
      });
    });

    it('shows loading state during restart', async () => {
      let resolveRestart: () => void;
      const restartPromise = new Promise<void>((resolve) => {
        resolveRestart = resolve;
      });

      const restartFetch = vi.fn().mockImplementation(async () => {
        await restartPromise;
        return {
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: { message: 'Server restarting' },
            }),
        };
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options) => {
        if (options?.method === 'POST' && url.includes('/restart')) {
          return restartFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsWithPendingRestart),
        });
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('restart-button'));
      });

      // Should show loading state
      await waitFor(() => {
        expect(screen.getByText('Restarting...')).toBeInTheDocument();
        expect(screen.getByTestId('restart-button')).toBeDisabled();
      });

      // Resolve the restart
      await act(async () => {
        resolveRestart!();
      });

      // Should go back to normal state
      await waitFor(() => {
        expect(screen.getByText('Restart Now')).toBeInTheDocument();
      });
    });
  });

  describe('styling', () => {
    it('uses primary color for styling', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const banner = screen.getByTestId('pending-restart-banner');
        // Uses semantic primary class for theme-aware colors
        expect(banner).toHaveClass('bg-primary/20');
      });
    });

    it('applies correct text styling', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const banner = screen.getByTestId('pending-restart-banner');
        const text = screen.getByText('Restart required');
        expect(text).toHaveClass('text-primary');
        expect(banner).toHaveClass('text-sm');
      });
    });
  });

  describe('accessibility', () => {
    it('has proper aria-hidden on icon', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const icon = screen.getByTestId('restart-icon');
        expect(icon).toHaveAttribute('aria-hidden', 'true');
      });
    });

    it('button is keyboard accessible', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const button = screen.getByTestId('restart-button');
        expect(button).toHaveProperty('tagName', 'BUTTON');
        expect(button).not.toHaveAttribute('tabIndex', '-1');
      });
    });
  });

  describe('button states', () => {
    it('button is enabled when not restarting', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const button = screen.getByTestId('restart-button');
        expect(button).not.toBeDisabled();
      });
    });

    it('button shows spinner icon during restart', async () => {
      let resolveRestart: () => void;
      const restartPromise = new Promise<void>((resolve) => {
        resolveRestart = resolve;
      });

      const restartFetch = vi.fn().mockImplementation(async () => {
        await restartPromise;
        return {
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: { message: 'Server restarting' },
            }),
        };
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options) => {
        if (options?.method === 'POST' && url.includes('/restart')) {
          return restartFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsWithPendingRestart),
        });
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('restart-button'));
      });

      // Should show spinner during loading
      await waitFor(() => {
        const button = screen.getByTestId('restart-button');
        const spinner = button.querySelector('.animate-spin');
        expect(spinner).toBeInTheDocument();
      });

      // Resolve the restart
      await act(async () => {
        resolveRestart!();
      });
    });
  });

  describe('error handling', () => {
    it('does not crash when mods query fails', async () => {
      globalThis.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      // Should not render banner on error
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(screen.queryByTestId('pending-restart-banner')).not.toBeInTheDocument();
    });

    it('does not call onRestart callback when restart fails', async () => {
      const restartFetch = vi.fn().mockRejectedValue(new Error('Restart failed'));

      globalThis.fetch = vi.fn().mockImplementation((url: string, options) => {
        if (options?.method === 'POST' && url.includes('/restart')) {
          return restartFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsWithPendingRestart),
        });
      });

      const onRestart = vi.fn();
      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner onRestart={onRestart} />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('restart-button'));
      });

      // Wait for the mutation to settle
      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      expect(onRestart).not.toHaveBeenCalled();
    });

    it('handles malformed API response gracefully', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data: {} }), // Missing mods and pendingRestart
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await act(async () => {
        await new Promise((resolve) => setTimeout(resolve, 100));
      });

      // Should not render banner with malformed response
      expect(screen.queryByTestId('pending-restart-banner')).not.toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles missing onRestart callback', async () => {
      const restartFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server restarting' },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options) => {
        if (options?.method === 'POST' && url.includes('/restart')) {
          return restartFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsWithPendingRestart),
        });
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
      });

      // Should not crash when clicking without onRestart callback
      await act(async () => {
        fireEvent.click(screen.getByTestId('restart-button'));
      });

      await waitFor(() => {
        expect(restartFetch).toHaveBeenCalled();
      });
    });

    it('button becomes disabled after first click to prevent rapid clicks', async () => {
      let resolveRestart: () => void;
      const restartPromise = new Promise<void>((resolve) => {
        resolveRestart = resolve;
      });

      const restartFetch = vi.fn().mockImplementation(async () => {
        await restartPromise;
        return {
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: { message: 'Server restarting' },
            }),
        };
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string, options) => {
        if (options?.method === 'POST' && url.includes('/restart')) {
          return restartFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsWithPendingRestart),
        });
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('restart-button')).toBeInTheDocument();
      });

      const button = screen.getByTestId('restart-button');

      // Click the button
      await act(async () => {
        fireEvent.click(button);
      });

      // Button should be disabled after click
      await waitFor(() => {
        expect(button).toBeDisabled();
      });

      // Resolve the restart
      await act(async () => {
        resolveRestart!();
      });

      // Button should be enabled again after restart completes
      await waitFor(() => {
        expect(button).not.toBeDisabled();
      });
    });

    it('transitions from visible to hidden when pendingRestart changes to false', async () => {
      let modsData = mockModsWithPendingRestart;

      globalThis.fetch = vi.fn().mockImplementation(() => {
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(modsData),
        });
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('pending-restart-banner')).toBeInTheDocument();
      });

      // Change the data to no pending restart
      modsData = mockModsNoPendingRestart;

      // Invalidate query to trigger refetch
      await act(async () => {
        await queryClient.invalidateQueries({ queryKey: ['mods'] });
      });

      await waitFor(() => {
        expect(screen.queryByTestId('pending-restart-banner')).not.toBeInTheDocument();
      });
    });
  });

  describe('layout', () => {
    it('arranges elements in a horizontal flex layout', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const banner = screen.getByTestId('pending-restart-banner');
        expect(banner).toHaveClass('flex');
        expect(banner).toHaveClass('items-center');
        expect(banner).toHaveClass('gap-2');
      });
    });

    it('applies correct spacing and padding', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const banner = screen.getByTestId('pending-restart-banner');
        expect(banner).toHaveClass('px-3');
        expect(banner).toHaveClass('py-1.5');
        expect(banner).toHaveClass('rounded-md');
      });
    });
  });
});
