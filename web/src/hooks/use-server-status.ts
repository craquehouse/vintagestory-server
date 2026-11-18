/**
 * Hooks for server status and lifecycle management.
 *
 * Uses TanStack Query for data fetching with polling support.
 */

import { useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { queryKeys } from '@/api/query-keys';
import {
  fetchServerStatus,
  startServer,
  stopServer,
  restartServer,
  installServer,
  fetchInstallStatus,
  uninstallServer,
} from '@/api/server';
import type { ServerState } from '@/api/types';

/**
 * Default polling interval for server status (5 seconds).
 */
const STATUS_POLL_INTERVAL = 5000;

/**
 * Hook to fetch and poll server status.
 *
 * Polls every 5 seconds to keep status up-to-date.
 * Status is automatically refetched after mutations.
 *
 * @example
 * function Dashboard() {
 *   const { data, isLoading, error } = useServerStatus();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return <ServerStatusBadge state={data.data.state} />;
 * }
 */
export function useServerStatus() {
  return useQuery({
    queryKey: queryKeys.server.status,
    queryFn: fetchServerStatus,
    // Poll every 5 seconds to keep status current
    refetchInterval: STATUS_POLL_INTERVAL,
    // Continue polling even when window is not focused
    refetchIntervalInBackground: false,
  });
}

/**
 * Hook to start the server.
 *
 * Automatically invalidates server status on success.
 *
 * @example
 * function StartButton() {
 *   const { mutate: start, isPending } = useStartServer();
 *
 *   return (
 *     <button onClick={() => start()} disabled={isPending}>
 *       {isPending ? 'Starting...' : 'Start Server'}
 *     </button>
 *   );
 * }
 */
export function useStartServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: startServer,
    onMutate: async () => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.server.status });

      // Snapshot the previous value
      const previousStatus = queryClient.getQueryData(queryKeys.server.status);

      // Optimistically update to 'starting' state
      queryClient.setQueryData(queryKeys.server.status, (old: unknown) => {
        if (old && typeof old === 'object' && 'data' in old) {
          const oldData = old as { data: { state: string } };
          return {
            ...old,
            data: { ...oldData.data, state: 'starting' },
          };
        }
        return old;
      });

      return { previousStatus };
    },
    onError: (_err, _variables, context) => {
      // Roll back on error
      if (context?.previousStatus) {
        queryClient.setQueryData(queryKeys.server.status, context.previousStatus);
      }
    },
    onSettled: () => {
      // Refetch after mutation settles
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
    },
  });
}

/**
 * Hook to stop the server.
 *
 * Automatically invalidates server status on success.
 */
export function useStopServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: stopServer,
    onMutate: async () => {
      // Cancel any outgoing refetches
      await queryClient.cancelQueries({ queryKey: queryKeys.server.status });

      // Snapshot the previous value
      const previousStatus = queryClient.getQueryData(queryKeys.server.status);

      // Optimistically update to 'stopping' state
      queryClient.setQueryData(queryKeys.server.status, (old: unknown) => {
        if (old && typeof old === 'object' && 'data' in old) {
          const oldData = old as { data: { state: string } };
          return {
            ...old,
            data: { ...oldData.data, state: 'stopping' },
          };
        }
        return old;
      });

      return { previousStatus };
    },
    onError: (_err, _variables, context) => {
      // Roll back on error
      if (context?.previousStatus) {
        queryClient.setQueryData(queryKeys.server.status, context.previousStatus);
      }
    },
    onSettled: () => {
      // Refetch after mutation settles
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
    },
  });
}

/**
 * Hook to restart the server.
 *
 * Automatically invalidates server status on success. Errors are not toasted
 * globally; pass `onError` to `mutate` to report them (Story 21.4).
 */
export function useRestartServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: restartServer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
    },
    // The caller reports errors; skip the global toast so they are not shown twice.
    onError: () => {},
  });
}

/**
 * Hook to install a specific server version.
 *
 * Story 13.4: Per ADR-4, invalidates both server status and versions queries
 * on success to ensure UI updates reflect the new installed version.
 * Errors are not toasted globally; pass `onError` to `mutate` to report them (Story 21.4).
 *
 * @param options.onSuccess - Callback when installation starts successfully
 *
 * @example
 * function InstallForm() {
 *   const { mutate: install, isPending } = useInstallServer();
 *
 *   return (
 *     <button onClick={() => install('1.21.3')} disabled={isPending}>
 *       Install
 *     </button>
 *   );
 * }
 */
