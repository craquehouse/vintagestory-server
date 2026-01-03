import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { useJobs } from './use-jobs';

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

// Mock jobs data (snake_case as returned by API before transformation)
const mockJobsResponse = {
  status: 'ok',
  data: {
    jobs: [
      {
        id: 'mod_cache_refresh',
        next_run_time: '2026-01-02T15:30:00Z',
        trigger_type: 'interval',
        trigger_details: 'every 3600 seconds',
      },
      {
        id: 'server_versions_check',
        next_run_time: '2026-01-03T00:00:00Z',
        trigger_type: 'interval',
        trigger_details: 'every 86400 seconds',
      },
    ],
  },
};

// Empty jobs response
const mockEmptyJobsResponse = {
  status: 'ok',
  data: {
    jobs: [],
  },
};

describe('useJobs', () => {
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
    it('fetches jobs from the correct endpoint', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockJobsResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useJobs(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/jobs',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );
    });

    it('transforms snake_case response to camelCase', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockJobsResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useJobs(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify camelCase transformation
      const jobs = result.current.data?.data.jobs;
      expect(jobs).toHaveLength(2);

      expect(jobs?.[0].id).toBe('mod_cache_refresh');
      expect(jobs?.[0].nextRunTime).toBe('2026-01-02T15:30:00Z');
      expect(jobs?.[0].triggerType).toBe('interval');
      expect(jobs?.[0].triggerDetails).toBe('every 3600 seconds');

      expect(jobs?.[1].id).toBe('server_versions_check');
      expect(jobs?.[1].nextRunTime).toBe('2026-01-03T00:00:00Z');
    });

    it('provides loading state while fetching', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockJobsResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useJobs(), {
        wrapper: createWrapper(queryClient),
      });

      expect(result.current.isLoading).toBe(true);

      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
    });

    it('handles empty jobs list', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockEmptyJobsResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useJobs(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const jobs = result.current.data?.data.jobs;
      expect(jobs).toHaveLength(0);
    });

    it('handles API errors', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () =>
          Promise.resolve({
            detail: {
              code: 'FORBIDDEN',
              message: 'Admin role required',
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useJobs(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeDefined();
    });

    it('returns all job fields correctly', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockJobsResponse),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useJobs(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const job = result.current.data?.data.jobs[0];
      expect(job).toBeDefined();
      expect(typeof job?.id).toBe('string');
      expect(typeof job?.nextRunTime).toBe('string');
      expect(typeof job?.triggerType).toBe('string');
      expect(typeof job?.triggerDetails).toBe('string');
    });

    it('handles null nextRunTime for paused jobs', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: {
              jobs: [
                {
                  id: 'paused_job',
                  next_run_time: null,
                  trigger_type: 'interval',
                  trigger_details: 'every 3600 seconds (paused)',
                },
              ],
            },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useJobs(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      const job = result.current.data?.data.jobs[0];
      expect(job?.nextRunTime).toBeNull();
    });
  });
});
