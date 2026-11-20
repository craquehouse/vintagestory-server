/**
 * InstalledModsFilterBar - filters above the installed mods (Story 24.7, FR341).
 *
 * A search box (part of the name or mod ID), a compatibility select and an "Update
 * available" switch. Controlled: the Installed tab keeps the values in the URL (ADR-6).
 */

import { useId } from 'react';
import { Search, X } from 'lucide-react';
import type { CompatibilityStatus } from '@/api/types';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Switch } from '@/components/ui/switch';
import { COMPATIBILITY_STATUSES, type InstalledModsFilters } from '@/lib/installed-mods-filters';

export const COMPATIBILITY_LABELS: Record<CompatibilityStatus, string> = {
  compatible: 'Compatible',
  not_verified: 'Not verified',
  incompatible: 'Incompatible',
};

const ALL = 'all';

interface InstalledModsFilterBarProps {
  value: InstalledModsFilters;
  /** Called on each keystroke in the search box */
  onQueryChange: (query: string) => void;
  onCompatChange: (compat: CompatibilityStatus | null) => void;
  onUpdatesChange: (updates: boolean) => void;
}

export function InstalledModsFilterBar({
  value,
  onQueryChange,
  onCompatChange,
  onUpdatesChange,
}: InstalledModsFilterBarProps) {
  const compatLabelId = useId();
  const updatesId = useId();

  return (
    <div
      className="flex flex-col gap-3 sm:flex-row sm:flex-wrap sm:items-center"
      data-testid="installed-mods-filters"
    >
      <div className="relative flex-1 sm:min-w-56">
        <Search
          className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground"
          aria-hidden="true"
        />
        <Input
          type="text"
          placeholder="Filter by name or mod ID"
          value={value.query}
          onChange={(event) => onQueryChange(event.target.value)}
          className="pl-9 pr-9 max-lg:h-11"
          aria-label="Filter installed mods by name or mod ID"
          data-testid="installed-mods-filter-query"
        />
        {value.query && (
          <Button
            variant="ghost"
            size="sm"
            className="absolute right-1 top-1/2 h-7 w-7 -translate-y-1/2 p-0 max-lg:h-11 max-lg:w-11"
            onClick={() => onQueryChange('')}
            aria-label="Clear the name filter"
            data-testid="installed-mods-filter-query-clear"
          >
            <X className="h-4 w-4" />
          </Button>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <span id={compatLabelId} className="text-sm text-muted-foreground">
          Compatibility
        </span>
        <Select
          value={value.compat ?? ALL}
          onValueChange={(next) =>
            onCompatChange(COMPATIBILITY_STATUSES.find((status) => status === next) ?? null)
          }
        >
          <SelectTrigger
            aria-labelledby={compatLabelId}
            className="max-lg:min-h-11"
            data-testid="installed-mods-filter-compat"
          >
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL} data-testid="installed-mods-filter-compat-all">
              All
            </SelectItem>
            {COMPATIBILITY_STATUSES.map((status) => (
              <SelectItem
                key={status}
                value={status}
                data-testid={`installed-mods-filter-compat-${status}`}
              >
                {COMPATIBILITY_LABELS[status]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      {/* The label makes the whole 44px area toggle the switch on phones */}
      <label
        htmlFor={updatesId}
        className="flex cursor-pointer items-center gap-2 text-sm max-lg:min-h-11"
      >
        <Switch
          id={updatesId}
          checked={value.updates}
          onCheckedChange={onUpdatesChange}
          data-testid="installed-mods-filter-updates"
        />
        Update available
      </label>
    </div>
  );
}
