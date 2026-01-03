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
  });

  describe('styling', () => {
    it('uses warning color scheme', () => {
      render(<DiskSpaceWarningBanner diskSpace={lowDiskSpace} />);
      const banner = screen.getByTestId('disk-space-warning-banner');
      expect(banner).toHaveClass('bg-yellow-500/20');
    });
  });
});
