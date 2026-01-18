/**
 * Tests for StatCardSkeleton component.
 *
 * Story 12.4: Dashboard Stats Cards (Review Follow-up)
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatCardSkeleton } from './StatCardSkeleton';

describe('StatCardSkeleton', () => {
  it('renders with default props', () => {
    render(<StatCardSkeleton testId="skeleton-card" />);

    expect(screen.getByTestId('skeleton-card')).toBeInTheDocument();
  });

  it('has aria-busy attribute for accessibility', () => {
    render(<StatCardSkeleton testId="skeleton-card" />);

    const card = screen.getByTestId('skeleton-card');
    expect(card).toHaveAttribute('aria-busy', 'true');
  });

  it('has aria-label for screen readers', () => {
    render(<StatCardSkeleton testId="skeleton-card" />);

    const card = screen.getByTestId('skeleton-card');
    expect(card).toHaveAttribute('aria-label', 'Loading...');
  });

  it('renders skeleton elements', () => {
    render(<StatCardSkeleton testId="skeleton-card" />);

    // Should have multiple skeleton elements (icon, title, value, subtitle)
    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons.length).toBeGreaterThanOrEqual(3);
  });

  it('shows subtitle skeleton by default', () => {
    render(<StatCardSkeleton testId="skeleton-card" />);

    // Should have 4 skeleton elements: icon, title, value, subtitle
    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons).toHaveLength(4);
  });

  it('hides subtitle skeleton when showSubtitle is false', () => {
    render(<StatCardSkeleton testId="skeleton-card" showSubtitle={false} />);

    // Should have 3 skeleton elements: icon, title, value
    const skeletons = document.querySelectorAll('[data-slot="skeleton"]');
    expect(skeletons).toHaveLength(3);
  });

  it('applies custom className', () => {
    render(<StatCardSkeleton testId="skeleton-card" className="custom-class" />);

    const card = screen.getByTestId('skeleton-card');
    expect(card.className).toContain('custom-class');
  });

  it('has minimum height for consistent grid layout', () => {
    render(<StatCardSkeleton testId="skeleton-card" />);

    const card = screen.getByTestId('skeleton-card');
    expect(card.className).toContain('min-h-');
  });
});
