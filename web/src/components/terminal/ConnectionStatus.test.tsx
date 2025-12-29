import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ConnectionStatus } from './ConnectionStatus';
import type { ConnectionState } from '@/hooks/use-console-websocket';

describe('ConnectionStatus', () => {
  describe('state rendering (AC: 4)', () => {
    const stateTestCases: Array<{
      state: ConnectionState;
      expectedLabel: string;
      expectedAriaLabel: string;
    }> = [
      {
        state: 'connecting',
        expectedLabel: 'Connecting...',
        expectedAriaLabel: 'Connection status: Connecting...',
      },
      {
        state: 'connected',
        expectedLabel: 'Connected',
        expectedAriaLabel: 'Connection status: Connected',
      },
      {
        state: 'disconnected',
        expectedLabel: 'Disconnected',
        expectedAriaLabel: 'Connection status: Disconnected',
      },
      {
        state: 'forbidden',
        expectedLabel: 'Access Denied',
        expectedAriaLabel: 'Connection status: Access Denied',
      },
    ];

    it.each(stateTestCases)(
      'renders "$expectedLabel" for state "$state"',
      ({ state, expectedLabel, expectedAriaLabel }) => {
        render(<ConnectionStatus state={state} />);

        expect(screen.getByText(expectedLabel)).toBeInTheDocument();
        expect(screen.getByRole('status')).toHaveAttribute(
          'aria-label',
          expectedAriaLabel
        );
      }
    );
  });

  describe('visual styling (AC: 4)', () => {
    it('applies green indicator for connected state', () => {
      const { container } = render(<ConnectionStatus state="connected" />);

      const indicator = container.querySelector('.bg-green-500');
      expect(indicator).toBeInTheDocument();
    });

    it('applies yellow indicator for connecting state', () => {
      const { container } = render(<ConnectionStatus state="connecting" />);

      const indicator = container.querySelector('.bg-yellow-500');
      expect(indicator).toBeInTheDocument();
    });

    it('applies gray indicator for disconnected state', () => {
      const { container } = render(<ConnectionStatus state="disconnected" />);

      const indicator = container.querySelector('.bg-gray-500');
      expect(indicator).toBeInTheDocument();
    });

    it('applies red indicator for forbidden state', () => {
      const { container } = render(<ConnectionStatus state="forbidden" />);

      const indicator = container.querySelector('.bg-red-500');
      expect(indicator).toBeInTheDocument();
    });

    it('applies pulse animation for connecting state', () => {
      const { container } = render(<ConnectionStatus state="connecting" />);

      const indicator = container.querySelector('.animate-pulse');
      expect(indicator).toBeInTheDocument();
    });

    it('does not apply pulse animation for connected state', () => {
      const { container } = render(<ConnectionStatus state="connected" />);

      const indicator = container.querySelector('.animate-pulse');
      expect(indicator).not.toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has role="status" for screen reader announcements', () => {
      render(<ConnectionStatus state="connected" />);

      expect(screen.getByRole('status')).toBeInTheDocument();
    });

    it('has aria-live="polite" for non-disruptive updates', () => {
      render(<ConnectionStatus state="connected" />);

      expect(screen.getByRole('status')).toHaveAttribute('aria-live', 'polite');
    });

    it('hides indicator dot from screen readers with aria-hidden', () => {
      const { container } = render(<ConnectionStatus state="connected" />);

      const indicator = container.querySelector('[aria-hidden="true"]');
      expect(indicator).toBeInTheDocument();
    });
  });

  describe('className prop', () => {
    it('accepts and applies custom className', () => {
      render(
        <ConnectionStatus state="connected" className="custom-class mt-4" />
      );

      const statusContainer = screen.getByRole('status');
      expect(statusContainer).toHaveClass('custom-class');
      expect(statusContainer).toHaveClass('mt-4');
    });
  });
});
