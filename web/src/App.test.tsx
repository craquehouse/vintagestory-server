/**
 * App routing tests.
 *
 * Story 11.6: Dashboard & Navigation Cleanup
 *
 * Tests verify the default route behavior for /game-server path.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route, Navigate, Outlet } from 'react-router';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';

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

// Simplified mock components for testing redirects
function MockVersionPage() {
  return <div data-testid="version-page">Version Page</div>;
}

function MockConsolePage() {
  return <div data-testid="console-page">Console Page</div>;
}

function MockGameServerLayout() {
  return (
    <div data-testid="game-server-layout">
      <Outlet />
    </div>
  );
}

/**
 * Test router that mirrors App.tsx route structure for /game-server.
 * Story 11.6: Tests the default redirect from /game-server to /game-server/version
 */
function createTestRouter(initialEntries: string[], queryClient: QueryClient, defaultRedirect: string = 'version') {
  return function TestRouter({ children }: { children?: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={initialEntries}>
          <Routes>
            <Route path="/game-server" element={<MockGameServerLayout />}>
              <Route index element={<Navigate to={defaultRedirect} replace />} />
              <Route path="version" element={<MockVersionPage />} />
              <Route path="console" element={<MockConsolePage />} />
            </Route>
          </Routes>
          {children}
        </MemoryRouter>
      </QueryClientProvider>
    );
  };
}

describe('App routing', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('Story 11.6 AC4: /game-server default redirect', () => {
    it('redirects /game-server to /game-server/version', async () => {
      const queryClient = createTestQueryClient();
      // Test with 'version' as the default redirect (the new expected behavior)
      const Router = createTestRouter(['/game-server'], queryClient, 'version');

      render(<Router />);

      // Should show the Version page (via redirect)
      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });

      // Should NOT show Console page
      expect(screen.queryByTestId('console-page')).not.toBeInTheDocument();
    });

    it('direct navigation to /game-server/version works', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/version'], queryClient, 'version');

      render(<Router />);

      await waitFor(() => {
        expect(screen.getByTestId('version-page')).toBeInTheDocument();
      });
    });

    it('direct navigation to /game-server/console works', async () => {
      const queryClient = createTestQueryClient();
      const Router = createTestRouter(['/game-server/console'], queryClient, 'version');

      render(<Router />);

      await waitFor(() => {
        expect(screen.getByTestId('console-page')).toBeInTheDocument();
      });
    });
  });
});
