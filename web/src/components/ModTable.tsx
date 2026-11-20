/**
 * ModTable - Table displaying installed mods with management actions.
 *
 * Features:
 * - Displays mod name, version, compatibility status
 * - Enable/disable toggle with optimistic updates
 * - Remove button with confirmation dialog
 * - Available column with update action and confirmation (Story 14.3)
 * - Sortable columns with persistent sort preference (VSS-g54)
 * - Empty state when no mods installed
 * - Below the `lg` breakpoint (Story 16.5 below `md`, Story 17.8 up to `lg`), one card
 *   per mod instead of the table, rendered from the same sorted rows with the same
 *   handlers and dialogs
 * - Story 18.4: below `lg`, a sort control above the cards writes the same preference as
 *   the headers; the Name column wraps so the table fits its container from 1024px
 * - Story 21.4: the remove dialog stays open until the DELETE answers and cannot be
 *   dismissed while it runs; on an error it offers Remove again
 */

import { useState, useMemo, useCallback } from 'react';
import { Loader2, ChevronUp, ChevronDown } from 'lucide-react';
import {
  createColumnHelper,
  createSortedRowModel,
  flexRender,
  rowSortingFeature,
  sortFns,
  tableFeatures,
  useTable,
  type SortingState,
} from '@tanstack/react-table';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import {
  AlertDialog,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { Button } from '@/components/ui/button';
import { SideBadge } from '@/components/SideBadge';
import {
  ModCompatibility,
  ModEnableToggle,
  ModNameLink,
  isLocalMod,
  ModRemoveButton,
  type ModTableRow,
} from '@/components/InstalledModParts';
import { ModUpdateCell } from '@/components/ModUpdateCell';
import { InstalledModCard } from '@/components/InstalledModCard';
import {
  InstalledModsSortControl,
  SORT_COLUMN_LABELS,
} from '@/components/InstalledModsSortControl';
import { VersionChangeConfirmDialog } from '@/components/VersionChangeConfirmDialog';
import { useVersionChangeFlow } from '@/hooks/use-version-change-flow';
import { useMediaQuery, LG_UP_QUERY } from '@/hooks/use-media-query';
import {
  useMods,
  useEnableMod,
  useDisableMod,
  useRemoveMod,
  useModsCompatibility,
  useModUpdates,
} from '@/hooks/use-mods';
import { usePreferences, type InstalledModsSort } from '@/contexts/PreferencesContext';
import type { ModInfo } from '@/api/types';
import { compareVersions } from '@/lib/version-compare';
import { ariaSort } from '@/lib/table-aria-sort';

interface ModTableProps {
  /** Callback when a mod is successfully removed */
  onRemoved?: (slug: string) => void;
  /** Callback when a mod's enabled state changes */
  onToggled?: (slug: string, enabled: boolean) => void;
}

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns,
});

const columnHelper = createColumnHelper<typeof features, ModTableRow>();

/**
 * Sortable column header component with chevron indicators.
 */
function SortableHeader({
  label,
  sorted,
  onClick,
}: {
  label: string;
  sorted: false | 'asc' | 'desc';
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      className="flex items-center gap-1 hover:text-foreground transition-colors"
      onClick={onClick}
    >
      {label}
      {sorted === 'asc' && <ChevronUp className="h-4 w-4" aria-hidden="true" />}
      {sorted === 'desc' && <ChevronDown className="h-4 w-4" aria-hidden="true" />}
      {!sorted && <span className="w-4" />}
    </button>
  );
}

/**
 * Table displaying installed mods with enable/disable toggles and remove actions.
 * Supports sortable columns with persistent preferences.
 *
 * @example
 * <ModTable
 *   onRemoved={(slug) => toast.success(`Removed ${slug}`)}
 *   onToggled={(slug, enabled) => toast.success(`${slug} ${enabled ? 'enabled' : 'disabled'}`)}
 * />
 */
