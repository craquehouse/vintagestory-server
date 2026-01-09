/**
 * Sort control for mod browsing.
 *
 * Provides a dropdown for selecting sort order:
 * - Newest (recent)
 * - Most Downloaded (downloads)
 * - Trending (trending)
 * - Name A-Z (name) - client-side only
 */

import { ArrowUpDown } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuLabel,
  DropdownMenuSeparator,
} from '@/components/ui/dropdown-menu';
import type { BrowseSortOption } from '@/api/types';

interface SortControlProps {
  value: BrowseSortOption | 'name';
  onChange: (value: BrowseSortOption) => void;
}

const SORT_OPTIONS: Array<{
  value: BrowseSortOption | 'name';
  label: string;
}> = [
  { value: 'recent', label: 'Newest' },
  { value: 'downloads', label: 'Most Downloaded' },
  { value: 'trending', label: 'Trending' },
  { value: 'name', label: 'Name (A-Z)' },
];

export function SortControl({ value, onChange }: SortControlProps) {
  const currentLabel =
    SORT_OPTIONS.find((opt) => opt.value === value)?.label || 'Newest';

  const handleSelect = (sortValue: string) => {
    // Type assertion safe because we control the options
    onChange(sortValue as BrowseSortOption);
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">Sort by:</span>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm">
            <ArrowUpDown className="mr-2 h-4 w-4" />
            {currentLabel}
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuLabel>Sort Order</DropdownMenuLabel>
          <DropdownMenuSeparator />
          {SORT_OPTIONS.map((option) => (
            <DropdownMenuItem
              key={option.value}
              onClick={() => handleSelect(option.value)}
            >
              {option.label}
            </DropdownMenuItem>
          ))}
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}
