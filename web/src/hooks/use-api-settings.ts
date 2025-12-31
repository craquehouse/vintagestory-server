/**
 * Hooks for API settings management using TanStack Query.
 *
 * Provides queries for fetching API settings and mutations for updates.
 * Includes optimistic updates and proper cache invalidation.
 *
 * Story 6.4: Settings UI
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchApiSettings, updateApiSetting } from '@/api/config';
import type { ApiResponse, ApiSettingsData } from '@/api/types';

/**
 * Default polling interval for API settings (60 seconds).
 * Settings change infrequently, so a longer interval is appropriate.
 */
const API_SETTINGS_POLL_INTERVAL = 60000;

/**
 * Hook to fetch and poll API settings.
 *
 * Polls every 60 seconds to keep data fresh.
 * Returns settings object with all API operational settings.
 *
 * @example
 * function SettingsPanel() {
 *   const { data, isLoading, error } = useApiSettings();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <div>
 *       Auto-start: {data.data.settings.autoStartServer ? 'Yes' : 'No'}
 *     </div>
 *   );
 * }
 */
export function useApiSettings() {
  return useQuery({
    queryKey: queryKeys.config.api,
    queryFn: fetchApiSettings,
    refetchInterval: API_SETTINGS_POLL_INTERVAL,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to update an API setting.
 *
 * Includes optimistic updates and proper rollback on error.
 * Invalidates the API settings query on success.
 *
 * @example
 * function AutoStartToggle() {
 *   const { data } = useApiSettings();
 *   const { mutate: update, isPending } = useUpdateApiSetting();
 *
 *   const handleToggle = () => {
 *     update({
 *       key: 'auto_start_server',
 *       value: !data?.data.settings.autoStartServer
 *     });
 *   };
 *
 *   return (
 *     <button onClick={handleToggle} disabled={isPending}>
 *       {data?.data.settings.autoStartServer ? 'Disable' : 'Enable'}
 *     </button>
 *   );
 * }
 */
export function useUpdateApiSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string | number | boolean }) =>
      updateApiSetting(key, value),
    onMutate: async ({ key, value }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.config.api });

      // Snapshot the previous value
      const previous = queryClient.getQueryData<ApiResponse<ApiSettingsData>>(
        queryKeys.config.api
      );

      // Optimistically update to the new value
      if (previous) {
        // Map API key (snake_case) to camelCase settings key
        const camelKey = key.replace(/_([a-z])/g, (_, c: string) => c.toUpperCase());

        queryClient.setQueryData<ApiResponse<ApiSettingsData>>(
          queryKeys.config.api,
          {
            ...previous,
            data: {
              ...previous.data,
              settings: {
                ...previous.data.settings,
                [camelKey]: value,
              },
            },
          }
        );
      }

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Rollback to previous state on error
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.config.api, context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure server state
      queryClient.invalidateQueries({ queryKey: queryKeys.config.api });
    },
  });
}
