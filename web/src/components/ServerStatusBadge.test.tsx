import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ServerStatusBadge, type ServerState } from './ServerStatusBadge';

describe('ServerStatusBadge', () => {
  describe('state rendering (AC: 3, 4)', () => {
    const stateTestCases: Array<{
      state: ServerState;
      expectedLabel: string;
      expectedAriaLabel: string;
    }> = [
      {
        state: 'not_installed',
        expectedLabel: 'Not Installed',
        expectedAriaLabel: 'Server status: Not Installed',
      },
      {
        state: 'installing',
        expectedLabel: 'Installing',
        expectedAriaLabel: 'Server status: Installing',
      },
      {
        state: 'installed',
        expectedLabel: 'Stopped',
        expectedAriaLabel: 'Server status: Stopped',
      },
      {
        state: 'starting',
        expectedLabel: 'Starting',
        expectedAriaLabel: 'Server status: Starting',
      },
      {
        state: 'running',
        expectedLabel: 'Running',
        expectedAriaLabel: 'Server status: Running',
      },
      {
        state: 'stopping',
        expectedLabel: 'Stopping',
        expectedAriaLabel: 'Server status: Stopping',
      },
      {
        state: 'error',
        expectedLabel: 'Error',
        expectedAriaLabel: 'Server status: Error',
      },
    ];

    it.each(stateTestCases)(
      'renders "$expectedLabel" for state "$state"',
      ({ state, expectedLabel, expectedAriaLabel }) => {
        render(<ServerStatusBadge state={state} />);

        expect(screen.getByText(expectedLabel)).toBeInTheDocument();
        expect(screen.getByRole('status')).toHaveAttribute(
          'aria-label',
          expectedAriaLabel
        );
      }
    );
  });

  describe('visual styling', () => {
    it('applies success styling for running state (AC: 4)', () => {
      render(<ServerStatusBadge state="running" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveClass('bg-success/20');
      expect(badge).toHaveClass('text-success');
    });

    it('applies destructive styling for stopped state (AC: 3)', () => {
      render(<ServerStatusBadge state="installed" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveClass('bg-destructive/20');
      expect(badge).toHaveClass('text-destructive');
    });

    it('applies destructive styling for error state', () => {
      render(<ServerStatusBadge state="error" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveClass('bg-destructive/20');
      expect(badge).toHaveClass('text-destructive');
    });

    it('applies muted styling for not_installed state', () => {
      render(<ServerStatusBadge state="not_installed" />);

      const badge = screen.getByRole('status');
      expect(badge).toHaveClass('bg-muted/50');
      expect(badge).toHaveClass('text-muted-foreground');
    });

    it('applies warning styling for transitional states', () => {
      const transitionalStates: ServerState[] = [
        'installing',
        'starting',
        'stopping',
      ];

      transitionalStates.forEach((state) => {
        const { unmount } = render(<ServerStatusBadge state={state} />);
        const badge = screen.getByRole('status');

        expect(badge).toHaveClass('bg-warning/20');
        expect(badge).toHaveClass('text-warning');

        unmount();
      });
    });
  });

  describe('animation', () => {
    it('has animated spinner for transitional states', () => {
      const animatedStates: ServerState[] = [
        'installing',
        'starting',
        'stopping',
      ];

      animatedStates.forEach((state) => {
        const { container, unmount } = render(
          <ServerStatusBadge state={state} />
        );
        const icon = container.querySelector('svg');

        expect(icon).toHaveClass('animate-spin');

        unmount();
      });
    });

    it('does not animate for static states', () => {
      const staticStates: ServerState[] = [
        'not_installed',
        'installed',
        'running',
        'error',
      ];

      staticStates.forEach((state) => {
        const { container, unmount } = render(
          <ServerStatusBadge state={state} />
        );
        const icon = container.querySelector('svg');

        expect(icon).not.toHaveClass('animate-spin');

        unmount();
      });
    });
  });

  describe('className prop', () => {
    it('accepts and applies custom className', () => {
      render(
        <ServerStatusBadge state="running" className="custom-class mt-4" />
      );

      const badge = screen.getByRole('status');
      expect(badge).toHaveClass('custom-class');
      expect(badge).toHaveClass('mt-4');
    });
  });
});
