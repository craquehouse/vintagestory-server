/**
 * BrowseTab - Browse and search for mods from the VintageStory mod database.
 *
 * Features:
 * - Displays newest mods immediately on load
 * - Search with 300ms debounce
 * - Clear search with button or Escape key
 * - Filter by Side, Tags, Version, and Type
 * - Sort by Newest, Downloads, Trending, Name
 * - Loading and error states
 * - Pagination for large result sets (Story 10.7)
 * - Install buttons on mod cards (Story 10.8)
 * - Game version filtering (Story VSS-vth)
 * - Direct slug/URL navigation on Enter key (VSS-195)
 *
 * Story 10.3: Browse Landing Page & Search
 * Story 10.4: Filter & Sort Controls
 * Story 10.7: Pagination
 * Story 10.8: Browse Install Integration
 * Story VSS-vth: Game version filter
 * VSS-195: Slug/URL detection in search
 * Story 16.1: Search, filters, sort and page live in the URL (Epic 16 ADR-1)
 */

import { useState, useCallback, useEffect, useRef, useMemo } from 'react';
import { useNavigate, useLocation, useSearchParams } from 'react-router';
import { Search, X, RefreshCw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useDebounce } from '@/hooks/use-debounce';
import { useBrowseMods } from '@/hooks/use-browse-mods';
import { useMods } from '@/hooks/use-mods';
import { useServerStatus } from '@/hooks/use-server-status';
import { useGameVersions } from '@/hooks/use-game-versions';
import { useModTags } from '@/hooks/use-mod-tags';
import {
  useBrowseScrollRestoration,
  getSavedScrollState,
} from '@/hooks/use-browse-scroll-restoration';
import { ModBrowseGrid } from '@/components/ModBrowseGrid';
import { FilterControls } from '@/components/FilterControls';
import { SortControl } from '@/components/SortControl';
import { Pagination } from '@/components/Pagination';
import { detectSlugOrUrl } from '@/lib/mod-utils';
import {
  parseBrowseSearch,
  buildBrowseSearch,
  saveLastBrowseSearch,
  type BrowseUrlState,
} from '@/lib/browse-search';

/**
 * Browse mods tab with search functionality.
 *
 * Loads newest mods immediately and provides search filtering.
 *
 * @example
 * <BrowseTab />
 */
