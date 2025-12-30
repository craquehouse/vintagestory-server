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
import { ModLookupInput, extractSlug } from './ModLookupInput';

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

describe('extractSlug utility', () => {
  it('extracts slug from full URL with https', () => {
    expect(extractSlug('https://mods.vintagestory.at/smithingplus')).toBe(
      'smithingplus'
    );
  });

  it('extracts slug from full URL with http', () => {
    expect(extractSlug('http://mods.vintagestory.at/carrycapacity')).toBe(
      'carrycapacity'
    );
  });

  it('extracts slug from URL without protocol', () => {
    expect(extractSlug('mods.vintagestory.at/newmod')).toBe('newmod');
  });

  it('returns slug as-is when already a plain slug', () => {
    expect(extractSlug('smithingplus')).toBe('smithingplus');
  });

  it('converts slug to lowercase', () => {
    expect(extractSlug('SmithingPlus')).toBe('smithingplus');
  });

  it('trims whitespace', () => {
    expect(extractSlug('  smithingplus  ')).toBe('smithingplus');
  });

  it('handles URL with trailing path', () => {
    expect(extractSlug('mods.vintagestory.at/modname')).toBe('modname');
  });
});

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
  });
});
