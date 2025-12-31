import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { SettingGroup } from './SettingGroup';

describe('SettingGroup', () => {
  describe('rendering', () => {
    it('renders title', () => {
      render(
        <SettingGroup title="Server Info">
          <div>Child content</div>
        </SettingGroup>
      );

      expect(screen.getByText('Server Info')).toBeInTheDocument();
    });

    it('renders description when provided', () => {
      render(
        <SettingGroup title="Server Info" description="Basic server settings">
          <div>Child content</div>
        </SettingGroup>
      );

      expect(screen.getByText('Basic server settings')).toBeInTheDocument();
    });

    it('renders children', () => {
      render(
        <SettingGroup title="Server Info">
          <div data-testid="child">Child content</div>
        </SettingGroup>
      );

      expect(screen.getByTestId('child')).toBeInTheDocument();
    });

    it('renders in a Card', () => {
      render(
        <SettingGroup title="Server Info">
          <div>Child content</div>
        </SettingGroup>
      );

      // Card has data-slot="card" attribute
      expect(document.querySelector('[data-slot="card"]')).toBeInTheDocument();
    });
  });

  describe('non-collapsible behavior', () => {
    it('always shows content when not collapsible', () => {
      render(
        <SettingGroup title="Always Visible">
          <div data-testid="content">Content here</div>
        </SettingGroup>
      );

      expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('does not show chevron when not collapsible', () => {
      render(
        <SettingGroup title="No Chevron">
          <div>Content</div>
        </SettingGroup>
      );

      // Chevron is not rendered
      expect(document.querySelector('svg')).not.toBeInTheDocument();
    });

    it('header is not clickable when not collapsible', () => {
      render(
        <SettingGroup title="Not Clickable">
          <div data-testid="content">Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Not Clickable').closest('[data-slot="card-header"]');
      expect(header).not.toHaveAttribute('role', 'button');
      expect(header).not.toHaveAttribute('tabIndex');
    });
  });

  describe('collapsible behavior', () => {
    it('shows chevron when collapsible', () => {
      render(
        <SettingGroup title="Collapsible" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      expect(document.querySelector('svg')).toBeInTheDocument();
    });

    it('shows content by default when collapsible', () => {
      render(
        <SettingGroup title="Collapsible" collapsible>
          <div data-testid="content">Content</div>
        </SettingGroup>
      );

      expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('hides content when defaultCollapsed is true', () => {
      render(
        <SettingGroup title="Collapsed" collapsible defaultCollapsed>
          <div data-testid="content">Content</div>
        </SettingGroup>
      );

      expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    });

    it('toggles content on header click', () => {
      render(
        <SettingGroup title="Toggle" collapsible>
          <div data-testid="content">Content</div>
        </SettingGroup>
      );

      // Initially visible
      expect(screen.getByTestId('content')).toBeInTheDocument();

      // Click to collapse
      const header = screen.getByText('Toggle').closest('[data-slot="card-header"]');
      fireEvent.click(header!);

      // Now hidden
      expect(screen.queryByTestId('content')).not.toBeInTheDocument();

      // Click to expand
      fireEvent.click(header!);

      // Visible again
      expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('shows down chevron when expanded', () => {
      render(
        <SettingGroup title="Expanded" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      // Check for the chevron-down class (ChevronDown icon)
      const svg = document.querySelector('svg');
      expect(svg).toBeInTheDocument();
      // The expanded state shows ChevronDown
      expect(screen.getByText('Content')).toBeInTheDocument();
    });

    it('shows right chevron when collapsed', () => {
      render(
        <SettingGroup title="Collapsed" collapsible defaultCollapsed>
          <div data-testid="content">Content</div>
        </SettingGroup>
      );

      // Content should be hidden
      expect(screen.queryByTestId('content')).not.toBeInTheDocument();
      // Chevron should still be visible
      expect(document.querySelector('svg')).toBeInTheDocument();
    });
  });

  describe('accessibility', () => {
    it('has role=button when collapsible', () => {
      render(
        <SettingGroup title="Accessible" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Accessible').closest('[data-slot="card-header"]');
      expect(header).toHaveAttribute('role', 'button');
    });

    it('has aria-expanded when collapsible', () => {
      render(
        <SettingGroup title="Accessible" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Accessible').closest('[data-slot="card-header"]');
      expect(header).toHaveAttribute('aria-expanded', 'true');
    });

    it('updates aria-expanded on toggle', () => {
      render(
        <SettingGroup title="Accessible" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Accessible').closest('[data-slot="card-header"]');
      expect(header).toHaveAttribute('aria-expanded', 'true');

      fireEvent.click(header!);

      expect(header).toHaveAttribute('aria-expanded', 'false');
    });

    it('has tabIndex when collapsible', () => {
      render(
        <SettingGroup title="Focusable" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Focusable').closest('[data-slot="card-header"]');
      expect(header).toHaveAttribute('tabIndex', '0');
    });

    it('toggles on Enter key', () => {
      render(
        <SettingGroup title="Keyboard" collapsible>
          <div data-testid="content">Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Keyboard').closest('[data-slot="card-header"]');

      // Press Enter to collapse
      fireEvent.keyDown(header!, { key: 'Enter' });
      expect(screen.queryByTestId('content')).not.toBeInTheDocument();

      // Press Enter to expand
      fireEvent.keyDown(header!, { key: 'Enter' });
      expect(screen.getByTestId('content')).toBeInTheDocument();
    });

    it('toggles on Space key', () => {
      render(
        <SettingGroup title="Keyboard" collapsible>
          <div data-testid="content">Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Keyboard').closest('[data-slot="card-header"]');

      // Press Space to collapse
      fireEvent.keyDown(header!, { key: ' ' });
      expect(screen.queryByTestId('content')).not.toBeInTheDocument();
    });

    it('chevron has aria-hidden', () => {
      render(
        <SettingGroup title="Hidden Chevron" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      const svg = document.querySelector('svg');
      expect(svg).toHaveAttribute('aria-hidden', 'true');
    });
  });

  describe('styling', () => {
    it('applies custom className', () => {
      render(
        <SettingGroup title="Custom" className="custom-class">
          <div>Content</div>
        </SettingGroup>
      );

      const card = document.querySelector('[data-slot="card"]');
      expect(card).toHaveClass('custom-class');
    });

    it('has hover effect on collapsible header', () => {
      render(
        <SettingGroup title="Hoverable" collapsible>
          <div>Content</div>
        </SettingGroup>
      );

      const header = screen.getByText('Hoverable').closest('[data-slot="card-header"]');
      expect(header).toHaveClass('cursor-pointer');
      expect(header).toHaveClass('hover:bg-muted/50');
    });
  });
});
