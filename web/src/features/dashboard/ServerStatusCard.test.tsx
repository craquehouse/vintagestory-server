import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { ServerStatusCard } from './ServerStatusCard';
import type { ServerState } from '@/api/types';

// Mock child components
vi.mock('@/components/ServerStatusBadge', () => ({
  ServerStatusBadge: ({ state }: { state: ServerState }) => (
    <div data-testid="server-status-badge" data-state={state}>
      Badge: {state}
    </div>
  ),
}));

vi.mock('./ServerControls', () => ({
  ServerControls: ({ serverState }: { serverState: ServerState }) => (
    <div data-testid="server-controls" data-state={serverState}>
      Controls: {serverState}
    </div>
  ),
}));

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

describe('ServerStatusCard', () => {
  describe('loading state', () => {
    it('renders loading state when isLoading is true', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" isLoading={true} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByTestId('server-status-card')).toBeInTheDocument();
      expect(screen.getByText('Server Status')).toBeInTheDocument();
      expect(screen.getByText('Loading...')).toBeInTheDocument();

      // Should not render badge or controls in loading state
      expect(screen.queryByTestId('server-status-badge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('server-controls')).not.toBeInTheDocument();
    });

    it('has Server icon in loading state', () => {
      const queryClient = createTestQueryClient();
      const { container } = render(
        <ServerStatusCard state="running" isLoading={true} />,
        { wrapper: createWrapper(queryClient) }
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveClass('text-muted-foreground');
    });
  });

  describe('rendering with different server states', () => {
    const serverStates: ServerState[] = [
      'not_installed',
      'installing',
      'installed',
      'starting',
      'running',
      'stopping',
      'error',
    ];

    it.each(serverStates)(
      'renders with server state: %s',
      (state) => {
        const queryClient = createTestQueryClient();
        render(
          <ServerStatusCard state={state} version="1.19.8" />,
          { wrapper: createWrapper(queryClient) }
        );

        expect(screen.getByTestId('server-status-card')).toBeInTheDocument();
        expect(screen.getByText('Server Status')).toBeInTheDocument();

        // Should render badge with correct state
        const badge = screen.getByTestId('server-status-badge');
        expect(badge).toBeInTheDocument();
        expect(badge).toHaveAttribute('data-state', state);

        // Should render controls with correct state
        const controls = screen.getByTestId('server-controls');
        expect(controls).toBeInTheDocument();
        expect(controls).toHaveAttribute('data-state', state);
      }
    );
  });

  describe('version display', () => {
    it('displays version when provided', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" version="1.19.8" />,
        { wrapper: createWrapper(queryClient) }
      );

      const versionElement = screen.getByTestId('server-status-card-version');
      expect(versionElement).toBeInTheDocument();
      expect(versionElement).toHaveTextContent('Version 1.19.8');
    });

    it('does not display version when null', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" version={null} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('server-status-card-version')).not.toBeInTheDocument();
    });

    it('does not display version when undefined', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" version={undefined} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('server-status-card-version')).not.toBeInTheDocument();
    });

    it('displays version with different formats', () => {
      const versions = ['1.19.8', '1.20.0-rc.1', '2.0.0-alpha'];

      versions.forEach((version) => {
        const queryClient = createTestQueryClient();
        const { unmount } = render(
          <ServerStatusCard state="running" version={version} />,
          { wrapper: createWrapper(queryClient) }
        );

        expect(screen.getByTestId('server-status-card-version')).toHaveTextContent(
          `Version ${version}`
        );

        unmount();
      });
    });
  });

  describe('integration with ServerStatusBadge', () => {
    it('passes correct state to ServerStatusBadge', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" version="1.19.8" />,
        { wrapper: createWrapper(queryClient) }
      );

      const badge = screen.getByTestId('server-status-badge');
      expect(badge).toHaveAttribute('data-state', 'running');
    });

    it('does not render ServerStatusBadge in loading state', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" isLoading={true} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('server-status-badge')).not.toBeInTheDocument();
    });
  });

  describe('integration with ServerControls', () => {
    it('passes correct state to ServerControls', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="installed" version="1.19.8" />,
        { wrapper: createWrapper(queryClient) }
      );

      const controls = screen.getByTestId('server-controls');
      expect(controls).toHaveAttribute('data-state', 'installed');
    });

    it('does not render ServerControls in loading state', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" isLoading={true} />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.queryByTestId('server-controls')).not.toBeInTheDocument();
    });

    it('renders ServerControls in dedicated container', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" version="1.19.8" />,
        { wrapper: createWrapper(queryClient) }
      );

      const controlsContainer = screen.getByTestId('server-status-card-controls');
      expect(controlsContainer).toBeInTheDocument();
      expect(controlsContainer.querySelector('[data-testid="server-controls"]')).toBeInTheDocument();
    });
  });

  describe('component structure', () => {
    it('has consistent card structure with header and content', () => {
      const queryClient = createTestQueryClient();
      const { container } = render(
        <ServerStatusCard state="running" version="1.19.8" />,
        { wrapper: createWrapper(queryClient) }
      );

      // Check for Card component structure
      expect(screen.getByTestId('server-status-card')).toBeInTheDocument();
      expect(screen.getByTestId('server-status-card')).toHaveClass('min-h-[140px]');

      // Check for header with icon and title
      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
      expect(screen.getByText('Server Status')).toBeInTheDocument();
    });

    it('maintains minimum height in all states', () => {
      const queryClient = createTestQueryClient();

      // Test loading state
      const { unmount: unmount1 } = render(
        <ServerStatusCard state="running" isLoading={true} />,
        { wrapper: createWrapper(queryClient) }
      );
      expect(screen.getByTestId('server-status-card')).toHaveClass('min-h-[140px]');
      unmount1();

      // Test normal state
      const { unmount: unmount2 } = render(
        <ServerStatusCard state="running" version="1.19.8" />,
        { wrapper: createWrapper(queryClient) }
      );
      expect(screen.getByTestId('server-status-card')).toHaveClass('min-h-[140px]');
      unmount2();
    });
  });

  describe('memoization', () => {
    it('is a memoized component', () => {
      // The component is wrapped in memo() - check that it has the memo wrapper
      // memo() components have a $$typeof property of Symbol.for('react.memo')
      expect(ServerStatusCard.$$typeof?.toString()).toBe('Symbol(react.memo)');
    });
  });

  describe('edge cases', () => {
    it('handles all props together', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard
          state="running"
          version="1.19.8"
          isLoading={false}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      expect(screen.getByTestId('server-status-card')).toBeInTheDocument();
      expect(screen.getByTestId('server-status-badge')).toBeInTheDocument();
      expect(screen.getByTestId('server-controls')).toBeInTheDocument();
      expect(screen.getByTestId('server-status-card-version')).toHaveTextContent('Version 1.19.8');
    });

    it('prioritizes isLoading over state', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard
          state="running"
          version="1.19.8"
          isLoading={true}
        />,
        { wrapper: createWrapper(queryClient) }
      );

      // Should show loading state, not running state
      expect(screen.getByText('Loading...')).toBeInTheDocument();
      expect(screen.queryByTestId('server-status-badge')).not.toBeInTheDocument();
      expect(screen.queryByTestId('server-controls')).not.toBeInTheDocument();
    });

    it('handles empty string version', () => {
      const queryClient = createTestQueryClient();
      render(
        <ServerStatusCard state="running" version="" />,
        { wrapper: createWrapper(queryClient) }
      );

      // Empty string is falsy, should not render version
      expect(screen.queryByTestId('server-status-card-version')).not.toBeInTheDocument();
    });
  });
});
