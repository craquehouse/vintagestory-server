/**
 * Tests for SideBadge component.
 *
 * VSS-qal: Ensures side badges correctly display Client/Server badges
 * based on the side value.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { SideBadge } from './SideBadge';

describe('SideBadge', () => {
  describe('with capitalized ModSide values', () => {
    it('shows both Client and Server badges when side is "Both"', () => {
      render(<SideBadge side="Both" />);

      expect(screen.getByTestId('side-badge')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
      expect(screen.getByText('Client')).toBeInTheDocument();
      expect(screen.getByText('Server')).toBeInTheDocument();
    });

    it('shows only Client badge when side is "Client"', () => {
      render(<SideBadge side="Client" />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.queryByTestId('side-badge-server')).not.toBeInTheDocument();
      expect(screen.getByText('Client')).toBeInTheDocument();
      expect(screen.queryByText('Server')).not.toBeInTheDocument();
    });

    it('shows only Server badge when side is "Server"', () => {
      render(<SideBadge side="Server" />);

      expect(screen.queryByTestId('side-badge-client')).not.toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
      expect(screen.queryByText('Client')).not.toBeInTheDocument();
      expect(screen.getByText('Server')).toBeInTheDocument();
    });
  });

  describe('with lowercase BrowseModSide values', () => {
    it('shows both Client and Server badges when side is "both"', () => {
      render(<SideBadge side="both" />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
    });

    it('shows only Client badge when side is "client"', () => {
      render(<SideBadge side="client" />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.queryByTestId('side-badge-server')).not.toBeInTheDocument();
    });

    it('shows only Server badge when side is "server"', () => {
      render(<SideBadge side="server" />);

      expect(screen.queryByTestId('side-badge-client')).not.toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
    });
  });

  describe('data attributes', () => {
    it('includes data-side attribute with original value', () => {
      render(<SideBadge side="Both" />);

      expect(screen.getByTestId('side-badge')).toHaveAttribute('data-side', 'Both');
    });

    it('preserves lowercase value in data-side', () => {
      render(<SideBadge side="client" />);

      expect(screen.getByTestId('side-badge')).toHaveAttribute('data-side', 'client');
    });
  });

  describe('styling', () => {
    it('applies custom className', () => {
      render(<SideBadge side="Both" className="custom-class" />);

      expect(screen.getByTestId('side-badge')).toHaveClass('custom-class');
    });

    it('badges have outline variant styling', () => {
      render(<SideBadge side="Both" />);

      // Badges should be present with badge styling
      const clientBadge = screen.getByTestId('side-badge-client');
      const serverBadge = screen.getByTestId('side-badge-server');

      expect(clientBadge).toBeInTheDocument();
      expect(serverBadge).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has aria-hidden on icons', () => {
      render(<SideBadge side="Both" />);

      // Icons should have aria-hidden="true"
      const svgs = screen.getByTestId('side-badge').querySelectorAll('svg');
      svgs.forEach((svg) => {
        expect(svg).toHaveAttribute('aria-hidden', 'true');
      });
    });
  });

  describe('edge cases and fallbacks', () => {
    it('shows both badges when side is null', () => {
      render(<SideBadge side={null} />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
    });

    it('shows both badges when side is undefined', () => {
      render(<SideBadge side={undefined} />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
    });

    it('shows both badges for unknown side value', () => {
      // @ts-expect-error - Testing invalid input
      render(<SideBadge side="unknown" />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
    });

    it('shows both badges for empty string', () => {
      // @ts-expect-error - Testing invalid input
      render(<SideBadge side="" />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
    });
  });
});
