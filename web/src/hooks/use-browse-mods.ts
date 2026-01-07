/**
 * Hook for fetching and filtering browsable mods.
 *
 * Combines server-side pagination/sorting with client-side search filtering.
 * Uses TanStack Query for caching and state management.
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchBrowseMods } from '@/api/mods';
import type { BrowseParams, ModBrowseItem } from '@/api/types';

/**
 * Cache time matches the API's 5-minute TTL for mod data.
 */
const BROWSE_STALE_TIME = 5 * 60 * 1000;

/**
 * Hook to fetch and filter browsable mods.
 *
 * Supports server-side pagination/sorting (via API) and client-side search filtering.
 * Search filtering is done client-side because the API doesn't support a search parameter yet.
 *
 * @param params - Browse parameters including page, pageSize, sort, and search
 * @returns Query result with filtered mods array and pagination metadata
 *
 * @example
 * function BrowseList() {
 *   const { mods, pagination, isLoading, isError } = useBrowseMods({
 *     page: 1,
 *     pageSize: 20,
 *     sort: 'recent',
 *     search: 'farming',
 *   });
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (isError) return <div>Error loading mods</div>;
 *
 *   return (
 *     <ul>
 *       {mods.map(mod => <li key={mod.slug}>{mod.name}</li>)}
 *     </ul>
 *   );
 * }
 */
export function useBrowseMods(params: BrowseParams = {}) {
  // Separate search from API params (search is client-side)
  const { search, ...apiParams } = params;

  const query = useQuery({
    queryKey: queryKeys.mods.browse(apiParams),
    queryFn: () => fetchBrowseMods(apiParams),
    staleTime: BROWSE_STALE_TIME,
  });

  // Client-side search filtering
  const allMods = query.data?.data?.mods ?? [];
  const filteredMods = filterModsBySearch(allMods, search);

  return {
    ...query,
    mods: filteredMods,
    pagination: query.data?.data?.pagination,
  };
}

/**
 * Filter mods by search term.
 *
 * Searches across name, author, summary, and tags.
 * Case-insensitive matching.
 *
 * @param mods - Array of mods to filter
 * @param search - Search term (empty or undefined returns all mods)
 * @returns Filtered array of mods
 */
export function filterModsBySearch(
  mods: ModBrowseItem[],
  search?: string
): ModBrowseItem[] {
  if (!search?.trim()) {
    return mods;
  }

  const searchLower = search.toLowerCase();

  return mods.filter((mod) => {
    // Check name
    if (mod.name.toLowerCase().includes(searchLower)) {
      return true;
    }

    // Check author
    if (mod.author.toLowerCase().includes(searchLower)) {
      return true;
    }

    // Check summary (may be null)
    if (mod.summary?.toLowerCase().includes(searchLower)) {
      return true;
    }

    // Check tags
    if (mod.tags.some((tag) => tag.toLowerCase().includes(searchLower))) {
      return true;
    }

    return false;
  });
}
