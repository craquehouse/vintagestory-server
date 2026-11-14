/**
 * Hooks for mod management using TanStack Query.
 *
 * Provides queries for fetching mod data and mutations for mod operations.
 * All mutations include optimistic updates and proper cache invalidation.
 */

import { useQuery, useQueries, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { ApiError } from '@/api/errors';
import {
  fetchMods,
  lookupMod,
  installMod,
  enableMod,
  disableMod,
  removeMod,
  fetchModUpdates,
  checkModUpdates,
  changeModVersion,
  applyAllModUpdates,
} from '@/api/mods';
import type {
  ApiResponse,
  ModsListData,
  CompatibilityStatus,
  ModCompatibility,
  ModSide,
} from '@/api/types';

/**
 * Default polling interval for mods list (10 seconds).
 * Less frequent than server status since mods change less often.
 */
const MODS_POLL_INTERVAL = 10000;

/**
 * Hook to fetch and poll installed mods list.
 *
 * Polls every 10 seconds to keep data fresh.
 * Returns mods array and pending restart status.
 *
 * @example
 * function ModList() {
 *   const { data, isLoading, error } = useMods();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <ul>
 *       {data.data.mods.map(mod => (
 *         <li key={mod.slug}>{mod.name}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 */
export function useMods() {
  return useQuery({
    queryKey: queryKeys.mods.all,
    queryFn: fetchMods,
    refetchInterval: MODS_POLL_INTERVAL,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to look up mod details from the VintageStory mod database.
 *
 * Only fetches when slug is non-empty.
 * Uses staleTime to avoid refetching the same mod repeatedly.
 *
 * @param slug - Mod slug or URL to look up (empty string disables query)
 *
 * @example
 * function ModSearch() {
 *   const [slug, setSlug] = useState('');
 *   const { data, isLoading, error } = useLookupMod(slug);
 *
 *   return (
 *     <>
 *       <input value={slug} onChange={e => setSlug(e.target.value)} />
 *       {data && <div>{data.data.name}</div>}
 *     </>
 *   );
 * }
 */
export function useLookupMod(slug: string | null) {
  return useQuery({
    queryKey: queryKeys.mods.lookup(slug ?? ''),
    queryFn: () => lookupMod(slug!),
    // Only fetch when slug is non-empty
    enabled: !!slug?.trim(),
    // Keep lookup results fresh for 5 minutes
    staleTime: 5 * 60 * 1000,
  });
}

/**
 * Hook to install a mod.
 *
 * Invalidates mods list on success.
 *
 * @example
 * function InstallButton({ slug }: { slug: string }) {
 *   const { mutate: install, isPending } = useInstallMod();
 *
 *   return (
 *     <button
 *       onClick={() => install({ slug })}
 *       disabled={isPending}
 *     >
 *       {isPending ? 'Installing...' : 'Install'}
 *     </button>
 *   );
 * }
 */
export function useInstallMod() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({ slug, version }: { slug: string; version?: string }) =>
      installMod(slug, version),
    onSuccess: () => {
      // Refetch mods list to include the new mod
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
  });
}

/**
 * Hook to enable a mod.
 *
 * Includes optimistic updates and proper rollback on error.
 *
 * @example
 * function EnableToggle({ slug, enabled }: { slug: string; enabled: boolean }) {
 *   const { mutate: enable, isPending } = useEnableMod();
 *
 *   return (
 *     <button onClick={() => enable(slug)} disabled={isPending || enabled}>
 *       Enable
 *     </button>
 *   );
 * }
 */
export function useEnableMod() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => enableMod(slug),
    onMutate: async (slug) => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.mods.all });

      // Snapshot the previous value
      const previous = queryClient.getQueryData<ApiResponse<ModsListData>>(
        queryKeys.mods.all
      );

      // Optimistically update to the new value
      if (previous) {
        queryClient.setQueryData<ApiResponse<ModsListData>>(
          queryKeys.mods.all,
          {
            ...previous,
            data: {
              ...previous.data,
              pendingRestart: true,
              mods: previous.data.mods.map((mod) =>
                mod.slug === slug ? { ...mod, enabled: true } : mod
              ),
            },
          }
        );
      }

      return { previous };
    },
    onError: (_err, _slug, context) => {
      // Rollback to previous state on error
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.mods.all, context.previous);
      }
    },
    onSettled: () => {
      // Always refetch after error or success to ensure server state
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
  });
}

/**
 * Hook to disable a mod.
 *
 * Includes optimistic updates and proper rollback on error.
 */
export function useDisableMod() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => disableMod(slug),
    onMutate: async (slug) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.mods.all });

      const previous = queryClient.getQueryData<ApiResponse<ModsListData>>(
        queryKeys.mods.all
      );

      if (previous) {
        queryClient.setQueryData<ApiResponse<ModsListData>>(
          queryKeys.mods.all,
          {
            ...previous,
            data: {
              ...previous.data,
              pendingRestart: true,
              mods: previous.data.mods.map((mod) =>
                mod.slug === slug ? { ...mod, enabled: false } : mod
              ),
            },
          }
        );
      }

      return { previous };
    },
    onError: (_err, _slug, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.mods.all, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
  });
}

/**
 * Hook to remove a mod.
 *
 * Includes optimistic updates and proper rollback on error.
 */
