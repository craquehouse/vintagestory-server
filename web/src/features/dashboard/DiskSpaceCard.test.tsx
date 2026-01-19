import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DiskSpaceCard } from './DiskSpaceCard';
import type { DiskSpaceData } from '@/api/types';

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

describe('DiskSpaceCard', () => {
  describe('loading state', () => {
    it('renders loading state when isLoading is true', () => {
      render(<DiskSpaceCard diskSpace={null} isLoading={true} />);

      expect(screen.getByTestId('disk-card')).toBeInTheDocument();
      expect(screen.getByTestId('disk-card-title')).toHaveTextContent('Disk Space');
      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('Loading...');
      expect(screen.queryByTestId('disk-card-subtitle')).not.toBeInTheDocument();
    });

    it('prioritizes loading state over data', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 50,
        availableGb: 50,
        usagePercent: 50,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} isLoading={true} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('Loading...');
    });
  });

  describe('no data state', () => {
    it('renders N/A when diskSpace is null', () => {
      render(<DiskSpaceCard diskSpace={null} isLoading={false} />);

      expect(screen.getByTestId('disk-card')).toBeInTheDocument();
      expect(screen.getByTestId('disk-card-title')).toHaveTextContent('Disk Space');
      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('N/A');
      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
        'Disk data unavailable'
      );
    });

    it('renders N/A when diskSpace is undefined', () => {
      render(<DiskSpaceCard diskSpace={undefined} isLoading={false} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('N/A');
      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
        'Disk data unavailable'
      );
    });
  });

  describe('rendering with valid disk space data', () => {
    it('displays available disk space in GB', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 45.5,
        availableGb: 54.5,
        usagePercent: 45.5,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('54.5 GB');
    });

    it('displays total disk space and usage percentage in subtitle', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 45.5,
        availableGb: 54.5,
        usagePercent: 45.5,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
        'Free of 100.0 GB (46% used)'
      );
    });

    it('formats availableGb to 1 decimal place', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 33.333,
        availableGb: 66.667,
        usagePercent: 33.333,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('66.7 GB');
    });

    it('formats totalGb to 1 decimal place', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 99.999,
        usedGb: 50.0,
        availableGb: 49.999,
        usagePercent: 50.0,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
        'Free of 100.0 GB'
      );
    });

    it('formats usagePercent to 0 decimal places (integer)', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 45.7,
        availableGb: 54.3,
        usagePercent: 45.7,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent('46% used');
    });
  });

  describe('edge cases', () => {
    it('handles zero available space', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 100.0,
        availableGb: 0.0,
        usagePercent: 100.0,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('0.0 GB');
      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
        'Free of 100.0 GB (100% used)'
      );
    });

    it('handles full available space (0% used)', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 0.0,
        availableGb: 100.0,
        usagePercent: 0.0,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('100.0 GB');
      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent('0% used');
    });

    it('handles small disk sizes', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 10.5,
        usedGb: 3.2,
        availableGb: 7.3,
        usagePercent: 30.5,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('7.3 GB');
      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
        'Free of 10.5 GB (31% used)'
      );
    });

    it('handles large disk sizes', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 2000.0,
        usedGb: 500.0,
        availableGb: 1500.0,
        usagePercent: 25.0,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-value')).toHaveTextContent('1500.0 GB');
      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent(
        'Free of 2000.0 GB (25% used)'
      );
    });

    it('handles fractional percentages', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 33.333,
        availableGb: 66.667,
        usagePercent: 33.333,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      // Should round to nearest integer
      expect(screen.getByTestId('disk-card-subtitle')).toHaveTextContent('33% used');
    });
  });

  describe('component structure', () => {
    it('uses HardDrive icon', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 50.0,
        availableGb: 50.0,
        usagePercent: 50.0,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card-icon')).toBeInTheDocument();
    });

    it('has consistent title in all states', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 50.0,
        availableGb: 50.0,
        usagePercent: 50.0,
      };

      // Loading state
      const { unmount: unmount1 } = render(
        <DiskSpaceCard diskSpace={null} isLoading={true} />
      );
      expect(screen.getByTestId('disk-card-title')).toHaveTextContent('Disk Space');
      unmount1();

      // No data state
      const { unmount: unmount2 } = render(
        <DiskSpaceCard diskSpace={null} isLoading={false} />
      );
      expect(screen.getByTestId('disk-card-title')).toHaveTextContent('Disk Space');
      unmount2();

      // Valid data state
      render(<DiskSpaceCard diskSpace={diskSpace} />);
      expect(screen.getByTestId('disk-card-title')).toHaveTextContent('Disk Space');
    });

    it('uses disk-card as testId', () => {
      const diskSpace: DiskSpaceData = {
        totalGb: 100.0,
        usedGb: 50.0,
        availableGb: 50.0,
        usagePercent: 50.0,
      };

      render(<DiskSpaceCard diskSpace={diskSpace} />);

      expect(screen.getByTestId('disk-card')).toBeInTheDocument();
    });
  });

  describe('memoization', () => {
    it('is a memoized component', () => {
      // The component is wrapped in memo() - check that it has the memo wrapper
      expect(DiskSpaceCard.$$typeof?.toString()).toBe('Symbol(react.memo)');
    });
  });
});
