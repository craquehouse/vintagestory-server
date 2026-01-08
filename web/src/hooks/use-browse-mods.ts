/**
 * Hook for fetching and filtering browsable mods.
 *
 * Combines server-side pagination/sorting with client-side search filtering.
 * Uses TanStack Query for caching and state management.
 */

import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchBrowseMods } from '@/api/mods';
import type { BrowseParams, ModBrowseItem, ModFilters } from '@/api/types';

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
  // Separate search and filters from API params (both are client-side)
  const { search, filters, ...apiParams } = params;

  const query = useQuery({
    queryKey: queryKeys.mods.browse(apiParams),
    queryFn: () => fetchBrowseMods(apiParams),
    staleTime: BROWSE_STALE_TIME,
  });

  // Client-side filtering pipeline
  const allMods = query.data?.data?.mods ?? [];
  const searchFiltered = filterModsBySearch(allMods, search);
  const fullyFiltered = filterModsByFilters(searchFiltered, filters);

  return {
    ...query,
    mods: fullyFiltered,
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

/**
 * Filter mods by filter criteria.
 *
 * Applies AND logic across different filter types:
 * - Must match side if specified
 * - Must match at least one tag if tags specified (OR logic within tags)
 * - Must match modType if specified
 * - Must be compatible with gameVersion if specified
 *
 * @param mods - Array of mods to filter
 * @param filters - Filter criteria
 * @returns Filtered array of mods
 */
export function filterModsByFilters(
  mods: ModBrowseItem[],
  filters?: ModFilters
): ModBrowseItem[] {
  if (!filters) return mods;

  return mods.filter((mod) => {
    // Side filter (exact match)
    if (filters.side && mod.side !== filters.side) {
      return false;
    }

    // Tags filter (OR logic - mod must have at least one selected tag)
    if (filters.tags && filters.tags.length > 0) {
      const hasMatchingTag = filters.tags.some((filterTag) =>
        mod.tags.some((modTag) => modTag.toLowerCase() === filterTag.toLowerCase())
      );
      if (!hasMatchingTag) {
        return false;
      }
    }

    // ModType filter (exact match)
    if (filters.modType && mod.modType !== filters.modType) {
      return false;
    }

    // Game version filter (compatibility check)
    // Check if lastReleased matches version prefix (major.minor)
    if (filters.gameVersion && mod.lastReleased) {
      const majorMinor = filters.gameVersion.split('.').slice(0, 2).join('.');
      if (!mod.lastReleased.startsWith(majorMinor)) {
        return false;
      }
    }

    // If gameVersion filter is set but mod has no lastReleased, exclude it
    if (filters.gameVersion && !mod.lastReleased) {
      return false;
    }

    return true;
  });
}
