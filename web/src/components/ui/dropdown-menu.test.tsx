/**
 * Tests for dropdown-menu components.
 *
 * Story VSS-029.13: Dropdown Menu Test Coverage
 * Tests Radix UI dropdown-menu wrapper components
 *
 * Note: Some Radix UI components require specific context hierarchies
 * (e.g., MenuItem requires MenuContent). Tests focus on components
 * and props that can be verified in jsdom environment.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  DropdownMenu,
  DropdownMenuTrigger,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuLabel,
} from './dropdown-menu';

describe('DropdownMenu', () => {
  describe('rendering (AC: 1)', () => {
    it('has correct data-slot when root is rendered', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="trigger">Open</DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('trigger')).toBeInTheDocument();
      expect(screen.getByTestId('trigger')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-trigger'
      );
    });
  });

  describe('DropdownMenuTrigger', () => {
    it('renders trigger with correct data-slot', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Open Menu
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-trigger'
      );
    });

    it('renders as button element', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Open
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toBeInstanceOf(
        HTMLButtonElement
      );
    });

    it('renders button text', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Click Me
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toHaveTextContent('Click Me');
    });

    it('has aria-haspopup attribute', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Open
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toHaveAttribute(
        'aria-haspopup',
        'menu'
      );
    });

    it('has correct button type', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Open
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toHaveAttribute('type', 'button');
    });

    it('has aria-expanded attribute set to closed by default', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Open
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toHaveAttribute(
        'aria-expanded',
        'false'
      );
    });
  });

  describe('DropdownMenuSeparator', () => {
    it('renders separator with correct data-slot', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuSeparator data-testid="dropdown-separator" />
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-separator')).toBeInTheDocument();
      expect(screen.getByTestId('dropdown-separator')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-separator'
      );
    });

    it('has role="separator" attribute', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuSeparator data-testid="dropdown-separator" />
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-separator')).toHaveAttribute(
        'role',
        'separator'
      );
    });

    it('has correct styling classes', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuSeparator data-testid="dropdown-separator" />
        </DropdownMenu>
      );

      const separator = screen.getByTestId('dropdown-separator');
      expect(separator.className).toContain('bg-border');
      expect(separator.className).toContain('h-px');
      expect(separator.className).toContain('my-1');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuSeparator
            data-testid="dropdown-separator"
            className="custom-separator"
          />
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-separator').className).toContain(
        'custom-separator'
      );
    });
  });

  describe('DropdownMenuLabel', () => {
    it('renders label with correct data-slot', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuLabel data-testid="dropdown-label">
            Group Label
          </DropdownMenuLabel>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-label')).toBeInTheDocument();
      expect(screen.getByTestId('dropdown-label')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-label'
      );
    });

    it('renders children content', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuLabel data-testid="dropdown-label">
            <span>Label Text</span>
          </DropdownMenuLabel>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-label')).toHaveTextContent(
        'Label Text'
      );
    });

    it('applies inset prop', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuLabel data-testid="dropdown-label" inset>
            Inset Label
          </DropdownMenuLabel>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-label')).toHaveAttribute(
        'data-inset',
        'true'
      );
    });

    it('does not apply data-inset when inset is false', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuLabel data-testid="dropdown-label">Label</DropdownMenuLabel>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-label')).not.toHaveAttribute(
        'data-inset'
      );
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuLabel
            data-testid="dropdown-label"
            className="custom-label"
          >
            Label
          </DropdownMenuLabel>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-label').className).toContain(
        'custom-label'
      );
    });
  });

  describe('cn() utility (className composition)', () => {
    it('merges base classes with custom className on Separator', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuSeparator
            data-testid="dropdown-separator"
            className="custom"
          />
        </DropdownMenu>
      );

      const separator = screen.getByTestId('dropdown-separator');
      // Should have both base styling classes and custom class
      expect(separator.className).toContain('bg-border');
      expect(separator.className).toContain('h-px');
      expect(separator.className).toContain('custom');
    });

    it('handles multiple className merges', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuSeparator
            data-testid="dropdown-separator"
            className="class1 class2"
          />
        </DropdownMenu>
      );

      const separator = screen.getByTestId('dropdown-separator');
      expect(separator.className).toContain('class1');
      expect(separator.className).toContain('class2');
      // Should also have base classes
      expect(separator.className).toContain('bg-border');
      expect(separator.className).toContain('h-px');
    });
  });

  describe('accessibility attributes', () => {
    it('trigger has aria-haspopup="menu"', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Open
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toHaveAttribute(
        'aria-haspopup',
        'menu'
      );
    });

    it('trigger has aria-expanded attribute', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger data-testid="dropdown-trigger">
            Open
          </DropdownMenuTrigger>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-trigger')).toHaveAttribute(
        'aria-expanded',
        'false'
      );
    });

    it('separator has role="separator"', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuSeparator data-testid="dropdown-separator" />
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-separator')).toHaveAttribute(
        'role',
        'separator'
      );
    });
  });

  describe('component structure', () => {
    it('renders menu with trigger, label, and separator', () => {
      expect(() => {
        render(
          <DropdownMenu>
            <DropdownMenuTrigger data-testid="menu-trigger">Menu</DropdownMenuTrigger>
            <DropdownMenuLabel data-testid="menu-label">Actions</DropdownMenuLabel>
            <DropdownMenuSeparator data-testid="menu-separator" />
          </DropdownMenu>
        );
      }).not.toThrow();

      // Components that don't require MenuContent should render
      expect(screen.getByTestId('menu-trigger')).toBeInTheDocument();
      expect(screen.getByTestId('menu-label')).toBeInTheDocument();
      expect(screen.getByTestId('menu-separator')).toBeInTheDocument();
    });

    it('label has font-medium class for consistent styling', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuLabel data-testid="dropdown-label">Label</DropdownMenuLabel>
        </DropdownMenu>
      );

      const label = screen.getByTestId('dropdown-label');
      expect(label.className).toContain('font-medium');
    });
  });
});
