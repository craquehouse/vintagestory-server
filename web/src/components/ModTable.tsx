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
 */

import { useState, useMemo, useCallback } from 'react';
import { Trash2, Loader2, ExternalLink, ChevronUp, ChevronDown } from 'lucide-react';
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
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import { CompatibilityBadge } from '@/components/CompatibilityBadge';
import { SideBadge } from '@/components/SideBadge';
import { ModUpdateCell } from '@/components/ModUpdateCell';
import { VersionChangeConfirmDialog } from '@/components/VersionChangeConfirmDialog';
import { useVersionChangeFlow } from '@/hooks/use-version-change-flow';
import {
  useMods,
  useEnableMod,
  useDisableMod,
  useRemoveMod,
  useModsCompatibility,
  useModUpdates,
} from '@/hooks/use-mods';
import { usePreferences, type InstalledModsSort } from '@/contexts/PreferencesContext';
import type { ModInfo, CompatibilityStatus, ModUpdateStatus } from '@/api/types';

interface ModTableProps {
  /** Callback when a mod is successfully removed */
  onRemoved?: (slug: string) => void;
  /** Callback when a mod's enabled state changes */
  onToggled?: (slug: string, enabled: boolean) => void;
}

/** Extended ModInfo with compatibility and side data for table rendering */
interface ModTableRow extends ModInfo {
  compatibilityStatus: CompatibilityStatus;
  /** Story 14.3: update status from GET /mods/updates */
  updateStatus?: ModUpdateStatus;
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
      {sorted === 'asc' && <ChevronUp className="h-4 w-4" />}
      {sorted === 'desc' && <ChevronDown className="h-4 w-4" />}
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
  const { mutate: removeModMutation, isPending: isRemoving } = useRemoveMod();
  const { preferences, setInstalledModsSort } = usePreferences();
  const versionChange = useVersionChangeFlow();
  const { start: startVersionChange, isPending: isChangingVersion } = versionChange;

  const mods = modsData?.data?.mods ?? [];

