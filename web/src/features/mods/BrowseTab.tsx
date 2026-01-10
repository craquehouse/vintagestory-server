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
 *
 * Story 10.3: Browse Landing Page & Search
 * Story 10.4: Filter & Sort Controls
 */

import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router';
import { Search, X, RefreshCw } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import { useDebounce } from '@/hooks/use-debounce';
import { useBrowseMods } from '@/hooks/use-browse-mods';
import { ModBrowseGrid } from '@/components/ModBrowseGrid';
import { FilterControls } from '@/components/FilterControls';
import { SortControl } from '@/components/SortControl';
import type { ModFilters, BrowseSortOption } from '@/api/types';

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
  const [searchInput, setSearchInput] = useState('');
  const [filters, setFilters] = useState<ModFilters>({});
  const [sort, setSort] = useState<BrowseSortOption>('recent');

  const debouncedSearch = useDebounce(searchInput, 300);

  // Navigate to mod detail view (Story 10.6)
  const handleModClick = useCallback(
    (slug: string) => {
      navigate(`/mods/browse/${slug}`);
    },
    [navigate]
  );

  const {
    mods,
    pagination,
    isLoading,
    isError,
    error,
    refetch,
    data: queryData,
  } = useBrowseMods({
    search: debouncedSearch,
    filters,
    sort,
  });

  const handleClearSearch = useCallback(() => {
    setSearchInput('');
  }, []);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key === 'Escape') {
        handleClearSearch();
      }
    },
    [handleClearSearch]
  );

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
            placeholder="Search mods by name, author, or tag..."
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
          <SortControl value={sort} onChange={setSort} />
        </div>
      </div>

      {/* Filter Controls */}
      <FilterControls
        filters={filters}
        onChange={setFilters}
        availableMods={queryData?.data?.mods ?? []}
      />

      {/* Results Grid */}
      <ModBrowseGrid mods={mods} isLoading={isLoading} onModClick={handleModClick} />

      {/* Results count */}
      {!isLoading && pagination && (
        <p
          className="text-sm text-muted-foreground"
          data-testid="browse-results-count"
        >
          {debouncedSearch ? (
            <>
              Found {mods.length} mod{mods.length !== 1 ? 's' : ''} matching &quot;{debouncedSearch}&quot;
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
