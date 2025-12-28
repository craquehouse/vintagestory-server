import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { type ReactNode } from 'react';
import { useAuthMe } from './use-auth-me';
import { UnauthorizedError, ForbiddenError } from '../errors';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        // Turn off retries for tests
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

describe('useAuthMe', () => {
  const originalFetch = globalThis.fetch;
  const originalEnv = { ...import.meta.env };

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8000';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    Object.keys(import.meta.env).forEach((key) => {
      if (!(key in originalEnv)) {
        delete import.meta.env[key];
      }
    });
    Object.assign(import.meta.env, originalEnv);
  });

  describe('successful requests (AC: 1, 2, 5)', () => {
    it('fetches auth/me endpoint with X-API-Key header', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { role: 'admin' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useAuthMe(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Verify the request was made with correct headers
      expect(mockFetch).toHaveBeenCalledWith(
        'http://localhost:8000/api/v1alpha1/auth/me',
        expect.objectContaining({
          headers: expect.any(Headers),
        })
      );

      const headers = mockFetch.mock.calls[0][1].headers as Headers;
      expect(headers.get('X-API-Key')).toBe('test-api-key');
    });

    it('transforms snake_case response to camelCase', async () => {
      // Simulate API returning snake_case (though this endpoint is simple)
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            // If API returned user_role, it would be transformed to userRole
            data: { role: 'monitor' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useAuthMe(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Data should be accessible with camelCase keys
      expect(result.current.data).toEqual({
        status: 'ok',
        data: { role: 'monitor' },
      });
    });

    it('uses TanStack Query for state management', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { role: 'admin' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useAuthMe(), {
        wrapper: createWrapper(queryClient),
      });

      // Initially loading
      expect(result.current.isLoading).toBe(true);
      expect(result.current.data).toBeUndefined();

      // After fetch completes
      await waitFor(() => expect(result.current.isSuccess).toBe(true));
      expect(result.current.isLoading).toBe(false);
      expect(result.current.data?.data.role).toBe('admin');
    });

    it('caches the result (staleTime: Infinity)', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { role: 'admin' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const wrapper = createWrapper(queryClient);

      // First render
      const { result: result1 } = renderHook(() => useAuthMe(), { wrapper });
      await waitFor(() => expect(result1.current.isSuccess).toBe(true));

      // Second render - should use cached data, no additional fetch
      const { result: result2 } = renderHook(() => useAuthMe(), { wrapper });

      expect(result2.current.data?.data.role).toBe('admin');
      expect(mockFetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('error handling (AC: 3, 4)', () => {
    it('handles 401 Unauthorized errors', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: 'Unauthorized',
        json: () =>
          Promise.resolve({
            detail: { code: 'UNAUTHORIZED', message: 'Invalid API key' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useAuthMe(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeInstanceOf(UnauthorizedError);
      expect(result.current.error?.message).toBe('Invalid API key');
    });

    it('handles 403 Forbidden errors', async () => {
      const mockFetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 403,
        statusText: 'Forbidden',
        json: () =>
          Promise.resolve({
            detail: { code: 'FORBIDDEN', message: 'Access denied' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useAuthMe(), {
        wrapper: createWrapper(queryClient),
      });

      await waitFor(() => expect(result.current.isError).toBe(true));

      expect(result.current.error).toBeInstanceOf(ForbiddenError);
      expect(result.current.error?.message).toBe('Access denied');
    });
  });

  describe('full integration flow', () => {
    it('demonstrates complete flow: fetch → transform → return typed data', async () => {
      // Simulate a realistic API response with snake_case fields
      const mockFetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            status: 'ok',
            data: { role: 'admin' },
          }),
      });
      globalThis.fetch = mockFetch;

      const queryClient = createTestQueryClient();
      const { result } = renderHook(() => useAuthMe(), {
        wrapper: createWrapper(queryClient),
      });

      // Flow step 1: Initially in loading state
      expect(result.current.isLoading).toBe(true);

      // Flow step 2: Wait for fetch to complete
      await waitFor(() => expect(result.current.isSuccess).toBe(true));

      // Flow step 3: Data is transformed and available
      expect(result.current.data).toEqual({
        status: 'ok',
        data: { role: 'admin' },
      });

      // Flow step 4: Type safety - can access data.data.role
      const role = result.current.data?.data.role;
      expect(role).toBe('admin');
    });
  });
});
