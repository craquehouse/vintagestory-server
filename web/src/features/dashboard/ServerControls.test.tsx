import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { ServerControls } from './ServerControls';
import type { ServerState } from '@/api/types';

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

// Wrapper component for rendering with providers
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

describe('ServerControls', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8000';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('button states when server is stopped (AC: 3)', () => {
    it('enables Start button when server is installed (stopped)', () => {
      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="installed" />, {
        wrapper: createWrapper(queryClient),
      });

      const startButton = screen.getByRole('button', { name: 'Start server' });
      expect(startButton).not.toBeDisabled();
    });

    it('disables Stop button when server is stopped', () => {
      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="installed" />, {
        wrapper: createWrapper(queryClient),
      });

      const stopButton = screen.getByRole('button', { name: 'Stop server' });
      expect(stopButton).toBeDisabled();
    });

    it('disables Restart button when server is stopped', () => {
      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="installed" />, {
        wrapper: createWrapper(queryClient),
      });

      const restartButton = screen.getByRole('button', { name: 'Restart server' });
      expect(restartButton).toBeDisabled();
    });
  });

  describe('button states when server is running (AC: 4)', () => {
    it('disables Start button when server is running', () => {
      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="running" />, {
        wrapper: createWrapper(queryClient),
      });

      const startButton = screen.getByRole('button', { name: 'Start server' });
      expect(startButton).toBeDisabled();
    });

    it('enables Stop button when server is running', () => {
      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="running" />, {
        wrapper: createWrapper(queryClient),
      });

      const stopButton = screen.getByRole('button', { name: 'Stop server' });
      expect(stopButton).not.toBeDisabled();
    });

    it('enables Restart button when server is running', () => {
      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="running" />, {
        wrapper: createWrapper(queryClient),
      });

      const restartButton = screen.getByRole('button', { name: 'Restart server' });
      expect(restartButton).not.toBeDisabled();
    });
  });

  describe('transitional states', () => {
    const transitionalStates: ServerState[] = ['starting', 'stopping', 'installing'];

    it.each(transitionalStates)(
      'disables all buttons when server is %s',
      (state) => {
        const queryClient = createTestQueryClient();
        render(<ServerControls serverState={state} />, {
          wrapper: createWrapper(queryClient),
        });

        expect(screen.getByRole('button', { name: 'Start server' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Stop server' })).toBeDisabled();
        expect(screen.getByRole('button', { name: 'Restart server' })).toBeDisabled();
      }
    );
  });

  describe('mutation calls (AC: 5)', () => {
    it('calls start mutation when Start button is clicked', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server starting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="installed" />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByRole('button', { name: 'Start server' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1alpha1/server/start',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('calls stop mutation when Stop button is clicked', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server stopping' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="running" />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByRole('button', { name: 'Stop server' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1alpha1/server/stop',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });

    it('calls restart mutation when Restart button is clicked', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Server restarting' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="running" />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByRole('button', { name: 'Restart server' }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8000/api/v1alpha1/server/restart',
          expect.objectContaining({ method: 'POST' })
        );
      });
    });
  });

  describe('loading states (AC: 5)', () => {
    it('shows loading spinner on Start button during mutation', async () => {
      const user = userEvent.setup();
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      const mockFetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve({ status: 'ok', data: { message: 'Started' } }),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="installed" />, {
        wrapper: createWrapper(queryClient),
      });

      await user.click(screen.getByRole('button', { name: 'Start server' }));

      // Should show loading spinner (button should have animate-spin class on its svg)
      await waitFor(() => {
        const button = screen.getByRole('button', { name: 'Start server' });
        const spinner = button.querySelector('.animate-spin');
        expect(spinner).toBeInTheDocument();
      });

      // Cleanup
      resolvePromise!();
    });
  });

  describe('error state', () => {
    it('disables all buttons when server is in error state', () => {
      const queryClient = createTestQueryClient();
      render(<ServerControls serverState="error" />, {
        wrapper: createWrapper(queryClient),
      });

      // In error state, Start should be disabled (not installed/stopped)
      // Stop and Restart should also be disabled (not running)
      expect(screen.getByRole('button', { name: 'Start server' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Stop server' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Restart server' })).toBeDisabled();
    });
  });
});
