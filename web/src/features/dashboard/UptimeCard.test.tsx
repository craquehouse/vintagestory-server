import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { UptimeCard } from './UptimeCard';

// Mock the StatCard component
vi.mock('@/components/StatCard', () => ({
  StatCard: ({
    icon: Icon,
    title,
    value,
    subtitle,
    testId,
  }: {
    icon: React.ComponentType;
    title: string;
    value: string | number;
    subtitle?: string;
    testId?: string;
  }) => (
    <div data-testid={testId}>
      <div data-testid={`${testId}-icon`}>
        <Icon />
      </div>
      <div data-testid={`${testId}-title`}>{title}</div>
      <div data-testid={`${testId}-value`}>{value}</div>
      {subtitle && <div data-testid={`${testId}-subtitle`}>{subtitle}</div>}
    </div>
  ),
}));

describe('UptimeCard', () => {
  describe('formatUptime utility function', () => {
    // Note: formatUptime is not exported, so we test it indirectly through the component

    describe('seconds only (< 60 seconds)', () => {
      it('formats 0 seconds', () => {
        render(<UptimeCard uptimeSeconds={0} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('0s');
      });

      it('formats single digit seconds', () => {
        render(<UptimeCard uptimeSeconds={5} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('5s');
      });

      it('formats double digit seconds', () => {
        render(<UptimeCard uptimeSeconds={45} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('45s');
      });

      it('formats 59 seconds', () => {
        render(<UptimeCard uptimeSeconds={59} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('59s');
      });

      it('rounds down fractional seconds', () => {
        render(<UptimeCard uptimeSeconds={45.7} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('45s');
      });
    });

    describe('minutes and seconds (60 to 3599 seconds)', () => {
      it('formats exactly 1 minute', () => {
        render(<UptimeCard uptimeSeconds={60} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1m');
      });

      it('formats 2 minutes 5 seconds', () => {
        render(<UptimeCard uptimeSeconds={125} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('2m 5s');
      });

      it('formats 45 minutes 30 seconds', () => {
        render(<UptimeCard uptimeSeconds={2730} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('45m 30s');
      });

      it('formats exactly 59 minutes', () => {
        render(<UptimeCard uptimeSeconds={3540} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('59m');
      });

      it('omits seconds when zero', () => {
        render(<UptimeCard uptimeSeconds={120} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('2m');
      });
    });

    describe('hours and minutes (3600 to 86399 seconds)', () => {
      it('formats exactly 1 hour', () => {
        render(<UptimeCard uptimeSeconds={3600} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1h');
      });

      it('formats 1 hour 1 minute', () => {
        render(<UptimeCard uptimeSeconds={3660} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1h 1m');
      });

      it('formats 5 hours 30 minutes', () => {
        render(<UptimeCard uptimeSeconds={19800} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('5h 30m');
      });

      it('formats 23 hours 59 minutes', () => {
        render(<UptimeCard uptimeSeconds={86340} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('23h 59m');
      });

      it('omits minutes when zero', () => {
        render(<UptimeCard uptimeSeconds={7200} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('2h');
      });

      it('does not display remaining seconds', () => {
        // 1h 1m 30s should display as "1h 1m" (seconds omitted)
        render(<UptimeCard uptimeSeconds={3690} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1h 1m');
      });
    });

    describe('days and hours (>= 86400 seconds)', () => {
      it('formats exactly 1 day', () => {
        render(<UptimeCard uptimeSeconds={86400} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1d');
      });

      it('formats 1 day 1 hour', () => {
        render(<UptimeCard uptimeSeconds={90000} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1d 1h');
      });

      it('formats 2 days 5 hours', () => {
        render(<UptimeCard uptimeSeconds={190800} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('2d 5h');
      });

      it('formats 7 days 12 hours', () => {
        render(<UptimeCard uptimeSeconds={648000} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('7d 12h');
      });

      it('omits hours when zero', () => {
        render(<UptimeCard uptimeSeconds={172800} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('2d');
      });

      it('does not display remaining minutes', () => {
        // 1d 1h 30m should display as "1d 1h" (minutes omitted)
        render(<UptimeCard uptimeSeconds={91800} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('1d 1h');
      });
    });

    describe('very large values', () => {
      it('formats 30 days', () => {
        render(<UptimeCard uptimeSeconds={2592000} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('30d');
      });

      it('formats 365 days', () => {
        render(<UptimeCard uptimeSeconds={31536000} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('365d');
      });

      it('formats 100 days 5 hours', () => {
        render(<UptimeCard uptimeSeconds={8658000} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('100d 5h');
      });
    });

    describe('invalid values', () => {
      it('handles NaN as invalid', () => {
        render(<UptimeCard uptimeSeconds={NaN} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('N/A');
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Uptime unavailable'
        );
      });

      it('handles Infinity as invalid', () => {
        render(<UptimeCard uptimeSeconds={Infinity} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('N/A');
      });

      it('handles negative values as invalid', () => {
        render(<UptimeCard uptimeSeconds={-100} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('N/A');
      });
    });
  });

  describe('getUptimeDescription utility function', () => {
    // Note: getUptimeDescription is not exported, so we test it indirectly through the component

    it('shows "Just started" for < 60 seconds', () => {
      render(<UptimeCard uptimeSeconds={30} isRunning={true} />);
      expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent('Just started');
    });

    it('shows "Running for minutes" for < 3600 seconds', () => {
      render(<UptimeCard uptimeSeconds={1800} isRunning={true} />);
      expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
        'Running for minutes'
      );
    });

    it('shows "Running for hours" for < 86400 seconds', () => {
      render(<UptimeCard uptimeSeconds={43200} isRunning={true} />);
      expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
        'Running for hours'
      );
    });

    it('shows "Running for days" for >= 86400 seconds', () => {
      render(<UptimeCard uptimeSeconds={172800} isRunning={true} />);
      expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
        'Running for days'
      );
    });

    describe('boundary conditions', () => {
      it('shows "Just started" at 59 seconds', () => {
        render(<UptimeCard uptimeSeconds={59} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Just started'
        );
      });

      it('shows "Running for minutes" at 60 seconds', () => {
        render(<UptimeCard uptimeSeconds={60} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Running for minutes'
        );
      });

      it('shows "Running for minutes" at 3599 seconds', () => {
        render(<UptimeCard uptimeSeconds={3599} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Running for minutes'
        );
      });

      it('shows "Running for hours" at 3600 seconds', () => {
        render(<UptimeCard uptimeSeconds={3600} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Running for hours'
        );
      });

      it('shows "Running for hours" at 86399 seconds', () => {
        render(<UptimeCard uptimeSeconds={86399} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Running for hours'
        );
      });

      it('shows "Running for days" at 86400 seconds', () => {
        render(<UptimeCard uptimeSeconds={86400} isRunning={true} />);
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Running for days'
        );
      });
    });
  });

  describe('component states', () => {
    describe('loading state', () => {
      it('renders loading state when isLoading is true', () => {
        render(<UptimeCard uptimeSeconds={null} isRunning={false} isLoading={true} />);

        expect(screen.getByTestId('uptime-card')).toBeInTheDocument();
        expect(screen.getByTestId('uptime-card-title')).toHaveTextContent('Uptime');
        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('Loading...');
        expect(screen.queryByTestId('uptime-card-subtitle')).not.toBeInTheDocument();
      });

      it('prioritizes loading state over other states', () => {
        render(<UptimeCard uptimeSeconds={3600} isRunning={true} isLoading={true} />);

        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('Loading...');
      });
    });

    describe('server not running state', () => {
      it('shows "Stopped" when isRunning is false', () => {
        render(<UptimeCard uptimeSeconds={null} isRunning={false} />);

        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('Stopped');
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Server is not running'
        );
      });

      it('shows "Stopped" even with valid uptime data when not running', () => {
        render(<UptimeCard uptimeSeconds={3600} isRunning={false} />);

        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('Stopped');
      });
    });

    describe('no data state', () => {
      it('shows N/A when uptimeSeconds is null and server is running', () => {
        render(<UptimeCard uptimeSeconds={null} isRunning={true} />);

        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('N/A');
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Uptime unavailable'
        );
      });

      it('shows N/A when uptimeSeconds is undefined and server is running', () => {
        render(<UptimeCard uptimeSeconds={undefined} isRunning={true} />);

        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('N/A');
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Uptime unavailable'
        );
      });
    });

    describe('valid uptime state', () => {
      it('displays formatted uptime and description for valid data', () => {
        render(<UptimeCard uptimeSeconds={7200} isRunning={true} />);

        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('2h');
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent(
          'Running for hours'
        );
      });

      it('handles zero uptime when server is running', () => {
        render(<UptimeCard uptimeSeconds={0} isRunning={true} />);

        expect(screen.getByTestId('uptime-card-value')).toHaveTextContent('0s');
        expect(screen.getByTestId('uptime-card-subtitle')).toHaveTextContent('Just started');
      });
    });
  });

  describe('component structure', () => {
    it('uses Clock icon', () => {
      render(<UptimeCard uptimeSeconds={3600} isRunning={true} />);
      expect(screen.getByTestId('uptime-card-icon')).toBeInTheDocument();
    });

    it('has consistent title in all states', () => {
      // Loading
      const { unmount: unmount1 } = render(
        <UptimeCard uptimeSeconds={null} isRunning={false} isLoading={true} />
      );
      expect(screen.getByTestId('uptime-card-title')).toHaveTextContent('Uptime');
      unmount1();

      // Stopped
      const { unmount: unmount2 } = render(
        <UptimeCard uptimeSeconds={null} isRunning={false} />
      );
      expect(screen.getByTestId('uptime-card-title')).toHaveTextContent('Uptime');
      unmount2();

      // No data
      const { unmount: unmount3 } = render(
        <UptimeCard uptimeSeconds={null} isRunning={true} />
      );
      expect(screen.getByTestId('uptime-card-title')).toHaveTextContent('Uptime');
      unmount3();

      // Valid data
      render(<UptimeCard uptimeSeconds={3600} isRunning={true} />);
      expect(screen.getByTestId('uptime-card-title')).toHaveTextContent('Uptime');
    });

    it('uses uptime-card as testId', () => {
      render(<UptimeCard uptimeSeconds={3600} isRunning={true} />);
      expect(screen.getByTestId('uptime-card')).toBeInTheDocument();
    });
  });

  describe('memoization', () => {
    it('is a memoized component', () => {
      expect(UptimeCard.$$typeof?.toString()).toBe('Symbol(react.memo)');
    });
  });
});
