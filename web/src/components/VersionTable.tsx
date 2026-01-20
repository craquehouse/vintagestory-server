/**
 * VersionTable - Table displaying VintageStory server versions with sorting.
 *
 * Features:
 * - Sortable columns (Version, Channel, Size)
 * - Responsive column hiding (Size hidden on mobile)
 * - Status badges (Latest, Installed)
 * - Row highlighting for newer versions
 * - Loading skeleton and empty states
 *
 * VSS-lvp [UI-033]: Replace card view with table view
 */

import { useState, useMemo } from 'react';
import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  flexRender,
  type SortingState,
} from '@tanstack/react-table';
import { Check, ExternalLink, ChevronUp, ChevronDown } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';
import type { VersionInfo, VersionChannel } from '@/api/types';

interface VersionTableProps {
  /** Array of versions to display */
  versions: VersionInfo[];
  /** Whether the data is currently loading */
  isLoading?: boolean;
  /** Currently installed version string for highlighting */
  installedVersion?: string | null;
  /** Click handler for version selection */
  onVersionSelect?: (version: string) => void;
}

/**
 * Number of skeleton rows to show during loading state.
 */
const SKELETON_COUNT = 8;

/**
 * Channel badge styles matching VersionCard.
 */
const channelStyles: Record<VersionChannel, { label: string; className: string }> = {
  stable: {
    label: 'Stable',
    className: 'text-success border-success/30 bg-success/10',
  },
  unstable: {
    label: 'Unstable',
    className: 'text-warning border-warning/30 bg-warning/10',
  },
};

/**
 * Compare two version strings semantically.
 * Handles versions like "1.20.0", "1.19.8", "1.20.1-rc.1".
 *
 * @returns negative if a < b, positive if a > b, 0 if equal
 */
function compareVersions(a: string, b: string): number {
  // Split into main version and prerelease suffix
  const [aMain, aPrerelease] = a.split('-');
  const [bMain, bPrerelease] = b.split('-');

  // Compare main version parts numerically
  const aParts = aMain.split('.').map(Number);
  const bParts = bMain.split('.').map(Number);

  for (let i = 0; i < Math.max(aParts.length, bParts.length); i++) {
    const aPart = aParts[i] ?? 0;
    const bPart = bParts[i] ?? 0;
    if (aPart !== bPart) {
      return aPart - bPart;
    }
  }

  // If main versions are equal, handle prerelease
  // No prerelease > prerelease (1.20.0 > 1.20.0-rc.1)
  if (!aPrerelease && bPrerelease) return 1;
  if (aPrerelease && !bPrerelease) return -1;
  if (!aPrerelease && !bPrerelease) return 0;

  // Both have prerelease, compare alphabetically
  return aPrerelease.localeCompare(bPrerelease);
}

/**
 * Extended version info with computed isNewer flag for table rows.
 */
interface VersionRowData extends VersionInfo {
  isNewer: boolean;
  isInstalled: boolean;
}

const columnHelper = createColumnHelper<VersionRowData>();

/**
 * Sort indicator component for sortable column headers.
 */
function SortIndicator({ direction }: { direction: 'asc' | 'desc' | false }) {
  if (!direction) return null;
  return direction === 'asc' ? (
    <ChevronUp className="h-4 w-4 ml-1" />
  ) : (
    <ChevronDown className="h-4 w-4 ml-1" />
  );
}

/**
 * Create columns with access to onVersionSelect callback.
 */
function createColumns(onVersionSelect?: (version: string) => void) {
  return [
    columnHelper.accessor('version', {
      header: 'Version',
      cell: (info) => {
        const version = info.getValue();
        return (
          <span
            className="inline-flex items-center gap-1.5 font-medium"
            data-testid={`version-table-version-${version}`}
          >
            {version}
            <a
              href={`https://wiki.vintagestory.at/${version}`}
              target="_blank"
              rel="noopener noreferrer"
              className="text-muted-foreground hover:text-foreground focus:outline-none focus:ring-1 focus:ring-ring rounded"
              onClick={(e) => e.stopPropagation()}
              data-testid={`version-table-changelog-${version}`}
              title="View changelog"
              aria-label={`View changelog for version ${version} (opens in new tab)`}
            >
              <ExternalLink className="h-3.5 w-3.5" />
            </a>
          </span>
        );
      },
      sortingFn: 'alphanumeric',
    }),
    columnHelper.accessor('channel', {
      header: 'Channel',
      cell: (info) => {
        const channel = info.getValue();
        const styles = channelStyles[channel];
        return (
          <Badge
            variant="outline"
            className={styles.className}
            data-testid={`version-table-channel-${info.row.original.version}`}
          >
            {styles.label}
          </Badge>
        );
      },
      sortingFn: 'alphanumeric',
    }),
    columnHelper.accessor('filesize', {
      header: 'Size',
      cell: (info) => (
        <span
          className="text-muted-foreground"
          data-testid={`version-table-size-${info.row.original.version}`}
        >
          {info.getValue()}
        </span>
      ),
      sortingFn: 'alphanumeric',
      meta: {
        className: 'hidden sm:table-cell',
      },
    }),
    columnHelper.display({
      id: 'status',
      header: 'Status',
      cell: (info) => {
        const { isLatest } = info.row.original;
        const { isInstalled } = info.row.original;
        const version = info.row.original.version;

        return (
          <div className="flex flex-wrap gap-2">
            {isLatest && (
              <Badge
                variant="secondary"
                data-testid={`version-table-latest-${version}`}
              >
                Latest
              </Badge>
            )}
            {isInstalled && (
              <div
                className="flex items-center gap-1 text-sm text-success"
                data-testid={`version-table-installed-${version}`}
              >
                <Check className="h-4 w-4" />
                <span>Installed</span>
              </div>
            )}
            {!isLatest && !isInstalled && (
              <span className="text-muted-foreground">-</span>
            )}
          </div>
        );
      },
    }),
    columnHelper.display({
      id: 'actions',
      header: 'Actions',
      cell: (info) => {
        const version = info.row.original.version;
        return (
          <Button
            variant="outline"
            size="sm"
            onClick={() => onVersionSelect?.(version)}
            disabled={!onVersionSelect}
            data-testid={`version-table-select-${version}`}
          >
            Select
          </Button>
        );
      },
    }),
  ];
}

