/**
 * JobsTable - Table displaying scheduled jobs using TanStack Table.
 *
 * Features:
 * - Displays job name, schedule, next run time, and status badge
 * - Empty state when no jobs are registered
 * - Uses TanStack Table for table management
 * - Below lg (1024px) each job is a card with the same four labelled values (Story 21.7)
 *
 * Story 8.3: Job Configuration UI
 */

import type { ReactNode } from 'react';
import { createColumnHelper, flexRender, tableFeatures, useTable } from '@tanstack/react-table';
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
import { LG_UP_QUERY, useMediaQuery } from '@/hooks/use-media-query';

interface JobsTableProps {
  /** Array of jobs to display */
  jobs: JobInfo[];
}

const features = tableFeatures({});

const columnHelper = createColumnHelper<typeof features, JobInfo>();

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

/**
 * The four values of a job, defined once: the table's columns and the cards below lg are both
 * built from this list, so a label or a formatter cannot differ between layouts (Story 21.7).
 */
const FIELDS: { id: string; label: string; render: (job: JobInfo) => ReactNode }[] = [
  {
    id: 'id',
    label: 'Job Name',
    render: (job) => (
      <code className="text-sm font-mono" data-testid={`job-name-${job.id}`}>
        {job.id}
      </code>
    ),
  },
  {
    id: 'triggerDetails',
    label: 'Schedule',
    render: (job) => (
      <span data-testid={`job-schedule-${job.id}`}>{formatSchedule(job.triggerDetails)}</span>
    ),
  },
  {
    id: 'nextRunTime',
    label: 'Next Run',
    render: (job) => (
      <span data-testid={`job-next-run-${job.id}`}>{formatNextRunTime(job.nextRunTime)}</span>
    ),
  },
  {
    id: 'triggerType',
    label: 'Status',
    render: (job) => (
      <Badge variant="outline" className="gap-1" data-testid={`job-status-${job.id}`}>
        <Clock className="h-3 w-3" />
        {job.triggerType}
      </Badge>
    ),
  },
];

const columns = columnHelper.columns(
  FIELDS.map((field) =>
    columnHelper.display({
      id: field.id,
      header: field.label,
      cell: (info) => field.render(info.row.original),
    })
  )
);

/** One card per job below lg (Story 21.7): the four values as a labelled list. */
function JobCards({ jobs }: JobsTableProps) {
  return (
    <ul className="space-y-3" aria-label="Scheduled jobs" data-testid="job-cards">
      {jobs.map((job) => (
        <li
          key={job.id}
          className="rounded-lg border bg-card p-3 text-card-foreground"
          data-testid={`job-card-${job.id}`}
        >
          <dl className="grid grid-cols-[auto_minmax(0,1fr)] items-center gap-x-3 gap-y-2 text-sm">
            {FIELDS.map((field) => (
              <div key={field.id} className="contents">
                <dt className="text-muted-foreground">{field.label}</dt>
                <dd className="min-w-0 break-words">{field.render(job)}</dd>
              </div>
            ))}
          </dl>
        </li>
      ))}
    </ul>
  );
}

/**
 * Table displaying scheduled jobs with TanStack Table.
 *
 * @example
 * <JobsTable jobs={jobs} />
 */
export function JobsTable({ jobs }: JobsTableProps) {
  // Story 21.7: one layout mounted, the table from lg (1024px) and cards below
  const isTableLayout = useMediaQuery(LG_UP_QUERY);
  const table = useTable({
    features,
    data: jobs,
    columns,
  });

  if (jobs.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground" data-testid="jobs-table-empty">
        <div className="text-lg font-medium mb-2">No scheduled jobs</div>
        <div className="text-sm">
          Jobs are registered when the server starts.
          <br />
          Check API Settings to configure job intervals.
        </div>
      </div>
    );
  }

  if (!isTableLayout) {
    return <JobCards jobs={jobs} />;
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
            {row.getAllCells().map((cell) => (
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
