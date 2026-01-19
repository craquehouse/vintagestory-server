/**
 * Hooks for debug logging status using TanStack Query.
 *
 * Provides queries for fetching debug status and mutations for toggling.
 * Includes optimistic updates and proper cache invalidation.
 *
 * VSS-c9o: Debug logging toggle UI
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchDebugStatus, enableDebug, disableDebug } from '@/api/debug';
import type { ApiResponse, DebugStatusData } from '@/api/types';

/**
 * Default polling interval for debug status (60 seconds).
 * Aligned with API settings polling interval for consistency.
 */
const DEBUG_STATUS_POLL_INTERVAL = 60000;

/**
 * Hook to fetch and poll debug logging status.
 *
 * Polls every 30 seconds to keep data fresh.
 * Returns current debug_enabled state.
 *
 * @example
 * function DebugToggle() {
 *   const { data, isLoading } = useDebugStatus();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *
 *   return (
 *     <div>Debug: {data?.data?.debugEnabled ? 'On' : 'Off'}</div>
 *   );
 * }
 */
export function useDebugStatus() {
  return useQuery({
    queryKey: queryKeys.debug.status,
    queryFn: fetchDebugStatus,
    staleTime: 30000, // Consider data fresh for 30s to prevent refetch on navigation
    refetchInterval: DEBUG_STATUS_POLL_INTERVAL,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to toggle debug logging status.
 *
 * Provides a single mutation that enables or disables debug logging
 * based on the `enabled` parameter.
 *
 * Includes optimistic updates and proper rollback on error.
 * Invalidates the debug status query on success.
 *
 * @example
 * function DebugSwitch() {
 *   const { data } = useDebugStatus();
 *   const { mutate: toggle, isPending } = useToggleDebug();
 *
 *   const handleToggle = () => {
 *     toggle({ enabled: !data?.data?.debugEnabled });
 *   };
 *
 *   return (
 *     <button onClick={handleToggle} disabled={isPending}>
 *       {data?.data?.debugEnabled ? 'Disable' : 'Enable'} Debug
 *     </button>
 *   );
 * }
 */
export function useToggleDebug() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ enabled }: { enabled: boolean }) =>
      enabled ? enableDebug() : disableDebug(),
    onMutate: async ({ enabled }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.debug.status });

      // Snapshot the previous value
      const previous = queryClient.getQueryData<ApiResponse<DebugStatusData>>(
        queryKeys.debug.status
      );

      // Optimistically update to the new value (even if no previous data)
      queryClient.setQueryData<ApiResponse<DebugStatusData>>(
        queryKeys.debug.status,
        {
          status: 'ok',
          data: {
            debugEnabled: enabled,
          },
        }
      );

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Rollback to previous state on error
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.debug.status, context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure server state
      queryClient.invalidateQueries({ queryKey: queryKeys.debug.status });
    },
  });
}
