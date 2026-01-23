/**
 * Tests for card components.
 *
 * Tests Card UI wrapper components including Card, CardHeader, CardTitle,
 * CardDescription, CardAction, CardContent, and CardFooter.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardAction,
  CardContent,
  CardFooter,
} from './card';

describe('Card', () => {
  describe('Card', () => {
    it('renders card with correct data-slot', () => {
      render(<Card data-testid="card">Card content</Card>);

      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByTestId('card')).toHaveAttribute('data-slot', 'card');
    });

    it('renders as div element', () => {
      render(<Card data-testid="card">Content</Card>);

      expect(screen.getByTestId('card')).toBeInstanceOf(HTMLDivElement);
    });

    it('renders children content', () => {
      render(<Card data-testid="card">Test content</Card>);

      expect(screen.getByTestId('card')).toHaveTextContent('Test content');
    });

    it('has correct styling classes', () => {
      render(<Card data-testid="card">Content</Card>);

      const card = screen.getByTestId('card');
      expect(card.className).toContain('bg-card');
      expect(card.className).toContain('text-card-foreground');
      expect(card.className).toContain('rounded-xl');
      expect(card.className).toContain('border');
      expect(card.className).toContain('shadow-sm');
    });

    it('applies custom className', () => {
      render(
        <Card data-testid="card" className="custom-card">
          Content
        </Card>
      );

      expect(screen.getByTestId('card').className).toContain('custom-card');
    });
  });

  describe('CardHeader', () => {
    it('renders header with correct data-slot', () => {
      render(<CardHeader data-testid="card-header">Header</CardHeader>);

      expect(screen.getByTestId('card-header')).toBeInTheDocument();
      expect(screen.getByTestId('card-header')).toHaveAttribute(
        'data-slot',
        'card-header'
      );
    });

    it('renders as div element', () => {
      render(<CardHeader data-testid="card-header">Header</CardHeader>);

      expect(screen.getByTestId('card-header')).toBeInstanceOf(HTMLDivElement);
    });

    it('renders children content', () => {
      render(
        <CardHeader data-testid="card-header">
          <span>Header text</span>
        </CardHeader>
      );

      expect(screen.getByTestId('card-header')).toHaveTextContent('Header text');
    });

    it('has correct styling classes', () => {
      render(<CardHeader data-testid="card-header">Header</CardHeader>);

      const header = screen.getByTestId('card-header');
      expect(header.className).toContain('grid');
      expect(header.className).toContain('px-6');
    });

    it('applies custom className', () => {
      render(
        <CardHeader data-testid="card-header" className="custom-header">
          Header
        </CardHeader>
      );

      expect(screen.getByTestId('card-header').className).toContain(
        'custom-header'
      );
    });
  });

  describe('CardTitle', () => {
    it('renders title with correct data-slot', () => {
      render(<CardTitle data-testid="card-title">Title</CardTitle>);

      expect(screen.getByTestId('card-title')).toBeInTheDocument();
      expect(screen.getByTestId('card-title')).toHaveAttribute(
        'data-slot',
        'card-title'
      );
    });

    it('renders as div element', () => {
      render(<CardTitle data-testid="card-title">Title</CardTitle>);

      expect(screen.getByTestId('card-title')).toBeInstanceOf(HTMLDivElement);
    });

    it('renders children content', () => {
      render(<CardTitle data-testid="card-title">Card Title</CardTitle>);

      expect(screen.getByTestId('card-title')).toHaveTextContent('Card Title');
    });

    it('has correct styling classes', () => {
      render(<CardTitle data-testid="card-title">Title</CardTitle>);

      const title = screen.getByTestId('card-title');
      expect(title.className).toContain('font-semibold');
      expect(title.className).toContain('leading-none');
    });

    it('applies custom className', () => {
      render(
        <CardTitle data-testid="card-title" className="custom-title">
          Title
        </CardTitle>
      );

      expect(screen.getByTestId('card-title').className).toContain(
        'custom-title'
      );
    });
  });

  describe('CardDescription', () => {
    it('renders description with correct data-slot', () => {
      render(
        <CardDescription data-testid="card-description">
          Description
        </CardDescription>
      );

      expect(screen.getByTestId('card-description')).toBeInTheDocument();
      expect(screen.getByTestId('card-description')).toHaveAttribute(
        'data-slot',
        'card-description'
      );
    });

    it('renders as div element', () => {
      render(
        <CardDescription data-testid="card-description">
          Description
        </CardDescription>
      );

      expect(screen.getByTestId('card-description')).toBeInstanceOf(
        HTMLDivElement
      );
    });

    it('renders children content', () => {
      render(
        <CardDescription data-testid="card-description">
          Card description text
        </CardDescription>
      );

      expect(screen.getByTestId('card-description')).toHaveTextContent(
        'Card description text'
      );
    });

    it('has correct styling classes', () => {
      render(
        <CardDescription data-testid="card-description">
          Description
        </CardDescription>
      );

      const description = screen.getByTestId('card-description');
      expect(description.className).toContain('text-muted-foreground');
      expect(description.className).toContain('text-sm');
    });

    it('applies custom className', () => {
      render(
        <CardDescription
          data-testid="card-description"
          className="custom-description"
        >
          Description
        </CardDescription>
      );

      expect(screen.getByTestId('card-description').className).toContain(
        'custom-description'
      );
    });
  });

  describe('CardAction', () => {
    it('renders action with correct data-slot', () => {
      render(<CardAction data-testid="card-action">Action</CardAction>);

      expect(screen.getByTestId('card-action')).toBeInTheDocument();
      expect(screen.getByTestId('card-action')).toHaveAttribute(
        'data-slot',
        'card-action'
      );
    });

    it('renders as div element', () => {
      render(<CardAction data-testid="card-action">Action</CardAction>);

      expect(screen.getByTestId('card-action')).toBeInstanceOf(HTMLDivElement);
    });

    it('renders children content', () => {
      render(
        <CardAction data-testid="card-action">
          <button>Click me</button>
        </CardAction>
      );

      expect(screen.getByTestId('card-action')).toHaveTextContent('Click me');
    });

    it('has correct styling classes', () => {
      render(<CardAction data-testid="card-action">Action</CardAction>);

      const action = screen.getByTestId('card-action');
      expect(action.className).toContain('col-start-2');
      expect(action.className).toContain('row-span-2');
      expect(action.className).toContain('row-start-1');
      expect(action.className).toContain('self-start');
      expect(action.className).toContain('justify-self-end');
    });

    it('applies custom className', () => {
      render(
        <CardAction data-testid="card-action" className="custom-action">
          Action
        </CardAction>
      );

      expect(screen.getByTestId('card-action').className).toContain(
        'custom-action'
      );
    });
  });

  describe('CardContent', () => {
    it('renders content with correct data-slot', () => {
      render(<CardContent data-testid="card-content">Content</CardContent>);

      expect(screen.getByTestId('card-content')).toBeInTheDocument();
      expect(screen.getByTestId('card-content')).toHaveAttribute(
        'data-slot',
        'card-content'
      );
    });

    it('renders as div element', () => {
      render(<CardContent data-testid="card-content">Content</CardContent>);

      expect(screen.getByTestId('card-content')).toBeInstanceOf(HTMLDivElement);
    });

    it('renders children content', () => {
      render(
        <CardContent data-testid="card-content">
          Card content text
        </CardContent>
      );

      expect(screen.getByTestId('card-content')).toHaveTextContent(
        'Card content text'
      );
    });

    it('has correct styling classes', () => {
      render(<CardContent data-testid="card-content">Content</CardContent>);

      const content = screen.getByTestId('card-content');
      expect(content.className).toContain('px-6');
    });

    it('applies custom className', () => {
      render(
        <CardContent data-testid="card-content" className="custom-content">
          Content
        </CardContent>
      );

      expect(screen.getByTestId('card-content').className).toContain(
        'custom-content'
      );
    });
  });

  describe('CardFooter', () => {
    it('renders footer with correct data-slot', () => {
      render(<CardFooter data-testid="card-footer">Footer</CardFooter>);

      expect(screen.getByTestId('card-footer')).toBeInTheDocument();
      expect(screen.getByTestId('card-footer')).toHaveAttribute(
        'data-slot',
        'card-footer'
      );
    });

    it('renders as div element', () => {
      render(<CardFooter data-testid="card-footer">Footer</CardFooter>);

      expect(screen.getByTestId('card-footer')).toBeInstanceOf(HTMLDivElement);
    });

    it('renders children content', () => {
      render(
        <CardFooter data-testid="card-footer">
          <button>Cancel</button>
          <button>Save</button>
        </CardFooter>
      );

      expect(screen.getByTestId('card-footer')).toHaveTextContent('Cancel');
      expect(screen.getByTestId('card-footer')).toHaveTextContent('Save');
    });

    it('has correct styling classes', () => {
      render(<CardFooter data-testid="card-footer">Footer</CardFooter>);

      const footer = screen.getByTestId('card-footer');
      expect(footer.className).toContain('flex');
      expect(footer.className).toContain('items-center');
      expect(footer.className).toContain('px-6');
    });

    it('applies custom className', () => {
      render(
        <CardFooter data-testid="card-footer" className="custom-footer">
          Footer
        </CardFooter>
      );

      expect(screen.getByTestId('card-footer').className).toContain(
        'custom-footer'
      );
    });
  });

  describe('cn() utility (className composition)', () => {
    it('merges base classes with custom className on Card', () => {
      render(
        <Card data-testid="card" className="custom">
          Content
        </Card>
      );

      const card = screen.getByTestId('card');
      expect(card.className).toContain('bg-card');
      expect(card.className).toContain('border');
      expect(card.className).toContain('custom');
    });

    it('merges base classes with custom className on CardAction', () => {
      render(
        <CardAction data-testid="card-action" className="custom-action">
          Action
        </CardAction>
      );

      const action = screen.getByTestId('card-action');
      expect(action.className).toContain('col-start-2');
      expect(action.className).toContain('row-span-2');
      expect(action.className).toContain('custom-action');
    });

    it('merges base classes with custom className on CardFooter', () => {
      render(
        <CardFooter data-testid="card-footer" className="custom-footer">
          Footer
        </CardFooter>
      );

      const footer = screen.getByTestId('card-footer');
      expect(footer.className).toContain('flex');
      expect(footer.className).toContain('items-center');
      expect(footer.className).toContain('custom-footer');
    });

    it('handles multiple className merges', () => {
      render(
        <Card data-testid="card" className="class1 class2">
          Content
        </Card>
      );

      const card = screen.getByTestId('card');
      expect(card.className).toContain('class1');
      expect(card.className).toContain('class2');
      expect(card.className).toContain('bg-card');
      expect(card.className).toContain('border');
    });
  });

  describe('component structure', () => {
    it('renders complete card with all components', () => {
      expect(() => {
        render(
          <Card data-testid="card">
            <CardHeader data-testid="header">
              <CardTitle data-testid="title">Card Title</CardTitle>
              <CardDescription data-testid="description">
                Card description
              </CardDescription>
              <CardAction data-testid="action">
                <button>Action</button>
              </CardAction>
            </CardHeader>
            <CardContent data-testid="content">Card content</CardContent>
            <CardFooter data-testid="footer">
              <button>Cancel</button>
              <button>Save</button>
            </CardFooter>
          </Card>
        );
      }).not.toThrow();

      expect(screen.getByTestId('card')).toBeInTheDocument();
      expect(screen.getByTestId('header')).toBeInTheDocument();
      expect(screen.getByTestId('title')).toBeInTheDocument();
      expect(screen.getByTestId('description')).toBeInTheDocument();
      expect(screen.getByTestId('action')).toBeInTheDocument();
      expect(screen.getByTestId('content')).toBeInTheDocument();
      expect(screen.getByTestId('footer')).toBeInTheDocument();
    });

    it('CardAction can contain interactive elements', () => {
      render(
        <CardAction data-testid="card-action">
          <button data-testid="action-button">Click</button>
        </CardAction>
      );

      expect(screen.getByTestId('action-button')).toBeInTheDocument();
      expect(screen.getByTestId('action-button')).toBeInstanceOf(
        HTMLButtonElement
      );
    });

    it('CardFooter can contain multiple action buttons', () => {
      render(
        <CardFooter data-testid="card-footer">
          <button data-testid="cancel-btn">Cancel</button>
          <button data-testid="save-btn">Save</button>
          <button data-testid="delete-btn">Delete</button>
        </CardFooter>
      );

      expect(screen.getByTestId('cancel-btn')).toBeInTheDocument();
      expect(screen.getByTestId('save-btn')).toBeInTheDocument();
      expect(screen.getByTestId('delete-btn')).toBeInTheDocument();
    });
  });

  describe('data-slot attributes', () => {
    it('all components have correct data-slot attributes', () => {
      render(
        <Card data-testid="card">
          <CardHeader data-testid="header">
            <CardTitle data-testid="title">Title</CardTitle>
            <CardDescription data-testid="description">
              Description
            </CardDescription>
            <CardAction data-testid="action">Action</CardAction>
          </CardHeader>
          <CardContent data-testid="content">Content</CardContent>
          <CardFooter data-testid="footer">Footer</CardFooter>
        </Card>
      );

      expect(screen.getByTestId('card')).toHaveAttribute('data-slot', 'card');
      expect(screen.getByTestId('header')).toHaveAttribute(
        'data-slot',
        'card-header'
      );
      expect(screen.getByTestId('title')).toHaveAttribute(
        'data-slot',
        'card-title'
      );
      expect(screen.getByTestId('description')).toHaveAttribute(
        'data-slot',
        'card-description'
      );
      expect(screen.getByTestId('action')).toHaveAttribute(
        'data-slot',
        'card-action'
      );
      expect(screen.getByTestId('content')).toHaveAttribute(
        'data-slot',
        'card-content'
      );
      expect(screen.getByTestId('footer')).toHaveAttribute(
        'data-slot',
        'card-footer'
      );
    });
  });
});
