/**
 * Hooks for game configuration management using TanStack Query.
 *
 * Provides queries for fetching game settings and mutations for updates.
 * Includes optimistic updates and proper cache invalidation.
 *
 * Story 6.4: Settings UI
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchGameConfig, updateGameSetting } from '@/api/config';
import type { ApiResponse, GameConfigData, GameSetting } from '@/api/types';

/**
 * Default polling interval for game config (30 seconds).
 * Less frequent than server status since settings change less often.
 */
const GAME_CONFIG_POLL_INTERVAL = 30000;

/**
 * Hook to fetch and poll game settings.
 *
 * Polls every 30 seconds to keep data fresh.
 * Returns settings array with metadata.
 *
 * @example
 * function SettingsList() {
 *   const { data, isLoading, error } = useGameConfig();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <ul>
 *       {data.data.settings.map(setting => (
 *         <li key={setting.key}>{setting.key}: {setting.value}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 */
export function useGameConfig() {
  return useQuery({
    queryKey: queryKeys.config.game,
    queryFn: fetchGameConfig,
    refetchInterval: GAME_CONFIG_POLL_INTERVAL,
    refetchIntervalInBackground: false,
  });
}

/**
 * Get a specific setting from the game config.
 *
 * @param key - Setting key to find
 * @returns The setting object or undefined if not found
 */
export function useGameSetting(key: string): GameSetting | undefined {
  const { data } = useGameConfig();
  return data?.data?.settings.find((s) => s.key === key);
}

/**
 * Hook to update a game setting.
 *
 * Includes optimistic updates and proper rollback on error.
 * Invalidates the game config query on success.
 *
 * @example
 * function SettingInput({ setting }: { setting: GameSetting }) {
 *   const { mutate: update, isPending } = useUpdateGameSetting();
 *
 *   const handleBlur = (value: string) => {
 *     update({ key: setting.key, value });
 *   };
 *
 *   return (
 *     <input
 *       defaultValue={String(setting.value)}
 *       onBlur={(e) => handleBlur(e.target.value)}
 *       disabled={isPending || setting.envManaged}
 *     />
 *   );
 * }
 */
export function useUpdateGameSetting() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string | number | boolean }) =>
      updateGameSetting(key, value),
    onMutate: async ({ key, value }) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.config.game });

      // Snapshot the previous value
      const previous = queryClient.getQueryData<ApiResponse<GameConfigData>>(
        queryKeys.config.game
      );

      // Optimistically update to the new value
      if (previous) {
        queryClient.setQueryData<ApiResponse<GameConfigData>>(
          queryKeys.config.game,
          {
            ...previous,
            data: {
              ...previous.data,
              settings: previous.data.settings.map((setting) =>
                setting.key === key ? { ...setting, value } : setting
              ),
            },
          }
        );
      }

      return { previous };
    },
    onError: (_err, _vars, context) => {
      // Rollback to previous state on error
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.config.game, context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure server state
      queryClient.invalidateQueries({ queryKey: queryKeys.config.game });
      // Also invalidate mods list in case pending restart changed
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
  });
}

/**
 * Utility to check if any config change requires restart.
 * Checks the mods pending restart status which is shared.
 */
export function useConfigPendingRestart(): boolean {
  // Config changes that require restart share the same pending restart state
  // as mods, so we can reuse the mods query for this check
  const { data } = useQuery({
    queryKey: queryKeys.mods.all,
    enabled: false, // Don't fetch, just read from cache
  });

  // Type assertion since we know the shape from mods types
  const modsData = data as ApiResponse<{ pendingRestart: boolean }> | undefined;
  return modsData?.data?.pendingRestart ?? false;
}
