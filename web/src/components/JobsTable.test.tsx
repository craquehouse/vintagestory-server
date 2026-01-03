import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { JobsTable } from './JobsTable';
import type { JobInfo } from '@/hooks/use-jobs';

// Mock jobs data (camelCase as transformed by API client)
const mockJobs: JobInfo[] = [
  {
    id: 'mod_cache_refresh',
    nextRunTime: '2026-01-02T15:30:00Z',
    triggerType: 'interval',
    triggerDetails: 'every 3600 seconds',
  },
  {
    id: 'server_versions_check',
    nextRunTime: '2026-01-03T00:00:00Z',
    triggerType: 'interval',
    triggerDetails: 'every 86400 seconds',
  },
];

describe('JobsTable', () => {
  describe('empty state (AC: 3)', () => {
    it('shows empty state when no jobs provided', () => {
      render(<JobsTable jobs={[]} />);

      expect(screen.getByTestId('jobs-table-empty')).toBeInTheDocument();
      expect(screen.getByText('No scheduled jobs')).toBeInTheDocument();
      expect(screen.getByText(/Jobs are registered when the server starts/)).toBeInTheDocument();
      expect(screen.getByText(/Check API Settings to configure job intervals/)).toBeInTheDocument();
    });

    it('does not render table when empty', () => {
      render(<JobsTable jobs={[]} />);

      expect(screen.queryByTestId('jobs-table')).not.toBeInTheDocument();
    });
  });

  describe('table rendering (AC: 1, 2)', () => {
    it('renders table when jobs are provided', () => {
      render(<JobsTable jobs={mockJobs} />);

      expect(screen.getByTestId('jobs-table')).toBeInTheDocument();
    });

    it('renders table headers', () => {
      render(<JobsTable jobs={mockJobs} />);

      expect(screen.getByText('Job Name')).toBeInTheDocument();
      expect(screen.getByText('Schedule')).toBeInTheDocument();
      expect(screen.getByText('Next Run')).toBeInTheDocument();
      expect(screen.getByText('Status')).toBeInTheDocument();
    });

    it('renders a row for each job', () => {
      render(<JobsTable jobs={mockJobs} />);

      expect(screen.getByTestId('job-row-mod_cache_refresh')).toBeInTheDocument();
      expect(screen.getByTestId('job-row-server_versions_check')).toBeInTheDocument();
    });
  });

  describe('job name column (AC: 2)', () => {
    it('displays job id in code element', () => {
      render(<JobsTable jobs={mockJobs} />);

      expect(screen.getByTestId('job-name-mod_cache_refresh')).toBeInTheDocument();
      expect(screen.getByText('mod_cache_refresh')).toBeInTheDocument();
      expect(screen.getByText('server_versions_check')).toBeInTheDocument();
    });
  });

  describe('schedule column (AC: 2)', () => {
    it('formats seconds to human-readable intervals', () => {
      render(<JobsTable jobs={mockJobs} />);

      // 3600 seconds = 1 hour
      expect(screen.getByTestId('job-schedule-mod_cache_refresh')).toHaveTextContent('every 1h');
      // 86400 seconds = 24 hours
      expect(screen.getByTestId('job-schedule-server_versions_check')).toHaveTextContent('every 24h');
    });

    it('formats minutes correctly', () => {
      const jobs: JobInfo[] = [
        {
          id: 'quick_job',
          nextRunTime: '2026-01-02T15:30:00Z',
          triggerType: 'interval',
          triggerDetails: 'every 300 seconds',
        },
      ];

      render(<JobsTable jobs={jobs} />);

      expect(screen.getByTestId('job-schedule-quick_job')).toHaveTextContent('every 5m');
    });

    it('shows seconds for small intervals', () => {
      const jobs: JobInfo[] = [
        {
          id: 'fast_job',
          nextRunTime: '2026-01-02T15:30:00Z',
          triggerType: 'interval',
          triggerDetails: 'every 30 seconds',
        },
      ];

      render(<JobsTable jobs={jobs} />);

      expect(screen.getByTestId('job-schedule-fast_job')).toHaveTextContent('every 30s');
    });

    it('passes through non-standard formats', () => {
      const jobs: JobInfo[] = [
        {
          id: 'cron_job',
          nextRunTime: '2026-01-02T15:30:00Z',
          triggerType: 'cron',
          triggerDetails: '0 0 * * *',
        },
      ];

      render(<JobsTable jobs={jobs} />);

      expect(screen.getByTestId('job-schedule-cron_job')).toHaveTextContent('0 0 * * *');
    });
  });

  describe('next run column (AC: 2)', () => {
    it('displays formatted next run time', () => {
      render(<JobsTable jobs={mockJobs} />);

      const nextRunCell = screen.getByTestId('job-next-run-mod_cache_refresh');
      expect(nextRunCell).toBeInTheDocument();
      // Just check it contains a date format (locale-dependent)
      expect(nextRunCell.textContent).toMatch(/\d/);
    });

    it('displays "Never" for null nextRunTime', () => {
      const jobs: JobInfo[] = [
        {
          id: 'paused_job',
          nextRunTime: null,
          triggerType: 'interval',
          triggerDetails: 'every 3600 seconds',
        },
      ];

      render(<JobsTable jobs={jobs} />);

      expect(screen.getByTestId('job-next-run-paused_job')).toHaveTextContent('Never');
    });
  });

  describe('status column (AC: 2)', () => {
    it('displays status badge with trigger type', () => {
      render(<JobsTable jobs={mockJobs} />);

      expect(screen.getByTestId('job-status-mod_cache_refresh')).toBeInTheDocument();
      expect(screen.getByTestId('job-status-mod_cache_refresh')).toHaveTextContent('interval');
    });

    it('displays badge with clock icon', () => {
      render(<JobsTable jobs={mockJobs} />);

      const badge = screen.getByTestId('job-status-mod_cache_refresh');
      expect(badge.querySelector('svg')).toBeInTheDocument();
    });

    it('displays cron trigger type', () => {
      const jobs: JobInfo[] = [
        {
          id: 'cron_job',
          nextRunTime: '2026-01-02T00:00:00Z',
          triggerType: 'cron',
          triggerDetails: '0 0 * * *',
        },
      ];

      render(<JobsTable jobs={jobs} />);

      expect(screen.getByTestId('job-status-cron_job')).toHaveTextContent('cron');
    });
  });

  describe('accessibility', () => {
    it('uses semantic table elements', () => {
      render(<JobsTable jobs={mockJobs} />);

      expect(screen.getByRole('table')).toBeInTheDocument();
      expect(screen.getAllByRole('columnheader')).toHaveLength(4);
      expect(screen.getAllByRole('row')).toHaveLength(3); // 1 header + 2 data rows
    });
  });
});
