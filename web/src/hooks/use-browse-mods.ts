/**
 * Hook for fetching and filtering browsable mods.
 *
 * Combines server-side pagination/sorting with client-side search filtering.
 * Uses TanStack Query for caching and state management.
 */

import { useState, useCallback } from 'react';
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
 * Story 10.7: Added pagination state management with setPage, goToNextPage, goToPrevPage.
 *
 * @param params - Browse parameters including page, pageSize, sort, and search
 * @returns Query result with filtered mods array, pagination metadata, and page control functions
 *
 * @example
 * function BrowseList() {
 *   const {
 *     mods,
 *     pagination,
 *     isLoading,
 *     isError,
 *     currentPage,
 *     setPage,
 *     goToNextPage,
 *     goToPrevPage,
 *   } = useBrowseMods({
 *     pageSize: 20,
 *     sort: 'recent',
 *     search: 'farming',
 *   });
 *
 *   if (isLoading) return <div>Loading...</div>;
 *   if (isError) return <div>Error loading mods</div>;
 *
 *   return (
 *     <>
 *       <ul>
 *         {mods.map(mod => <li key={mod.slug}>{mod.name}</li>)}
 *       </ul>
 *       <div>
 *         <button onClick={goToPrevPage} disabled={!pagination?.hasPrev}>Prev</button>
 *         <span>Page {currentPage} of {pagination?.totalPages}</span>
 *         <button onClick={goToNextPage} disabled={!pagination?.hasNext}>Next</button>
 *       </div>
 *     </>
 *   );
 * }
 */
export function useBrowseMods(params: BrowseParams = {}) {
  // Story 10.7: Manage page state internally, with initial value from params
  const [currentPage, setCurrentPage] = useState(params.page ?? 1);

  // Separate search and filters from API params (both are client-side)
  // Also separate 'name' sort since it's client-side only
  const { search, filters, sort, page: _ignoredPage, ...apiParams } = params;

  // Only pass sort to API if it's a server-side option
  const apiSort = sort === 'name' ? undefined : sort;

  const query = useQuery({
    queryKey: queryKeys.mods.browse({ ...apiParams, page: currentPage, sort: apiSort }),
    queryFn: () => fetchBrowseMods({ ...apiParams, page: currentPage, sort: apiSort }),
    staleTime: BROWSE_STALE_TIME,
  });

  // Get pagination from response (if available)
  const pagination = query.data?.data?.pagination;

  // Story 10.7: Page navigation functions
  const setPage = useCallback(
    (page: number) => {
      // Validate page number: must be positive integer within bounds
      if (page < 1) return;
      if (pagination?.totalPages && page > pagination.totalPages) return;
      setCurrentPage(page);
    },
    [pagination?.totalPages]
  );

  const goToNextPage = useCallback(() => {
    setCurrentPage((prev) => {
      if (pagination?.hasNext) {
        return prev + 1;
      }
      return prev;
    });
  }, [pagination?.hasNext]);

  const goToPrevPage = useCallback(() => {
    setCurrentPage((prev) => {
      if (pagination?.hasPrev && prev > 1) {
        return prev - 1;
      }
      return prev;
    });
  }, [pagination?.hasPrev]);

  // Client-side filtering pipeline
  const allMods = query.data?.data?.mods ?? [];
  const searchFiltered = filterModsBySearch(allMods, search);
  const fullyFiltered = filterModsByFilters(searchFiltered, filters);

  // Client-side sorting for 'name' option
  const sorted = sort === 'name'
    ? sortModsByName(fullyFiltered)
    : fullyFiltered;

  return {
    ...query,
    mods: sorted,
    pagination,
    // Story 10.7: Expose page state and navigation functions
    currentPage,
    setPage,
    goToNextPage,
    goToPrevPage,
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
 * Sort mods alphabetically by name (A-Z).
 *
 * Client-side only - API doesn't support name sorting yet.
 *
 * @param mods - Array of mods to sort
 * @returns Sorted array of mods (new array, doesn't mutate input)
 */
export function sortModsByName(mods: ModBrowseItem[]): ModBrowseItem[] {
  return [...mods].sort((a, b) => a.name.localeCompare(b.name));
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

    // Game version filter disabled - API doesn't provide version compatibility in browse endpoint
    // The lastReleased field is a timestamp, not a game version
    // TODO: Add to polish backlog - requires API enhancement
    // if (filters.gameVersion) {
    //   return false; // Would need version compatibility data from API
    // }

    return true;
  });
}