  // VSS-j3c: Fetch compatibility status for all installed mods
  // VSS-qal: Also fetch side info for SideBadge display
  const slugs = mods.map((m) => m.slug);
  const { compatibilityMap, sideMap } = useModsCompatibility(slugs);

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
      const newSorting = typeof updaterOrValue === 'function'
        ? updaterOrValue(sorting)
        : updaterOrValue;

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
      // Use API side if available, fall back to sideMap for legacy data
      side: mod.side ?? sideMap.get(mod.slug) ?? null,
      updateStatus: updateMap.get(mod.slug),
    }));
  }, [mods, compatibilityMap, sideMap, updateMap]);

  const handleToggle = useCallback((mod: ModInfo) => {
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
  }, [disableMod, enableMod, onToggled]);

  // Story 14.3: apply the offered update through the confirmation flow
  const handleUpdate = useCallback((mod: ModTableRow) => {
    const offered = mod.updateStatus?.offeredVersion;
    if (!offered) return;
    startVersionChange({
      slug: mod.slug,
      name: mod.name || mod.slug,
      version: offered,
      installedVersion: mod.version,
      kind: 'update',
    });
  }, [startVersionChange]);

  const handleRemoveClick = useCallback((mod: ModInfo) => {
    setModToRemove(mod);
  }, []);

  const handleRemoveConfirm = () => {
    if (!modToRemove) return;

    removeModMutation(modToRemove.slug, {
      onSuccess: () => {
        onRemoved?.(modToRemove.slug);
        setModToRemove(null);
      },
      onError: () => {
        setModToRemove(null);
      },
    });
  };

  const handleRemoveCancel = () => {
    setModToRemove(null);
  };

  const isTogglingMod = useCallback((slug: string) => {
    return (
      (isEnabling && enablingSlug === slug) ||
      (isDisabling && disablingSlug === slug)
    );
  }, [isEnabling, enablingSlug, isDisabling, disablingSlug]);

  // Define columns with TanStack Table
  // eslint-disable-next-line react-hooks/exhaustive-deps
  const columns = useMemo(() => columnHelper.columns([
    columnHelper.accessor('name', {
      header: ({ column }) => (
        <SortableHeader
          label="Name"
          sorted={column.getIsSorted()}
          onClick={() => column.toggleSorting()}
        />
      ),
      cell: ({ row }) => {
        const mod = row.original;
        return (
          <div>
            <div className="font-medium">
              <a
                href={
                  mod.assetId > 0
                    ? `https://mods.vintagestory.at/show/mod/${mod.assetId}`
                    : `https://mods.vintagestory.at/${mod.slug}`
                }
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1 hover:underline"
                data-testid={`mod-link-${mod.slug}`}
              >
                {mod.name || mod.slug}
                <ExternalLink className="h-3 w-3 text-muted-foreground" />
              </a>
            </div>
            {mod.name && (
              <div className="text-sm text-muted-foreground">{mod.slug}</div>
            )}
          </div>
        );
      },
      sortFn: (rowA, rowB) => {
        const a = (rowA.original.name || rowA.original.slug).toLowerCase();
        const b = (rowB.original.name || rowB.original.slug).toLowerCase();
        return a.localeCompare(b);
      },
    }),
    columnHelper.accessor('version', {
      header: ({ column }) => (
        <SortableHeader
          label="Version"
          sorted={column.getIsSorted()}
          onClick={() => column.toggleSorting()}
        />
      ),
      cell: ({ getValue }) => (
        <span className="text-muted-foreground">v{getValue()}</span>
      ),
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
      cell: ({ getValue }) => <CompatibilityBadge status={getValue()} />,
      enableSorting: false,
    }),
    columnHelper.accessor('enabled', {
      header: ({ column }) => (
        <SortableHeader
          label="Status"
          sorted={column.getIsSorted()}
          onClick={() => column.toggleSorting()}
        />
      ),
      cell: ({ row }) => {
        const mod = row.original;
        const isToggling = isTogglingMod(mod.slug);
        return (
          <div className="flex items-center gap-2">
            <Switch
              checked={mod.enabled}
              onCheckedChange={() => handleToggle(mod)}
              disabled={isToggling}
              data-testid={`mod-toggle-${mod.slug}`}
              aria-label={mod.enabled ? 'Disable mod' : 'Enable mod'}
            />
            {isToggling && (
              <Loader2
                className="h-4 w-4 animate-spin text-muted-foreground"
                data-testid={`mod-toggle-spinner-${mod.slug}`}
              />
            )}
          </div>
        );
      },
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
      cell: ({ row }) => {
        const mod = row.original;
        return (
          <Button
            variant="ghost"
            size="icon"
            onClick={() => handleRemoveClick(mod)}
            data-testid={`mod-remove-${mod.slug}`}
            aria-label={`Remove ${mod.name || mod.slug}`}
          >
            <Trash2 className="h-4 w-4 text-muted-foreground hover:text-destructive" />
          </Button>
        );
      },
      meta: { className: 'w-[80px]' },
    }),
  ]), [handleToggle, handleRemoveClick, isTogglingMod, gameVersion, handleUpdate, isChangingVersion]);

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

  if (mods.length === 0) {
    return (
      <div
        className="text-center py-8 text-muted-foreground"
        data-testid="mod-table-empty"
      >
        No mods installed yet
      </div>
    );
  }

  return (
    <>
      <Table data-testid="mod-table">
        <TableHeader>
          {table.getHeaderGroups().map((headerGroup) => (
            <TableRow key={headerGroup.id}>
              {headerGroup.headers.map((header) => (
                <TableHead
                  key={header.id}
                  className={
                    (header.column.columnDef.meta as { className?: string } | undefined)?.className
                  }
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
                <TableCell key={cell.id}>
                  {flexRender(cell.column.columnDef.cell, cell.getContext())}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <VersionChangeConfirmDialog
        confirmation={versionChange.confirmation}
        gameVersion={gameVersion}
        onConfirm={versionChange.confirm}
        onCancel={versionChange.cancel}
      />

      {/* Remove confirmation dialog */}
      <AlertDialog
        open={!!modToRemove}
        onOpenChange={(open) => !open && handleRemoveCancel()}
      >
        <AlertDialogContent data-testid="remove-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Remove {modToRemove?.name || modToRemove?.slug}?</AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the mod from your server. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              onClick={handleRemoveCancel}
              data-testid="remove-dialog-cancel"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              onClick={handleRemoveConfirm}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
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
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}
