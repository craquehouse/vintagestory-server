/**
 * Tests for SettingsPage component.
 *
 * Story 11.3: Settings Page Extraction
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter } from 'react-router';
import { SettingsPage } from './SettingsPage';
import * as serverStatusHook from '@/hooks/use-server-status';

// Mock the server status hook
vi.mock('@/hooks/use-server-status', () => ({
  useServerStatus: vi.fn(),
}));

// Mock GameConfigPanel to isolate SettingsPage tests
vi.mock('./GameConfigPanel', () => ({
  GameConfigPanel: () => (
    <div data-testid="game-config-panel">GameConfigPanel Mock</div>
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

describe('SettingsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('page header', () => {
    it('renders page title "Game Settings"', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.getByRole('heading', { name: /game settings/i })).toBeInTheDocument();
    });

    it('renders ServerStatusBadge in header when server is installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

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

      renderWithProviders(<SettingsPage />);

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

      renderWithProviders(<SettingsPage />);

      expect(screen.getByTestId('settings-page-loading')).toBeInTheDocument();
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

      renderWithProviders(<SettingsPage />);

      expect(screen.getByTestId('settings-page-error')).toBeInTheDocument();
      expect(screen.getByText(/failed to connect/i)).toBeInTheDocument();
    });
  });

  describe('installed state (AC: 1, 4)', () => {
    it('renders GameConfigPanel when server is installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installed', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
    });

    it('renders GameConfigPanel when server is running', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.getByTestId('game-config-panel')).toBeInTheDocument();
    });

    it('has full-width layout container', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      const page = screen.getByTestId('settings-page');
      expect(page).toBeInTheDocument();
      // Verify it has the expected layout classes
      expect(page).toHaveClass('h-full');
    });
  });

  describe('not installed state (AC: 2)', () => {
    it('renders empty state when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.getByTestId('settings-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/server not installed/i)).toBeInTheDocument();
    });

    it('shows link to Installation page when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      const installLink = screen.getByRole('link', { name: /installation/i });
      expect(installLink).toBeInTheDocument();
      expect(installLink).toHaveAttribute('href', '/game-server/version');
    });

    it('does not render GameConfigPanel when server is not installed', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'not_installed', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.queryByTestId('game-config-panel')).not.toBeInTheDocument();
    });
  });

  describe('installing state', () => {
    it('shows installation in progress message when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installing', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.getByTestId('settings-page-empty')).toBeInTheDocument();
      expect(screen.getByText(/installation in progress/i)).toBeInTheDocument();
    });

    it('does not render GameConfigPanel when server is installing', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'installing', version: null } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.queryByTestId('game-config-panel')).not.toBeInTheDocument();
    });
  });

  describe('data-testid attributes', () => {
    it('has settings-page testid on main container', () => {
      vi.mocked(serverStatusHook.useServerStatus).mockReturnValue({
        data: { data: { state: 'running', version: '1.21.3' } },
        isLoading: false,
        error: null,
      } as ReturnType<typeof serverStatusHook.useServerStatus>);

      renderWithProviders(<SettingsPage />);

      expect(screen.getByTestId('settings-page')).toBeInTheDocument();
    });
  });
});
