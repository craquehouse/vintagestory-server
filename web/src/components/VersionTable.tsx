/**
 * VersionTable - Table displaying VintageStory server versions with sorting.
 *
 * Features:
 * - Sortable columns (Version, Channel, Size)
 * - Responsive column hiding (Size hidden on mobile; below sm Channel and Status are hidden
 *   and shown under the version, Story 21.7)
 * - Status badges (Latest, Installed)
 * - Row highlighting for newer versions
 * - Loading skeleton and empty states
 *
 * VSS-lvp [UI-033]: Replace card view with table view
 */

import { useState, useMemo } from 'react';
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
import { compareVersions } from '@/lib/version-compare';
import { parseFilesize } from '@/lib/numeric-utils';
import { ariaSort } from '@/lib/table-aria-sort';
import { OPENS_IN_NEW_TAB } from '@/lib/new-tab';
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
 * Compare two file sizes ("45.2 MB") by size; sizes that cannot be read come last, in
 * text order. Story 21.5.
 */
function compareFilesizes(a: string, b: string): number {
  const bytesA = parseFilesize(a);
  const bytesB = parseFilesize(b);
  if (bytesA !== null && bytesB !== null) return Math.sign(bytesA - bytesB);
  if (bytesA !== null) return -1;
  if (bytesB !== null) return 1;
  return a < b ? -1 : a > b ? 1 : 0;
}

/**
 * Extended version info with computed isNewer flag for table rows.
 */
interface VersionRowData extends VersionInfo {
  isNewer: boolean;
  isInstalled: boolean;
}

const features = tableFeatures({
  rowSortingFeature,
  sortedRowModel: createSortedRowModel(),
  sortFns,
});

const columnHelper = createColumnHelper<typeof features, VersionRowData>();

/** A channel badge; the Channel column and the inline row below sm both use it (Story 21.7). */
function ChannelBadge({ channel, testId }: { channel: VersionChannel; testId: string }) {
  const styles = channelStyles[channel];
  return (
    <Badge variant="outline" className={styles.className} data-testid={testId}>
      {styles.label}
    </Badge>
  );
}

/** The "Latest" mark, in the Status column and in the inline row below sm. */
function LatestMark({ testId }: { testId: string }) {
  return (
    <Badge variant="secondary" data-testid={testId}>
      Latest
    </Badge>
  );
}

/** The "Installed" mark, in the Status column and in the inline row below sm. */
function InstalledMark({ testId }: { testId: string }) {
  return (
    <div className="flex items-center gap-1 text-sm text-success" data-testid={testId}>
      <Check className="h-4 w-4" />
      <span>Installed</span>
    </div>
  );
}

/**
 * Sort indicator component for sortable column headers.
 */
function SortIndicator({ direction }: { direction: 'asc' | 'desc' | false }) {
  if (!direction) return null;
  return direction === 'asc' ? (
    <ChevronUp className="h-4 w-4 ml-1" aria-hidden="true" />
  ) : (
    <ChevronDown className="h-4 w-4 ml-1" aria-hidden="true" />
  );
}

/**
 * Create columns with access to onVersionSelect callback.
 */
function createColumns(onVersionSelect?: (version: string) => void) {
  return columnHelper.columns([
    columnHelper.accessor('version', {
      header: 'Version',
      cell: (info) => {
        const version = info.getValue();
        const { channel, isLatest, isInstalled } = info.row.original;
        return (
          <div className="flex flex-col items-start gap-1">
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
                aria-label={`View changelog for version ${version} ${OPENS_IN_NEW_TAB}`}
              >
                <ExternalLink className="h-3.5 w-3.5" aria-hidden="true" />
              </a>
            </span>
            {/* Story 21.7: below sm the Channel and Status columns are hidden; shown here instead */}
            <div className="flex flex-wrap items-center gap-1 sm:hidden">
              <ChannelBadge channel={channel} testId={`version-table-inline-channel-${version}`} />
              {isLatest && <LatestMark testId={`version-table-inline-latest-${version}`} />}
              {isInstalled && (
                <InstalledMark testId={`version-table-inline-installed-${version}`} />
              )}
            </div>
          </div>
        );
      },
      sortFn: (rowA, rowB) => compareVersions(rowA.original.version, rowB.original.version),
    }),
    columnHelper.accessor('channel', {
      header: 'Channel',
      cell: (info) => (
        <ChannelBadge
          channel={info.getValue()}
          testId={`version-table-channel-${info.row.original.version}`}
        />
      ),
      sortFn: 'alphanumeric',
      // Story 21.7: below sm the channel is shown under the version
      meta: {
        className: 'hidden sm:table-cell',
      },
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
      sortFn: (rowA, rowB) => compareFilesizes(rowA.original.filesize, rowB.original.filesize),
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
            {isLatest && <LatestMark testId={`version-table-latest-${version}`} />}
            {isInstalled && <InstalledMark testId={`version-table-installed-${version}`} />}
            {!isLatest && !isInstalled && <span className="text-muted-foreground">-</span>}
          </div>
        );
      },
      // Story 21.7: below sm "Latest" and "Installed" are shown under the version
      meta: {
        className: 'hidden sm:table-cell',
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
            className="max-lg:h-11"
            onClick={() => onVersionSelect?.(version)}
            disabled={!onVersionSelect}
            data-testid={`version-table-select-${version}`}
          >
            Select
          </Button>
        );
      },
    }),
  ]);
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
          <TableHead className="hidden sm:table-cell">Channel</TableHead>
          <TableHead className="hidden sm:table-cell">Size</TableHead>
          <TableHead className="hidden sm:table-cell">Status</TableHead>
          <TableHead>Actions</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {Array.from({ length: SKELETON_COUNT }).map((_, index) => (
          <TableRow key={index} data-testid="version-table-skeleton-row">
            <TableCell>
              <Skeleton className="h-5 w-20" />
            </TableCell>
            <TableCell className="hidden sm:table-cell">
              <Skeleton className="h-5 w-16" />
            </TableCell>
            <TableCell className="hidden sm:table-cell">
              <Skeleton className="h-5 w-16" />
            </TableCell>
            <TableCell className="hidden sm:table-cell">
              <Skeleton className="h-5 w-16" />
            </TableCell>
            <TableCell>
              <Skeleton className="h-8 w-16" />
            </TableCell>
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
  const [sorting, setSorting] = useState<SortingState>([{ id: 'version', desc: true }]);

  // Memoize columns to prevent unnecessary re-renders
  const columns = useMemo(() => createColumns(onVersionSelect), [onVersionSelect]);

  // Compute isNewer and isInstalled for each row with proper version comparison
  const rowData = useMemo<VersionRowData[]>(
    () =>
      versions.map((version) => ({
        ...version,
        isNewer: installedVersion ? compareVersions(version.version, installedVersion) > 0 : false,
        isInstalled: installedVersion === version.version,
      })),
    [versions, installedVersion]
  );

  const table = useTable({
    features,
    data: rowData,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
  });

  if (isLoading) {
    return <VersionTableSkeleton />;
  }

  if (versions.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground" data-testid="version-table-empty">
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
              const meta = header.column.columnDef.meta;

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
                  className={cn(canSort && 'cursor-pointer select-none', meta?.className)}
                  onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                  onKeyDown={handleKeyDown}
                  tabIndex={canSort ? 0 : undefined}
                  role={canSort ? 'columnheader' : undefined}
                  aria-sort={ariaSort(canSort, sortDirection)}
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
              {row.getAllCells().map((cell) => {
                const cellMeta = cell.column.columnDef.meta;
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
