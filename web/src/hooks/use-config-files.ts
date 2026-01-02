/**
 * Hooks for config file management using TanStack Query.
 *
 * Provides queries for fetching config file list and content.
 *
 * Story 6.6: File Manager UI
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchConfigFiles, fetchConfigFileContent } from '@/api/config';

/**
 * Hook to fetch the list of available configuration files.
 *
 * @example
 * function FileList() {
 *   const { data, isLoading, error } = useConfigFiles();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <ul>
 *       {data?.data.files.map(file => (
 *         <li key={file}>{file}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 */
export function useConfigFiles() {
  return useQuery({
    queryKey: queryKeys.config.files,
    queryFn: fetchConfigFiles,
  });
}

/**
 * Hook to fetch the content of a specific configuration file.
 *
 * Only fetches when a filename is provided (enabled when filename is non-null).
 *
 * @param filename - Name of the config file to fetch, or null to disable query
 *
 * @example
 * function FileViewer({ filename }: { filename: string | null }) {
 *   const { data, isLoading, error } = useConfigFileContent(filename);
 *
 *   if (!filename) return <div>Select a file</div>;
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <pre>{JSON.stringify(data?.data.content, null, 2)}</pre>
 *   );
 * }
 */
export function useConfigFileContent(filename: string | null) {
  return useQuery({
    queryKey: queryKeys.config.file(filename ?? ''),
    queryFn: () => fetchConfigFileContent(filename!),
    enabled: !!filename,
  });
}
