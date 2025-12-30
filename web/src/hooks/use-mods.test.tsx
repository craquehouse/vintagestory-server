import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import {
  useMods,
  useLookupMod,
  useInstallMod,
  useEnableMod,
  useDisableMod,
  useRemoveMod,
} from './use-mods';

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

// Wrapper component for rendering hooks with QueryClientProvider
function createWrapper(queryClient: QueryClient) {
  return function Wrapper({ children }: { children: ReactNode }) {
    return (
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
  };
}

// Mock mod data
const mockModsList = {
  status: 'ok',
  data: {
    mods: [
      {
        filename: 'smithingplus-1.0.0.zip',
        slug: 'smithingplus',
        version: '1.0.0',
        enabled: true,
        installed_at: '2025-01-01T00:00:00Z',
        name: 'Smithing Plus',
        authors: ['TestAuthor'],
        description: 'Enhanced smithing',
      },
      {
        filename: 'carrycapacity-2.0.0.zip',
        slug: 'carrycapacity',
        version: '2.0.0',
        enabled: false,
        installed_at: '2025-01-02T00:00:00Z',
        name: 'Carry Capacity',
        authors: null,
        description: null,
      },
    ],
    pending_restart: false,
  },
};

const mockLookupResponse = {
  status: 'ok',
  data: {
    slug: 'newmod',
    name: 'New Mod',
    author: 'ModAuthor',
    description: 'A new mod description',
    latest_version: '1.5.0',
    downloads: 1000,
    side: 'Both',
    compatibility: {
      status: 'compatible',
      game_version: '1.21.3',
      mod_version: '1.5.0',
      message: 'Compatible with current server version',
    },
  },
};

describe('useMods', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior', () => {
    it('fetches mods list from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsList),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useMods(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsList),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useMods(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify camelCase transformation
      expect(result.current.data?.data.pendingRestart).toBe(false);
      expect(result.current.data?.data.mods[0].installedAt).toBe(
        '2025-01-01T00:00:00Z'
      );
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsList),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useMods(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('returns mods array and pending restart status', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModsList),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useMods(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.mods).toHaveLength(2);
      expect(result.current.data?.data.mods[0].slug).toBe('smithingplus');
      expect(result.current.data?.data.mods[1].slug).toBe('carrycapacity');
      expect(result.current.data?.data.pendingRestart).toBe(false);
    });
  });
});

describe('useLookupMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('query behavior', () => {
    it('fetches mod details from lookup endpoint when slug is provided', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLookupMod('newmod'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods/lookup/newmod',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('does not fetch when slug is empty', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLookupMod(''), {
        wrapper: createWrapper(queryClient),
      });

      // Should not be loading since query is disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('encodes special characters in slug (URL handling)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useLookupMod('https://mods.vintagestory.at/newmod'),
        {
          wrapper: createWrapper(queryClient),
        }
      );

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        expect.stringContaining(
          '/api/v1alpha1/mods/lookup/https%3A%2F%2Fmods.vintagestory.at%2Fnewmod'
        ),
        expect.any(Object)
      );
    });

    it('transforms response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockLookupResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLookupMod('newmod'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.latestVersion).toBe('1.5.0');
      expect(result.current.data?.data.compatibility.gameVersion).toBe('1.21.3');
      expect(result.current.data?.data.compatibility.modVersion).toBe('1.5.0');
    });
  });
});

describe('useInstallMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior', () => {
    it('calls install endpoint with POST method and slug in body', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'newmod',
              version: '1.5.0',
              filename: 'newmod-1.5.0.zip',
              compatibility: 'compatible',
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useInstallMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ slug: 'newmod' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ slug: 'newmod' }),
        })
      );
    });

    it('includes version in body when provided', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'newmod',
              version: '1.4.0',
              filename: 'newmod-1.4.0.zip',
              compatibility: 'compatible',
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useInstallMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ slug: 'newmod', version: '1.4.0' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods',
        expect.objectContaining({
          method: 'POST',
          body: JSON.stringify({ slug: 'newmod', version: '1.4.0' }),
        })
      );
    });

    it('invalidates mods query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'newmod',
              version: '1.5.0',
              filename: 'newmod-1.5.0.zip',
              compatibility: 'compatible',
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useInstallMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate({ slug: 'newmod' });
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['mods'],
      });
    });
  });
});

