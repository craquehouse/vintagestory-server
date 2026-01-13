/**
 * Hooks for version management using TanStack Query.
 *
 * Story 13.2: Version Card Component
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

/**
 * Options for the useVersions hook.
 */
export interface UseVersionsOptions {
  /** Filter by channel (stable/unstable) */
  channel?: VersionChannel;
  /** Whether the query is enabled */
  enabled?: boolean;
}

/**
 * Hook to fetch available server versions.
 *
 * Story 13.2: Version Card Component
 *
 * @param options - Query options including optional channel filter
 * @returns TanStack Query result with versions list
 *
 * @example
 * ```tsx
 * function VersionList() {
 *   const { data, isLoading, error } = useVersions();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <ul>
 *       {data.data.versions.map(v => (
 *         <li key={v.version}>{v.version} ({v.channel})</li>
 *       ))}
 *     </ul>
 *   );
 * }
 * ```
 *
 * @example
 * ```tsx
 * // Filter by channel
 * const { data } = useVersions({ channel: 'stable' });
 * ```
 */
export function useVersions(options: UseVersionsOptions = {}) {
  const { channel, enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.versions.list(channel),
    queryFn: async () => {
      const params = channel ? `?channel=${channel}` : '';
      const response = await apiClient<ApiResponse<VersionListResponse>>(
        `/api/v1alpha1/versions${params}`
      );
      return response;
    },
    enabled,
    // Version data doesn't change frequently, cache for 5 minutes
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Options for the useVersionDetail hook.
 */
export interface UseVersionDetailOptions {
  /** Whether the query is enabled */
  enabled?: boolean;
}

/**
 * Hook to fetch details for a specific version.
 *
 * Story 13.2: Version Card Component
 *
 * @param version - Version string to fetch details for
 * @param options - Query options
 * @returns TanStack Query result with version details
 *
 * @example
 * ```tsx
 * function VersionDetail({ version }: { version: string }) {
 *   const { data, isLoading } = useVersionDetail(version);
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (!data) return null;
 *
 *   return <div>{data.data.version.version} - {data.data.version.filesize}</div>;
 * }
 * ```
 */
export function useVersionDetail(
  version: string,
  options: UseVersionDetailOptions = {}
) {
  const { enabled = true } = options;

  return useQuery({
    queryKey: queryKeys.versions.detail(version),
    queryFn: async () => {
      const response = await apiClient<ApiResponse<VersionDetailResponse>>(
        `/api/v1alpha1/versions/${encodeURIComponent(version)}`
      );
      return response;
    },
    enabled: enabled && !!version,
    // Version details don't change, cache for longer
    staleTime: 10 * 60 * 1000,
  });
}
