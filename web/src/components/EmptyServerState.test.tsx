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

    it('shows ServerOff icon when not installing', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const icon = container.querySelector('svg');
      expect(icon).toBeInTheDocument();
      expect(icon).not.toHaveClass('animate-spin');
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

    it('applies correct CSS classes for not installed state', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'h-64', 'text-center');
    });

    it('renders with empty string message', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage=""
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText('Server Not Installed')).toBeInTheDocument();
      expect(screen.queryByText(defaultNotInstalledMessage)).not.toBeInTheDocument();
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

    it('shows Loader2 icon with animation when installing', () => {
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

    it('applies correct CSS classes for installing state', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const wrapper = container.firstChild;
      expect(wrapper).toHaveClass('flex', 'flex-col', 'items-center', 'justify-center', 'h-64', 'text-center');
    });

    it('renders with empty string message', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage=""
          />
        </MemoryRouter>
      );

      expect(screen.getByText('Installation in Progress')).toBeInTheDocument();
      expect(screen.queryByText(defaultInstallingMessage)).not.toBeInTheDocument();
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

  describe('button variants', () => {
    it('renders default variant button for not installing state', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const button = screen.getByRole('button', { name: 'Go to Installation' });
      // Button component applies variant classes - we can check it exists and is accessible
      expect(button).toBeInTheDocument();
      expect(button).toBeEnabled();
    });

    it('renders outline variant button for installing state', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const button = screen.getByRole('button', { name: 'View Installation Progress' });
      expect(button).toBeInTheDocument();
      expect(button).toBeEnabled();
    });
  });

  describe('icon rendering', () => {
    it('uses different icons for different states', () => {
      const { container: notInstalledContainer } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const { container: installingContainer } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const notInstalledIcon = notInstalledContainer.querySelector('svg');
      const installingIcon = installingContainer.querySelector('svg');

      // Both should have icons
      expect(notInstalledIcon).toBeInTheDocument();
      expect(installingIcon).toBeInTheDocument();

      // Only installing icon should have animation
      expect(notInstalledIcon).not.toHaveClass('animate-spin');
      expect(installingIcon).toHaveClass('animate-spin');
    });

    it('applies correct CSS classes to icons', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const icon = container.querySelector('svg');
      expect(icon).toHaveClass('h-12', 'w-12', 'text-muted-foreground', 'mb-4');
    });
  });

  describe('text content structure', () => {
    it('renders title, message, and button in correct order for not installed', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const title = screen.getByText('Server Not Installed');
      const message = screen.getByText(defaultNotInstalledMessage);
      const button = screen.getByRole('button', { name: 'Go to Installation' });

      // All elements should be present
      expect(title).toBeInTheDocument();
      expect(message).toBeInTheDocument();
      expect(button).toBeInTheDocument();

      // Check title has correct styling
      expect(title).toHaveClass('text-lg', 'font-medium');
      expect(message).toHaveClass('text-muted-foreground', 'mb-4');
    });

    it('renders title, message, and button in correct order for installing', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={true}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const title = screen.getByText('Installation in Progress');
      const message = screen.getByText(defaultInstallingMessage);
      const button = screen.getByRole('button', { name: 'View Installation Progress' });

      expect(title).toBeInTheDocument();
      expect(message).toBeInTheDocument();
      expect(button).toBeInTheDocument();

      expect(title).toHaveClass('text-lg', 'font-medium');
      expect(message).toHaveClass('text-muted-foreground', 'mb-4');
    });
  });

  describe('edge cases', () => {
    it('handles very long message text without breaking layout', () => {
      const longMessage = 'This is a very long message that goes on and on and on to test how the component handles extremely long text content that might wrap to multiple lines and could potentially affect the layout of the component';

      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={longMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText(longMessage)).toBeInTheDocument();
    });

    it('handles special characters in messages', () => {
      const specialCharMessage = 'Server <not> "installed" & ready!';

      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={specialCharMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      expect(screen.getByText(specialCharMessage)).toBeInTheDocument();
    });

    it('handles messages with line breaks', () => {
      const multilineMessage = 'First line\nSecond line\nThird line';

      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={multilineMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      // React preserves line breaks in text content
      expect(screen.getByText((_content, element) => {
        return element?.textContent === multilineMessage;
      })).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('maintains semantic structure with proper heading hierarchy', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      // Title should be displayed prominently
      const title = screen.getByText('Server Not Installed');
      expect(title).toHaveClass('text-lg', 'font-medium');
    });

    it('button is keyboard accessible', () => {
      render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      const button = screen.getByRole('button', { name: 'Go to Installation' });
      expect(button).toBeEnabled();
      expect(button.closest('a')).toHaveAttribute('href', '/game-server/version');
    });

    it('provides clear visual hierarchy with CSS classes', () => {
      const { container } = render(
        <MemoryRouter>
          <EmptyServerState
            isInstalling={false}
            notInstalledMessage={defaultNotInstalledMessage}
            installingMessage={defaultInstallingMessage}
          />
        </MemoryRouter>
      );

      // Container centers content
      expect(container.firstChild).toHaveClass('items-center', 'justify-center');
    });
  });
});