describe('useEnableMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior', () => {
    it('calls enable endpoint with POST method', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              enabled: true,
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useEnableMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('smithingplus');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods/smithingplus/enable',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('performs optimistic update', async () => {
      // Initial mods with disabled mod
      const initialMods = {
        status: 'ok',
        data: {
          mods: [
            {
              filename: 'testmod-1.0.0.zip',
              slug: 'testmod',
              version: '1.0.0',
              enabled: false,
              installed_at: '2025-01-01T00:00:00Z',
              name: 'Test Mod',
              authors: null,
              description: null,
            },
          ],
          pending_restart: false,
        },
      };

      let callCount = 0;
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        callCount++;
        if (url.includes('/enable')) {
          // Delay the enable response
          await new Promise((r) => setTimeout(r, 100));
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { slug: 'testmod', enabled: true, pending_restart: true },
              }),
          };
        }
        // Initial mods fetch
        return {
          ok: true,
          json: () => Promise.resolve(initialMods),
        };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with initial mods
      queryClient.setQueryData(['mods'], {
        status: 'ok',
        data: {
          mods: [
            {
              filename: 'testmod-1.0.0.zip',
              slug: 'testmod',
              version: '1.0.0',
              enabled: false,
              installedAt: '2025-01-01T00:00:00Z',
              name: 'Test Mod',
              authors: null,
              description: null,
            },
          ],
          pendingRestart: false,
        },
      });

      const { result } = renderHook(() => useEnableMod(), {
        wrapper: createWrapper(queryClient),
      });

      // Start the mutation
      act(() => {
        result.current.mutate('testmod');
      });

      // Check optimistic update happened immediately
      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['mods']) as {
          data: { mods: { enabled: boolean }[] };
        };
        expect(cachedData.data.mods[0].enabled).toBe(true);
      });
    });

    it('invalidates mods query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              enabled: true,
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useEnableMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('smithingplus');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['mods'],
      });
    });
  });
});

describe('useDisableMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior', () => {
    it('calls disable endpoint with POST method', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              enabled: false,
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useDisableMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('smithingplus');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods/smithingplus/disable',
        expect.objectContaining({
          method: 'POST',
        })
      );
    });

    it('performs optimistic update', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/disable')) {
          await new Promise((r) => setTimeout(r, 100));
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { slug: 'testmod', enabled: false, pending_restart: true },
              }),
          };
        }
        return { ok: true, json: () => Promise.resolve(mockModsList) };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with enabled mod
      queryClient.setQueryData(['mods'], {
        status: 'ok',
        data: {
          mods: [
            {
              filename: 'testmod-1.0.0.zip',
              slug: 'testmod',
              version: '1.0.0',
              enabled: true,
              installedAt: '2025-01-01T00:00:00Z',
              name: 'Test Mod',
              authors: null,
              description: null,
            },
          ],
          pendingRestart: false,
        },
      });

      const { result } = renderHook(() => useDisableMod(), {
        wrapper: createWrapper(queryClient),
      });

      act(() => {
        result.current.mutate('testmod');
      });

      // Check optimistic update
      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['mods']) as {
          data: { mods: { enabled: boolean }[] };
        };
        expect(cachedData.data.mods[0].enabled).toBe(false);
      });
    });
  });
});

describe('useRemoveMod', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
  });

  describe('mutation behavior', () => {
    it('calls remove endpoint with DELETE method', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useRemoveMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('smithingplus');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods/smithingplus',
        expect.objectContaining({
          method: 'DELETE',
        })
      );
    });

    it('performs optimistic update (removes mod from list)', async () => {
      const mockFetch = vi.fn().mockImplementation(async (url: string) => {
        if (url.includes('/mods/testmod') && !url.includes('/lookup')) {
          await new Promise((r) => setTimeout(r, 100));
          return {
            ok: true,
            json: () =>
              Promise.resolve({
                status: 'ok',
                data: { slug: 'testmod', pending_restart: true },
              }),
          };
        }
        return { ok: true, json: () => Promise.resolve(mockModsList) };
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Pre-populate the cache with two mods
      queryClient.setQueryData(['mods'], {
        status: 'ok',
        data: {
          mods: [
            {
              filename: 'testmod-1.0.0.zip',
              slug: 'testmod',
              version: '1.0.0',
              enabled: true,
              installedAt: '2025-01-01T00:00:00Z',
              name: 'Test Mod',
              authors: null,
              description: null,
            },
            {
              filename: 'othermod-1.0.0.zip',
              slug: 'othermod',
              version: '1.0.0',
              enabled: true,
              installedAt: '2025-01-02T00:00:00Z',
              name: 'Other Mod',
              authors: null,
              description: null,
            },
          ],
          pendingRestart: false,
        },
      });

      const { result } = renderHook(() => useRemoveMod(), {
        wrapper: createWrapper(queryClient),
      });

      act(() => {
        result.current.mutate('testmod');
      });

      // Check optimistic update - testmod should be removed
      await waitFor(() => {
        const cachedData = queryClient.getQueryData(['mods']) as {
          data: { mods: { slug: string }[] };
        };
        expect(cachedData.data.mods).toHaveLength(1);
        expect(cachedData.data.mods[0].slug).toBe('othermod');
      });
    });

    it('invalidates mods query on success', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              slug: 'smithingplus',
              pending_restart: true,
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

      const { result } = renderHook(() => useRemoveMod(), {
        wrapper: createWrapper(queryClient),
      });

      await act(async () => {
        result.current.mutate('smithingplus');
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['mods'],
      });
    });
  });
});
