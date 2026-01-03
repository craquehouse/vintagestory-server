/**
 * JobsTable - Table displaying scheduled jobs using TanStack Table.
 *
 * Features:
 * - Displays job name, schedule, next run time, and status badge
 * - Empty state when no jobs are registered
 * - Uses TanStack Table for table management
 *
 * Story 8.3: Job Configuration UI
 */

import {
  createColumnHelper,
  useReactTable,
  getCoreRowModel,
  flexRender,
} from '@tanstack/react-table';
import { Clock } from 'lucide-react';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Badge } from '@/components/ui/badge';
import type { JobInfo } from '@/hooks/use-jobs';

interface JobsTableProps {
  /** Array of jobs to display */
  jobs: JobInfo[];
}

const columnHelper = createColumnHelper<JobInfo>();

/**
 * Format a job's next run time for display.
 * Returns a human-readable string or 'Never' if null.
 */
function formatNextRunTime(value: string | null): string {
  if (!value) return 'Never';
  return new Date(value).toLocaleString();
}

/**
 * Format trigger details into a more readable form.
 * Converts "every X seconds" to friendlier units.
 */
function formatSchedule(details: string): string {
  const match = details.match(/every (\d+) seconds/);
  if (match) {
    const seconds = parseInt(match[1], 10);
    if (seconds >= 86400) {
      const hours = Math.round(seconds / 3600);
      return `every ${hours}h`;
    }
    if (seconds >= 3600) {
      const hours = Math.round(seconds / 3600);
      return `every ${hours}h`;
    }
    if (seconds >= 60) {
      const minutes = Math.round(seconds / 60);
      return `every ${minutes}m`;
    }
    return `every ${seconds}s`;
  }
  return details;
}

const columns = [
  columnHelper.accessor('id', {
    header: 'Job Name',
    cell: (info) => (
      <code className="text-sm font-mono" data-testid={`job-name-${info.getValue()}`}>
        {info.getValue()}
      </code>
    ),
  }),
  columnHelper.accessor('triggerDetails', {
    header: 'Schedule',
    cell: (info) => (
      <span data-testid={`job-schedule-${info.row.original.id}`}>
        {formatSchedule(info.getValue())}
      </span>
    ),
  }),
  columnHelper.accessor('nextRunTime', {
    header: 'Next Run',
    cell: (info) => (
      <span data-testid={`job-next-run-${info.row.original.id}`}>
        {formatNextRunTime(info.getValue())}
      </span>
    ),
  }),
  columnHelper.accessor('triggerType', {
    header: 'Status',
    cell: (info) => (
      <Badge
        variant="outline"
        className="gap-1"
        data-testid={`job-status-${info.row.original.id}`}
      >
        <Clock className="h-3 w-3" />
        {info.getValue()}
      </Badge>
    ),
  }),
];

/**
 * Table displaying scheduled jobs with TanStack Table.
 *
 * @example
 * <JobsTable jobs={jobs} />
 */
export function JobsTable({ jobs }: JobsTableProps) {
  const table = useReactTable({
    data: jobs,
    columns,
    getCoreRowModel: getCoreRowModel(),
  });

  if (jobs.length === 0) {
    return (
      <div
        className="text-center py-8 text-muted-foreground"
        data-testid="jobs-table-empty"
      >
        <div className="text-lg font-medium mb-2">No scheduled jobs</div>
        <div className="text-sm">
          Jobs are registered when the server starts.
          <br />
          Check API Settings to configure job intervals.
        </div>
      </div>
    );
  }

  return (
    <Table data-testid="jobs-table">
      <TableHeader>
        {table.getHeaderGroups().map((headerGroup) => (
          <TableRow key={headerGroup.id}>
            {headerGroup.headers.map((header) => (
              <TableHead key={header.id}>
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
          <TableRow key={row.id} data-testid={`job-row-${row.original.id}`}>
            {row.getVisibleCells().map((cell) => (
              <TableCell key={cell.id}>
                {flexRender(cell.column.columnDef.cell, cell.getContext())}
              </TableCell>
            ))}
          </TableRow>
        ))}
      </TableBody>
    </Table>
  );
}
