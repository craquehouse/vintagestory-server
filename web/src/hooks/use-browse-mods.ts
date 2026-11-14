/**
 * Hook for fetching and filtering browsable mods.
 *
 * All filtering (search, side, tags, modType, gameVersion) is done
 * server-side for accurate pagination. Uses TanStack Query for caching
 * and state management.
 *
 * Story VSS-vth: Added server-side game version filtering.
 * VSS-y7u: Moved all filters (side, tags, modType) to server-side.
 */

import { useCallback } from 'react';
import { useQuery } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchBrowseMods } from '@/api/mods';
import type { BrowseParams, ModBrowseItem, ModFilters } from '@/api/types';

/**
 * Cache time matches the API's 5-minute TTL for mod data.
 */
const BROWSE_STALE_TIME = 5 * 60 * 1000;

/** Options for useBrowseMods. */
export interface UseBrowseModsOptions {
  /** Called with a validated page number when the page should change. */
  onPageChange?: (page: number) => void;
}

/**
 * Hook to fetch and filter browsable mods.
 *
 * Supports server-side pagination, sorting, search, and filtering (via API).
 * VSS-y7u: All filters (side, tags, modType) are now server-side for accurate pagination.
 *
 * Story 10.7: Added pagination state management with setPage, goToNextPage, goToPrevPage.
 * Story 16.1: The page is controlled: `params.page` is the current page and page
 * changes are reported through `options.onPageChange`.
 *
 * @param params - Browse parameters including page, pageSize, sort, and search
 * @param options - `onPageChange` receives validated page changes
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
 *   } = useBrowseMods(
 *     { page, pageSize: 20, sort: 'recent', search: 'farming' },
 *     { onPageChange: setPageInUrl },
 *   );
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
export function useBrowseMods(
  params: BrowseParams = {},
  options: UseBrowseModsOptions = {}
) {
  // Story 16.1: The page is controlled by the caller (BrowseTab keeps it in the URL).
  // Resetting the page when search/filters/sort change is also the caller's job.
  const currentPage = params.page ?? 1;
  const { onPageChange } = options;

  // VSS-y7u: All filters are now server-side for accurate pagination
  // Extract filters for API - support both new flat params and legacy filters object
  const { filters, sort, page: _ignoredPage, ...apiParams } = params;

  // Only pass sort to API if it's a server-side option
  const apiSort = sort === 'name' ? undefined : sort;

  // VSS-arp: When sorting by name client-side, fetch all data to sort correctly
  // Use a large pageSize to get all mods for client-side name sorting
  const effectivePageSize = sort === 'name' ? 1000 : params.pageSize;
  const apiPageSize = effectivePageSize ?? 20;

  // VSS-y7u: Build API params with all filters (server-side)
  // Support both new flat params and legacy filters object for backwards compat
  const apiVersion = params.version ?? filters?.gameVersion;
  const apiSide = params.side ?? filters?.side;
  const apiModType = params.modType ?? filters?.modType;
  const apiTags = params.tags ?? filters?.tags;

  const query = useQuery({
    queryKey: queryKeys.mods.browse({
      ...apiParams,
      page: currentPage,
      sort: apiSort,
      pageSize: apiPageSize,
      search: params.search,
      version: apiVersion,
      // VSS-y7u: Server-side filters
      side: apiSide,
      modType: apiModType,
      tags: apiTags,
    }),
    queryFn: () =>
      fetchBrowseMods({
        ...apiParams,
        page: currentPage,
        sort: apiSort,
        pageSize: apiPageSize,
        search: params.search,
        version: apiVersion,
        // VSS-y7u: Server-side filters
        side: apiSide,
        modType: apiModType,
        tags: apiTags,
      }),
    staleTime: BROWSE_STALE_TIME,
  });

  // Get pagination from response (if available)
  const pagination = query.data?.data?.pagination;

  // Story 10.7: Page navigation functions
  // Story 16.1: Validated page changes are reported through onPageChange
  const setPage = useCallback(
    (page: number) => {
      // Validate page number: must be positive integer within bounds
      if (page < 1) return;
      if (pagination?.totalPages && page > pagination.totalPages) return;
      onPageChange?.(page);
    },
    [pagination?.totalPages, onPageChange]
  );

  const goToNextPage = useCallback(() => {
    if (pagination?.hasNext) {
      onPageChange?.(currentPage + 1);
    }
  }, [pagination?.hasNext, currentPage, onPageChange]);

  const goToPrevPage = useCallback(() => {
    if (pagination?.hasPrev && currentPage > 1) {
      onPageChange?.(currentPage - 1);
    }
  }, [pagination?.hasPrev, currentPage, onPageChange]);

  // VSS-y7u: All filtering is now server-side, no client-side filtering needed
  const allMods = query.data?.data?.mods ?? [];

  // Client-side sorting for 'name' option (only remaining client-side operation)
  const sorted = sort === 'name' ? sortModsByName(allMods) : allMods;

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
 * Filter mods by filter criteria (client-side).
 *
 * @deprecated VSS-y7u: All filtering is now server-side for accurate pagination.
 * This function is kept for backwards compatibility but is no longer used by useBrowseMods.
 *
 * Applies AND logic across different filter types:
 * - Must match side if specified
 * - Must match at least one tag if tags specified (OR logic within tags)
 * - Must match modType if specified
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

    return true;
  });
}
