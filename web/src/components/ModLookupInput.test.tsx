import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  render,
  screen,
  waitFor,
  fireEvent,
  act,
} from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { ModLookupInput } from './ModLookupInput';

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

// Mock mod lookup response
const mockLookupResponse = {
  status: 'ok',
  data: {
    slug: 'smithingplus',
    name: 'Smithing Plus',
    author: 'TestAuthor',
    description: 'Enhanced smithing features for VintageStory',
    latest_version: '1.5.0',
    downloads: 10000,
    side: 'Both',
    compatibility: {
      status: 'compatible',
      game_version: '1.21.3',
      mod_version: '1.5.0',
      message: 'Compatible with current server version',
    },
  },
};

const mockIncompatibleResponse = {
  status: 'ok',
  data: {
    slug: 'oldmod',
    name: 'Old Mod',
    author: 'SomeAuthor',
    description: 'An old mod',
    latest_version: '1.0.0',
    downloads: 500,
    side: 'Server',
    compatibility: {
      status: 'incompatible',
      game_version: '1.19.0',
      mod_version: '1.0.0',
      message: 'Requires server version 1.19.x or earlier',
    },
  },
};

// Note: extractSlug tests moved to lib/mod-utils.test.ts (VSS-195)

describe('ModLookupInput', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    vi.useFakeTimers({ shouldAdvanceTime: true });
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.useRealTimers();
  });

  describe('rendering (AC: 1)', () => {
    it('renders input with correct placeholder', () => {
      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByPlaceholderText('Enter mod slug or paste URL');
      expect(input).toBeInTheDocument();
    });

    it('does not show preview card initially', () => {
      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      expect(screen.queryByTestId('mod-preview-card')).not.toBeInTheDocument();
    });
  });

  describe('debounced lookup (AC: 2)', () => {
    it('debounces lookup requests by 300ms', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      // Type quickly - each keystroke should reset the timer
      await act(async () => {
        fireEvent.change(input, { target: { value: 's' } });
      });
      await act(async () => {
        vi.advanceTimersByTime(100);
      });
      await act(async () => {
        fireEvent.change(input, { target: { value: 'sm' } });
      });
      await act(async () => {
        vi.advanceTimersByTime(100);
      });
      await act(async () => {
        fireEvent.change(input, { target: { value: 'smi' } });
      });

      // Should not have fetched yet (debounce not complete)
      expect(mockFetch).not.toHaveBeenCalled();

      // Advance past debounce delay
      await act(async () => {
        vi.advanceTimersByTime(350);
      });

      // Now it should fetch
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });
    });

    it('shows loading spinner during lookup', async () => {
      let resolvePromise: () => void;
      const pendingPromise = new Promise<void>((resolve) => {
        resolvePromise = resolve;
      });

      const mockFetch = vi.fn().mockImplementation(async () => {
        await pendingPromise;
        return {
          ok: true,
          json: () => Promise.resolve(mockLookupResponse),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      // Wait for loading state
      await waitFor(() => {
        expect(screen.getByTestId('lookup-spinner')).toBeInTheDocument();
      });

      // Resolve the fetch
      await act(async () => {
        resolvePromise!();
      });

      // Spinner should disappear
      await waitFor(() => {
        expect(screen.queryByTestId('lookup-spinner')).not.toBeInTheDocument();
      });
    });
  });

  describe('preview card (AC: 3)', () => {
    it('displays mod details in preview card after lookup', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-preview-card')).toBeInTheDocument();
      });

      // Check all mod details are displayed
      expect(screen.getByText('Smithing Plus')).toBeInTheDocument();
      expect(screen.getByText('by TestAuthor')).toBeInTheDocument();
      expect(
        screen.getByText(/Enhanced smithing features/i)
      ).toBeInTheDocument();
      expect(screen.getByText('v1.5.0')).toBeInTheDocument();
      expect(screen.getByText(/10,000 downloads/i)).toBeInTheDocument();
      expect(screen.getByTestId('compatibility-badge')).toBeInTheDocument();
    });

    it('shows compatibility badge with correct status', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        const badge = screen.getByTestId('compatibility-badge');
        expect(badge).toHaveAttribute('data-status', 'compatible');
      });
    });

    it('shows install button', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
        expect(screen.getByTestId('install-button')).toHaveTextContent(
          'Install'
        );
      });
    });
  });

  describe('error handling', () => {
    it('shows error message when mod not found', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: 'Not Found',
        json: () =>
          Promise.resolve({
            detail: { code: 'MOD_NOT_FOUND', message: 'Mod not found' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'nonexistent' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('lookup-error')).toBeInTheDocument();
        expect(screen.getByText(/Mod not found/i)).toBeInTheDocument();
      });
    });
  });

  describe('incompatible mod confirmation (AC: 5)', () => {
    it('shows confirmation dialog when installing incompatible mod', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockIncompatibleResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'oldmod' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      // Click install on incompatible mod
      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      // Dialog should appear
      await waitFor(() => {
        expect(screen.getByTestId('incompatible-dialog')).toBeInTheDocument();
        expect(
          screen.getByText(/Install Incompatible Mod/i)
        ).toBeInTheDocument();
      });
    });

    it('allows canceling incompatible mod installation', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockIncompatibleResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'oldmod' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('dialog-cancel')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('dialog-cancel'));
      });

      // Dialog should close
      await waitFor(() => {
        expect(
          screen.queryByTestId('incompatible-dialog')
        ).not.toBeInTheDocument();
      });
    });
  });

  describe('installation (AC: 4)', () => {
    it('calls install mutation for compatible mods', async () => {
      const lookupFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });

      const installFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              version: '1.5.0',
              filename: 'smithingplus-1.5.0.zip',
              compatibility: 'compatible',
              pending_restart: true,
            },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/lookup/')) {
          return lookupFetch();
        }
        return installFetch();
      });

      const onInstalled = vi.fn();
      const queryClient = createTestQueryClient();
      render(<ModLookupInput onInstalled={onInstalled} />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      await waitFor(() => {
        expect(onInstalled).toHaveBeenCalledWith({
          slug: 'smithingplus',
          version: '1.5.0',
        });
      });
    });

    it('clears input after successful installation', async () => {
      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/lookup/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockLookupResponse),
          });
        }
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: {
                slug: 'smithingplus',
                version: '1.5.0',
                filename: 'smithingplus-1.5.0.zip',
                compatibility: 'compatible',
                pending_restart: true,
              },
            }),
        });
      });

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId(
        'mod-search-input'
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      await waitFor(() => {
        expect(input.value).toBe('');
      });
    });

    it('confirms and installs incompatible mod when user confirms', async () => {
      const lookupFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockIncompatibleResponse),
      });

      const installFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'oldmod',
              version: '1.0.0',
              filename: 'oldmod-1.0.0.zip',
              compatibility: 'incompatible',
              pending_restart: true,
            },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/lookup/')) {
          return lookupFetch();
        }
        return installFetch();
      });

      const onInstalled = vi.fn();
      const queryClient = createTestQueryClient();
      render(<ModLookupInput onInstalled={onInstalled} />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'oldmod' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      // Click install - should show dialog
      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('incompatible-dialog')).toBeInTheDocument();
      });

      // Confirm installation
      await act(async () => {
        fireEvent.click(screen.getByTestId('dialog-confirm'));
      });

      await waitFor(() => {
        expect(onInstalled).toHaveBeenCalledWith({
          slug: 'oldmod',
          version: '1.0.0',
        });
      });
    });

    it('shows install button as disabled while installing', async () => {
      let resolveInstall: () => void;
      const installPromise = new Promise<void>((resolve) => {
        resolveInstall = resolve;
      });

      globalThis.fetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/lookup/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(mockLookupResponse),
          });
        }
        await installPromise;
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: {
                slug: 'smithingplus',
                version: '1.5.0',
                filename: 'smithingplus-1.5.0.zip',
                compatibility: 'compatible',
                pending_restart: true,
              },
            }),
        });
      });

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      // Button should be disabled and show loading state
      await waitFor(() => {
        const installButton = screen.getByTestId('install-button');
        expect(installButton).toBeDisabled();
        expect(installButton).toHaveTextContent('Installing...');
      });

      // Resolve the install
      await act(async () => {
        resolveInstall!();
      });
    });
  });

  describe('URL parsing and slug extraction', () => {
    it('extracts slug from full HTTPS URL', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, {
          target: { value: 'https://mods.vintagestory.at/smithingplus' },
        });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-preview-card')).toBeInTheDocument();
      });
    });

    it('extracts slug from URL without protocol', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, {
          target: { value: 'mods.vintagestory.at/smithingplus' },
        });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-preview-card')).toBeInTheDocument();
      });
    });

    it('extracts slug from URL with query parameters', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, {
          target: { value: 'mods.vintagestory.at/smithingplus?tab=files' },
        });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-preview-card')).toBeInTheDocument();
      });
    });

    it('handles plain slug with uppercase converted to lowercase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'SmithingPlus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
        const fetchUrl = mockFetch.mock.calls[0][0] as string;
        expect(fetchUrl).toContain('/smithingplus');
      });
    });

    it('does not trigger lookup for empty input', async () => {
      const mockFetch = vi.fn();
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: '' } });
        vi.advanceTimersByTime(350);
      });

      // Should not fetch for empty input
      expect(mockFetch).not.toHaveBeenCalled();
      expect(screen.queryByTestId('mod-preview-card')).not.toBeInTheDocument();
    });

    it('does not trigger lookup for whitespace-only input', async () => {
      const mockFetch = vi.fn();
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: '   ' } });
        vi.advanceTimersByTime(350);
      });

      // Should not fetch for whitespace-only input
      expect(mockFetch).not.toHaveBeenCalled();
      expect(screen.queryByTestId('mod-preview-card')).not.toBeInTheDocument();
    });

    it('does not trigger lookup for invalid characters', async () => {
      const mockFetch = vi.fn();
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'invalid@slug!' } });
        vi.advanceTimersByTime(350);
      });

      // Should not fetch for invalid slug characters
      expect(mockFetch).not.toHaveBeenCalled();
      expect(screen.queryByTestId('mod-preview-card')).not.toBeInTheDocument();
    });
  });

  describe('preview card content', () => {
    it('displays mod logo when available', async () => {
      const responseWithLogo = {
        ...mockLookupResponse,
        data: {
          ...mockLookupResponse.data,
          logoUrl: 'https://mods.vintagestory.at/logo.png',
        },
      };

      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(responseWithLogo),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        const logo = screen.getByTestId('mod-logo');
        expect(logo).toBeInTheDocument();
        expect(logo).toHaveAttribute('src', 'https://mods.vintagestory.at/logo.png');
        expect(logo).toHaveAttribute('alt', 'Smithing Plus logo');
      });
    });

    it('does not display logo when not available', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-preview-card')).toBeInTheDocument();
      });

      expect(screen.queryByTestId('mod-logo')).not.toBeInTheDocument();
    });

    it('displays mod description when available', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(
          screen.getByText(/Enhanced smithing features/i)
        ).toBeInTheDocument();
      });
    });

    it('displays formatted download count', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByText(/10,000 downloads/i)).toBeInTheDocument();
      });
    });

    it('displays mod side information', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByText('both')).toBeInTheDocument();
      });
    });
  });

  describe('edge cases and special scenarios', () => {
    it('verifies defensive guard on line 71 via documentation test', async () => {
      // Line 71 (`if (!modData) return;`) is defensive code that's unreachable
      // through normal UI flow because the install button only renders when modData exists (line 147).
      // This test documents that the guard is there for safety but cannot be hit via UI.

      // Scenario: API returns lookup data with null/undefined data field
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/lookup/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve({ status: 'ok', data: null }),
          });
        }
        return Promise.resolve({ ok: true, json: () => Promise.resolve({}) });
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'testmod' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalled();
      });

      // Install button doesn't render when modData is null
      // This proves line 71's guard is defensive - handleInstall can't be called when modData is null
      expect(screen.queryByTestId('install-button')).not.toBeInTheDocument();

      // The guard on line 71 would protect against direct function calls or
      // race conditions in future code changes, but is unreachable via current UI flow
    });

    it('handles performInstall when modData becomes null during dialog', async () => {
      // This tests line 83: the guard in performInstall when modData is null
      let returnValidData = true;
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/lookup/')) {
          if (returnValidData) {
            return Promise.resolve({
              ok: true,
              json: () => Promise.resolve(mockIncompatibleResponse),
            });
          }
          return Promise.resolve({
            ok: false,
            status: 404,
            statusText: 'Not Found',
            json: () =>
              Promise.resolve({
                detail: { code: 'MOD_NOT_FOUND', message: 'Mod not found' },
              }),
          });
        }
        // Install endpoint
        return Promise.resolve({
          ok: true,
          json: () =>
            Promise.resolve({
              status: 'ok',
              data: {
                slug: 'oldmod',
                version: '1.0.0',
                filename: 'oldmod-1.0.0.zip',
                compatibility: 'incompatible',
                pending_restart: true,
              },
            }),
        });
      });
      globalThis.fetch = mockFetch;

      const onInstalled = vi.fn();
      const queryClient = createTestQueryClient();
      render(<ModLookupInput onInstalled={onInstalled} />, {
        wrapper: createWrapper(queryClient),
      });

      const input = screen.getByTestId('mod-search-input');

      // Enter incompatible mod
      await act(async () => {
        fireEvent.change(input, { target: { value: 'oldmod' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      // Click install to show dialog
      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('incompatible-dialog')).toBeInTheDocument();
      });

      // Make subsequent lookups fail
      returnValidData = false;

      // Clear input - this will trigger a new lookup that fails
      await act(async () => {
        fireEvent.change(input, { target: { value: 'different' } });
        vi.advanceTimersByTime(350);
      });

      // Wait for error state
      await waitFor(() => {
        expect(screen.queryByTestId('lookup-error')).toBeInTheDocument();
      });

      // Now click confirm - performInstall should handle null modData
      await act(async () => {
        fireEvent.click(screen.getByTestId('dialog-confirm'));
      });

      // Installation should not proceed
      await act(async () => {
        vi.advanceTimersByTime(100);
      });

      expect(onInstalled).not.toHaveBeenCalled();
    });

    it('handles rapid input changes correctly with debouncing', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      // Type rapidly
      await act(async () => {
        fireEvent.change(input, { target: { value: 'a' } });
        vi.advanceTimersByTime(50);
        fireEvent.change(input, { target: { value: 'ab' } });
        vi.advanceTimersByTime(50);
        fireEvent.change(input, { target: { value: 'abc' } });
        vi.advanceTimersByTime(50);
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      // Should only fetch once for the final value
      await waitFor(() => {
        expect(mockFetch).toHaveBeenCalledTimes(1);
      });
    });

    it('clears preview when input is cleared', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      // First, enter a valid slug
      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('mod-preview-card')).toBeInTheDocument();
      });

      // Clear the input
      await act(async () => {
        fireEvent.change(input, { target: { value: '' } });
        vi.advanceTimersByTime(350);
      });

      // Preview should disappear
      await waitFor(() => {
        expect(screen.queryByTestId('mod-preview-card')).not.toBeInTheDocument();
      });
    });

    it('handles network errors gracefully', async () => {
      const mockFetch = vi.fn().mockRejectedValue(new Error('Network error'));
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'smithingplus' } });
        vi.advanceTimersByTime(350);
      });

      // Should show error state
      await waitFor(() => {
        expect(screen.getByTestId('lookup-error')).toBeInTheDocument();
      });
    });

    it('closes incompatible dialog and clears input after successful installation', async () => {
      const lookupFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockIncompatibleResponse),
      });

      const installFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'oldmod',
              version: '1.0.0',
              filename: 'oldmod-1.0.0.zip',
              compatibility: 'incompatible',
              pending_restart: true,
            },
          }),
      });

      globalThis.fetch = vi.fn().mockImplementation((url: string) => {
        if (url.includes('/lookup/')) {
          return lookupFetch();
        }
        return installFetch();
      });

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId(
        'mod-search-input'
      ) as HTMLInputElement;

      await act(async () => {
        fireEvent.change(input, { target: { value: 'oldmod' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      // Click install
      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('incompatible-dialog')).toBeInTheDocument();
      });

      // Confirm installation
      await act(async () => {
        fireEvent.click(screen.getByTestId('dialog-confirm'));
      });

      // Dialog should close and input should be cleared
      await waitFor(() => {
        expect(
          screen.queryByTestId('incompatible-dialog')
        ).not.toBeInTheDocument();
        expect(input.value).toBe('');
      });
    });

    it('displays incompatibility message in dialog', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockIncompatibleResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      const input = screen.getByTestId('mod-search-input');

      await act(async () => {
        fireEvent.change(input, { target: { value: 'oldmod' } });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });

      await act(async () => {
        fireEvent.click(screen.getByTestId('install-button'));
      });

      await waitFor(() => {
        expect(screen.getByTestId('incompatible-dialog')).toBeInTheDocument();
        expect(
          screen.getByText(/Requires server version 1.19.x or earlier/i)
        ).toBeInTheDocument();
      });
    });
  });

  describe('formatted description (Story 16.4)', () => {
    /** Look up a mod whose description is `description` and wait for the preview. */
    async function renderWithDescription(description: string | null) {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockLookupResponse,
            data: { ...mockLookupResponse.data, description },
          }),
      });

      const queryClient = createTestQueryClient();
      render(<ModLookupInput />, { wrapper: createWrapper(queryClient) });

      await act(async () => {
        fireEvent.change(screen.getByTestId('mod-search-input'), {
          target: { value: 'smithingplus' },
        });
        vi.advanceTimersByTime(350);
      });

      await waitFor(() => {
        expect(screen.getByTestId('install-button')).toBeInTheDocument();
      });
    }

    it('renders the description HTML as formatting, not as tags (AC 1)', async () => {
      await renderWithDescription(
        '<p>Improves <strong>smithing</strong>. Requires <a href="https://mods.vintagestory.at/commonlib">CommonLib</a>.</p>'
      );

      const description = screen.getByTestId('mod-preview-description');
      expect(description.querySelector('strong')).toHaveTextContent('smithing');
      expect(description.querySelector('a')).toHaveTextContent('CommonLib');
      expect(description.textContent).not.toContain('<strong>');
      expect(description.textContent).not.toContain('<p>');
    });

    it('clamps the rendered element and keeps the whole description (AC 1)', async () => {
      const paragraphs = Array.from(
        { length: 12 },
        (_, index) => `<p>Paragraph ${index + 1} with <em>emphasis</em>.</p>`
      ).join('');
      await renderWithDescription(paragraphs);

      const description = screen.getByTestId('mod-preview-description');
      expect(description).toHaveClass('line-clamp-3');
      expect(description.querySelectorAll('p')).toHaveLength(12);
      expect(description).toHaveTextContent('Paragraph 12 with emphasis.');
    });

    it('strips scripts, event handlers and javascript: URLs (AC 2)', async () => {
      await renderWithDescription(
        '<p onclick="alert(1)">Safe text</p><script>alert("xss")</script>' +
          '<a href="javascript:alert(1)">bad link</a><img src="x" onerror="alert(1)">'
      );

      const description = screen.getByTestId('mod-preview-description');
      expect(description.querySelector('script')).toBeNull();
      expect(description.innerHTML).not.toContain('onclick');
      expect(description.innerHTML).not.toContain('onerror');
      expect(description.innerHTML.toLowerCase()).not.toContain('javascript');
      expect(description).toHaveTextContent('Safe text');
    });

    it('opens links in a new tab with rel="noopener noreferrer" (AC 3)', async () => {
      await renderWithDescription(
        '<p><a href="https://ko-fi.com/x" target="_self" rel="noopener">Ko-fi</a></p>'
      );

      const link = screen.getByTestId('mod-preview-description').querySelector('a');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('drops images, embeds and inline styling, and uses theme colors (AC 4)', async () => {
      await renderWithDescription(
        '<div style="background: #fbbf9d; color: #222" class="fixed inset-0">' +
          '<p>Support me</p><img src="https://i.imgur.com/a.png">' +
          '<iframe src="https://www.youtube.com/embed/x"></iframe></div>'
      );

      const description = screen.getByTestId('mod-preview-description');
      expect(description.querySelector('img')).toBeNull();
      expect(description.querySelector('iframe')).toBeNull();
      expect(description.querySelector('[style]')).toBeNull();
      expect(description.querySelector('[class]')).toBeNull();
      expect(description).toHaveTextContent('Support me');
      expect(description).toHaveClass('text-muted-foreground');
      expect(description.className).toContain('[&_a]:text-primary');
    });

    it('shows no description when nothing visible is left (AC 4)', async () => {
      await renderWithDescription(
        '<p><a href="https://discord.com/x"><img src="https://i.imgur.com/a.png"></a></p>'
      );

      expect(screen.queryByTestId('mod-preview-description')).not.toBeInTheDocument();
    });

    it('shows no description when the mod has none', async () => {
      await renderWithDescription(null);

      expect(screen.queryByTestId('mod-preview-description')).not.toBeInTheDocument();
    });
  });
});
