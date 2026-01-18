/**
 * Hooks for metrics data fetching.
 *
 * Story 12.4: Dashboard Stats Cards
 *
 * Uses TanStack Query for data fetching with polling support.
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { apiClient } from '@/api/client';
import type { ApiResponse, MetricsSnapshot, MetricsHistoryResponse } from '@/api/types';

/**
 * Polling interval for metrics (10 seconds).
 * Matches the metrics collection interval on the backend.
 */
const METRICS_POLL_INTERVAL = 10000;

/**
 * Hook to fetch and poll current metrics.
 *
 * Polls every 10 seconds to keep metrics up-to-date (AC: 2).
 * Returns null for data if no metrics have been collected yet.
 * Game metrics (gameMemoryMb, gameCpuPercent) are null when server is not running (AC: 4).
 *
 * @example
 * function MemoryCard() {
 *   const { data, isLoading, error } = useCurrentMetrics();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *   if (!data?.data) return <div>No metrics yet</div>;
 *
 *   return (
 *     <div>
 *       <p>API: {data.data.apiMemoryMb} MB</p>
 *       <p>Game: {data.data.gameMemoryMb ?? 'N/A'} MB</p>
 *     </div>
 *   );
 * }
 */
export function useCurrentMetrics() {
  return useQuery({
    queryKey: queryKeys.metrics.current,
    queryFn: async () => {
      const response = await apiClient<ApiResponse<MetricsSnapshot | null>>(
        '/api/v1alpha1/metrics/current'
      );
      return response;
    },
    // Poll every 10 seconds (matches collection interval)
    refetchInterval: METRICS_POLL_INTERVAL,
    // Stop polling when window is not focused to save resources
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to fetch historical metrics.
 *
 * Used for time-series charts (Story 12.5).
 * Optional minutes parameter filters to recent metrics.
 *
 * @param minutes - Optional time filter in minutes (1-1440)
 *
 * @example
 * function MetricsChart() {
 *   // Get last 30 minutes of metrics
 *   const { data, isLoading } = useMetricsHistory(30);
 *
 *   if (isLoading) return <div>Loading...</div>;
 *
 *   return <Chart data={data?.data?.metrics ?? []} />;
 * }
 */
export function useMetricsHistory(minutes?: number) {
  return useQuery({
    queryKey: queryKeys.metrics.history(minutes),
    queryFn: async () => {
      const params = minutes !== undefined ? `?minutes=${minutes}` : '';
      const response = await apiClient<ApiResponse<MetricsHistoryResponse>>(
        `/api/v1alpha1/metrics/history${params}`
      );
      return response;
    },
    // No automatic polling for history - charts will refetch on demand
  });
}