export function useInstallServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: installServer,
    onSuccess: () => {
      // Invalidate server status to show new installed version
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
      // Story 13.4: Also invalidate versions list to update "Installed" badges
      queryClient.invalidateQueries({ queryKey: ['versions'] });
    },
    // The caller reports errors; skip the global toast so they are not shown twice.
    onError: () => {},
  });
}

/**
 * Hook to fetch installation status.
 *
 * Only enabled when server is in 'installing' state.
 * Polls every 2 seconds during installation.
 *
 * @param enabled - Whether to enable the query (typically when state === 'installing')
 */
export function useInstallStatus(enabled: boolean) {
  return useQuery({
    queryKey: queryKeys.server.installStatus,
    queryFn: fetchInstallStatus,
    enabled,
    // Poll more frequently during installation
    refetchInterval: enabled ? 2000 : false,
  });
}

/**
 * Hook to show toast notifications when server state transitions complete.
 *
 * Detects when the server transitions from a transitional state to a stable state:
 * - `starting` → `running`: Shows "Server started" toast
 * - `stopping` → `installed`: Shows "Server stopped" toast
 * - `installing` → `installed`: Shows "Installation complete" toast (Story 13.4)
 *
 * @param currentState - Current server state from useServerStatus
 */
export function useServerStateToasts(currentState: ServerState | undefined) {
  const previousStateRef = useRef<ServerState | undefined>(undefined);

  useEffect(() => {
    const previousState = previousStateRef.current;

    // Only check for transitions after we have a previous state
    if (previousState && currentState) {
      // Server finished starting
      if (previousState === 'starting' && currentState === 'running') {
        toast.success('Server started', {
          description: 'The server is now running.',
        });
      }

      // Server finished stopping
      if (previousState === 'stopping' && currentState === 'installed') {
        toast.success('Server stopped', {
          description: 'The server has stopped.',
        });
      }

      // Story 13.4: Server finished installing
      if (previousState === 'installing' && currentState === 'installed') {
        toast.success('Installation complete', {
          description: 'The server has been installed successfully.',
        });
      }
    }

    // Update the ref for next render
    previousStateRef.current = currentState;
  }, [currentState]);
}

/**
 * Hook to fetch mod data again when the installed game version changes (Story 21.4).
 *
 * Watches the version the polled server status reports. When it differs from the last
 * one seen (another version, an uninstall, or an install where none was), it
 * invalidates every mod query, so the browse cards, the installed list and the mod
 * detail pages describe the new version. The trigger is the status, not the install
 * request, which answers when the installation has only started.
 *
 * - Until the status has loaded, nothing is remembered; the first loaded value, a
 *   version or `null` (no server), is remembered and invalidates nothing.
 * - A failed poll keeps the last data, so the version does not change.
 * - `['mods']` does not cover the status query, so an invalidation cannot change this
 *   hook's input and cause another one.
 *
 * Call it once, in the layout.
 */
export function useRefreshModDataOnGameVersionChange(): void {
  const queryClient = useQueryClient();
  const { data } = useServerStatus();
  const isLoaded = data?.data !== undefined;
  const version = data?.data?.version ?? null;
  // null until the first status has loaded; then the version seen last
  const lastVersionRef = useRef<{ version: string | null } | null>(null);

  useEffect(() => {
    if (!isLoaded) return;
    const last = lastVersionRef.current;
    lastVersionRef.current = { version };
    if (last !== null && last.version !== version) {
      queryClient.invalidateQueries({ queryKey: queryKeys.mods.all });
    }
  }, [isLoaded, version, queryClient]);
}

/**
 * Hook to uninstall the server.
 *
 * Story 13.7: Removes server binaries while preserving config/mods/worlds.
 * Per ADR-4, invalidates both server status and versions queries on success
 * to ensure UI updates reflect the uninstalled state. Errors are not toasted globally;
 * pass `onError` to `mutate` to report them (Story 21.4).
 *
 * @example
 * function RemoveButton() {
 *   const { mutate: uninstall, isPending } = useUninstallServer();
 *
 *   return (
 *     <button onClick={() => uninstall()} disabled={isPending}>
 *       {isPending ? 'Removing...' : 'Remove Server'}
 *     </button>
 *   );
 * }
 */
export function useUninstallServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: uninstallServer,
    onSuccess: () => {
      // Invalidate server status to show not_installed state
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
      // Story 13.7: Also invalidate versions list to update "Installed" badges
      queryClient.invalidateQueries({ queryKey: ['versions'] });
    },
    // The caller reports errors; skip the global toast so they are not shown twice.
    onError: () => {},
  });
}
