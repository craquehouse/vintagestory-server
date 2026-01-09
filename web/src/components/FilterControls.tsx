/**
 * Filter controls for mod browsing.
 *
 * Provides dropdowns for filtering by Side, Tags, Game Version, and Mod Type.
 * Displays active filters as removable badges.
 */

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
import type { ModFilters, BrowseModSide, ModType } from '@/api/types';

interface FilterControlsProps {
  filters: ModFilters;
  onChange: (filters: ModFilters) => void;
}

// Common tags from VintageStory mod database
const COMMON_TAGS = [
  'qol',
  'utility',
  'survival',
  'decoration',
  'farming',
  'crafting',
  'tools',
  'combat',
  'magic',
  'technology',
];

// Common game versions (placeholder - could be fetched from API)
const GAME_VERSIONS = ['1.21', '1.20', '1.19', '1.18'];

export function FilterControls({ filters, onChange }: FilterControlsProps) {
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
            <DropdownMenuItem onClick={() => handleSideChange('both')}>
              Both
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleSideChange('client')}>
              Client
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleSideChange('server')}>
              Server
            </DropdownMenuItem>
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
            <div className="max-h-[300px] overflow-y-auto">
              {COMMON_TAGS.map((tag) => (
                <DropdownMenuCheckboxItem
                  key={tag}
                  checked={filters.tags?.includes(tag) || false}
                  onCheckedChange={() => handleTagToggle(tag)}
                >
                  {tag}
                </DropdownMenuCheckboxItem>
              ))}
            </div>
          </DropdownMenuContent>
        </DropdownMenu>

        {/* Game Version Filter */}
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
            <DropdownMenuItem onClick={() => handleTypeChange('mod')}>
              Code Mod
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleTypeChange('externaltool')}>
              External Tool
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => handleTypeChange('other')}>
              Other
            </DropdownMenuItem>
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
