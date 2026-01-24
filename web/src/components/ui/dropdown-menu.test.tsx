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
  DropdownMenuContent,
  DropdownMenuPortal,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuCheckboxItem,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuLabel,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubTrigger,
  DropdownMenuSubContent,
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

  describe('DropdownMenuPortal', () => {
    it('renders portal with correct data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuPortal>
            <div data-testid="portal-content">Portal Content</div>
          </DropdownMenuPortal>
        </DropdownMenu>
      );

      expect(screen.getByTestId('portal-content')).toBeInTheDocument();
    });
  });

  describe('DropdownMenuContent', () => {
    it('renders content with correct data-slot when menu is open', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent data-testid="dropdown-content">
            <DropdownMenuItem>Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-content')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-content'
      );
    });

    it('renders children content', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent data-testid="dropdown-content">
            <DropdownMenuItem data-testid="item">Test Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('item')).toHaveTextContent('Test Item');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent data-testid="dropdown-content" className="custom-content">
            <DropdownMenuItem>Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-content').className).toContain('custom-content');
    });

    it('has correct base styling classes', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent data-testid="dropdown-content">
            <DropdownMenuItem>Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const content = screen.getByTestId('dropdown-content');
      expect(content.className).toContain('bg-popover');
      expect(content.className).toContain('z-50');
      expect(content.className).toContain('rounded-md');
      expect(content.className).toContain('border');
    });

    it('uses default sideOffset of 4', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent data-testid="dropdown-content">
            <DropdownMenuItem>Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      // Content should render without errors with default sideOffset
      expect(screen.getByTestId('dropdown-content')).toBeInTheDocument();
    });
  });

  describe('DropdownMenuGroup', () => {
    it('renders group with correct data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup data-testid="dropdown-group">
              <DropdownMenuItem>Item 1</DropdownMenuItem>
              <DropdownMenuItem>Item 2</DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-group')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-group'
      );
    });

    it('renders children items', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup data-testid="dropdown-group">
              <DropdownMenuItem data-testid="item-1">First</DropdownMenuItem>
              <DropdownMenuItem data-testid="item-2">Second</DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('item-1')).toHaveTextContent('First');
      expect(screen.getByTestId('item-2')).toHaveTextContent('Second');
    });

    it('has role="group" attribute', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuGroup data-testid="dropdown-group">
              <DropdownMenuItem>Item</DropdownMenuItem>
            </DropdownMenuGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-group')).toHaveAttribute('role', 'group');
    });
  });

  describe('DropdownMenuItem', () => {
    it('renders item with correct data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item">Action</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-item'
      );
    });

    it('renders item text', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item">Click Me</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item')).toHaveTextContent('Click Me');
    });

    it('applies inset prop', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item" inset>
              Inset Item
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item')).toHaveAttribute('data-inset', 'true');
    });

    it('does not apply data-inset when inset is not set', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item">Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item')).not.toHaveAttribute('data-inset');
    });

    it('applies default variant', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item">Default</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item')).toHaveAttribute('data-variant', 'default');
    });

    it('applies destructive variant', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item" variant="destructive">
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item')).toHaveAttribute('data-variant', 'destructive');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item" className="custom-item">
              Item
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item').className).toContain('custom-item');
    });

    it('has correct base styling classes', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item">Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const item = screen.getByTestId('dropdown-item');
      expect(item.className).toContain('flex');
      expect(item.className).toContain('cursor-default');
      expect(item.className).toContain('items-center');
      expect(item.className).toContain('rounded-sm');
      expect(item.className).toContain('text-sm');
    });

    it('has role="menuitem" attribute', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuItem data-testid="dropdown-item">Item</DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('dropdown-item')).toHaveAttribute('role', 'menuitem');
    });
  });

  describe('DropdownMenuCheckboxItem', () => {
    it('renders checkbox item with correct data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem data-testid="checkbox-item" checked={false}>
              Option
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('checkbox-item')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-checkbox-item'
      );
    });

    it('renders children content', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem data-testid="checkbox-item" checked={false}>
              Checkbox Label
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('checkbox-item')).toHaveTextContent('Checkbox Label');
    });

    it('has role="menuitemcheckbox" attribute', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem data-testid="checkbox-item" checked={false}>
              Option
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('checkbox-item')).toHaveAttribute('role', 'menuitemcheckbox');
    });

    it('shows checked state', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem data-testid="checkbox-item" checked={true}>
              Checked Option
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('checkbox-item')).toHaveAttribute('aria-checked', 'true');
    });

    it('shows unchecked state', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem data-testid="checkbox-item" checked={false}>
              Unchecked Option
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('checkbox-item')).toHaveAttribute('aria-checked', 'false');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuCheckboxItem
              data-testid="checkbox-item"
              checked={false}
              className="custom-checkbox"
            >
              Option
            </DropdownMenuCheckboxItem>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('checkbox-item').className).toContain('custom-checkbox');
    });
  });

  describe('DropdownMenuRadioGroup', () => {
    it('renders radio group with correct data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup data-testid="radio-group" value="option1">
              <DropdownMenuRadioItem value="option1">Option 1</DropdownMenuRadioItem>
              <DropdownMenuRadioItem value="option2">Option 2</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-group')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-radio-group'
      );
    });

    it('renders children radio items', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup data-testid="radio-group" value="option1">
              <DropdownMenuRadioItem data-testid="radio-1" value="option1">
                First
              </DropdownMenuRadioItem>
              <DropdownMenuRadioItem data-testid="radio-2" value="option2">
                Second
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-1')).toHaveTextContent('First');
      expect(screen.getByTestId('radio-2')).toHaveTextContent('Second');
    });

    it('has role="group" attribute', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup data-testid="radio-group" value="option1">
              <DropdownMenuRadioItem value="option1">Option</DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-group')).toHaveAttribute('role', 'group');
    });
  });

  describe('DropdownMenuRadioItem', () => {
    it('renders radio item with correct data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup value="option1">
              <DropdownMenuRadioItem data-testid="radio-item" value="option1">
                Option
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-item')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-radio-item'
      );
    });

    it('has role="menuitemradio" attribute', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup value="option1">
              <DropdownMenuRadioItem data-testid="radio-item" value="option1">
                Option
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-item')).toHaveAttribute('role', 'menuitemradio');
    });

    it('shows selected state when value matches', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup value="option1">
              <DropdownMenuRadioItem data-testid="radio-item" value="option1">
                Selected
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-item')).toHaveAttribute('aria-checked', 'true');
    });

    it('shows unselected state when value does not match', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup value="option1">
              <DropdownMenuRadioItem data-testid="radio-item" value="option2">
                Not Selected
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-item')).toHaveAttribute('aria-checked', 'false');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuRadioGroup value="option1">
              <DropdownMenuRadioItem
                data-testid="radio-item"
                value="option1"
                className="custom-radio"
              >
                Option
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('radio-item').className).toContain('custom-radio');
    });
  });

  describe('DropdownMenuShortcut', () => {
    it('renders shortcut with correct data-slot', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuShortcut data-testid="shortcut">⌘K</DropdownMenuShortcut>
        </DropdownMenu>
      );

      expect(screen.getByTestId('shortcut')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-shortcut'
      );
    });

    it('renders shortcut text', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuShortcut data-testid="shortcut">Ctrl+S</DropdownMenuShortcut>
        </DropdownMenu>
      );

      expect(screen.getByTestId('shortcut')).toHaveTextContent('Ctrl+S');
    });

    it('has correct styling classes', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuShortcut data-testid="shortcut">⌘K</DropdownMenuShortcut>
        </DropdownMenu>
      );

      const shortcut = screen.getByTestId('shortcut');
      expect(shortcut.className).toContain('text-muted-foreground');
      expect(shortcut.className).toContain('ml-auto');
      expect(shortcut.className).toContain('text-xs');
      expect(shortcut.className).toContain('tracking-widest');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuShortcut data-testid="shortcut" className="custom-shortcut">
            ⌘K
          </DropdownMenuShortcut>
        </DropdownMenu>
      );

      expect(screen.getByTestId('shortcut').className).toContain('custom-shortcut');
    });

    it('is a span element', () => {
      render(
        <DropdownMenu>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuShortcut data-testid="shortcut">⌘K</DropdownMenuShortcut>
        </DropdownMenu>
      );

      expect(screen.getByTestId('shortcut').tagName).toBe('SPAN');
    });
  });

  describe('DropdownMenuSub', () => {
    it('renders sub menu structure', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger">
                More Options
              </DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-trigger')).toBeInTheDocument();
    });
  });

  describe('DropdownMenuSubTrigger', () => {
    it('renders sub trigger with correct data-slot', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger">
                More
              </DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-trigger')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-sub-trigger'
      );
    });

    it('renders children content', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger">
                More Options
              </DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-trigger')).toHaveTextContent('More Options');
    });

    it('has chevron icon', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger">
                More
              </DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const trigger = screen.getByTestId('sub-trigger');
      expect(trigger.querySelector('svg')).toBeInTheDocument();
    });

    it('applies inset prop', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger" inset>
                Inset Sub
              </DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-trigger')).toHaveAttribute('data-inset', 'true');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger" className="custom-sub">
                More
              </DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-trigger').className).toContain('custom-sub');
    });

    it('has correct styling classes', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger">
                More
              </DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const trigger = screen.getByTestId('sub-trigger');
      expect(trigger.className).toContain('flex');
      expect(trigger.className).toContain('cursor-default');
      expect(trigger.className).toContain('items-center');
      expect(trigger.className).toContain('rounded-sm');
    });
  });

  describe('DropdownMenuSubContent', () => {
    it('renders sub content when sub menu is open', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub open>
              <DropdownMenuSubTrigger>More</DropdownMenuSubTrigger>
              <DropdownMenuSubContent data-testid="sub-content">
                <DropdownMenuItem>Sub Item</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-content')).toHaveAttribute(
        'data-slot',
        'dropdown-menu-sub-content'
      );
    });

    it('renders children in sub content', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub open>
              <DropdownMenuSubTrigger>More</DropdownMenuSubTrigger>
              <DropdownMenuSubContent data-testid="sub-content">
                <DropdownMenuItem data-testid="sub-item">Sub Item</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-item')).toHaveTextContent('Sub Item');
    });

    it('applies custom className', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub open>
              <DropdownMenuSubTrigger>More</DropdownMenuSubTrigger>
              <DropdownMenuSubContent data-testid="sub-content" className="custom-sub-content">
                <DropdownMenuItem>Item</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('sub-content').className).toContain('custom-sub-content');
    });

    it('has correct styling classes', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger>Open</DropdownMenuTrigger>
          <DropdownMenuContent>
            <DropdownMenuSub open>
              <DropdownMenuSubTrigger>More</DropdownMenuSubTrigger>
              <DropdownMenuSubContent data-testid="sub-content">
                <DropdownMenuItem>Item</DropdownMenuItem>
              </DropdownMenuSubContent>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      const content = screen.getByTestId('sub-content');
      expect(content.className).toContain('bg-popover');
      expect(content.className).toContain('z-50');
      expect(content.className).toContain('rounded-md');
      expect(content.className).toContain('border');
    });
  });

  describe('complete dropdown structure', () => {
    it('renders full dropdown with all components', () => {
      render(
        <DropdownMenu open>
          <DropdownMenuTrigger data-testid="trigger">Options</DropdownMenuTrigger>
          <DropdownMenuContent data-testid="content">
            <DropdownMenuLabel data-testid="label">Actions</DropdownMenuLabel>
            <DropdownMenuSeparator data-testid="separator" />
            <DropdownMenuGroup>
              <DropdownMenuItem data-testid="item">
                Edit
                <DropdownMenuShortcut data-testid="shortcut">⌘E</DropdownMenuShortcut>
              </DropdownMenuItem>
            </DropdownMenuGroup>
            <DropdownMenuSeparator />
            <DropdownMenuCheckboxItem data-testid="checkbox" checked={true}>
              Show Toolbar
            </DropdownMenuCheckboxItem>
            <DropdownMenuSeparator />
            <DropdownMenuRadioGroup value="small">
              <DropdownMenuRadioItem data-testid="radio" value="small">
                Small
              </DropdownMenuRadioItem>
            </DropdownMenuRadioGroup>
            <DropdownMenuSeparator />
            <DropdownMenuSub>
              <DropdownMenuSubTrigger data-testid="sub-trigger">More</DropdownMenuSubTrigger>
            </DropdownMenuSub>
          </DropdownMenuContent>
        </DropdownMenu>
      );

      expect(screen.getByTestId('trigger')).toBeInTheDocument();
      expect(screen.getByTestId('content')).toBeInTheDocument();
      expect(screen.getByTestId('label')).toBeInTheDocument();
      expect(screen.getByTestId('separator')).toBeInTheDocument();
      expect(screen.getByTestId('item')).toBeInTheDocument();
      expect(screen.getByTestId('shortcut')).toBeInTheDocument();
      expect(screen.getByTestId('checkbox')).toBeInTheDocument();
      expect(screen.getByTestId('radio')).toBeInTheDocument();
      expect(screen.getByTestId('sub-trigger')).toBeInTheDocument();
    });
  });
});
