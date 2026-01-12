/**
 * Tests for ConsolePage component.
 *
 * Story 11.5: Console Page Extraction
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router';
import { ConsolePage } from './ConsolePage';
import * as serverStatusHook from '@/hooks/use-server-status';

// Mock the server status hook
vi.mock('@/hooks/use-server-status', () => ({
  useServerStatus: vi.fn(),
}));

// Mock ConsolePanel to isolate ConsolePage tests
vi.mock('@/components/ConsolePanel', () => ({
  ConsolePanel: ({ className }: { className?: string }) => (
    <div data-testid="console-panel" className={className}>ConsolePanel Mock</div>
  ),
}));

// Helper to create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

// Wrapper component with providers
function renderWithProviders(ui: React.ReactElement) {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>{ui}</MemoryRouter>
    </QueryClientProvider>
  );
}

describe('ConsolePage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('page header', () => {
    it('renders page title "Server Console"', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByRole('heading', { name: /server console/i })).toBeInTheDocument();
    });

    it('renders ServerStatusBadge in header when server is installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      // ServerStatusBadge renders with role="status"
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('Running')).toBeInTheDocument();
    });

    it('renders ServerStatusBadge showing "Stopped" when server is installed but stopped', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installed', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('Stopped')).toBeInTheDocument();
    });
  });

  describe('loading state', () => {
    it('renders loading indicator when server status is loading', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: undefined,
        isLoading: true,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('renders error message when server status fetch fails', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: undefined,
        isLoading: false,
        error: new Error('Failed to connect'),
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-error')).toBeInTheDocument();
      expect(screen.getByText(/failed to connect/i)).toBeInTheDocument();
    });
  });

  describe('installed state (AC: 1, 3)', () => {
    it('renders ConsolePanel when server is installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installed', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-panel')).toBeInTheDocument();
    });

    it('renders ConsolePanel when server is running', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-panel')).toBeInTheDocument();
    });

    it('has full-height flex column layout container', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      const page = screen.getByTestId('console-page');
      expect(page).toBeInTheDocument();
      expect(page).toHaveClass('h-full');
      expect(page).toHaveClass('flex');
      expect(page).toHaveClass('flex-col');
    });

    it('ConsolePanel has flex-1 and min-h-0 for height allocation', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      const panel = screen.getByTestId('console-panel');
      expect(panel).toHaveClass('flex-1');
      expect(panel).toHaveClass('min-h-0');
    });
  });

  describe('not installed state (AC: 2)', () => {
    it('renders empty state when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/server not installed/i)).toBeInTheDocument();
    });

    it('shows link to Installation page when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      const installLink = screen.getByRole('link', { name: /installation/i });
      expect(installLink).toBeInTheDocument();
      expect(installLink).toHaveAttribute('href', '/game-server/version');
    });

    it('does not render ConsolePanel when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.queryByTestId('console-panel')).not.toBeInTheDocument();
    });
  });

  describe('installing state', () => {
    it('shows installation in progress message when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installing', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/installation in progress/i)).toBeInTheDocument();
    });

    it('does not render ConsolePanel when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installing', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.queryByTestId('console-panel')).not.toBeInTheDocument();
    });

    it('shows "View Installation Progress" link when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installing', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      const progressLink = screen.getByRole('link', { name: /view installation progress/i });
      expect(progressLink).toBeInTheDocument();
      expect(progressLink).toHaveAttribute('href', '/game-server/version');
    });
  });

  describe('data-testid attributes', () => {
    it('has console-page testid on main container', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page')).toBeInTheDocument();
    });
  });

  describe('responsive layout', () => {
    it('applies responsive padding classes (p-4 and lg:p-6)', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      const page = screen.getByTestId('console-page');
      expect(page).toHaveClass('p-4');
      expect(page).toHaveClass('lg:p-6');
    });
  });

  describe('route integration', () => {
    it('renders ConsolePage at /game-server/console route', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      const queryClient = createTestQueryClient();
      render(
        <QueryClientProvider client={queryClient}>
          <MemoryRouter initialEntries={['/game-server/console']}>
            <Routes>
              <Route path="/game-server/console" element={<ConsolePage />} />
            </Routes>
          </MemoryRouter>
        </QueryClientProvider>
      );

      expect(screen.getByTestId('console-page')).toBeInTheDocument();
      expect(screen.getByRole('heading', { name: /server console/i })).toBeInTheDocument();
    });
  });
});
