import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import {
  UninstallConfirmDialog,
  type UninstallConfirmDialogProps,
} from './UninstallConfirmDialog';

/**
 * UninstallConfirmDialog Tests - Story 13.7
 *
 * Tests cover:
 * - Preservation message display (AC: 2, 3)
 * - Server running warning (AC: 2)
 * - Cancel behavior (AC: 5)
 * - Confirm behavior (AC: 4)
 * - Pending state handling
 */

// Default props helper
function getDefaultProps(
  overrides?: Partial<UninstallConfirmDialogProps>
): UninstallConfirmDialogProps {
  return {
    serverState: 'installed',
    open: true,
    onOpenChange: vi.fn(),
    onConfirm: vi.fn(),
    isPending: false,
    ...overrides,
  };
}

describe('UninstallConfirmDialog', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('dialog visibility', () => {
    it('is not visible when open is false', () => {
      render(<UninstallConfirmDialog {...getDefaultProps({ open: false })} />);

      expect(
        screen.queryByTestId('uninstall-confirm-dialog')
      ).not.toBeInTheDocument();
    });

    it('is visible when open is true', () => {
      render(<UninstallConfirmDialog {...getDefaultProps({ open: true })} />);

      expect(
        screen.getByTestId('uninstall-confirm-dialog')
      ).toBeInTheDocument();
    });
  });

  describe('preservation message (AC: 2, 3)', () => {
    it('shows preservation message in all cases', () => {
      render(<UninstallConfirmDialog {...getDefaultProps()} />);

      const message = screen.getByTestId('preservation-message');
      expect(message).toBeInTheDocument();
      expect(message).toHaveTextContent('configuration files');
      expect(message).toHaveTextContent('mods');
      expect(message).toHaveTextContent('world saves');
      expect(message).toHaveTextContent('will be preserved');
    });

    it('shows preservation message when server is running', () => {
      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ serverState: 'running' })}
        />
      );

      expect(screen.getByTestId('preservation-message')).toBeInTheDocument();
    });

    it('shows preservation message when server is stopped', () => {
      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ serverState: 'installed' })}
        />
      );

      expect(screen.getByTestId('preservation-message')).toBeInTheDocument();
    });
  });

  describe('server running warning (AC: 2)', () => {
    it('shows server running warning when server is running', () => {
      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ serverState: 'running' })}
        />
      );

      const warning = screen.getByTestId('server-running-warning');
      expect(warning).toBeInTheDocument();
      expect(warning).toHaveTextContent('currently running');
      expect(warning).toHaveTextContent('will be stopped');
    });

    it('hides server running warning when server is stopped', () => {
      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ serverState: 'installed' })}
        />
      );

      expect(
        screen.queryByTestId('server-running-warning')
      ).not.toBeInTheDocument();
    });

    it('hides server running warning when server is starting', () => {
      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ serverState: 'starting' })}
        />
      );

      expect(
        screen.queryByTestId('server-running-warning')
      ).not.toBeInTheDocument();
    });

    it('hides server running warning when server is stopping', () => {
      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ serverState: 'stopping' })}
        />
      );

      expect(
        screen.queryByTestId('server-running-warning')
      ).not.toBeInTheDocument();
    });
  });

  describe('button interactions (AC: 4, 5)', () => {
    it('calls onConfirm when Remove Server button clicked', async () => {
      const user = userEvent.setup();
      const mockOnConfirm = vi.fn();

      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ onConfirm: mockOnConfirm })}
        />
      );

      await user.click(screen.getByTestId('confirm-button'));

      expect(mockOnConfirm).toHaveBeenCalledTimes(1);
    });

    it('calls onOpenChange(false) when Cancel clicked', async () => {
      const user = userEvent.setup();
      const mockOnOpenChange = vi.fn();

      render(
        <UninstallConfirmDialog
          {...getDefaultProps({ onOpenChange: mockOnOpenChange })}
        />
      );

      await user.click(screen.getByTestId('cancel-button'));

      expect(mockOnOpenChange).toHaveBeenCalledWith(false);
    });
  });

  describe('pending state', () => {
    it('disables Remove button when isPending is true', () => {
      render(
        <UninstallConfirmDialog {...getDefaultProps({ isPending: true })} />
      );

      expect(screen.getByTestId('confirm-button')).toBeDisabled();
    });

    it('disables Cancel button when isPending is true', () => {
      render(
        <UninstallConfirmDialog {...getDefaultProps({ isPending: true })} />
      );

      expect(screen.getByTestId('cancel-button')).toBeDisabled();
    });

    it('shows "Removing..." text when isPending is true', () => {
      render(
        <UninstallConfirmDialog {...getDefaultProps({ isPending: true })} />
      );

      expect(screen.getByTestId('confirm-button')).toHaveTextContent(
        'Removing...'
      );
    });

    it('shows "Remove Server" text when not pending', () => {
      render(
        <UninstallConfirmDialog {...getDefaultProps({ isPending: false })} />
      );

      expect(screen.getByTestId('confirm-button')).toHaveTextContent(
        'Remove Server'
      );
    });
  });

  describe('dialog title and description', () => {
    it('shows correct title', () => {
      render(<UninstallConfirmDialog {...getDefaultProps()} />);

      expect(screen.getByTestId('dialog-title')).toHaveTextContent(
        'Remove Server Installation'
      );
    });

    it('shows description about removing server binaries', () => {
      render(<UninstallConfirmDialog {...getDefaultProps()} />);

      expect(screen.getByText(/remove the VintageStory server binaries/i)).toBeInTheDocument();
    });
  });
});
