import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React from 'react';
import { useDebugStatus, useToggleDebug } from './use-debug';
import type { ApiResponse, DebugStatusData, DebugToggleData } from '@/api/types';

// Mock the debug API functions
vi.mock('@/api/debug', () => ({
  fetchDebugStatus: vi.fn(),
  enableDebug: vi.fn(),
  disableDebug: vi.fn(),
}));

import { fetchDebugStatus, enableDebug, disableDebug } from '@/api/debug';

// Helper to create a wrapper with QueryClientProvider
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
      mutations: {
        retry: false,
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

describe('useDebugStatus', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('fetches debug status on mount', async () => {
    const mockResponse: ApiResponse<DebugStatusData> = {
      status: 'ok',
      data: { debugEnabled: false },
    };
    vi.mocked(fetchDebugStatus).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useDebugStatus(), {
      wrapper: createWrapper(),
    });

    // Initially loading
    expect(result.current.isLoading).toBe(true);

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(fetchDebugStatus).toHaveBeenCalled();
    expect(result.current.data).toEqual(mockResponse);
  });

  it('returns debug enabled state', async () => {
    const mockResponse: ApiResponse<DebugStatusData> = {
      status: 'ok',
      data: { debugEnabled: true },
    };
    vi.mocked(fetchDebugStatus).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useDebugStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isLoading).toBe(false);
    });

    expect(result.current.data?.data?.debugEnabled).toBe(true);
  });

  it('handles fetch errors', async () => {
    vi.mocked(fetchDebugStatus).mockRejectedValue(new Error('Forbidden'));

    const { result } = renderHook(() => useDebugStatus(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(Error);
  });
});

describe('useToggleDebug', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('calls enableDebug when enabled=true', async () => {
    const mockResponse: ApiResponse<DebugToggleData> = {
      status: 'ok',
      data: { debugEnabled: true, changed: true },
    };
    vi.mocked(enableDebug).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useToggleDebug(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ enabled: true });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(enableDebug).toHaveBeenCalled();
    expect(disableDebug).not.toHaveBeenCalled();
  });

  it('calls disableDebug when enabled=false', async () => {
    const mockResponse: ApiResponse<DebugToggleData> = {
      status: 'ok',
      data: { debugEnabled: false, changed: true },
    };
    vi.mocked(disableDebug).mockResolvedValue(mockResponse);

    const { result } = renderHook(() => useToggleDebug(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ enabled: false });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(disableDebug).toHaveBeenCalled();
    expect(enableDebug).not.toHaveBeenCalled();
  });

  it('handles mutation errors', async () => {
    vi.mocked(enableDebug).mockRejectedValue(new Error('Server error'));

    const { result } = renderHook(() => useToggleDebug(), {
      wrapper: createWrapper(),
    });

    result.current.mutate({ enabled: true });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error).toBeInstanceOf(Error);
  });

  it('tracks pending state during mutation', async () => {
    // Create a promise we can control
    let resolvePromise: (value: ApiResponse<DebugToggleData>) => void;
    const pendingPromise = new Promise<ApiResponse<DebugToggleData>>(
      (resolve) => {
        resolvePromise = resolve;
      }
    );
    vi.mocked(enableDebug).mockReturnValue(pendingPromise);

    const { result } = renderHook(() => useToggleDebug(), {
      wrapper: createWrapper(),
    });

    expect(result.current.isPending).toBe(false);

    result.current.mutate({ enabled: true });

    await waitFor(() => {
      expect(result.current.isPending).toBe(true);
    });

    // Resolve the promise
    resolvePromise!({
      status: 'ok',
      data: { debugEnabled: true, changed: true },
    });

    await waitFor(() => {
      expect(result.current.isPending).toBe(false);
    });
  });
});
