/**
 * Filter controls for mod browsing.
 *
 * Provides dropdowns for filtering by Side, Tags, Game Version, and Mod Type.
 * Displays active filters as removable badges.
 */

import { useMemo } from 'react';
import { Filter, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
  DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import type { ModFilters, BrowseModSide, ModType, ModBrowseItem } from '@/api/types';

interface FilterControlsProps {
  filters: ModFilters;
  onChange: (filters: ModFilters) => void;
  availableMods?: ModBrowseItem[]; // For extracting available tags dynamically
}

// Game version filtering requires API enhancement - browse endpoint doesn't include
// game version compatibility data (only in detailed mod endpoint's releases array)
// TODO: Add to polish backlog - requires API to include compatibility in browse response
const GAME_VERSIONS: string[] = []; // Disabled until API supports it

// Side options derived from type system
const SIDE_OPTIONS: Array<{ value: BrowseModSide; label: string }> = [
  { value: 'both', label: 'Both' },
  { value: 'client', label: 'Client' },
  { value: 'server', label: 'Server' },
];

// Mod type options derived from type system
const MOD_TYPE_OPTIONS: Array<{ value: ModType; label: string }> = [
  { value: 'mod', label: 'Code Mod' },
  { value: 'externaltool', label: 'External Tool' },
  { value: 'other', label: 'Other' },
];

export function FilterControls({ filters, onChange, availableMods = [] }: FilterControlsProps) {
  // Extract unique tags from available mods
  const availableTags = useMemo(() => {
    const tagSet = new Set<string>();
    availableMods.forEach((mod) => {
      mod.tags.forEach((tag) => tagSet.add(tag.toLowerCase()));
    });
    return Array.from(tagSet).sort();
  }, [availableMods]);
  const handleSideChange = (side: BrowseModSide) => {
    onChange({ ...filters, side });
  };

  const handleTagToggle = (tag: string) => {
    const currentTags = filters.tags || [];
    const newTags = currentTags.includes(tag)
      ? currentTags.filter((t) => t !== tag)
      : [...currentTags, tag];

    onChange({ ...filters, tags: newTags.length > 0 ? newTags : undefined });
  };

  const handleVersionChange = (version: string) => {
    onChange({ ...filters, gameVersion: version });
  };

  const handleTypeChange = (modType: ModType) => {
    onChange({ ...filters, modType });
  };

  const handleRemoveSide = () => {
    const { side, ...rest } = filters;
    onChange(rest);
  };

  const handleRemoveTag = (tag: string) => {
    const currentTags = filters.tags || [];
    const newTags = currentTags.filter((t) => t !== tag);
    onChange({ ...filters, tags: newTags.length > 0 ? newTags : undefined });
  };

  const handleRemoveVersion = () => {
    const { gameVersion, ...rest } = filters;
    onChange(rest);
  };

  const handleRemoveType = () => {
    const { modType, ...rest } = filters;
    onChange(rest);
  };

  const hasActiveFilters =
    filters.side ||
    (filters.tags && filters.tags.length > 0) ||
    filters.gameVersion ||
    filters.modType;

  return (
    <div className="space-y-3">
      {/* Filter Dropdowns */}
      <div className="flex flex-wrap gap-2">
        {/* Side Filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Filter className="mr-2 h-4 w-4" />
              Side
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuLabel>Mod Side</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {SIDE_OPTIONS.map((option) => (
              <DropdownMenuItem
                key={option.value}
                onClick={() => handleSideChange(option.value)}
              >
                {option.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Tags Filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Filter className="mr-2 h-4 w-4" />
              Tags
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start" className="w-48">
            <DropdownMenuLabel>Filter by Tags</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {availableTags.length > 0 ? (
              <div className="max-h-[300px] overflow-y-auto">
                {availableTags.map((tag) => (
                  <DropdownMenuCheckboxItem
                    key={tag}
                    checked={filters.tags?.includes(tag) || false}
                    onCheckedChange={() => handleTagToggle(tag)}
                  >
                    {tag}
                  </DropdownMenuCheckboxItem>
                ))}
              </div>
            ) : (
              <div className="px-2 py-1.5 text-sm text-muted-foreground">
                No tags available
              </div>
            )}
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Game Version Filter - Disabled: API doesn't provide version compatibility in browse endpoint */}
        {GAME_VERSIONS.length > 0 && (
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Filter className="mr-2 h-4 w-4" />
                Version
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="start">
              <DropdownMenuLabel>Game Version</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {GAME_VERSIONS.map((version) => (
                <DropdownMenuItem
                  key={version}
                  onClick={() => handleVersionChange(version)}
                >
                  {version}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        )}

        {/* Mod Type Filter */}
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="outline" size="sm">
              <Filter className="mr-2 h-4 w-4" />
              Type
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="start">
            <DropdownMenuLabel>Mod Type</DropdownMenuLabel>
            <DropdownMenuSeparator />
            {MOD_TYPE_OPTIONS.map((option) => (
              <DropdownMenuItem
                key={option.value}
                onClick={() => handleTypeChange(option.value)}
              >
                {option.label}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>

      {/* Active Filter Badges */}
      {hasActiveFilters && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm text-muted-foreground">Active filters:</span>

          {filters.side && (
            <Badge variant="secondary" className="gap-1">
              {filters.side}
              <button
                type="button"
                onClick={handleRemoveSide}
                className="ml-1 rounded-full hover:bg-muted"
                aria-label={`Remove side filter: ${filters.side}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}

          {filters.tags?.map((tag) => (
            <Badge key={tag} variant="secondary" className="gap-1">
              {tag}
              <button
                type="button"
                onClick={() => handleRemoveTag(tag)}
                className="ml-1 rounded-full hover:bg-muted"
                aria-label={`Remove tag filter: ${tag}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          ))}

          {filters.gameVersion && (
            <Badge variant="secondary" className="gap-1">
              v{filters.gameVersion}
              <button
                type="button"
                onClick={handleRemoveVersion}
                className="ml-1 rounded-full hover:bg-muted"
                aria-label={`Remove version filter: ${filters.gameVersion}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}

          {filters.modType && (
            <Badge variant="secondary" className="gap-1">
              {filters.modType === 'mod' ? 'Code Mod' : filters.modType}
              <button
                type="button"
                onClick={handleRemoveType}
                className="ml-1 rounded-full hover:bg-muted"
                aria-label={`Remove type filter: ${filters.modType}`}
              >
                <X className="h-3 w-3" />
              </button>
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
