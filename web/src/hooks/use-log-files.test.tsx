import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import type { ReactNode } from 'react';
import { useLogFiles } from './use-log-files';
import type { ApiResponse, LogFilesData } from '@/api/types';

// Mock the API client
vi.mock('@/api/client', () => ({
  apiClient: vi.fn(),
}));

// Import the mocked apiClient
import { apiClient } from '@/api/client';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        // Disable refetch intervals during tests
        refetchInterval: false,
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

describe('useLogFiles', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  describe('successful fetch', () => {
    it('returns log files list on successful fetch', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'server-main.txt',
              sizeBytes: 1024,
              modifiedAt: '2026-01-17T10:30:00Z',
            },
            {
              name: 'error.txt',
              sizeBytes: 512,
              modifiedAt: '2026-01-17T09:15:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data).toEqual(mockResponse);
      expect(result.current.data?.data.files).toHaveLength(2);
      expect(result.current.data?.data.files[0].name).toBe('server-main.txt');
    });

    it('handles empty log files list', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.data.files).toEqual([]);
    });
  });

  describe('loading state', () => {
    it('starts in loading state', () => {
      vi.mocked(apiClient).mockImplementation(
        () => new Promise(() => {}) // Never resolves
      );

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();
    });

    it('transitions from loading to success', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'test.txt',
              sizeBytes: 256,
              modifiedAt: '2026-01-17T10:00:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      expect(result.current.isSuccess).toBe(true);
    });
  });

  describe('error state', () => {
    it('returns error state on fetch failure', async () => {
      const mockError = new Error('Failed to fetch log files');
      vi.mocked(apiClient).mockRejectedValue(mockError);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
      expect(result.current.data).toBeUndefined();
    });

    it('handles network errors', async () => {
      vi.mocked(apiClient).mockRejectedValue(new Error('Network error'));

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isError).toBe(true);
      });

      expect(result.current.error).toBeTruthy();
    });
  });

  describe('query configuration', () => {
    it('uses correct query key', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: { files: [] },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Query key should be from queryKeys.console.logs
      const queries = queryClient.getQueryCache().getAll();
      expect(queries).toHaveLength(1);
      expect(queries[0].queryKey).toEqual(['console', 'logs']);
    });

    it('calls correct API endpoint', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: { files: [] },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(apiClient).toHaveBeenCalledWith('/api/v1alpha1/console/logs');
      });
    });
  });

  describe('refetch behavior', () => {
    it('supports manual refetch', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'initial.txt',
              sizeBytes: 100,
              modifiedAt: '2026-01-17T10:00:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(apiClient).toHaveBeenCalledTimes(1);

      // Update mock for refetch
      const updatedResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'updated.txt',
              sizeBytes: 200,
              modifiedAt: '2026-01-17T11:00:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(updatedResponse);

      // Trigger refetch
      const refetchResult = await result.current.refetch();

      await waitFor(() => {
        expect(apiClient).toHaveBeenCalledTimes(2);
      });

      expect(refetchResult.data?.data.files[0].name).toBe('updated.txt');
    });
  });

  describe('multiple log files', () => {
    it('handles multiple log files with different properties', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'server-main.txt',
              sizeBytes: 2048,
              modifiedAt: '2026-01-17T10:30:00Z',
            },
            {
              name: 'error.txt',
              sizeBytes: 1024,
              modifiedAt: '2026-01-17T09:15:00Z',
            },
            {
              name: 'debug.txt',
              sizeBytes: 512,
              modifiedAt: '2026-01-17T08:00:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      const files = result.current.data?.data.files;
      expect(files).toHaveLength(3);
      expect(files?.[0].name).toBe('server-main.txt');
      expect(files?.[0].sizeBytes).toBe(2048);
      expect(files?.[1].name).toBe('error.txt');
      expect(files?.[2].name).toBe('debug.txt');
    });
  });

  describe('return value structure', () => {
    it('returns all expected TanStack Query properties', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: { files: [] },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      // Check for common TanStack Query properties
      expect(result.current).toHaveProperty('data');
      expect(result.current).toHaveProperty('isLoading');
      expect(result.current).toHaveProperty('isError');
      expect(result.current).toHaveProperty('isSuccess');
      expect(result.current).toHaveProperty('error');
      expect(result.current).toHaveProperty('refetch');
    });
  });

  describe('edge cases', () => {
    it('handles log files with zero size', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'empty.txt',
              sizeBytes: 0,
              modifiedAt: '2026-01-17T10:00:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.data.files[0].sizeBytes).toBe(0);
    });

    it('handles log files with very large sizes', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'huge.txt',
              sizeBytes: 1073741824, // 1 GB
              modifiedAt: '2026-01-17T10:00:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.data.files[0].sizeBytes).toBe(1073741824);
    });

    it('handles log files with special characters in name', async () => {
      const mockResponse: ApiResponse<LogFilesData> = {
        status: 'ok',
        data: {
          files: [
            {
              name: 'server-log-2026-01-17_10-30-00.txt',
              sizeBytes: 1024,
              modifiedAt: '2026-01-17T10:30:00Z',
            },
          ],
        },
      };

      vi.mocked(apiClient).mockResolvedValue(mockResponse);

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useLogFiles(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => {
        expect(result.current.isSuccess).toBe(true);
      });

      expect(result.current.data?.data.files[0].name).toBe(
        'server-log-2026-01-17_10-30-00.txt'
      );
    });
  });
});
