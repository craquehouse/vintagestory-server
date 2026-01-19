import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { CompatibilityBadge } from './CompatibilityBadge';
import type { CompatibilityStatus } from '@/api/types';

describe('CompatibilityBadge', () => {
  describe('status rendering (AC: 3, 6)', () => {
    const statusTestCases: Array<{
      status: CompatibilityStatus;
      expectedLabel: string;
    }> = [
      { status: 'compatible', expectedLabel: 'Compatible' },
      { status: 'not_verified', expectedLabel: 'Not verified' },
      { status: 'incompatible', expectedLabel: 'Incompatible' },
    ];

    it.each(statusTestCases)(
      'renders "$expectedLabel" for status "$status"',
      ({ status, expectedLabel }) => {
        render(<CompatibilityBadge status={status} />);

        expect(screen.getByText(expectedLabel)).toBeInTheDocument();
        expect(screen.getByTestId('compatibility-badge')).toHaveAttribute(
          'data-status',
          status
        );
      }
    );
  });

  describe('visual styling', () => {
    it('applies success styling for compatible status', () => {
      render(<CompatibilityBadge status="compatible" />);

      const badge = screen.getByTestId('compatibility-badge');
      // Uses semantic badge-success class for theme-aware colors
      expect(badge).toHaveClass('badge-success');
    });

    it('applies warning styling for not_verified status', () => {
      render(<CompatibilityBadge status="not_verified" />);

      const badge = screen.getByTestId('compatibility-badge');
      // Uses semantic badge-warning class for theme-aware colors
      expect(badge).toHaveClass('badge-warning');
    });

    it('applies destructive styling for incompatible status', () => {
      render(<CompatibilityBadge status="incompatible" />);

      const badge = screen.getByTestId('compatibility-badge');
      // Uses semantic badge-destructive class for theme-aware colors
      expect(badge).toHaveClass('badge-destructive');
    });
  });

  describe('icons', () => {
    it('renders checkmark icon for compatible status', () => {
      const { container } = render(<CompatibilityBadge status="compatible" />);

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveClass('h-3', 'w-3');
    });

    it('renders warning icon for not_verified status', () => {
      const { container } = render(
        <CompatibilityBadge status="not_verified" />
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });

    it('renders X icon for incompatible status', () => {
      const { container } = render(
        <CompatibilityBadge status="incompatible" />
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
    });
  });

  describe('message prop', () => {
    it('sets title attribute when message is provided', () => {
      render(
        <CompatibilityBadge
          status="not_verified"
          message="No matching version found"
        />
      );

      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).toHaveAttribute('title', 'No matching version found');
    });

    it('does not set title when message is not provided', () => {
      render(<CompatibilityBadge status="compatible" />);

      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).not.toHaveAttribute('title');
    });
  });

  describe('className prop', () => {
    it('accepts and applies custom className', () => {
      render(
        <CompatibilityBadge status="compatible" className="custom-class mt-4" />
      );

      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).toHaveClass('custom-class');
      expect(badge).toHaveClass('mt-4');
    });
  });

  describe('accessibility', () => {
    it('hides decorative icon from screen readers', () => {
      const { container } = render(<CompatibilityBadge status="compatible" />);

      const icon = container.querySelector('svg');
      expect(icon).toHaveAttribute('aria-hidden', 'true');
    });
  });
});
