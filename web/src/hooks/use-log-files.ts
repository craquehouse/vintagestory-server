import { useQuery } from '@tanstack/react-query';

import { apiClient } from '@/api/client';
import { queryKeys } from '@/api/query-keys';
import type { ApiResponse, LogFilesData } from '@/api/types';

/**
 * Hook to fetch available log files from the server.
 *
 * Returns the list of log files in the serverdata/Logs directory
 * with file names, sizes, and modification times.
 *
 * @example
 * ```tsx
 * function LogSelector() {
 *   const { data, isLoading } = useLogFiles();
 *
 *   if (isLoading) return <Spinner />;
 *
 *   return (
 *     <select>
 *       {data?.data.files.map(file => (
 *         <option key={file.name} value={file.name}>
 *           {file.name}
 *         </option>
 *       ))}
 *     </select>
 *   );
 * }
 * ```
 */
export function useLogFiles() {
  return useQuery({
    queryKey: queryKeys.console.logs,
    queryFn: () =>
      apiClient<ApiResponse<LogFilesData>>('/api/v1alpha1/console/logs'),
    // Refresh every 30 seconds to pick up new log files
    refetchInterval: 30000,
    // Keep showing stale data while refreshing
    staleTime: 10000,
  });
}
