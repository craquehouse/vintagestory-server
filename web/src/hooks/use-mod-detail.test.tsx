/**
 * Tests for useModDetail hook.
 *
 * Story 10.6: Verifies the mod detail hook fetches and returns
 * extended mod information including releases and metadata.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { useModDetail } from './use-mod-detail';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
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

// Mock mod detail response with extended fields (Story 10.6)
const mockModDetailResponse = {
  status: 'ok',
  data: {
    slug: 'smithingplus',
    name: 'Smithing Plus',
    author: 'jayu',
    description: '<p>Enhanced smithing mechanics</p>',
    latest_version: '1.8.3',
    downloads: 204656,
    follows: 2348,
    side: 'Both',
    compatibility: {
      status: 'compatible',
      game_version: '1.21.3',
      mod_version: '1.8.3',
      message: 'Compatible with current server version',
    },
    logo_url: 'https://moddbcdn.vintagestory.at/logo.png',
    releases: [
      {
        version: '1.8.3',
        filename: 'smithingplus_1.8.3.zip',
        file_id: 59176,
        downloads: 49726,
        game_versions: ['1.21.0', '1.21.1', '1.21.2', '1.21.3'],
        created: '2025-10-09 21:28:57',
        changelog: '<ul><li>Bug fixes</li></ul>',
      },
      {
        version: '1.8.2',
        filename: 'smithingplus_1.8.2.zip',
        file_id: 57894,
        downloads: 31245,
        game_versions: ['1.21.0', '1.21.1'],
        created: '2025-09-15 14:22:11',
        changelog: null,
      },
    ],
    tags: ['Crafting', 'QoL', 'Utility'],
    homepage_url: 'https://example.com/smithingplus',
    source_url: 'https://github.com/user/smithingplus',
    created: '2024-10-24 01:06:14',
    last_released: '2025-10-09 21:28:57',
  },
};

describe('useModDetail', () => {
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
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods/lookup/smithingplus',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('does not fetch when slug is empty', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail(''), {
        wrapper: createWrapper(queryClient),
      });

      // Should not be loading since query is disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('does not fetch when slug is whitespace only', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('   '), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.fetchStatus).toBe('idle');
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const data = result.current.data?.data;
      // Verify camelCase transformation
      expect(data?.latestVersion).toBe('1.8.3');
      expect(data?.logoUrl).toBe('https://moddbcdn.vintagestory.at/logo.png');
      expect(data?.compatibility.gameVersion).toBe('1.21.3');
      expect(data?.compatibility.modVersion).toBe('1.8.3');
      expect(data?.homepageUrl).toBe('https://example.com/smithingplus');
      expect(data?.sourceUrl).toBe('https://github.com/user/smithingplus');
      expect(data?.lastReleased).toBe('2025-10-09 21:28:57');
    });
  });

  describe('extended data (Story 10.6)', () => {
    it('returns releases array with all release data', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const data = result.current.data?.data;
      expect(data?.releases).toHaveLength(2);

      // Check first release (latest)
      const latestRelease = data?.releases[0];
      expect(latestRelease?.version).toBe('1.8.3');
      expect(latestRelease?.filename).toBe('smithingplus_1.8.3.zip');
      expect(latestRelease?.fileId).toBe(59176);
      expect(latestRelease?.downloads).toBe(49726);
      expect(latestRelease?.gameVersions).toEqual([
        '1.21.0',
        '1.21.1',
        '1.21.2',
        '1.21.3',
      ]);
      expect(latestRelease?.changelog).toBe('<ul><li>Bug fixes</li></ul>');

      // Check second release
      const olderRelease = data?.releases[1];
      expect(olderRelease?.version).toBe('1.8.2');
      expect(olderRelease?.changelog).toBe(null);
    });

    it('returns follows count', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.follows).toBe(2348);
    });

    it('returns tags array', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(result.current.data?.data.tags).toEqual([
        'Crafting',
        'QoL',
        'Utility',
      ]);
    });

    it('returns external URLs', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const data = result.current.data?.data;
      expect(data?.homepageUrl).toBe('https://example.com/smithingplus');
      expect(data?.sourceUrl).toBe('https://github.com/user/smithingplus');
    });

    it('returns timestamp metadata', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const data = result.current.data?.data;
      expect(data?.created).toBe('2024-10-24 01:06:14');
      expect(data?.lastReleased).toBe('2025-10-09 21:28:57');
    });
  });

  describe('loading states', () => {
    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('provides error state on fetch failure', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () =>
          Promise.resolve({
            detail: { code: 'MOD_NOT_FOUND', message: 'Mod not found' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useModDetail('nonexistent'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));
      expect(result.current.error).toBeDefined();
    });
  });

  describe('caching behavior', () => {
    it('uses query key with mod slug for caching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      renderHook(() => useModDetail('smithingplus'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        const cache = queryClient.getQueryData(['mods', 'smithingplus']);
        expect(cache).toBeDefined();
      });
    });
  });
});
