import { describe, it, expect } from 'vitest';
import { act, render, screen, within } from '@testing-library/react';
import { JobsTable } from './JobsTable';
import type { JobInfo } from '@/hooks/use-jobs';
import { setViewportWidth } from '../../tests/viewport';

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
      expect(screen.getByTestId('job-schedule-server_versions_check')).toHaveTextContent(
        'every 24h'
      );
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

  // Story 21.7 (AC 6): below lg (1024px) each job is a card; tests/setup.ts resets the width
  describe('cards below lg (Story 21.7)', () => {
    const FIELDS = ['Job Name', 'Schedule', 'Next Run', 'Status'];
    const VALUE_IDS = ['job-name', 'job-schedule', 'job-next-run', 'job-status'];

    /** The four values' texts for a job, by test ID. */
    function valueTexts(id: string): string[] {
      return VALUE_IDS.map((prefix) => screen.getByTestId(`${prefix}-${id}`).textContent ?? '');
    }

    it('shows a card per job at 390px, and no table', () => {
      setViewportWidth(390);
      render(<JobsTable jobs={mockJobs} />);

      const cards = screen.getByTestId('job-cards');
      expect(cards.tagName).toBe('UL');
      expect(cards).toHaveAttribute('aria-label', 'Scheduled jobs');
      expect(screen.queryByTestId('jobs-table')).not.toBeInTheDocument();
      expect(screen.queryByRole('table')).not.toBeInTheDocument();
      expect(screen.queryByTestId(/^job-row-/)).not.toBeInTheDocument();
      expect(within(cards).getAllByRole('listitem')).toHaveLength(2);
      expect(screen.getByTestId('job-card-mod_cache_refresh')).toBeInTheDocument();
      expect(screen.getByTestId('job-card-server_versions_check')).toBeInTheDocument();
    });

    it('labels the four values of each card', () => {
      setViewportWidth(390);
      render(<JobsTable jobs={mockJobs} />);

      for (const job of mockJobs) {
        const card = screen.getByTestId(`job-card-${job.id}`);
        const terms = card.querySelectorAll('dt');
        expect([...terms].map((term) => term.textContent)).toEqual(FIELDS);
        expect(card.querySelectorAll('dd')).toHaveLength(4);
        for (const prefix of VALUE_IDS) {
          const value = within(card).getByTestId(`${prefix}-${job.id}`);
          expect(value.closest('dd')).not.toBeNull();
        }
      }
    });

    it('shows the same four texts as the table', () => {
      const { unmount } = render(<JobsTable jobs={mockJobs} />);
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument();
      const inTable = mockJobs.map((job) => valueTexts(job.id));
      unmount();

      setViewportWidth(390);
      render(<JobsTable jobs={mockJobs} />);
      expect(screen.getByTestId('job-cards')).toBeInTheDocument();
      expect(mockJobs.map((job) => valueTexts(job.id))).toEqual(inTable);
    });

    it('shows cards at 1023px and the table at 1024px', () => {
      setViewportWidth(1023);
      const { unmount } = render(<JobsTable jobs={mockJobs} />);
      expect(screen.getByTestId('job-cards')).toBeInTheDocument();
      expect(screen.queryByTestId('jobs-table')).not.toBeInTheDocument();
      unmount();

      setViewportWidth(1024);
      render(<JobsTable jobs={mockJobs} />);
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument();
      expect(screen.queryByTestId('job-cards')).not.toBeInTheDocument();
    });

    it('swaps the layout when the width changes, never showing both', () => {
      render(<JobsTable jobs={mockJobs} />);
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument();
      expect(screen.queryByTestId('job-cards')).not.toBeInTheDocument();

      act(() => setViewportWidth(390));
      expect(screen.getByTestId('job-cards')).toBeInTheDocument();
      expect(screen.queryByTestId('jobs-table')).not.toBeInTheDocument();
      expect(screen.getAllByTestId('job-name-mod_cache_refresh')).toHaveLength(1);

      act(() => setViewportWidth(1280));
      expect(screen.getByTestId('jobs-table')).toBeInTheDocument();
      expect(screen.queryByTestId('job-cards')).not.toBeInTheDocument();
      expect(screen.getAllByTestId('job-name-mod_cache_refresh')).toHaveLength(1);
    });

    it('shows the same empty state at 390px', () => {
      setViewportWidth(390);
      render(<JobsTable jobs={[]} />);

      expect(screen.getByTestId('jobs-table-empty')).toBeInTheDocument();
      expect(screen.getByText('No scheduled jobs')).toBeInTheDocument();
      expect(screen.queryByTestId('job-cards')).not.toBeInTheDocument();
    });

    it('shows "Never" in a card for a null next run time', () => {
      setViewportWidth(390);
      render(
        <JobsTable
          jobs={[
            {
              id: 'paused_job',
              nextRunTime: null,
              triggerType: 'interval',
              triggerDetails: 'every 3600 seconds',
            },
          ]}
        />
      );

      const card = screen.getByTestId('job-card-paused_job');
      expect(within(card).getByTestId('job-next-run-paused_job')).toHaveTextContent('Never');
    });
  });
});
