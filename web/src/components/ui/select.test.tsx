/**
 * Tests for select components.
 *
 * Tests Radix UI select wrapper components including SelectGroup,
 * SelectLabel, and SelectSeparator to achieve full coverage.
 *
 * Note: Some Radix UI components require specific context hierarchies
 * (e.g., SelectItem requires SelectContent). Tests focus on components
 * and props that can be verified in jsdom environment.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectGroup,
  SelectLabel,
  SelectSeparator,
} from './select';

describe('Select', () => {
  describe('Select root component', () => {
    it('renders with correct data-slot', () => {
      render(
        <Select>
          <SelectTrigger data-testid="trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      const trigger = screen.getByTestId('trigger');
      expect(trigger).toBeInTheDocument();
      expect(trigger).toHaveAttribute('data-slot', 'select-trigger');
    });
  });

  describe('SelectTrigger', () => {
    it('renders trigger with correct data-slot', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-trigger')).toHaveAttribute(
        'data-slot',
        'select-trigger'
      );
    });

    it('renders as button element', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-trigger')).toBeInstanceOf(
        HTMLButtonElement
      );
    });

    it('has default size attribute', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-trigger')).toHaveAttribute(
        'data-size',
        'default'
      );
    });

    it('applies small size when specified', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger" size="sm">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-trigger')).toHaveAttribute(
        'data-size',
        'sm'
      );
    });

    it('has correct button type', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-trigger')).toHaveAttribute(
        'type',
        'button'
      );
    });

    it('has aria-expanded attribute', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-trigger')).toHaveAttribute(
        'aria-expanded'
      );
    });
  });

  describe('SelectValue', () => {
    it('renders value with correct data-slot', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue data-testid="select-value" />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-value')).toHaveAttribute(
        'data-slot',
        'select-value'
      );
    });

    it('accepts placeholder prop', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue
              data-testid="select-value"
              placeholder="Select an option"
            />
          </SelectTrigger>
        </Select>
      );

      const value = screen.getByTestId('select-value');
      expect(value).toBeInTheDocument();
    });
  });

  describe('SelectGroup', () => {
    it('renders group with correct data-slot', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectGroup data-testid="select-group" />
        </Select>
      );

      expect(screen.getByTestId('select-group')).toBeInTheDocument();
      expect(screen.getByTestId('select-group')).toHaveAttribute(
        'data-slot',
        'select-group'
      );
    });

    it('renders children content', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectGroup data-testid="select-group">
            <div data-testid="group-child">Group content</div>
          </SelectGroup>
        </Select>
      );

      expect(screen.getByTestId('select-group')).toBeInTheDocument();
      expect(screen.getByTestId('group-child')).toHaveTextContent(
        'Group content'
      );
    });
  });

  describe('SelectLabel', () => {
    it('renders label with correct data-slot', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectGroup>
            <SelectLabel data-testid="select-label">Label Text</SelectLabel>
          </SelectGroup>
        </Select>
      );

      expect(screen.getByTestId('select-label')).toBeInTheDocument();
      expect(screen.getByTestId('select-label')).toHaveAttribute(
        'data-slot',
        'select-label'
      );
    });

    it('renders children content', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectGroup>
            <SelectLabel data-testid="select-label">
              <span>Label Content</span>
            </SelectLabel>
          </SelectGroup>
        </Select>
      );

      expect(screen.getByTestId('select-label')).toHaveTextContent(
        'Label Content'
      );
    });

    it('has correct styling classes', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectGroup>
            <SelectLabel data-testid="select-label">Label</SelectLabel>
          </SelectGroup>
        </Select>
      );

      const label = screen.getByTestId('select-label');
      expect(label.className).toContain('text-muted-foreground');
      expect(label.className).toContain('px-2');
      expect(label.className).toContain('py-1.5');
      expect(label.className).toContain('text-xs');
    });

    it('applies custom className', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectGroup>
            <SelectLabel data-testid="select-label" className="custom-label">
              Label
            </SelectLabel>
          </SelectGroup>
        </Select>
      );

      expect(screen.getByTestId('select-label').className).toContain(
        'custom-label'
      );
    });
  });

  describe('SelectSeparator', () => {
    it('renders separator with correct data-slot', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectSeparator data-testid="select-separator" />
        </Select>
      );

      expect(screen.getByTestId('select-separator')).toBeInTheDocument();
      expect(screen.getByTestId('select-separator')).toHaveAttribute(
        'data-slot',
        'select-separator'
      );
    });

    it('has correct styling classes', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectSeparator data-testid="select-separator" />
        </Select>
      );

      const separator = screen.getByTestId('select-separator');
      expect(separator.className).toContain('bg-border');
      expect(separator.className).toContain('h-px');
      expect(separator.className).toContain('my-1');
      expect(separator.className).toContain('pointer-events-none');
    });

    it('applies custom className', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectSeparator
            data-testid="select-separator"
            className="custom-separator"
          />
        </Select>
      );

      expect(screen.getByTestId('select-separator').className).toContain(
        'custom-separator'
      );
    });
  });

  describe('cn() utility (className composition)', () => {
    it('merges base classes with custom className on Separator', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectSeparator data-testid="select-separator" className="custom" />
        </Select>
      );

      const separator = screen.getByTestId('select-separator');
      // Should have both base styling classes and custom class
      expect(separator.className).toContain('bg-border');
      expect(separator.className).toContain('h-px');
      expect(separator.className).toContain('custom');
    });

    it('merges base classes with custom className on Label', () => {
      render(
        <Select>
          <SelectTrigger>
            <SelectValue />
          </SelectTrigger>
          <SelectGroup>
            <SelectLabel data-testid="select-label" className="custom">
              Label
            </SelectLabel>
          </SelectGroup>
        </Select>
      );

      const label = screen.getByTestId('select-label');
      expect(label.className).toContain('text-muted-foreground');
      expect(label.className).toContain('custom');
    });
  });

  describe('accessibility attributes', () => {
    it('trigger has aria-expanded attribute', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      expect(screen.getByTestId('select-trigger')).toHaveAttribute(
        'aria-expanded'
      );
    });
  });

  describe('component structure', () => {
    it('renders select with trigger, value, group, label, and separator', () => {
      expect(() => {
        render(
          <Select>
            <SelectTrigger data-testid="select-trigger">
              <SelectValue data-testid="select-value" />
            </SelectTrigger>
            <SelectGroup data-testid="select-group">
              <SelectLabel data-testid="select-label">Options</SelectLabel>
              <SelectSeparator data-testid="select-separator" />
            </SelectGroup>
          </Select>
        );
      }).not.toThrow();

      // All components should render
      expect(screen.getByTestId('select-trigger')).toBeInTheDocument();
      expect(screen.getByTestId('select-value')).toBeInTheDocument();
      expect(screen.getByTestId('select-group')).toBeInTheDocument();
      expect(screen.getByTestId('select-label')).toBeInTheDocument();
      expect(screen.getByTestId('select-separator')).toBeInTheDocument();
    });

    it('trigger contains chevron icon', () => {
      render(
        <Select>
          <SelectTrigger data-testid="select-trigger">
            <SelectValue />
          </SelectTrigger>
        </Select>
      );

      const trigger = screen.getByTestId('select-trigger');
      const svg = trigger.querySelector('svg');
      expect(svg).toBeInTheDocument();
    });
  });
});
