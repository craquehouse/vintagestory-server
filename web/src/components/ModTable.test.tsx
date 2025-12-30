import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { ModTable } from './ModTable';

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

// Mock mods list response
const mockModsResponse = {
  status: 'ok',
  data: {
    mods: [
      {
        filename: 'smithingplus-1.5.0.zip',
        slug: 'smithingplus',
        version: '1.5.0',
        enabled: true,
        installedAt: '2024-01-15T10:30:00Z',
        name: 'Smithing Plus',
        authors: ['TestAuthor'],
        description: 'Enhanced smithing features',
      },
      {
        filename: 'carrycapacity-2.0.0.zip',
        slug: 'carrycapacity',
        version: '2.0.0',
        enabled: false,
        installedAt: '2024-01-14T08:00:00Z',
        name: 'Carry Capacity',
        authors: ['AnotherAuthor'],
        description: 'Increase carry capacity',
      },
    ],
    pendingRestart: false,
  },
};

const mockEmptyModsResponse = {
  status: 'ok',
  data: {
    mods: [],
    pendingRestart: false,
  },
};

describe('ModTable', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('loading state', () => {
    it('shows loading spinner while fetching mods', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      globalThis.fetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve(mockModsResponse),
        };
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      expect(screen.getByTestId('mod-table-loading')).toBeInTheDocument();

      // Resolve the fetch
      await act(async () => {
        resolvePromise!();
      });

      await waitFor(() => {
        expect(screen.queryByTestId('mod-table-loading')).not.toBeInTheDocument();
      });
    });
  });

  describe('empty state (AC: 4.4)', () => {
    it('shows empty state when no mods installed', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockEmptyModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-table-empty')).toBeInTheDocument();
        expect(screen.getByText('No mods installed yet')).toBeInTheDocument();
      });
    });
  });

  describe('table rendering (AC: 6)', () => {
    it('renders table with mod rows', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-table')).toBeInTheDocument();
      });

      // Check table headers
      expect(screen.getByText('Name')).toBeInTheDocument();
      expect(screen.getByText('Version')).toBeInTheDocument();
      expect(screen.getByText('Compatibility')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
      expect(screen.getByText('Actions')).toBeInTheDocument();
    });

    it('displays mod name and slug', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('Smithing Plus')).toBeInTheDocument();
        expect(screen.getByText('smithingplus')).toBeInTheDocument();
      });
    });

    it('displays mod version', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByText('v1.5.0')).toBeInTheDocument();
        expect(screen.getByText('v2.0.0')).toBeInTheDocument();
      });
    });

    it('displays compatibility badge for each mod', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        const badges = screen.getAllByTestId('compatibility-badge');
        expect(badges.length).toBe(2);
      });
    });

    it('displays enable/disable toggle for each mod', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-toggle-smithingplus')).toBeInTheDocument();
        expect(screen.getByTestId('mod-toggle-carrycapacity')).toBeInTheDocument();
      });
    });

    it('displays remove button for each mod', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-remove-smithingplus')).toBeInTheDocument();
        expect(screen.getByTestId('mod-remove-carrycapacity')).toBeInTheDocument();
      });
    });
  });

  describe('enable/disable toggle (AC: 7)', () => {
    it('toggles enabled state when switch is clicked', async () => {
      const disableFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              enabled: false,
              pendingRestart: true,
            },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/disable')) {
          return disableFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsResponse),
        });
      });

      const onToggled = vi.fn();
      const queryClient = createTestQueryClient();
      render(<ModTable onToggled={onToggled} />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-toggle-smithingplus')).toBeInTheDocument();
      });

      // Click toggle to disable the mod
      await act(async () => {
        fireEvent.click(screen.getByTestId('mod-toggle-smithingplus'));
      });

      await waitFor(() => {
        expect(disableFetch).toHaveBeenCalled();
        expect(onToggled).toHaveBeenCalledWith('smithingplus', false);
      });
    });

    it('enables a disabled mod when toggle is clicked', async () => {
      const enableFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'carrycapacity',
              enabled: true,
              pendingRestart: true,
            },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/enable')) {
          return enableFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsResponse),
        });
      });

      const onToggled = vi.fn();
      const queryClient = createTestQueryClient();
      render(<ModTable onToggled={onToggled} />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-toggle-carrycapacity')).toBeInTheDocument();
      });

      // Click toggle to enable the mod
      await act(async () => {
        fireEvent.click(screen.getByTestId('mod-toggle-carrycapacity'));
      });

      await waitFor(() => {
        expect(enableFetch).toHaveBeenCalled();
        expect(onToggled).toHaveBeenCalledWith('carrycapacity', true);
      });
    });
  });

  describe('remove mod (AC: 8)', () => {
    it('shows confirmation dialog when remove button is clicked', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-remove-smithingplus')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('mod-remove-smithingplus'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('remove-dialog')).toBeInTheDocument();
        expect(screen.getByText('Remove Smithing Plus?')).toBeInTheDocument();
        expect(
          screen.getByText(/This will remove the mod from your server/)
        ).toBeInTheDocument();
      });
    });

    it('closes dialog when cancel is clicked', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsResponse),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        expect(screen.getByTestId('mod-remove-smithingplus')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('mod-remove-smithingplus'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('remove-dialog')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('remove-dialog-cancel'));
      });

      await waitFor(() => {
        expect(screen.queryByTestId('remove-dialog')).not.toBeInTheDocument();
      });
    });

    it('removes mod when confirm is clicked', async () => {
      const removeFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              pendingRestart: true,
            },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((_url: string, options) => {
        if (options?.method === 'DELETE') {
          return removeFetch();
        }
        return Promise.resolve({
          ok: true,
          json: () => Promise.resolve(mockModsResponse),
        });
      });

      const onRemoved = vi.fn();
      const queryClient = createTestQueryClient();
      render(<ModTable onRemoved={onRemoved} />, {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-remove-smithingplus')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('mod-remove-smithingplus'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('remove-dialog-confirm')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('remove-dialog-confirm'));
      });

      await waitFor(() => {
        expect(removeFetch).toHaveBeenCalled();
        expect(onRemoved).toHaveBeenCalledWith('smithingplus');
      });
    });
  });

  describe('mod without name', () => {
    it('falls back to slug when name is null', async () => {
      const modWithoutName = {
        status: 'ok',
        data: {
          mods: [
            {
              filename: 'unknownmod-1.0.0.zip',
              slug: 'unknownmod',
              version: '1.0.0',
              enabled: true,
              installedAt: '2024-01-15T10:30:00Z',
              name: null,
              authors: null,
              description: null,
            },
          ],
          pendingRestart: false,
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(modWithoutName),
      });

      const queryClient = createTestQueryClient();
      render(<ModTable />, { wrapper: createWrapper(queryClient) });

      await waitFor(() => {
        // When name is null, only show slug once (as the name)
        const slugElements = screen.getAllByText('unknownmod');
        expect(slugElements.length).toBe(1);
      });
    });
  });
});
