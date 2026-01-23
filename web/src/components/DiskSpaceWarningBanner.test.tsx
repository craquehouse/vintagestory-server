/**
 * Tests for DiskSpaceWarningBanner component (API-008).
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { DiskSpaceWarningBanner } from './DiskSpaceWarningBanner';
import type { DiskSpaceData } from '@/api/types';

describe('DiskSpaceWarningBanner', () => {
  const lowDiskSpace: DiskSpaceData = {
    totalGb: 100,
    usedGb: 95,
    availableGb: 5,
    usagePercent: 95,
    warning: true,
  };

  const healthyDiskSpace: DiskSpaceData = {
    totalGb: 100,
    usedGb: 50,
    availableGb: 50,
    usagePercent: 50,
    warning: false,
  };

  describe('visibility', () => {
    it('renders when disk space warning is true', () => {
      render(<DiskSpaceWarningBanner diskSpace={lowDiskSpace} />);
      expect(screen.getByTestId('disk-space-warning-banner')).toBeInTheDocument();
    });

    it('does not render when disk space warning is false', () => {
      render(<DiskSpaceWarningBanner diskSpace={healthyDiskSpace} />);
      expect(screen.queryByTestId('disk-space-warning-banner')).not.toBeInTheDocument();
    });

    it('does not render when diskSpace is null', () => {
      render(<DiskSpaceWarningBanner diskSpace={null} />);
      expect(screen.queryByTestId('disk-space-warning-banner')).not.toBeInTheDocument();
    });

    it('does not render when diskSpace is undefined', () => {
      render(<DiskSpaceWarningBanner diskSpace={undefined} />);
      expect(screen.queryByTestId('disk-space-warning-banner')).not.toBeInTheDocument();
    });
  });

  describe('content', () => {
    it('displays available GB with one decimal place', () => {
      render(<DiskSpaceWarningBanner diskSpace={lowDiskSpace} />);
      expect(screen.getByText(/5\.0 GB available/)).toBeInTheDocument();
    });

    it('displays usage percentage without decimals', () => {
      render(<DiskSpaceWarningBanner diskSpace={lowDiskSpace} />);
      expect(screen.getByText(/95% used/)).toBeInTheDocument();
    });

    it('shows warning icon', () => {
      render(<DiskSpaceWarningBanner diskSpace={lowDiskSpace} />);
      expect(screen.getByTestId('disk-warning-icon')).toBeInTheDocument();
    });

    it('handles fractional values correctly', () => {
      const fractionalDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 99.5,
        availableGb: 0.5,
        usagePercent: 99.5,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={fractionalDiskSpace} />);
      expect(screen.getByText(/0\.5 GB available/)).toBeInTheDocument();
      expect(screen.getByText(/100% used/)).toBeInTheDocument(); // 99.5 rounds to 100
    });

    it('displays complete warning message format', () => {
      render(<DiskSpaceWarningBanner diskSpace={lowDiskSpace} />);
      expect(screen.getByText(/Low disk space: 5\.0 GB available \(95% used\)/)).toBeInTheDocument();
    });
  });

  describe('edge cases', () => {
    it('handles zero available space', () => {
      const zeroDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 100,
        availableGb: 0,
        usagePercent: 100,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={zeroDiskSpace} />);
      expect(screen.getByText(/0\.0 GB available/)).toBeInTheDocument();
      expect(screen.getByText(/100% used/)).toBeInTheDocument();
    });

    it('handles very small available space', () => {
      const minimalDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 99.99,
        availableGb: 0.01,
        usagePercent: 99.99,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={minimalDiskSpace} />);
      expect(screen.getByText(/0\.0 GB available/)).toBeInTheDocument();
      expect(screen.getByText(/100% used/)).toBeInTheDocument();
    });

    it('handles large disk sizes', () => {
      const largeDiskSpace: DiskSpaceData = {
        totalGb: 10000,
        usedGb: 9500,
        availableGb: 500,
        usagePercent: 95,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={largeDiskSpace} />);
      expect(screen.getByText(/500\.0 GB available/)).toBeInTheDocument();
      expect(screen.getByText(/95% used/)).toBeInTheDocument();
    });

    it('handles decimal percentage rounding down', () => {
      const roundDownDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 94.4,
        availableGb: 5.6,
        usagePercent: 94.4,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={roundDownDiskSpace} />);
      expect(screen.getByText(/5\.6 GB available/)).toBeInTheDocument();
      expect(screen.getByText(/94% used/)).toBeInTheDocument();
    });

    it('handles decimal percentage rounding up', () => {
      const roundUpDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 94.6,
        availableGb: 5.4,
        usagePercent: 94.6,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={roundUpDiskSpace} />);
      expect(screen.getByText(/5\.4 GB available/)).toBeInTheDocument();
      expect(screen.getByText(/95% used/)).toBeInTheDocument();
    });

    it('handles very precise decimal values', () => {
      const preciseData: DiskSpaceData = {
        totalGb: 100,
        usedGb: 94.567,
        availableGb: 5.433,
        usagePercent: 94.567,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={preciseData} />);
      expect(screen.getByText(/5\.4 GB available/)).toBeInTheDocument(); // 5.433 rounds to 5.4
      expect(screen.getByText(/95% used/)).toBeInTheDocument(); // 94.567 rounds to 95
    });

    it('handles negative available space (disk overfull)', () => {
      // Edge case: filesystem reports negative space (over-allocated)
      const overfullDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 100.5,
        availableGb: -0.5,
        usagePercent: 100.5,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={overfullDiskSpace} />);
      expect(screen.getByText(/-0\.5 GB available/)).toBeInTheDocument();
      expect(screen.getByText(/101% used/)).toBeInTheDocument(); // Can be over 100%
    });
  });

  describe('threshold behavior', () => {
    it('shows warning at exactly threshold (warning: true)', () => {
      const thresholdDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 90,
        availableGb: 10,
        usagePercent: 90,
        warning: true,
      };
      render(<DiskSpaceWarningBanner diskSpace={thresholdDiskSpace} />);
      expect(screen.getByTestId('disk-space-warning-banner')).toBeInTheDocument();
    });

    it('hides banner just below threshold (warning: false)', () => {
      const belowThresholdDiskSpace: DiskSpaceData = {
        totalGb: 100,
        usedGb: 89,
        availableGb: 11,
        usagePercent: 89,
        warning: false,
      };
      render(<DiskSpaceWarningBanner diskSpace={belowThresholdDiskSpace} />);
      expect(screen.queryByTestId('disk-space-warning-banner')).not.toBeInTheDocument();
    });

    it('relies solely on warning flag, not calculated values', () => {
      // Even with healthy disk space, if warning: true, it should show
      const counterintuitiveData: DiskSpaceData = {
        totalGb: 100,
        usedGb: 10,
        availableGb: 90,
        usagePercent: 10,
        warning: true, // Backend says show warning despite low usage
      };
      render(<DiskSpaceWarningBanner diskSpace={counterintuitiveData} />);
      expect(screen.getByTestId('disk-space-warning-banner')).toBeInTheDocument();
    });
  });

  describe('styling', () => {
    it('uses warning color scheme', () => {
      render(<DiskSpaceWarningBanner diskSpace={lowDiskSpace} />);
      const banner = screen.getByTestId('disk-space-warning-banner');
      // Uses semantic warning class for theme-aware colors
      expect(banner).toHaveClass('bg-warning/20');
    });
  });
});
