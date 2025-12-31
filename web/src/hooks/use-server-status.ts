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
    }

    // Update the ref for next render
    previousStateRef.current = currentState;
  }, [currentState]);
}
