/**
 * Tests for StatCardErrorBoundary component.
 *
 * Story 12.4: Dashboard Stats Cards (Review Follow-up)
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatCardErrorBoundary } from './StatCardErrorBoundary';

// Component that throws an error
function ThrowingComponent(): never {
  throw new Error('Test error');
}

// Component that renders normally
function NormalComponent() {
  return <div data-testid="normal-content">Normal content</div>;
}

describe('StatCardErrorBoundary', () => {
  // Suppress console.error for expected error tests
  const originalError = console.error;

  beforeEach(() => {
    console.error = vi.fn();
  });

  afterEach(() => {
    console.error = originalError;
  });

  it('renders children when no error occurs', () => {
    render(
      <StatCardErrorBoundary title="Test Card" testId="test-card">
        <NormalComponent />
      </StatCardErrorBoundary>
    );

    expect(screen.getByTestId('normal-content')).toBeInTheDocument();
    expect(screen.getByText('Normal content')).toBeInTheDocument();
  });

  it('renders error fallback when child throws', () => {
    render(
      <StatCardErrorBoundary title="Test Card" testId="test-card">
        <ThrowingComponent />
      </StatCardErrorBoundary>
    );

    expect(screen.getByTestId('test-card-error')).toBeInTheDocument();
    expect(screen.getByText('Test Card')).toBeInTheDocument();
    expect(screen.getByText('Unable to load card data')).toBeInTheDocument();
  });

  it('has proper ARIA attributes in error state', () => {
    render(
      <StatCardErrorBoundary title="Memory Usage" testId="memory-card">
        <ThrowingComponent />
      </StatCardErrorBoundary>
    );

    const card = screen.getByTestId('memory-card-error');
    expect(card).toHaveAttribute('role', 'region');
    expect(card).toHaveAttribute('aria-label', 'Memory Usage - Error');
  });

  it('displays error icon in error state', () => {
    render(
      <StatCardErrorBoundary title="Test Card" testId="test-card">
        <ThrowingComponent />
      </StatCardErrorBoundary>
    );

    const icon = document.querySelector('svg[aria-hidden="true"]');
    expect(icon).toBeInTheDocument();
  });

  it('logs error to console', () => {
    render(
      <StatCardErrorBoundary title="Test Card" testId="test-card">
        <ThrowingComponent />
      </StatCardErrorBoundary>
    );

    expect(console.error).toHaveBeenCalled();
  });

  it('isolates error to single card', () => {
    render(
      <div>
        <StatCardErrorBoundary title="Failing Card" testId="failing-card">
          <ThrowingComponent />
        </StatCardErrorBoundary>
        <StatCardErrorBoundary title="Working Card" testId="working-card">
          <NormalComponent />
        </StatCardErrorBoundary>
      </div>
    );

    // Failing card shows error
    expect(screen.getByTestId('failing-card-error')).toBeInTheDocument();

    // Working card still renders normally
    expect(screen.getByTestId('normal-content')).toBeInTheDocument();
  });
});