export function ModTable({ onRemoved, onToggled }: ModTableProps) {
  const [modToRemove, setModToRemove] = useState<ModInfo | null>(null);

  const { data: modsData, isLoading } = useMods();
  const { mutate: enableMod, isPending: isEnabling, variables: enablingSlug } = useEnableMod();
  const { mutate: disableMod, isPending: isDisabling, variables: disablingSlug } = useDisableMod();
  const {
    mutate: removeModMutation,
    isPending: isRemovePending,
    variables: removingSlug,
  } = useRemoveMod();
  const { preferences, setInstalledModsSort } = usePreferences();
  const versionChange = useVersionChangeFlow();
  // Story 16.5, Story 17.8: the table at lg and up, cards below; only one layout is mounted
  const isTableLayout = useMediaQuery(LG_UP_QUERY);
  const { start: startVersionChange, isPending: isChangingVersion } = versionChange;

  const mods = modsData?.data?.mods ?? [];

  // VSS-j3c: Fetch compatibility status for all installed mods
  // VSS-qal: Also fetch side info for SideBadge display
  // Story 16.3: for the installed release, not the newest one
  const { compatibilityMap, compatibilityDetails, sideMap } = useModsCompatibility(mods);

  // Story 14.3: update status for the Available column
  const { data: updatesData } = useModUpdates();
  const gameVersion = updatesData?.data?.gameVersion ?? null;
  const updateMap = useMemo(
    () => new Map((updatesData?.data?.mods ?? []).map((item) => [item.slug, item])),
    [updatesData]
  );

  // VSS-g54: Convert preferences to TanStack Table sorting state
  const sorting: SortingState = useMemo(() => {
    const { column, direction } = preferences.installedModsSort;
    return [{ id: column, desc: direction === 'desc' }];
  }, [preferences.installedModsSort]);

  // VSS-g54: Update preferences when sorting changes
  const onSortingChange = useCallback(
    (updaterOrValue: SortingState | ((old: SortingState) => SortingState)) => {
      const newSorting =
        typeof updaterOrValue === 'function' ? updaterOrValue(sorting) : updaterOrValue;

      if (newSorting.length > 0) {
        const { id, desc } = newSorting[0];
        // Only update if the column is one we support sorting on
        if (id === 'name' || id === 'version' || id === 'enabled') {
          const newSort: InstalledModsSort = {
            column: id,
            direction: desc ? 'desc' : 'asc',
          };
          setInstalledModsSort(newSort);
        }
      }
    },
    [sorting, setInstalledModsSort]
  );

  // Merge mod data with compatibility info for table rendering
  // VSS-jco: side now comes from API response, use sideMap as fallback for legacy data
  const tableData: ModTableRow[] = useMemo(() => {
    return mods.map((mod) => ({
      ...mod,
      compatibilityStatus: compatibilityMap.get(mod.slug) ?? 'not_verified',
      compatibility: compatibilityDetails.get(mod.slug),
      // Use API side if available, fall back to sideMap for legacy data
      side: mod.side ?? sideMap.get(mod.slug) ?? null,
      updateStatus: updateMap.get(mod.slug),
    }));
  }, [mods, compatibilityMap, compatibilityDetails, sideMap, updateMap]);

  const handleToggle = useCallback(
    (mod: ModInfo) => {
      if (mod.enabled) {
        disableMod(mod.slug, {
          onSuccess: () => {
            onToggled?.(mod.slug, false);
          },
        });
      } else {
        enableMod(mod.slug, {
          onSuccess: () => {
            onToggled?.(mod.slug, true);
          },
        });
      }
    },
    [disableMod, enableMod, onToggled]
  );

  // Story 14.3: apply the offered update through the confirmation flow
  const handleUpdate = useCallback(
    (mod: ModTableRow) => {
      const offered = mod.updateStatus?.offeredVersion;
      if (!offered) return;
      startVersionChange({
        slug: mod.slug,
        name: mod.name || mod.slug,
        version: offered,
        installedVersion: mod.version,
        kind: 'update',
      });
    },
    [startVersionChange]
  );

  const handleRemoveClick = useCallback((mod: ModInfo) => {
    setModToRemove(mod);
  }, []);

  // Story 21.4: "Removing..." belongs to the dialog of the mod whose DELETE runs
  const isRemoving = isRemovePending && modToRemove !== null && removingSlug === modToRemove.slug;

  // Story 21.4: the dialog stays open until the DELETE answers. On success it closes; on
  // an error the hook restores the row and shows the toast, and the dialog offers Remove
  // again.
  const handleRemoveConfirm = () => {
    if (!modToRemove || isRemoving) return;

    const slug = modToRemove.slug;
    removeModMutation(slug, {
      onSuccess: () => {
        onRemoved?.(slug);
        // Close only this mod's dialog, never one opened for another mod meanwhile
        setModToRemove((current) => (current?.slug === slug ? null : current));
      },
    });
  };

  // Cancel, Escape and onOpenChange all come here; nothing closes the dialog while the
  // DELETE runs
  const handleRemoveCancel = () => {
    if (isRemoving) return;
    setModToRemove(null);
  };

  const isTogglingMod = useCallback(
    (slug: string) => {
      return (isEnabling && enablingSlug === slug) || (isDisabling && disablingSlug === slug);
    },
    [isEnabling, enablingSlug, isDisabling, disablingSlug]
  );

  // Define columns with TanStack Table
  const columns = useMemo(
    () =>
      columnHelper.columns([
        columnHelper.accessor('name', {
          header: ({ column }) => (
            <SortableHeader
              label={SORT_COLUMN_LABELS.name}
              sorted={column.getIsSorted()}
              onClick={() => column.toggleSorting()}
            />
          ),
          cell: ({ row }) => <ModNameLink mod={row.original} local={isLocalMod(row.original)} />,
          // Story 18.4: long names (and slugs without spaces) wrap so the table fits at 1024px
          meta: { className: 'min-w-32 whitespace-normal wrap-anywhere' },
          sortFn: (rowA, rowB) => {
            const a = (rowA.original.name || rowA.original.slug).toLowerCase();
            const b = (rowB.original.name || rowB.original.slug).toLowerCase();
            return a.localeCompare(b);
          },
        }),
        columnHelper.accessor('version', {
          header: ({ column }) => (
            <SortableHeader
              label={SORT_COLUMN_LABELS.version}
              sorted={column.getIsSorted()}
              onClick={() => column.toggleSorting()}
            />
          ),
          cell: ({ getValue }) => <span className="text-muted-foreground">v{getValue()}</span>,
          sortFn: (rowA, rowB) => compareVersions(rowA.original.version, rowB.original.version),
        }),
        columnHelper.display({
          id: 'available',
          header: 'Available',
          cell: ({ row }) => (
            <ModUpdateCell
              status={row.original.updateStatus}
              gameVersion={gameVersion}
              onUpdate={() => handleUpdate(row.original)}
              isUpdating={isChangingVersion(row.original.slug)}
            />
          ),
        }),
        columnHelper.accessor('side', {
          header: 'Side',
          cell: ({ getValue }) => <SideBadge side={getValue()} />,
          enableSorting: false,
        }),
        columnHelper.accessor('compatibilityStatus', {
          header: 'Compatibility',
          cell: ({ row, getValue }) => (
            <ModCompatibility
              slug={row.original.slug}
              status={getValue()}
              compatibility={row.original.compatibility}
            />
          ),
          enableSorting: false,
        }),
        columnHelper.accessor('enabled', {
          header: ({ column }) => (
            <SortableHeader
              label={SORT_COLUMN_LABELS.enabled}
              sorted={column.getIsSorted()}
              onClick={() => column.toggleSorting()}
            />
          ),
          cell: ({ row }) => (
            <ModEnableToggle
              mod={row.original}
              isToggling={isTogglingMod(row.original.slug)}
              onToggle={() => handleToggle(row.original)}
            />
          ),
          // Sort enabled mods first when ascending
          sortFn: (rowA, rowB) => {
            const a = rowA.original.enabled ? 1 : 0;
            const b = rowB.original.enabled ? 1 : 0;
            return a - b;
          },
        }),
        columnHelper.display({
          id: 'actions',
          header: () => <span className="sr-only">Actions</span>,
          cell: ({ row }) => (
            <ModRemoveButton mod={row.original} onRemove={() => handleRemoveClick(row.original)} />
          ),
          meta: { className: 'w-[80px]' },
        }),
      ]),
    [handleToggle, handleRemoveClick, isTogglingMod, gameVersion, handleUpdate, isChangingVersion]
  );

  const table = useTable({
    features,
    data: tableData,
    columns,
    state: { sorting },
    onSortingChange,
    // The sort preference always names a column, so toggling must never clear it
    enableSortingRemoval: false,
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8" data-testid="mod-table-loading">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  // Story 21.4: rendered beside the empty state too, so removing the last mod (which
  // empties the list at once) does not unmount the dialog while its DELETE runs
  const removeDialog = (
    <AlertDialog open={!!modToRemove} onOpenChange={(open) => !open && handleRemoveCancel()}>
      <AlertDialogContent data-testid="remove-dialog">
        <AlertDialogHeader>
          <AlertDialogTitle>Remove {modToRemove?.name || modToRemove?.slug}?</AlertDialogTitle>
          <AlertDialogDescription>
            This will remove the mod from your server. This action cannot be undone.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          {/* Radix's AlertDialogCancel, so the dialog focuses it when it opens */}
          <AlertDialogCancel
            onClick={handleRemoveCancel}
            disabled={isRemoving}
            data-testid="remove-dialog-cancel"
          >
            Cancel
          </AlertDialogCancel>
          {/* A plain button, not AlertDialogAction, which would close the dialog on click */}
          <Button
            variant="destructive"
            onClick={handleRemoveConfirm}
            disabled={isRemoving}
            data-testid="remove-dialog-confirm"
          >
            {isRemoving ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Removing...
              </>
            ) : (
              'Remove'
            )}
          </Button>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  );

  if (mods.length === 0) {
    return (
      <>
        <div className="text-center py-8 text-muted-foreground" data-testid="mod-table-empty">
          No mods installed yet
        </div>
        {removeDialog}
      </>
    );
  }

  return (
    <>
      {isTableLayout ? (
        <Table data-testid="mod-table">
          <TableHeader>
            {table.getHeaderGroups().map((headerGroup) => (
              <TableRow key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <TableHead
                    key={header.id}
                    className={header.column.columnDef.meta?.className}
                    aria-sort={ariaSort(header.column.getCanSort(), header.column.getIsSorted())}
                  >
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                  </TableHead>
                ))}
              </TableRow>
            ))}
          </TableHeader>
          <TableBody>
            {table.getRowModel().rows.map((row) => (
              <TableRow key={row.id} data-testid={`mod-row-${row.original.slug}`}>
                {row.getAllCells().map((cell) => (
                  <TableCell key={cell.id} className={cell.column.columnDef.meta?.className}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      ) : (
        <div className="space-y-3">
          <InstalledModsSortControl
            value={preferences.installedModsSort}
            onChange={setInstalledModsSort}
          />
          <ul className="space-y-3" aria-label="Installed mods" data-testid="installed-mod-cards">
            {table.getRowModel().rows.map((row) => {
              const mod = row.original;
              return (
                <InstalledModCard
                  key={row.id}
                  mod={mod}
                  gameVersion={gameVersion}
                  isToggling={isTogglingMod(mod.slug)}
                  isUpdating={isChangingVersion(mod.slug)}
                  onToggle={() => handleToggle(mod)}
                  onUpdate={() => handleUpdate(mod)}
                  onRemove={() => handleRemoveClick(mod)}
                />
              );
            })}
          </ul>
        </div>
      )}

      <VersionChangeConfirmDialog
        confirmation={versionChange.confirmation}
        gameVersion={gameVersion}
        onConfirm={versionChange.confirm}
        onCancel={versionChange.cancel}
      />

      {/* Remove confirmation dialog */}
      {removeDialog}
    </>
  );
}
