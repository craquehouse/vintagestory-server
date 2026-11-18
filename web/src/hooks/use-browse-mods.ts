/**
 * Hook for fetching and filtering browsable mods.
 *
 * All filtering (search, side, tags, modType, gameVersion) and sorting,
 * including the Name (A-Z) sort, is done server-side for accurate pagination.
 * Uses TanStack Query for caching and state management.
 *
 * Story VSS-vth: Added server-side game version filtering.
 * VSS-y7u: Moved all filters (side, tags, modType) to server-side.
 * Story 16.8: The Name sort is server-side too (VSS-stm.1).
 * Story 17.7: A page beyond the results is reported to the caller (VSS-nhb).
 * Story 18.3: Returns `gameVersion`, the installed game version the cards' flags refer to.
 */

import { useCallback, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { queryKeys } from '@/api/query-keys';
import { fetchBrowseMods } from '@/api/mods';
import type { BrowseParams, ModBrowseItem } from '@/api/types';

/**
 * Cache time matches the API's 5-minute TTL for mod data.
 */
const BROWSE_STALE_TIME = 5 * 60 * 1000;

/** Options for useBrowseMods. */
export interface UseBrowseModsOptions {
  /** Called with a validated page number when the page should change. */
  onPageChange?: (page: number) => void;
  /**
   * Called once the response shows that `params.page` is beyond the last page, with
   * the last page (1 when there are no results). The caller replaces the page in its
   * URL without adding a history entry (Story 17.7).
   */
  onPageOutOfRange?: (lastPage: number) => void;
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
 * Story 17.7: A page beyond the results is reported through `options.onPageOutOfRange`;
 * the API serves the last page for it, and that response is stored as the last page,
 * so moving there needs no second request.
 *
 * @param params - Browse parameters including page, pageSize, sort, and search
 * @param options - `onPageChange` receives validated page changes; `onPageOutOfRange`
 *   receives the last page when `params.page` is beyond it
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
export function useBrowseMods(params: BrowseParams = {}, options: UseBrowseModsOptions = {}) {
  // Story 16.1: The page is controlled by the caller (BrowseTab keeps it in the URL).
  // Resetting the page when search/filters/sort change is also the caller's job.
  const currentPage = params.page ?? 1;
  const { onPageChange, onPageOutOfRange } = options;
  const queryClient = useQueryClient();

  // VSS-y7u: All filters are now server-side for accurate pagination
  // Extract filters for API - support both new flat params and legacy filters object
  const { filters, sort: apiSort, page: _ignoredPage, ...apiParams } = params;

  // Story 16.8: every sort, including 'name', is server-side and paged normally
  const apiPageSize = params.pageSize ?? 20;

  // VSS-y7u: Build API params with all filters (server-side)
  // Support both new flat params and legacy filters object for backwards compat
  const apiVersion = params.version ?? filters?.gameVersion;
  const apiSide = params.side ?? filters?.side;
  const apiModType = params.modType ?? filters?.modType;
  const apiTags = params.tags ?? filters?.tags;

  const requestParams = {
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
  };

  const query = useQuery({
    queryKey: queryKeys.mods.browse(requestParams),
    queryFn: async () => {
      const response = await fetchBrowseMods(requestParams);
      // Story 17.7: For a page beyond the results the API serves the last page. Store
      // the response under that page's key as well, so the caller's move to the last
      // page renders from the cache instead of requesting the same page again.
      const servedPage = response.data?.pagination?.page;
      if (servedPage !== undefined && servedPage < currentPage) {
        queryClient.setQueryData(
          queryKeys.mods.browse({ ...requestParams, page: servedPage }),
          response
        );
      }
      return response;
    },
    staleTime: BROWSE_STALE_TIME,
  });

  // Get pagination from response (if available)
  const pagination = query.data?.data?.pagination;

  // Story 17.7: Report a page beyond the results; the move can only go down, so it
  // cannot loop (after it, currentPage === lastPage)
  const lastPage = pagination ? Math.max(1, pagination.totalPages) : undefined;
  useEffect(() => {
    if (lastPage !== undefined && currentPage > lastPage) onPageOutOfRange?.(lastPage);
  }, [lastPage, currentPage, onPageOutOfRange]);

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

  // VSS-y7u, Story 16.8: filtering and sorting are server-side; keep the API's order
  const mods = query.data?.data?.mods ?? [];

  // Story 18.3: the version the items' hasReleaseForGameVersion flags refer to
  const gameVersion = query.data?.data?.gameVersion ?? null;

  return {
    ...query,
    mods,
    pagination,
    gameVersion,
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
export function filterModsBySearch(mods: ModBrowseItem[], search?: string): ModBrowseItem[] {
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
