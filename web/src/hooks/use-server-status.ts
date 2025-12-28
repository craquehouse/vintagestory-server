/**
 * Hooks for server status and lifecycle management.
 *
 * Uses TanStack Query for data fetching with polling support.
 */

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import {
  fetchServerStatus,
  startServer,
  stopServer,
  restartServer,
  installServer,
  fetchInstallStatus,
} from '@/api/server';

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
    onSuccess: () => {
      // Immediately refetch status after starting
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
    },
  });
}

/**
 * Hook to restart the server.
 *
 * Automatically invalidates server status on success.
 */
export function useRestartServer() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: restartServer,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
    },
  });
}

/**
 * Hook to install a specific server version.
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
      queryClient.invalidateQueries({ queryKey: queryKeys.server.status });
    },
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
    queryKey: ['server', 'install', 'status'],
    queryFn: fetchInstallStatus,
    enabled,
    // Poll more frequently during installation
    refetchInterval: enabled ? 2000 : false,
  });
}
