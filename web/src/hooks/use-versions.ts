/**
 * Hooks for version management using TanStack Query.
 *
 * Provides queries for fetching available VintageStory server versions.
 */

import { useQuery } from '@tanstack/react-query';
import { apiClient } from '@/api/client';
import { queryKeys } from '@/api/query-keys';
import type {
  ApiResponse,
  VersionListResponse,
  VersionDetailResponse,
  VersionChannel,
} from '@/api/types';

/** Options for the useVersions hook. */
export interface UseVersionsOptions {
  channel?: VersionChannel;
  enabled?: boolean;
}

/**
 * Hook to fetch available server versions.
 *
 * @param options - Query options including optional channel filter
 * @returns TanStack Query result with versions list
 */
export function useVersions(options: UseVersionsOptions = {}) {
  const { channel, enabled = true } = options;
  const params = channel ? `?channel=${channel}` : '';

  return useQuery({
    queryKey: queryKeys.versions.all(channel),
    queryFn: () =>
      apiClient<ApiResponse<VersionListResponse>>(
        `/api/v1alpha1/versions${params}`
      ),
    enabled,
    staleTime: 5 * 60 * 1000,
  });
}

/** Options for the useVersionDetail hook. */
export interface UseVersionDetailOptions {
  enabled?: boolean;
}

/**
 * Hook to fetch details for a specific version.
 *
 * @param version - Version string to fetch details for
 * @param options - Query options
 * @returns TanStack Query result with version details
 */
export function useVersionDetail(
  version: string,
  options: UseVersionDetailOptions = {}
) {
  const { enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.versions.detail(version),
    queryFn: () =>
      apiClient<ApiResponse<VersionDetailResponse>>(
        `/api/v1alpha1/versions/${encodeURIComponent(version)}`
      ),
    enabled: enabled && !!version,
    staleTime: 10 * 60 * 1000,
  });
}