/**
 * Skeleton row component for loading state.
 */
function VersionTableSkeleton() {
  return (
    <Table data-testid="version-table-loading">
      <TableHeader>
        <TableRow>
          <TableHead>Version</TableHead>
          <TableHead>Channel</TableHead>
          <TableHead className="hidden sm:table-cell">Size</TableHead>
          <TableHead>Status</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: SKELETON_COUNT }).map((_, index) => (
          <TableRow key={index} data-testid="version-table-skeleton-row">
            <TableCell><Skeleton className="h-5 w-20" /></TableCell>
            <TableCell><Skeleton className="h-5 w-16" /></TableCell>
            <TableCell className="hidden sm:table-cell"><Skeleton className="h-5 w-16" /></TableCell>
            <TableCell><Skeleton className="h-5 w-16" /></TableCell>
            <TableCell><Skeleton className="h-8 w-16" /></TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}

/**
 * Table displaying VintageStory server versions with sorting support.
 *
 * @example
 * <VersionTable
 *   versions={versionData}
 *   isLoading={isLoading}
 *   installedVersion={serverStatus?.version}
 *   onVersionSelect={handleVersionSelect}
 * />
 */
export function VersionTable({
  versions,
  isLoading = false,
  installedVersion,
  onVersionSelect,
}: VersionTableProps) {
  // Default sort: version descending (newest first)
  const [sorting, setSorting] = useState<SortingState>([
    { id: 'version', desc: true },
  ]);

  // Memoize columns to prevent unnecessary re-renders
  const columns = useMemo(
    () => createColumns(onVersionSelect),
    [onVersionSelect]
  );

  // Compute isNewer and isInstalled for each row with proper version comparison
  const rowData = useMemo<VersionRowData[]>(
    () =>
      versions.map((version) => ({
        ...version,
        isNewer: installedVersion
          ? compareVersions(version.version, installedVersion) > 0
          : false,
        isInstalled: installedVersion === version.version,
      })),
    [versions, installedVersion]
  );

  const table = useReactTable({
    data: rowData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
  });

  if (isLoading) {
    return <VersionTableSkeleton />;
  }

  if (versions.length === 0) {
    return (
      <div
        className="text-center py-8 text-muted-foreground"
        data-testid="version-table-empty"
      >
        No versions found for this channel.
      </div>
    );
  }

  return (
    <Table data-testid="version-table">
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => {
              const canSort = header.column.getCanSort();
              const sortDirection = header.column.getIsSorted();
              const meta = header.column.columnDef.meta as { className?: string } | undefined;

              // Map sort direction to aria-sort value
              const ariaSort = sortDirection
                ? sortDirection === 'asc'
                  ? 'ascending'
                  : 'descending'
                : undefined;

              const handleKeyDown = canSort
                ? (e: React.KeyboardEvent) => {
                    if (e.key === 'Enter' || e.key === ' ') {
                      e.preventDefault();
                      header.column.getToggleSortingHandler()?.(e);
                    }
                  }
                : undefined;

              return (
                <TableHead
                  key={header.id}
                  className={cn(
                    canSort && 'cursor-pointer select-none',
                    meta?.className
                  )}
                  onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                  onKeyDown={handleKeyDown}
                  tabIndex={canSort ? 0 : undefined}
                  role={canSort ? 'columnheader' : undefined}
                  aria-sort={ariaSort}
                  data-testid={`version-table-header-${header.id}`}
                >
                  <span className="inline-flex items-center">
                    {header.isPlaceholder
                      ? null
                      : flexRender(header.column.columnDef.header, header.getContext())}
                    {canSort && <SortIndicator direction={sortDirection} />}
                  </span>
                </TableHead>
              );
            })}
          </TableRow>
        ))}
      </TableHeader>
      <TableBody>
        {table.getRowModel().rows.map((row) => {
          const { isNewer } = row.original;

          return (
            <TableRow
              key={row.id}
              className={cn(isNewer && 'bg-primary/5')}
              data-testid={`version-table-row-${row.original.version}`}
            >
              {row.getVisibleCells().map((cell) => {
                const cellMeta = cell.column.columnDef.meta as { className?: string } | undefined;
                return (
                  <TableCell key={cell.id} className={cellMeta?.className}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </TableCell>
                );
              })}
            </TableRow>
          );
        })}
      </TableBody>
    </Table>
  );
}