export function BrowseTab() {
  const navigate = useNavigate();
  const location = useLocation();

  // Story 16.1: The URL is the source of truth for search, filters, sort and page.
  // Parse once per distinct query string so filters keep their identity between renders.
  const [searchParams, setSearchParams] = useSearchParams();
  const urlQuery = searchParams.toString();
  const browseState = useMemo(() => parseBrowseSearch(urlQuery), [urlQuery]);
  const { sort, filters, page } = browseState;

  // The search box keeps local state for responsiveness; the URL gets the debounced value.
  const [searchInput, setSearchInput] = useState(browseState.search);
  // When the URL search changes from outside (browser back/forward), show it in the box.
  const [syncedUrlSearch, setSyncedUrlSearch] = useState(browseState.search);
  if (browseState.search !== syncedUrlSearch) {
    setSyncedUrlSearch(browseState.search);
    if (searchInput.trim() !== browseState.search) {
      setSearchInput(browseState.search);
    }
  }

  // Story 10.8: Get installed mods to show install state on cards
  const { data: modsData } = useMods();
  const installedSlugs = useMemo(
    () => new Set(modsData?.data?.mods?.map((mod) => mod.slug) ?? []),
    [modsData]
  );

  // VSS-1u2: Get installed server version to show first in version filter
  const { data: serverStatus } = useServerStatus();
  const installedVersion = serverStatus?.data?.version ?? null;

  // VSS-vth: Fetch available game versions for filtering
  const {
    data: gameVersionsData,
    isLoading: gameVersionsLoading,
    isError: gameVersionsError,
  } = useGameVersions();
  const gameVersions = gameVersionsData?.data?.versions ?? [];

  // VSS-y7u: Fetch all available mod tags for filtering
  const {
    data: modTagsData,
    isLoading: modTagsLoading,
    isError: modTagsError,
  } = useModTags();
  const modTags = modTagsData?.data?.tags ?? [];

  // Story 10.7: Scroll position restoration
  // Read saved state synchronously for initial page (before first render)
  const [savedState] = useState(() => getSavedScrollState());
  const { savePosition, restorePosition, clearPosition, scrollToPosition } =
    useBrowseScrollRestoration();
  const hasRestoredScrollRef = useRef(false);

  // Restore scroll position on mount (after content renders)
  useEffect(() => {
    if (hasRestoredScrollRef.current) return;
    hasRestoredScrollRef.current = true;

    if (savedState) {
      // Consume the saved state (clears from sessionStorage)
      restorePosition();
      // Scroll after a short delay to allow content to render
      setTimeout(() => scrollToPosition(savedState.scrollY), 100);
    }
  }, [savedState, restorePosition, scrollToPosition]);

  const debouncedSearch = useDebounce(searchInput, 300);

  /**
   * Story 16.1: Write the next browse state to the URL in one call.
   * Changing search, sort or a filter goes back to page 1 (the page is omitted).
   * Discrete changes push a history entry; the debounced search replaces.
   */
  const updateBrowseState = useCallback(
    (patch: Partial<BrowseUrlState>, options: { replace?: boolean } = {}) => {
      const nextSearch = buildBrowseSearch({ ...browseState, page: 1, ...patch });
      if (nextSearch === buildBrowseSearch(browseState)) return;
      if (patch.page === undefined) {
        // Story 10.7: A saved position belongs to the old results
        clearPosition();
      }
      setSearchParams(new URLSearchParams(nextSearch), { replace: options.replace });
    },
    [browseState, setSearchParams, clearPosition]
  );

  // Story 16.1: Write the debounced search only when the debounced value itself changes,
  // so browser back/forward is not overwritten by the previous text still in the debounce.
  const lastDebouncedRef = useRef(debouncedSearch);
  useEffect(() => {
    if (lastDebouncedRef.current === debouncedSearch) return;
    lastDebouncedRef.current = debouncedSearch;
    if (debouncedSearch.trim() === browseState.search) return;
    updateBrowseState({ search: debouncedSearch }, { replace: true });
  }, [debouncedSearch, browseState.search, updateBrowseState]);

  // Story 16.1: Remember the browse URL so the Browse tab can return to it
  useEffect(() => {
    saveLastBrowseSearch(location.search);
  }, [location.search]);

  const handlePageChange = useCallback(
    (nextPage: number) => updateBrowseState({ page: nextPage }),
    [updateBrowseState]
  );

  const {
    mods,
    pagination,
    isLoading,
    isFetching,
    isError,
    error,
    refetch,
    // Story 10.7: Pagination state and controls
    currentPage,
    setPage,
  } = useBrowseMods(
    {
      search: browseState.search,
      filters,
      sort,
      page,
    },
    { onPageChange: handlePageChange }
  );

  // Navigate to mod detail view (Story 10.6)
  // Story 10.7: Save scroll position before navigating
  // Story 11.4: Updated path to /game-server/mods/browse
  const handleModClick = useCallback(
    (slug: string) => {
      savePosition(currentPage);
      navigate(`/game-server/mods/browse/${slug}`);
    },
    [navigate, savePosition, currentPage]
  );

  function handleClearSearch(): void {
    setSearchInput('');
  }

  // VSS-195: Handle Enter key for direct slug/URL navigation
  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>): void {
    if (e.key === 'Escape') {
      e.preventDefault();
      handleClearSearch();
      return;
    }

    if (e.key === 'Enter') {
      const slug = detectSlugOrUrl(searchInput);
      if (slug) {
        e.preventDefault();
        // Navigate directly to mod detail page
        savePosition(currentPage);
        navigate(`/game-server/mods/browse/${slug}`);
      }
      // If not a slug/URL, debounced search is already active - no action needed
    }
  }

  if (isError) {
    return (
      <div
        className="flex flex-col items-center justify-center py-12 text-center"
        data-testid="browse-tab-error"
      >
        <p className="text-destructive mb-4" data-testid="browse-error-message">
          Failed to load mods: {error?.message ?? 'Unknown error'}
        </p>
        <Button
          onClick={() => refetch()}
          variant="outline"
          data-testid="browse-retry-button"
        >
          <RefreshCw className="mr-2 h-4 w-4" />
          Retry
        </Button>
      </div>
    );
  }

  return (
    <div className="space-y-4" data-testid="browse-tab-content">
      {/* Search and Sort */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        {/* Search Input */}
        <div className="relative flex-1" data-testid="browse-search-container">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            type="text"
            placeholder="Search mods or enter slug/URL and press Enter..."
            value={searchInput}
            onChange={(e) => setSearchInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="pl-9 pr-9"
            data-testid="browse-search-input"
            aria-label="Search mods"
          />
          {searchInput && (
            <Button
              variant="ghost"
              size="sm"
              className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0"
              onClick={handleClearSearch}
              data-testid="browse-search-clear"
              aria-label="Clear search"
            >
              <X className="h-4 w-4" />
            </Button>
          )}
        </div>

        {/* Sort Control */}
        <div className="sm:ml-auto">
          <SortControl value={sort} onChange={(nextSort) => updateBrowseState({ sort: nextSort })} />
        </div>
      </div>

      {/* Filter Controls */}
      <FilterControls
        filters={filters}
        onChange={(nextFilters) => updateBrowseState({ filters: nextFilters })}
        // VSS-y7u: Use full tag list from API instead of extracting from current page
        availableTags={modTags}
        tagsLoading={modTagsLoading}
        tagsError={modTagsError}
        gameVersions={gameVersions}
        gameVersionsLoading={gameVersionsLoading}
        gameVersionsError={gameVersionsError}
        installedVersion={installedVersion}
      />

      {/* Results Grid */}
      <ModBrowseGrid
        mods={mods}
        isLoading={isLoading}
        onModClick={handleModClick}
        installedSlugs={installedSlugs}
      />

      {/* Story 10.7: Pagination controls */}
      {/* VSS-arp: Hide pagination when sorting by name (client-side sort of all results) */}
      {!isLoading && pagination && pagination.totalPages > 1 && sort !== 'name' && (
        <Pagination
          currentPage={currentPage}
          totalPages={pagination.totalPages}
          totalItems={pagination.totalItems}
          isLoading={isFetching}
          onPageChange={setPage}
        />
      )}

      {/* Results count */}
      {!isLoading && pagination && (
        <p
          className="text-sm text-muted-foreground"
          data-testid="browse-results-count"
        >
          {sort === 'name' ? (
            <>
              Showing all {pagination.totalItems} mods sorted alphabetically
            </>
          ) : browseState.search ? (
            <>
              Found {mods.length} mod{mods.length !== 1 ? 's' : ''} matching &quot;{browseState.search}&quot;
            </>
          ) : (
            <>
              Showing {mods.length} of {pagination.totalItems} mods
            </>
          )}
        </p>
      )}
    </div>
  );
}
