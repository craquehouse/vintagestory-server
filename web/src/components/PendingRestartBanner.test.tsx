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
    it('uses Catppuccin mauve color for styling', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsWithPendingRestart),
      });

      const queryClient = createTestQueryClient();
      render(<PendingRestartBanner />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const banner = screen.getByTestId('pending-restart-banner');
        // Check for Catppuccin mauve background color
        expect(banner).toHaveClass('bg-[#cba6f7]/20');
      });
    });
  });
});
