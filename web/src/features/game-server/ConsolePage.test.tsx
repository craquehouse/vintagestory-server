/**
 * Tests for ConsolePage component.
 *
 * Story 11.5: Console Page Extraction
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route } from 'react-router';
import { ConsolePage } from './ConsolePage';
import * as serverStatusHook from '@/hooks/use-server-status';

// Type-safe mock return value helper
function mockServerStatus(state: string, version: string | null = '1.21.3') {
  return {
    data: { data: { state, version } },
    isLoading: false,
    error: null,
    isError: false,
    isPending: false,
    isSuccess: true,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof serverStatusHook.useServerStatus>;
}

// Mock mutation hook return value
const createMockMutation = (isPending = false) => ({
  mutate: vi.fn(),
  isPending,
  isError: false,
  isSuccess: false,
  reset: vi.fn(),
});

// Mock the server status hook
vi.mock('@/hooks/use-server-status', () => ({
  useServerStatus: vi.fn(),
  useStartServer: vi.fn(() => createMockMutation()),
  useStopServer: vi.fn(() => createMockMutation()),
  useRestartServer: vi.fn(() => createMockMutation()),
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
    // Reset mutation mocks to default state
    vi.mocked(serverStatusHook.useStartServer).mockReturnValue(createMockMutation() as unknown as ReturnType<typeof serverStatusHook.useStartServer>);
    vi.mocked(serverStatusHook.useStopServer).mockReturnValue(createMockMutation() as unknown as ReturnType<typeof serverStatusHook.useStopServer>);
    vi.mocked(serverStatusHook.useRestartServer).mockReturnValue(createMockMutation() as unknown as ReturnType<typeof serverStatusHook.useRestartServer>);
  });

  describe('page header', () => {
    it('renders page title "Server Console"', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      expect(screen.getByRole('heading', { name: /server console/i })).toBeInTheDocument();
    });

    it('renders ServerStatusBadge in header when server is installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      // ServerStatusBadge renders with role="status"
      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('Running')).toBeInTheDocument();
    });

    it('renders ServerStatusBadge showing "Stopped" when server is installed but stopped', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installed'));

      renderWithProviders(<ConsolePage />);

      expect(screen.getByRole('status')).toBeInTheDocument();
      expect(screen.getByText('Stopped')).toBeInTheDocument();
    });

    it('renders ServerControls in header when server is installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      // ServerControls renders Start, Stop, Restart buttons (exact match to avoid Start matching Restart)
      expect(screen.getByRole('button', { name: 'Start server' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Stop server' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Restart server' })).toBeInTheDocument();
    });

    it('does not render ServerControls when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('not_installed', null));

      renderWithProviders(<ConsolePage />);

      expect(screen.queryByRole('button', { name: 'Start server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Stop server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Restart server' })).not.toBeInTheDocument();
    });

    it('does not render ServerControls when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installing', null));

      renderWithProviders(<ConsolePage />);

      expect(screen.queryByRole('button', { name: 'Start server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Stop server' })).not.toBeInTheDocument();
      expect(screen.queryByRole('button', { name: 'Restart server' })).not.toBeInTheDocument();
    });
  });

  describe('ServerControls behavior', () => {
    it('renders ServerControls when server is in error state', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('error'));

      renderWithProviders(<ConsolePage />);

      // Error state is "installed" per isServerInstalled, so controls should render
      expect(screen.getByRole('button', { name: 'Start server' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Stop server' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Restart server' })).toBeInTheDocument();
    });

    it('renders ServerControls when server is starting (transitional state)', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('starting'));

      renderWithProviders(<ConsolePage />);

      // Starting is "installed" per isServerInstalled, controls render but are disabled
      expect(screen.getByRole('button', { name: 'Start server' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Start server' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Stop server' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Restart server' })).toBeDisabled();
    });

    it('renders ServerControls when server is stopping (transitional state)', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('stopping'));

      renderWithProviders(<ConsolePage />);

      // Stopping is "installed" per isServerInstalled, controls render but are disabled
      expect(screen.getByRole('button', { name: 'Start server' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: 'Start server' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Stop server' })).toBeDisabled();
      expect(screen.getByRole('button', { name: 'Restart server' })).toBeDisabled();
    });

    it('disables Start button when start mutation is pending', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installed'));
      vi.mocked(serverStatusHook.useStartServer).mockReturnValue(createMockMutation(true) as unknown as ReturnType<typeof serverStatusHook.useStartServer>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByRole('button', { name: 'Start server' })).toBeDisabled();
    });

    it('disables Stop button when stop mutation is pending', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));
      vi.mocked(serverStatusHook.useStopServer).mockReturnValue(createMockMutation(true) as unknown as ReturnType<typeof serverStatusHook.useStopServer>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByRole('button', { name: 'Stop server' })).toBeDisabled();
    });

    it('disables Restart button when restart mutation is pending', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));
      vi.mocked(serverStatusHook.useRestartServer).mockReturnValue(createMockMutation(true) as unknown as ReturnType<typeof serverStatusHook.useRestartServer>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByRole('button', { name: 'Restart server' })).toBeDisabled();
    });

    it('calls start mutation when Start button is clicked', async () => {
      const user = userEvent.setup();
      const mockMutate = vi.fn();
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installed'));
      vi.mocked(serverStatusHook.useStartServer).mockReturnValue({
        ...createMockMutation(),
        mutate: mockMutate,
      } as unknown as ReturnType<typeof serverStatusHook.useStartServer>);

      renderWithProviders(<ConsolePage />);

      await user.click(screen.getByRole('button', { name: 'Start server' }));

      expect(mockMutate).toHaveBeenCalledTimes(1);
    });

    it('calls stop mutation when Stop button is clicked', async () => {
      const user = userEvent.setup();
      const mockMutate = vi.fn();
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));
      vi.mocked(serverStatusHook.useStopServer).mockReturnValue({
        ...createMockMutation(),
        mutate: mockMutate,
      } as unknown as ReturnType<typeof serverStatusHook.useStopServer>);

      renderWithProviders(<ConsolePage />);

      await user.click(screen.getByRole('button', { name: 'Stop server' }));

      expect(mockMutate).toHaveBeenCalledTimes(1);
    });

    it('calls restart mutation when Restart button is clicked', async () => {
      const user = userEvent.setup();
      const mockMutate = vi.fn();
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));
      vi.mocked(serverStatusHook.useRestartServer).mockReturnValue({
        ...createMockMutation(),
        mutate: mockMutate,
      } as unknown as ReturnType<typeof serverStatusHook.useRestartServer>);

      renderWithProviders(<ConsolePage />);

      await user.click(screen.getByRole('button', { name: 'Restart server' }));

      expect(mockMutate).toHaveBeenCalledTimes(1);
    });

    it('supports keyboard navigation - buttons are focusable and activatable', async () => {
      const user = userEvent.setup();
      const mockMutate = vi.fn();
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installed'));
      vi.mocked(serverStatusHook.useStartServer).mockReturnValue({
        ...createMockMutation(),
        mutate: mockMutate,
      } as unknown as ReturnType<typeof serverStatusHook.useStartServer>);

      renderWithProviders(<ConsolePage />);

      // Tab to the Start button and press Enter
      await user.tab();
      await user.tab();
      await user.tab(); // Navigate through header elements to buttons
      await user.keyboard('{Enter}');

      // The mutation should be called via keyboard
      expect(mockMutate).toHaveBeenCalled();
    });
  });

  describe('loading state', () => {
    it('renders loading indicator when server status is loading', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        ...mockServerStatus('running'),
        data: undefined,
        isLoading: true,
      } as unknown as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-loading')).toBeInTheDocument();
      expect(screen.getByText(/loading/i)).toBeInTheDocument();
    });
  });

  describe('error state', () => {
    it('renders error message when server status fetch fails', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        ...mockServerStatus('running'),
        data: undefined,
        isLoading: false,
        error: new Error('Failed to connect'),
      } as unknown as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-error')).toBeInTheDocument();
      expect(screen.getByText(/failed to connect/i)).toBeInTheDocument();
    });
  });

  describe('installed state (AC: 1, 3)', () => {
    it('renders ConsolePanel when server is installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installed'));

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-panel')).toBeInTheDocument();
    });

    it('renders ConsolePanel when server is running', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-panel')).toBeInTheDocument();
    });

    it('has viewport-height flex column layout container', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      const page = screen.getByTestId('console-page');
      expect(page).toBeInTheDocument();
      // Uses viewport-relative height: calc(100vh - header - padding)
      expect(page).toHaveClass('h-[calc(100vh-80px)]');
      expect(page).toHaveClass('flex');
      expect(page).toHaveClass('flex-col');
    });

    it('ConsolePanel has flex-1 and min-h-0 for height allocation', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      const panel = screen.getByTestId('console-panel');
      expect(panel).toHaveClass('flex-1');
      expect(panel).toHaveClass('min-h-0');
    });
  });

  describe('not installed state (AC: 2)', () => {
    it('renders empty state when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('not_installed', null));

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/server not installed/i)).toBeInTheDocument();
    });

    it('shows link to Installation page when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('not_installed', null));

      renderWithProviders(<ConsolePage />);

      const installLink = screen.getByRole('link', { name: /installation/i });
      expect(installLink).toBeInTheDocument();
      expect(installLink).toHaveAttribute('href', '/game-server/version');
    });

    it('does not render ConsolePanel when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('not_installed', null));

      renderWithProviders(<ConsolePage />);

      expect(screen.queryByTestId('console-panel')).not.toBeInTheDocument();
    });
  });

  describe('installing state', () => {
    it('shows installation in progress message when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installing', null));

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/installation in progress/i)).toBeInTheDocument();
    });

    it('does not render ConsolePanel when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installing', null));

      renderWithProviders(<ConsolePage />);

      expect(screen.queryByTestId('console-panel')).not.toBeInTheDocument();
    });

    it('shows "View Installation Progress" link when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('installing', null));

      renderWithProviders(<ConsolePage />);

      const progressLink = screen.getByRole('link', { name: /view installation progress/i });
      expect(progressLink).toBeInTheDocument();
      expect(progressLink).toHaveAttribute('href', '/game-server/version');
    });
  });

  describe('data-testid attributes', () => {
    it('has console-page testid on main container', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      expect(screen.getByTestId('console-page')).toBeInTheDocument();
    });
  });

  describe('responsive layout', () => {
    it('applies responsive viewport height classes', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

      renderWithProviders(<ConsolePage />);

      const page = screen.getByTestId('console-page');
      // Mobile: calc(100vh - 80px), Desktop: calc(100vh - 96px)
      expect(page).toHaveClass('h-[calc(100vh-80px)]');
      expect(page).toHaveClass('md:h-[calc(100vh-96px)]');
    });
  });

  describe('route integration', () => {
    it('renders ConsolePage at /game-server/console route', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue(mockServerStatus('running'));

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
