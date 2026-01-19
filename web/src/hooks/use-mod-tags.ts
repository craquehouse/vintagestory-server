/**
 * Hook for fetching available mod tags for filtering.
 *
 * VSS-y7u: Server-side filtering for mod browser.
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchModTags } from '@/api/mods';

/**
 * Cache time for mod tags (30 minutes).
 * Tags rarely change, so we can cache aggressively.
 */
const TAGS_STALE_TIME = 30 * 60 * 1000;

/**
 * Hook to fetch available mod tags for filtering.
 *
 * Returns a list of all unique tags across all mods, sorted alphabetically.
 * Results are cached for 30 minutes since tags rarely change.
 *
 * @example
 * function TagFilter() {
 *   const { data, isLoading } = useModTags();
 *
 *   if (isLoading) return <div>Loading...</div>;
 *
 *   return (
 *     <select>
 *       {data?.data?.tags.map(tag => (
 *         <option key={tag} value={tag}>{tag}</option>
 *       ))}
 *     </select>
 *   );
 * }
 */
export function useModTags() {
  return useQuery({
    queryKey: queryKeys.mods.tags,
    queryFn: fetchModTags,
    staleTime: TAGS_STALE_TIME,
  });
}
