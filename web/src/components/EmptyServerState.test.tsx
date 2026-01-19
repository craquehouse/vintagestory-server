import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router';
import { EmptyServerState } from './EmptyServerState';

describe('EmptyServerState', () => {
  const defaultNotInstalledMessage = 'VintageStory server is not installed';
  const defaultInstallingMessage = 'Installing the server...';

  describe('not installing state (AC: 1)', () => {
    it('renders server not installed state with default messages', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText('Server Not Installed')).toBeInTheDocument();
      expect(screen.getByText(defaultNotInstalledMessage)).toBeInTheDocument();
    });

    it('renders server not installed state with custom messages', () => {
      const customMessage = 'Custom not installed message';
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={customMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText(customMessage)).toBeInTheDocument();
    });

    it('shows icon when not installing', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(container.querySelector('svg')).toBeInTheDocument();
    });

    it('shows "Go to Installation" button', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByRole('button', { name: 'Go to Installation' })).toBeInTheDocument();
    });
  });

  describe('installing state (AC: 2)', () => {
    it('renders installing state with default messages', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText('Installation in Progress')).toBeInTheDocument();
      expect(screen.getByText(defaultInstallingMessage)).toBeInTheDocument();
    });

    it('renders installing state with custom messages', () => {
      const customMessage = 'Custom installing message';
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={customMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText(customMessage)).toBeInTheDocument();
    });

    it('shows animated loading icon when installing', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
      expect(icon).toHaveClass('animate-spin');
    });

    it('shows "View Installation Progress" button', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByRole('button', { name: 'View Installation Progress' })).toBeInTheDocument();
    });
  });

  describe('testId prop (AC: 5)', () => {
    it('applies testId to container element when provided', () => {
      const testId = 'empty-server-state-container';
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
            testId={testId}
          />
        </MemoryRouter>
      );

      expect(screen.getByTestId(testId)).toBeInTheDocument();
    });

    it('does not apply data-testid when testId is undefined', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(container.firstChild).not.toHaveAttribute('data-testid');
    });
  });

  describe('state switching', () => {
    it('switches from installing to not installing when isInstalling changes', () => {
      const { rerender } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText('Installation in Progress')).toBeInTheDocument();
      expect(screen.queryByText('Server Not Installed')).not.toBeInTheDocument();

      rerender(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText('Server Not Installed')).toBeInTheDocument();
      expect(screen.queryByText('Installation in Progress')).not.toBeInTheDocument();
    });
  });

  describe('navigation links', () => {
    it('contains link to installation page for not installing state', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const link = screen.getByRole('link', { name: 'Go to Installation' });
      expect(link).toHaveAttribute('href', '/game-server/version');
    });

    it('contains link to installation page for installing state', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const link = screen.getByRole('link', { name: 'View Installation Progress' });
      expect(link).toHaveAttribute('href', '/game-server/version');
    });
  });
});