export function useRemoveMod() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (slug: string) => removeMod(slug),
    onMutate: async (slug) => {
      await queryClient.cancelQueries({ queryKey: queryKeys.mods.all });

      const previous = queryClient.getQueryData<ApiResponse<ModsListData>>(
        queryKeys.mods.all
      );

      if (previous) {
        queryClient.setQueryData<ApiResponse<ModsListData>>(
          queryKeys.mods.all,
          {
            ...previous,
            data: {
              ...previous.data,
              pendingRestart: true,
              mods: previous.data.mods.filter((mod) => mod.slug !== slug),
            },
          }
        );
      }

      return { previous };
    },
    onError: (_err, _slug, context) => {
      if (context?.previous) {
        queryClient.setQueryData(queryKeys.mods.all, context.previous);
      }
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
  });
}

/**
 * Utility to get pending restart status from mods query.
 * Useful for components that need to know if a restart is required.
 */
export function useModsPendingRestart() {
  const { data } = useMods();
  return data?.data?.pendingRestart ?? false;
}

/**
 * Hook to fetch compatibility status for multiple installed mods.
 *
 * Uses parallel queries to fetch mod details for each installed mod, extracting
 * compatibility status. Results are cached with a 5-minute stale time.
 *
 * VSS-j3c: Fixes false "not verified" status on installed mods page.
 * Story 16.3: each lookup passes the installed version, so compatibility describes
 * the installed release rather than the newest one.
 *
 * @param mods - Installed mods (slug and installed version) to look up
 * @returns Map of slug -> CompatibilityStatus, slug -> full compatibility details
 *   (message, latest supported game version), plus loading state
 *
 * @example
 * function ModTable() {
 *   const { data: modsData } = useMods();
 *   const mods = modsData?.data?.mods ?? [];
 *
 *   const { compatibilityMap, isLoading } = useModsCompatibility(mods);
 *
 *   return mods.map(mod => (
 *     <CompatibilityBadge
 *       status={compatibilityMap.get(mod.slug) ?? 'not_verified'}
 *       loading={isLoading}
 *     />
 *   ));
 * }
 */
export function useModsCompatibility(mods: readonly { slug: string; version: string }[]) {
  const queries = useQueries({
    queries: mods.map(({ slug, version }) => ({
      queryKey: queryKeys.mods.lookup(slug, version),
      queryFn: () => lookupMod(slug, version),
      // Keep results fresh for 5 minutes
      staleTime: 5 * 60 * 1000,
      // Don't refetch on window focus
      refetchOnWindowFocus: false,
      // Allow individual failures without failing all queries
      retry: 1,
    })),
  });

  // Build maps of slug -> compatibility status/details and slug -> side
  const compatibilityMap = new Map<string, CompatibilityStatus>();
  const compatibilityDetails = new Map<string, ModCompatibility>();
  const sideMap = new Map<string, ModSide>();

  queries.forEach((query, index) => {
    const slug = mods[index].slug;
    const compatibility = query.data?.data?.compatibility;
    if (compatibility?.status) {
      compatibilityMap.set(slug, compatibility.status);
      compatibilityDetails.set(slug, compatibility);
    }
    if (query.data?.data?.side) {
      sideMap.set(slug, query.data.data.side);
    }
    // If query failed or no data, we don't add to map (caller can fallback)
  });

  // Consider loading if any query is still loading
  const isLoading = queries.some((q) => q.isLoading);

  // Consider all fetched if all queries have either data or error
  const isAllFetched = queries.every((q) => q.isFetched);

  return {
    compatibilityMap,
    compatibilityDetails,
    sideMap,
    isLoading,
    isAllFetched,
    queries, // Expose raw queries for advanced usage
  };
}

/**
 * Polling interval for mod update status (60 seconds).
 * The endpoint reads stored check data; it changes only after a check or version change.
 */
const MOD_UPDATES_POLL_INTERVAL = 60000;

/**
 * Hook to fetch update status for installed mods (Story 14.3).
 */
export function useModUpdates() {
  return useQuery({
    queryKey: queryKeys.mods.updateStatus,
    queryFn: fetchModUpdates,
    refetchInterval: MOD_UPDATES_POLL_INTERVAL,
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to run an update check against the mod database (Admin).
 *
 * Invalidates the update status when it settles.
 * Errors are not toasted globally; pass `onError` to `mutate` to report them.
 */
export function useCheckModUpdates() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => checkModUpdates(),
    // The caller reports errors; skip the global toast so they are not shown twice.
    onError: () => {},
    // A check changes only the stored update data.
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.updateStatus });
    },
  });
}

/**
 * Hook to update, roll back or switch an installed mod's version (Admin).
 *
 * A risky change rejects with ApiError code MOD_CONFIRMATION_REQUIRED and
 * `details.reasons`; call again with `confirm: true` after the user agrees.
 * Errors are not toasted globally; useVersionChangeFlow reports them.
 */
export function useChangeModVersion() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: ({
      slug,
      version,
      confirm = false,
    }: {
      slug: string;
      version: string;
      confirm?: boolean;
    }) => changeModVersion(slug, version, confirm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
    // The caller reports errors, so skip the global toast. A confirmation request
    // (409) changed nothing; after any other failure, refetch to show server state.
    onError: (error) => {
      if (!(error instanceof ApiError && error.code === 'MOD_CONFIRMATION_REQUIRED')) {
        queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
      }
    },
  });
}

/**
 * Hook to apply every compatible update (Admin, Story 14.4).
 *
 * Refetches all mod queries when it settles: some mods may have changed even if the
 * request failed. Errors are not toasted globally; pass `onError` to `mutate`.
 */
export function useApplyAllModUpdates() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: () => applyAllModUpdates(),
    onError: () => {},
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    },
  });
}
