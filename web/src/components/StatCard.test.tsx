/**
 * Tests for StatCard component.
 *
 * Story 12.4: Dashboard Stats Cards
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryStick, Server, HardDrive, Clock } from 'lucide-react';
import { StatCard } from './StatCard';

describe('StatCard', () => {
  describe('rendering (AC: 1)', () => {
    it('renders with icon, title, and value', () => {
      render(
        <StatCard
          icon={MemoryStick}
          title="Memory Usage"
          value="128.5 MB"
          testId="memory-card"
        />
      );

      expect(screen.getByText('Memory Usage')).toBeInTheDocument();
      expect(screen.getByText('128.5 MB')).toBeInTheDocument();
    });

    it('renders the icon', () => {
      render(
        <StatCard
          icon={Server}
          title="Server Status"
          value="Running"
          testId="status-card"
        />
      );

      // Icon should be present (aria-hidden)
      const icon = document.querySelector('svg[aria-hidden="true"]');
      expect(icon).toBeInTheDocument();
    });

    it('renders subtitle when provided', () => {
      render(
        <StatCard
          icon={HardDrive}
          title="Disk Space"
          value="45.2 GB"
          subtitle="Free of 100 GB"
          testId="disk-card"
        />
      );

      expect(screen.getByText('Free of 100 GB')).toBeInTheDocument();
    });

    it('does not render subtitle when not provided', () => {
      render(
        <StatCard icon={Clock} title="Uptime" value="5d 12h" testId="uptime-card" />
      );

      expect(screen.queryByTestId('uptime-card-subtitle')).not.toBeInTheDocument();
    });

    it('renders with numeric value', () => {
      render(
        <StatCard
          icon={MemoryStick}
          title="Memory"
          value={512}
          testId="memory-numeric"
        />
      );

      expect(screen.getByText('512')).toBeInTheDocument();
    });
  });

  describe('test IDs', () => {
    it('applies testId to card element', () => {
      render(
        <StatCard
          icon={Server}
          title="Server"
          value="Online"
          testId="server-card"
        />
      );

      expect(screen.getByTestId('server-card')).toBeInTheDocument();
    });

    it('applies testId to value element', () => {
      render(
        <StatCard
          icon={Server}
          title="Server"
          value="Online"
          testId="server-card"
        />
      );

      expect(screen.getByTestId('server-card-value')).toHaveTextContent('Online');
    });

    it('applies testId to subtitle element when present', () => {
      render(
        <StatCard
          icon={Server}
          title="Server"
          value="Online"
          subtitle="Healthy"
          testId="server-card"
        />
      );

      expect(screen.getByTestId('server-card-subtitle')).toHaveTextContent(
        'Healthy'
      );
    });

    it('does not apply id to title when testId is not provided', () => {
      render(
        <StatCard
          icon={Server}
          title="Server Status"
          value="Online"
        />
      );

      const title = screen.getByText('Server Status');
      expect(title).not.toHaveAttribute('id');
    });

    it('does not apply data-testid to value when testId is not provided', () => {
      render(
        <StatCard
          icon={Server}
          title="Server"
          value="Online"
        />
      );

      const value = screen.getByText('Online');
      expect(value).not.toHaveAttribute('data-testid');
    });

    it('does not apply data-testid to subtitle when testId is not provided', () => {
      render(
        <StatCard
          icon={Server}
          title="Server"
          value="Online"
          subtitle="Healthy"
        />
      );

      const subtitle = screen.getByText('Healthy');
      expect(subtitle).not.toHaveAttribute('data-testid');
    });
  });

  describe('custom content', () => {
    it('renders children when provided', () => {
      render(
        <StatCard icon={Server} title="Server" value="Online" testId="server-card">
          <button data-testid="custom-button">Action</button>
        </StatCard>
      );

      expect(screen.getByTestId('custom-button')).toBeInTheDocument();
    });
  });

  describe('styling', () => {
    it('applies custom className', () => {
      render(
        <StatCard
          icon={Server}
          title="Server"
          value="Online"
          className="custom-class"
          testId="server-card"
        />
      );

      const card = screen.getByTestId('server-card');
      expect(card.className).toContain('custom-class');
    });

    it('has minimum height for consistent grid layout', () => {
      render(
        <StatCard
          icon={Server}
          title="Server"
          value="Online"
          testId="server-card"
        />
      );

      const card = screen.getByTestId('server-card');
      expect(card.className).toContain('min-h-');
    });
  });

  describe('different icons', () => {
    it('works with MemoryStick icon', () => {
      render(
        <StatCard
          icon={MemoryStick}
          title="Memory"
          value="128 MB"
          testId="memory-card"
        />
      );

      expect(screen.getByTestId('memory-card')).toBeInTheDocument();
    });

    it('works with HardDrive icon', () => {
      render(
        <StatCard
          icon={HardDrive}
          title="Disk"
          value="100 GB"
          testId="disk-card"
        />
      );

      expect(screen.getByTestId('disk-card')).toBeInTheDocument();
    });

    it('works with Clock icon', () => {
      render(
        <StatCard icon={Clock} title="Uptime" value="5 days" testId="uptime-card" />
      );

      expect(screen.getByTestId('uptime-card')).toBeInTheDocument();
    });

    it('works with Server icon', () => {
      render(
        <StatCard
          icon={Server}
          title="Status"
          value="Running"
          testId="status-card"
        />
      );

      expect(screen.getByTestId('status-card')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has role="region" for semantic grouping', () => {
      render(
        <StatCard
          icon={Server}
          title="Server Status"
          value="Running"
          testId="status-card"
        />
      );

      const card = screen.getByTestId('status-card');
      expect(card).toHaveAttribute('role', 'region');
    });

    it('has aria-label set to title for screen readers', () => {
      render(
        <StatCard
          icon={Server}
          title="Server Status"
          value="Running"
          testId="status-card"
        />
      );

      const card = screen.getByTestId('status-card');
      expect(card).toHaveAttribute('aria-label', 'Server Status');
    });

    it('has aria-hidden on decorative icon', () => {
      render(
        <StatCard
          icon={Server}
          title="Server Status"
          value="Running"
          testId="status-card"
        />
      );

      const icon = document.querySelector('svg[aria-hidden="true"]');
      expect(icon).toBeInTheDocument();
    });

    it('has aria-live="polite" on value for live updates', () => {
      render(
        <StatCard
          icon={MemoryStick}
          title="Memory Usage"
          value="128.5 MB"
          testId="memory-card"
        />
      );

      const value = screen.getByTestId('memory-card-value');
      expect(value).toHaveAttribute('aria-live', 'polite');
    });

    it('title element has id for programmatic association', () => {
      render(
        <StatCard
          icon={Server}
          title="Server Status"
          value="Running"
          testId="status-card"
        />
      );

      const title = document.getElementById('status-card-title');
      expect(title).toBeInTheDocument();
      expect(title).toHaveTextContent('Server Status');
    });
  });
});
