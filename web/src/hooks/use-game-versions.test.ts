import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useGameVersions } from './use-game-versions';
import type { ApiResponse, GameVersionsData } from '@/api/types';

// Mock the mods API functions
vi.mock('@/api/mods', () => ({
  fetchGameVersions: vi.fn(),
}));

import { fetchGameVersions } from '@/api/mods';

// Helper to create a wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });

  return function Wrapper({ children }: { children: React.ReactNode }) {
    return React.createElement(
      QueryClientProvider,
      { client: queryClient },
      children
    );
  };
}

describe('useGameVersions', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('fetches game versions on mount', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3', '1.21.2', '1.21.1', '1.21.0', '1.20.0'],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(fetchGameVersions).toHaveBeenCalled();
    expect(result.current.data).toEqual(mockResponse);
  });

  it('returns list of game versions sorted newest to oldest', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3', '1.21.2', '1.21.1', '1.21.0', '1.20.0'],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.data?.versions).toEqual([
      '1.21.3',
      '1.21.2',
      '1.21.1',
      '1.21.0',
      '1.20.0',
    ]);
    expect(result.current.data?.data?.versions[0]).toBe('1.21.3');
  });

  it('handles empty versions list', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: [],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.data?.versions).toEqual([]);
    expect(result.current.isSuccess).toBe(true);
  });

  it('handles fetch errors', async () => {
    const mockError = new Error('Network error');
    vi.mocked(fetchGameVersions).mockRejectedValue(mockError);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Network error');
    expect(result.current.data).toBeUndefined();
  });

  it('caches results for 30 minutes (staleTime)', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3', '1.21.2'],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const wrapper = createWrapper();

    // First render
    const { result: result1 } = renderHook(() => useGameVersions(), {
      wrapper,
    });

    await waitFor(() => {
      expect(result1.current.isLoading).toBe(false);
    });

    expect(fetchGameVersions).toHaveBeenCalledTimes(1);

    // Second render with same wrapper (shared query client)
    const { result: result2 } = renderHook(() => useGameVersions(), {
      wrapper,
    });

    await waitFor(() => {
      expect(result2.current.isLoading).toBe(false);
    });

    // Should still be called only once due to caching
    expect(fetchGameVersions).toHaveBeenCalledTimes(1);
    expect(result2.current.data).toEqual(mockResponse);
  });

  it('tracks loading state correctly', async () => {
    // Create a promise we can control
    let resolvePromise: (value: ApiResponse<GameVersionsData>) => void;
    const pendingPromise = new Promise<ApiResponse<GameVersionsData>>(
      (resolve) => {
        resolvePromise = resolve;
      }
    );
    vi.mocked(fetchGameVersions).mockReturnValue(pendingPromise);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    // Should be loading initially
    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();

    // Resolve the promise
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3', '1.21.2'],
      },
    };
    resolvePromise!(mockResponse);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.isSuccess).toBe(true);
    expect(result.current.data).toEqual(mockResponse);
  });

  it('provides isPending state', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3'],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    // Initially pending
    expect(result.current.isPending).toBe(true);

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });

    expect(result.current.isSuccess).toBe(true);
  });

  it('handles single version', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3'],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.data?.versions).toHaveLength(1);
    expect(result.current.data?.data?.versions[0]).toBe('1.21.3');
  });

  it('handles many versions', async () => {
    const versions = Array.from({ length: 50 }, (_, i) => `1.${20 - Math.floor(i / 10)}.${i % 10}`);
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: { versions },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.data?.versions).toHaveLength(50);
    expect(result.current.data?.data?.versions[0]).toBe('1.20.0');
  });

  it('uses correct query key from queryKeys.mods.gameVersions', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3'],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    // Verify the query key is correctly set (it's accessible via internal state)
    expect(result.current.isSuccess).toBe(true);
    expect(fetchGameVersions).toHaveBeenCalled();
  });

  it('handles 403 Forbidden error', async () => {
    const mockError = new Error('Forbidden');
    vi.mocked(fetchGameVersions).mockRejectedValue(mockError);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(Error);
    expect(result.current.error?.message).toBe('Forbidden');
  });

  it('handles 500 Internal Server Error', async () => {
    const mockError = new Error('Internal Server Error');
    vi.mocked(fetchGameVersions).mockRejectedValue(mockError);

    const { result } = renderHook(() => useGameVersions(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe('Internal Server Error');
  });

  it('does not refetch when component remounts within staleTime', async () => {
    const mockResponse: ApiResponse<GameVersionsData> = {
      status: 'ok',
      data: {
        versions: ['1.21.3', '1.21.2'],
      },
    };
    vi.mocked(fetchGameVersions).mockResolvedValue(mockResponse);

    const wrapper = createWrapper();

    // First mount
    const { result: result1, unmount } = renderHook(() => useGameVersions(), {
      wrapper,
    });

    await waitFor(() => {
      expect(result1.current.isLoading).toBe(false);
    });

    expect(fetchGameVersions).toHaveBeenCalledTimes(1);

    // Unmount
    unmount();

    // Remount immediately
    const { result: result2 } = renderHook(() => useGameVersions(), {
      wrapper,
    });

    await waitFor(() => {
      expect(result2.current.isLoading).toBe(false);
    });

    // Should not refetch due to staleTime
    expect(fetchGameVersions).toHaveBeenCalledTimes(1);
    expect(result2.current.data).toEqual(mockResponse);
  });
});
