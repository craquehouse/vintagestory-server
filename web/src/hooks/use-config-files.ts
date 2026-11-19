/**
 * Hooks for config file management using TanStack Query.
 *
 * Provides queries for fetching config directories, file list, and content.
 *
 * Story 6.6: File Manager UI
 * Story 9.7: Dynamic File Browser
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { useDebounce } from '@/hooks/use-debounce';
import { queryKeys } from '@/api/query-keys';
import {
  checkConfigText,
  fetchConfigDirectories,
  fetchConfigFiles,
  fetchConfigFileContent,
  saveConfigFile,
} from '@/api/config';

/**
 * Hook to fetch the list of directories in serverdata or a subdirectory.
 *
 * @param directory - Directory names from the root (Story 9.7, Story 23.2); `[]` is the root
 *
 * Story 9.7: Dynamic File Browser
 *
 * @example
 * function DirectoryList() {
 *   const { data, isLoading, error } = useConfigDirectories();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (error) return <div>Error: {error.message}</div>;
 *
 *   return (
 *     <ul>
 *       {data?.data.directories.map(dir => (
 *         <li key={dir}>{dir}</li>
 *       ))}
 *     </ul>
 *   );
 * }
 */
export function useConfigDirectories(directory: readonly string[] = []) {
  // The key only identifies the cache entry; the fetch validates the names (Story 23.2)
  const key = directory.join('/');
  return useQuery({
    queryKey: queryKeys.config.directories(key || undefined),
    queryFn: () => fetchConfigDirectories(directory),
  });
}

/**
 * Hook to fetch the list of available configuration files.
 *
 * @param directory - Directory names from the root (Story 9.7, Story 23.2); `[]` is the root
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
export function useConfigFiles(directory: readonly string[] = []) {
  const key = directory.join('/');
  return useQuery({
    queryKey: queryKeys.config.files(key || undefined),
    queryFn: () => fetchConfigFiles(directory),
  });
}

/**
 * Hook to fetch the content of a specific configuration file.
 *
 * Only fetches when a filename is provided (enabled when filename is non-null).
 *
 * @param path - Directory names then the file name (Story 23.2), or null to disable the query
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
export function useConfigFileContent(path: readonly string[] | null) {
  return useQuery({
    queryKey: queryKeys.config.file(path ? path.join('/') : ''),
    queryFn: () => fetchConfigFileContent(path ?? []),
    enabled: path !== null && path.length > 0,
  });
}

/** Variables of a config file save. */
export interface SaveConfigFileVariables {
  path: readonly string[];
  text: string;
  version: string;
}

/**
 * Save a config file's text (Story 23.5); on success the file's read is refetched.
 */
export function useSaveConfigFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ path, text, version }: SaveConfigFileVariables) =>
      saveConfigFile(path, text, version),
    onSuccess: (_data, { path }) =>
      queryClient.invalidateQueries({ queryKey: queryKeys.config.file(path.join('/')) }),
  });
}

/** How long typing must pause before the text is checked (Epic 23 ADR-5 decision 4). */
export const CONFIG_TEXT_CHECK_DELAY_MS = 500;

/**
 * Check a text against the file's parser rule after typing pauses (Story 23.5).
 *
 * `isPending` is true while the debounced text lags behind `text` or the check runs, so
 * a Save button can wait for the check of the text it would send.
 */
export function useConfigTextCheck(path: readonly string[] | null, text: string, enabled: boolean) {
  const debounced = useDebounce(text, CONFIG_TEXT_CHECK_DELAY_MS);
  const key = path ? path.join('/') : '';
  const query = useQuery({
    queryKey: ['config', 'files', 'check', key, debounced] as const,
    queryFn: () => checkConfigText(path ?? [], debounced),
    enabled: enabled && path !== null && path.length > 0,
    staleTime: Infinity,
    retry: false,
  });
  const lagging = debounced !== text;
  return {
    check: lagging ? undefined : query.data,
    isPending: enabled && (lagging || query.isFetching || query.data === undefined),
    error: query.error,
  };
}
