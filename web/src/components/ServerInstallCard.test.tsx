import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { ServerInstallCard } from './ServerInstallCard';
import type { InstallStatus } from '@/api/types';

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

describe('ServerInstallCard', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('empty state (AC: 1)', () => {
    it('renders version input field when not installing', () => {
      const queryClient = createTestQueryClient();
      render(<ServerInstallCard isInstalling={false} />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByRole('textbox', { name: /server version/i })).toBeInTheDocument();
    });

    it('renders Install Server button when not installing', () => {
      const queryClient = createTestQueryClient();
      render(<ServerInstallCard isInstalling={false} />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByRole('button', { name: /install server/i })).toBeInTheDocument();
    });

    it('shows correct title and description in empty state', () => {
      const queryClient = createTestQueryClient();
      render(<ServerInstallCard isInstalling={false} />, {
        wrapper: createWrapper(queryClient),
      });

      expect(screen.getByText('Install Server')).toBeInTheDocument();
      expect(screen.getByText(/enter the vintagestory version to install/i)).toBeInTheDocument();
    });

    it('disables install button when version is empty', () => {
      const queryClient = createTestQueryClient();
      render(<ServerInstallCard isInstalling={false} />, {
        wrapper: createWrapper(queryClient),
      });

      const installButton = screen.getByRole('button', { name: /install server/i });
      expect(installButton).toBeDisabled();
    });

    it('enables install button when version is entered', async () => {
      const user = userEvent.setup();
      const queryClient = createTestQueryClient();
      render(<ServerInstallCard isInstalling={false} />, {
        wrapper: createWrapper(queryClient),
      });

      await user.type(screen.getByRole('textbox', { name: /server version/i }), '1.21.3');

      const installButton = screen.getByRole('button', { name: /install server/i });
      expect(installButton).not.toBeDisabled();
    });
  });

  describe('installing state (AC: 2)', () => {
    const mockInstallStatus: InstallStatus = {
      state: 'downloading',
      progress: 45,
      message: 'Downloading VintageStory 1.21.3...',
    };

    it('shows progress indicator during installation', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerInstallCard isInstalling={true} installStatus={mockInstallStatus} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByRole('status', { name: /installation progress/i })).toBeInTheDocument();
    });

    it('displays current progress percentage', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerInstallCard isInstalling={true} installStatus={mockInstallStatus} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByText('45%')).toBeInTheDocument();
    });

    it('displays current stage', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerInstallCard isInstalling={true} installStatus={mockInstallStatus} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByText('downloading')).toBeInTheDocument();
    });

    it('displays progress message', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerInstallCard isInstalling={true} installStatus={mockInstallStatus} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByText('Downloading VintageStory 1.21.3...')).toBeInTheDocument();
    });

    it('hides version input and install button during installation', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerInstallCard isInstalling={true} installStatus={mockInstallStatus} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByRole('textbox', { name: /server version/i })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: /install server/i })).not.toBeInTheDocument();
    });

    it('shows different stages correctly', () => {
      const stages: Array<{ state: InstallStatus['state']; display: string }> = [
        { state: 'downloading', display: 'downloading' },
        { state: 'extracting', display: 'extracting' },
        { state: 'configuring', display: 'configuring' },
        { state: 'complete', display: 'complete' },
      ];

      stages.forEach(({ state, display }) => {
        const queryClient = createTestQueryClient();
        const status: InstallStatus = {
          state,
          progress: 50,
          message: 'Test message',
        };

        const { unmount } = render(
          <ServerInstallCard isInstalling={true} installStatus={status} />,
          { wrapper: createWrapper(queryClient) }
        );

        expect(screen.getByText(display)).toBeInTheDocument();
        unmount();
      });
    });
  });

  describe('install action', () => {
    it('calls install endpoint when button is clicked', async () => {
      const user = userEvent.setup();
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { message: 'Installation started' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ServerInstallCard isInstalling={false} />, {
        wrapper: createWrapper(queryClient),
      });

      await user.type(screen.getByRole('textbox', { name: /server version/i }), '1.21.3');
      await user.click(screen.getByRole('button', { name: /install server/i }));

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledWith(
          'http://localhost:8080/api/v1alpha1/server/install',
          expect.objectContaining({
            method: 'POST',
            body: JSON.stringify({ version: '1.21.3' }),
          })
        );
      });
    });

    it('shows loading state on button during mutation', async () => {
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
      render(<ServerInstallCard isInstalling={false} />, {
        wrapper: createWrapper(queryClient),
      });

      await user.type(screen.getByRole('textbox', { name: /server version/i }), '1.21.3');
      await user.click(screen.getByRole('button', { name: /install server/i }));

      await waitFor(() => {
        expect(screen.getByText(/installing/i)).toBeInTheDocument();
      });

      // Cleanup
      resolvePromise!();
    });
  });
});
