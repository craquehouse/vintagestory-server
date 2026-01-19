import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useGameVersions } from './use-game-versions';
import * as modsApi from '@/api/mods';
import type { ApiResponse, GameVersionsData } from '@/api/types';

// VSS-vth: Tests for useGameVersions hook

vi.mock('@/api/mods');

describe('useGameVersions', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );

  const mockVersionsResponse: ApiResponse<GameVersionsData> = {
    status: 'ok',
    data: {
      versions: ['1.21.3', '1.21.2', '1.21.1', '1.21.0', '1.20.0'],
    },
  };

  it('fetches game versions on mount', async () => {
    vi.mocked(modsApi.fetchGameVersions).mockResolvedValue(mockVersionsResponse);

    const { result } = renderHook(() => useGameVersions(), { wrapper });

    await waitFor(() => {
      expect(result.current.isSuccess).toBe(true);
    });

    expect(modsApi.fetchGameVersions).toHaveBeenCalledTimes(1);
    expect(result.current.data?.data?.versions).toHaveLength(5);
    expect(result.current.data?.data?.versions[0]).toBe('1.21.3');
  });

  it('returns loading state initially', () => {
    vi.mocked(modsApi.fetchGameVersions).mockImplementation(
      () => new Promise(() => {}) // Never resolves
    );

    const { result } = renderHook(() => useGameVersions(), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
  });

  it('handles API errors', async () => {
    vi.mocked(modsApi.fetchGameVersions).mockRejectedValue(
      new Error('API error')
    );

    const { result } = renderHook(() => useGameVersions(), { wrapper });

    await waitFor(() => {
      expect(result.current.isError).toBe(true);
    });

    expect(result.current.error?.message).toBe('API error');
  });
});
