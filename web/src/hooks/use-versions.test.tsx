import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { useVersions, useVersionDetail } from './use-versions';

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

// Mock version list response (snake_case as returned by API)
const mockVersionListResponse = {
  status: 'ok',
  data: {
    versions: [
      {
        version: '1.21.6',
        filename: 'vs_server_linux-x64_1.21.6.tar.gz',
        filesize: '40.2 MB',
        md5: 'abc123',
        cdn_url: 'https://cdn.example.com/stable/1.21.6',
        local_url: '/downloads/stable/1.21.6',
        is_latest: true,
        channel: 'stable',
      },
      {
        version: '1.21.5',
        filename: 'vs_server_linux-x64_1.21.5.tar.gz',
        filesize: '39.8 MB',
        md5: 'def456',
        cdn_url: 'https://cdn.example.com/stable/1.21.5',
        local_url: '/downloads/stable/1.21.5',
        is_latest: false,
        channel: 'stable',
      },
      {
        version: '1.22.0-rc1',
        filename: 'vs_server_linux-x64_1.22.0-rc1.tar.gz',
        filesize: '41.0 MB',
        md5: 'ghi789',
        cdn_url: 'https://cdn.example.com/unstable/1.22.0-rc1',
        local_url: '/downloads/unstable/1.22.0-rc1',
        is_latest: true,
        channel: 'unstable',
      },
    ],
    total: 3,
    cached: true,
    cached_at: '2026-01-12T10:00:00Z',
  },
};

// Mock filtered stable versions
const mockStableVersionsResponse = {
  status: 'ok',
  data: {
    versions: [
      {
        version: '1.21.6',
        filename: 'vs_server_linux-x64_1.21.6.tar.gz',
        filesize: '40.2 MB',
        md5: 'abc123',
        cdn_url: 'https://cdn.example.com/stable/1.21.6',
        local_url: '/downloads/stable/1.21.6',
        is_latest: true,
        channel: 'stable',
      },
      {
        version: '1.21.5',
        filename: 'vs_server_linux-x64_1.21.5.tar.gz',
        filesize: '39.8 MB',
        md5: 'def456',
        cdn_url: 'https://cdn.example.com/stable/1.21.5',
        local_url: '/downloads/stable/1.21.5',
        is_latest: false,
        channel: 'stable',
      },
    ],
    total: 2,
    cached: true,
    cached_at: '2026-01-12T10:00:00Z',
  },
};

// Mock version detail response
const mockVersionDetailResponse = {
  status: 'ok',
  data: {
    version: {
      version: '1.21.6',
      filename: 'vs_server_linux-x64_1.21.6.tar.gz',
      filesize: '40.2 MB',
      md5: 'abc123',
      cdn_url: 'https://cdn.example.com/stable/1.21.6',
      local_url: '/downloads/stable/1.21.6',
      is_latest: true,
      channel: 'stable',
    },
    cached: false,
    cached_at: null,
  },
};

describe('useVersions', () => {
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
    it('fetches versions list from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionListResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersions(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/versions',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionListResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersions(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify camelCase transformation
      const data = result.current.data?.data;
      expect(data?.cachedAt).toBe('2026-01-12T10:00:00Z');
      expect(data?.versions[0].cdnUrl).toBe(
        'https://cdn.example.com/stable/1.21.6'
      );
      expect(data?.versions[0].localUrl).toBe('/downloads/stable/1.21.6');
      expect(data?.versions[0].isLatest).toBe(true);
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionListResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersions(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('returns versions array with all fields', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionListResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersions(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const data = result.current.data?.data;
      expect(data?.versions).toHaveLength(3);
      expect(data?.total).toBe(3);
      expect(data?.cached).toBe(true);

      // Check first version
      const v1 = data?.versions[0];
      expect(v1?.version).toBe('1.21.6');
      expect(v1?.filename).toBe('vs_server_linux-x64_1.21.6.tar.gz');
      expect(v1?.filesize).toBe('40.2 MB');
      expect(v1?.md5).toBe('abc123');
      expect(v1?.channel).toBe('stable');
      expect(v1?.isLatest).toBe(true);
    });

    it('can filter by channel parameter', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockStableVersionsResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersions({ channel: 'stable' }), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/versions?channel=stable',
        expect.any(Object)
      );

      expect(result.current.data?.data.versions).toHaveLength(2);
      expect(result.current.data?.data.versions[0].channel).toBe('stable');
    });

    it('can be disabled with enabled option', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionListResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersions({ enabled: false }), {
        wrapper: createWrapper(queryClient),
      });

      // Should not be loading since query is disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('uses different query keys for different channels', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockStableVersionsResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();

      // Fetch stable versions
      const { result: stableResult } = renderHook(
        () => useVersions({ channel: 'stable' }),
        { wrapper: createWrapper(queryClient) }
      );

      await waitFor(() => expect(stableResult.current.isSuccess).toBe(true));

      // Fetch unstable versions (different query key)
      const { result: unstableResult } = renderHook(
        () => useVersions({ channel: 'unstable' }),
        { wrapper: createWrapper(queryClient) }
      );

      await waitFor(() => expect(unstableResult.current.isSuccess).toBe(true));

      // Both calls should have been made (different query keys)
      expect(mockFetch).toHaveBeenCalledTimes(2);
    });
  });
});

describe('useVersionDetail', () => {
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
    it('fetches version detail from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersionDetail('1.21.6'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/versions/1.21.6',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersionDetail('1.21.6'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const data = result.current.data?.data;
      expect(data?.version.cdnUrl).toBe(
        'https://cdn.example.com/stable/1.21.6'
      );
      expect(data?.version.localUrl).toBe('/downloads/stable/1.21.6');
      expect(data?.version.isLatest).toBe(true);
      expect(data?.cachedAt).toBe(null);
    });

    it('encodes version string in URL', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersionDetail('1.22.0-rc1'), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/versions/1.22.0-rc1',
        expect.any(Object)
      );
    });

    it('does not fetch when version is empty', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useVersionDetail(''), {
        wrapper: createWrapper(queryClient),
      });

      // Should not be loading since query is disabled
      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockFetch).not.toHaveBeenCalled();
    });

    it('can be disabled with enabled option', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockVersionDetailResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(
        () => useVersionDetail('1.21.6', { enabled: false }),
        { wrapper: createWrapper(queryClient) }
      );

      expect(result.current.isLoading).toBe(false);
      expect(result.current.fetchStatus).toBe('idle');
      expect(mockFetch).not.toHaveBeenCalled();
    });
  });
});
