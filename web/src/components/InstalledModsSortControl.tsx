/**
 * InstalledModsSortControl - sort control above the installed mod cards (Story 18.4).
 *
 * Below the `lg` breakpoint the installed mods are cards without table headers, so this
 * control sets the same `installedModsSort` preference the table's sortable headers set:
 * a column picker (Name, Version, Status) and a button that shows the direction in effect
 * and flips it. Choosing a column keeps the direction.
 */

import { useId } from 'react';
import { ChevronDown, ChevronUp } from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { InstalledModsSort, InstalledModsSortColumn } from '@/contexts/PreferencesContext';

/** Labels of the sortable columns, shared with the table headers so they cannot drift */
export const SORT_COLUMN_LABELS: Record<InstalledModsSortColumn, string> = {
  name: 'Name',
  version: 'Version',
  enabled: 'Status',
};

const SORT_COLUMNS: InstalledModsSortColumn[] = ['name', 'version', 'enabled'];

function isSortColumn(value: string): value is InstalledModsSortColumn {
  return value === 'name' || value === 'version' || value === 'enabled';
}

interface InstalledModsSortControlProps {
  value: InstalledModsSort;
  onChange: (sort: InstalledModsSort) => void;
}

export function InstalledModsSortControl({ value, onChange }: InstalledModsSortControlProps) {
  const labelId = useId();
  const isAscending = value.direction === 'asc';

  return (
    <div className="flex flex-wrap items-center gap-2" data-testid="installed-mods-sort">
      <span id={labelId} className="text-sm text-muted-foreground">
        Sort by
      </span>
      <Select
        value={value.column}
        onValueChange={(column) => {
          if (isSortColumn(column)) onChange({ column, direction: value.direction });
        }}
      >
        <SelectTrigger
          aria-labelledby={labelId}
          className="min-h-11"
          data-testid="installed-mods-sort-column"
        >
          <SelectValue />
        </SelectTrigger>
        <SelectContent>
          {SORT_COLUMNS.map((column) => (
            <SelectItem
              key={column}
              value={column}
              data-testid={`installed-mods-sort-option-${column}`}
            >
              {SORT_COLUMN_LABELS[column]}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <Button
        type="button"
        variant="outline"
        size="sm"
        className="min-h-11"
        onClick={() => onChange({ column: value.column, direction: isAscending ? 'desc' : 'asc' })}
        data-testid="installed-mods-sort-direction"
      >
        {isAscending ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
        {isAscending ? 'Ascending' : 'Descending'}
      </Button>
    </div>
  );
}
