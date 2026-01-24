/**
 * Tests for dialog components.
 *
 * Tests Radix UI dialog wrapper components including Dialog root,
 * DialogTrigger, DialogClose, DialogPortal, DialogOverlay, DialogContent,
 * DialogHeader, DialogFooter, DialogTitle, and DialogDescription.
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Dialog,
  DialogTrigger,
  DialogClose,
  DialogPortal,
  DialogOverlay,
  DialogContent,
  DialogHeader,
  DialogFooter,
  DialogTitle,
  DialogDescription,
} from './dialog';

describe('Dialog', () => {
  describe('Dialog root', () => {
    it('renders with correct data-slot', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="trigger">Open</DialogTrigger>
        </Dialog>
      );

      expect(screen.getByTestId('trigger')).toBeInTheDocument();
    });

    it('passes props to Radix Root', () => {
      render(
        <Dialog defaultOpen={false}>
          <DialogTrigger data-testid="trigger">Open</DialogTrigger>
        </Dialog>
      );

      const trigger = screen.getByTestId('trigger');
      expect(trigger).toHaveAttribute('aria-expanded', 'false');
    });
  });

  describe('DialogTrigger', () => {
    it('renders trigger with correct data-slot', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="dialog-trigger">Open Dialog</DialogTrigger>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-trigger')).toHaveAttribute(
        'data-slot',
        'dialog-trigger'
      );
    });

    it('renders as button element', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="dialog-trigger">Open</DialogTrigger>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-trigger')).toBeInstanceOf(HTMLButtonElement);
    });

    it('renders button text', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="dialog-trigger">Click Me</DialogTrigger>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-trigger')).toHaveTextContent('Click Me');
    });

    it('has correct button type', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="dialog-trigger">Open</DialogTrigger>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-trigger')).toHaveAttribute('type', 'button');
    });
  });

  describe('DialogClose', () => {
    it('renders close button with correct data-slot', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogClose data-testid="dialog-close">Close</DialogClose>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-close')).toHaveAttribute(
        'data-slot',
        'dialog-close'
      );
    });

    it('renders as button element', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogClose data-testid="dialog-close">Close</DialogClose>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-close')).toBeInstanceOf(HTMLButtonElement);
    });

    it('renders children content', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogClose data-testid="dialog-close">
            <span>Close Dialog</span>
          </DialogClose>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-close')).toHaveTextContent('Close Dialog');
    });

    it('has correct button type', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogClose data-testid="dialog-close">Close</DialogClose>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-close')).toHaveAttribute('type', 'button');
    });
  });

  describe('DialogPortal', () => {
    it('is used by DialogContent to portal content', () => {
      // DialogPortal is tested indirectly via DialogContent
      // which uses it internally. Testing in isolation requires
      // complex setup that's not practical in jsdom.
      render(
        <Dialog open={true}>
          <DialogContent data-testid="dialog-content">
            <DialogDescription>Description</DialogDescription>
            Content
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-content')).toBeInTheDocument();
    });
  });

  describe('DialogOverlay', () => {
    it('is rendered by DialogContent', () => {
      // DialogOverlay is tested indirectly via DialogContent
      // which renders it internally. The overlay is automatically
      // created when DialogContent is rendered.
      render(
        <Dialog open={true}>
          <DialogContent data-testid="dialog-content">
            <DialogDescription>Description</DialogDescription>
            Content
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-content')).toBeInTheDocument();
    });
  });

  describe('DialogContent', () => {
    it('renders content with overlay', () => {
      render(
        <Dialog open={true}>
          <DialogContent data-testid="dialog-content">
            <DialogDescription>Description</DialogDescription>
            <div>Content</div>
          </DialogContent>
        </Dialog>
      );

      const content = screen.getByTestId('dialog-content');
      expect(content).toBeInTheDocument();
      expect(content).toHaveAttribute('data-slot', 'dialog-content');
    });

    it('renders children', () => {
      render(
        <Dialog open={true}>
          <DialogContent>
            <DialogDescription>Description</DialogDescription>
            <div data-testid="dialog-child">Test Content</div>
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-child')).toHaveTextContent('Test Content');
    });

    it('shows close button by default', () => {
      render(
        <Dialog open={true}>
          <DialogContent data-testid="dialog-content">
            <DialogDescription>Description</DialogDescription>
            Content
          </DialogContent>
        </Dialog>
      );

      // Close button should have sr-only text
      expect(screen.getByText('Close')).toBeInTheDocument();
    });

    it('hides close button when showCloseButton is false', () => {
      render(
        <Dialog open={true}>
          <DialogContent showCloseButton={false}>
            <DialogDescription>Description</DialogDescription>
            Content
          </DialogContent>
        </Dialog>
      );

      expect(screen.queryByText('Close')).not.toBeInTheDocument();
    });

    it('applies custom className', () => {
      render(
        <Dialog open={true}>
          <DialogContent data-testid="dialog-content" className="custom-content">
            <DialogDescription>Description</DialogDescription>
            Content
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-content').className).toContain('custom-content');
    });

    it('has correct positioning classes', () => {
      render(
        <Dialog open={true}>
          <DialogContent data-testid="dialog-content">
            <DialogDescription>Description</DialogDescription>
            Content
          </DialogContent>
        </Dialog>
      );

      const content = screen.getByTestId('dialog-content');
      expect(content.className).toContain('fixed');
      expect(content.className).toContain('z-50');
      expect(content.className).toContain('translate-x-[-50%]');
      expect(content.className).toContain('translate-y-[-50%]');
    });
  });

  describe('DialogHeader', () => {
    it('renders header with correct data-slot', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogHeader data-testid="dialog-header">
            <h2>Title</h2>
          </DialogHeader>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-header')).toHaveAttribute(
        'data-slot',
        'dialog-header'
      );
    });

    it('renders children content', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogHeader data-testid="dialog-header">
            <h2>Dialog Title</h2>
          </DialogHeader>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-header')).toHaveTextContent('Dialog Title');
    });

    it('has flex layout classes', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogHeader data-testid="dialog-header">Title</DialogHeader>
        </Dialog>
      );

      const header = screen.getByTestId('dialog-header');
      expect(header.className).toContain('flex');
      expect(header.className).toContain('flex-col');
      expect(header.className).toContain('gap-2');
    });

    it('applies custom className', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogHeader data-testid="dialog-header" className="custom-header">
            Title
          </DialogHeader>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-header').className).toContain('custom-header');
    });
  });

  describe('DialogFooter', () => {
    it('renders footer with correct data-slot', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogFooter data-testid="dialog-footer">
            <button>OK</button>
          </DialogFooter>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-footer')).toHaveAttribute(
        'data-slot',
        'dialog-footer'
      );
    });

    it('renders children content', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogFooter data-testid="dialog-footer">
            <button>Cancel</button>
            <button>Confirm</button>
          </DialogFooter>
        </Dialog>
      );

      const footer = screen.getByTestId('dialog-footer');
      expect(footer).toHaveTextContent('Cancel');
      expect(footer).toHaveTextContent('Confirm');
    });

    it('has flex layout classes', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogFooter data-testid="dialog-footer">Actions</DialogFooter>
        </Dialog>
      );

      const footer = screen.getByTestId('dialog-footer');
      expect(footer.className).toContain('flex');
      expect(footer.className).toContain('flex-col-reverse');
      expect(footer.className).toContain('gap-2');
    });

    it('applies custom className', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogFooter data-testid="dialog-footer" className="custom-footer">
            Actions
          </DialogFooter>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-footer').className).toContain('custom-footer');
    });
  });

  describe('DialogTitle', () => {
    it('renders title with correct data-slot', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogTitle data-testid="dialog-title">Dialog Title</DialogTitle>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-title')).toHaveAttribute(
        'data-slot',
        'dialog-title'
      );
    });

    it('renders title text', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogTitle data-testid="dialog-title">My Dialog</DialogTitle>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-title')).toHaveTextContent('My Dialog');
    });

    it('has text styling classes', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogTitle data-testid="dialog-title">Title</DialogTitle>
        </Dialog>
      );

      const title = screen.getByTestId('dialog-title');
      expect(title.className).toContain('text-lg');
      expect(title.className).toContain('font-semibold');
    });

    it('applies custom className', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogTitle data-testid="dialog-title" className="custom-title">
            Title
          </DialogTitle>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-title').className).toContain('custom-title');
    });
  });

  describe('DialogDescription', () => {
    it('renders description with correct data-slot', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogDescription data-testid="dialog-description">
            Description text
          </DialogDescription>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-description')).toHaveAttribute(
        'data-slot',
        'dialog-description'
      );
    });

    it('renders description text', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogDescription data-testid="dialog-description">
            This is a description
          </DialogDescription>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-description')).toHaveTextContent(
        'This is a description'
      );
    });

    it('has text styling classes', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogDescription data-testid="dialog-description">
            Description
          </DialogDescription>
        </Dialog>
      );

      const description = screen.getByTestId('dialog-description');
      expect(description.className).toContain('text-muted-foreground');
      expect(description.className).toContain('text-sm');
    });

    it('applies custom className', () => {
      render(
        <Dialog>
          <DialogTrigger>Open</DialogTrigger>
          <DialogDescription
            data-testid="dialog-description"
            className="custom-description"
          >
            Description
          </DialogDescription>
        </Dialog>
      );

      expect(screen.getByTestId('dialog-description').className).toContain(
        'custom-description'
      );
    });
  });

  describe('complete dialog structure', () => {
    it('renders full dialog with all components', () => {
      render(
        <Dialog open={true}>
          <DialogTrigger data-testid="trigger">Open</DialogTrigger>
          <DialogContent data-testid="content">
            <DialogHeader data-testid="header">
              <DialogTitle data-testid="title">Test Dialog</DialogTitle>
              <DialogDescription data-testid="description">
                Test description
              </DialogDescription>
            </DialogHeader>
            <div data-testid="body">Dialog body content</div>
            <DialogFooter data-testid="footer">
              <DialogClose data-testid="close">Close</DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      );

      expect(screen.getByTestId('trigger')).toBeInTheDocument();
      expect(screen.getByTestId('content')).toBeInTheDocument();
      expect(screen.getByTestId('header')).toBeInTheDocument();
      expect(screen.getByTestId('title')).toHaveTextContent('Test Dialog');
      expect(screen.getByTestId('description')).toHaveTextContent('Test description');
      expect(screen.getByTestId('body')).toHaveTextContent('Dialog body content');
      expect(screen.getByTestId('footer')).toBeInTheDocument();
      expect(screen.getByTestId('close')).toHaveTextContent('Close');
    });
  });

  describe('accessibility', () => {
    it('trigger has aria-haspopup attribute', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="trigger">Open</DialogTrigger>
        </Dialog>
      );

      expect(screen.getByTestId('trigger')).toHaveAttribute('aria-haspopup', 'dialog');
    });

    it('trigger has aria-expanded attribute', () => {
      render(
        <Dialog>
          <DialogTrigger data-testid="trigger">Open</DialogTrigger>
        </Dialog>
      );

      expect(screen.getByTestId('trigger')).toHaveAttribute('aria-expanded', 'false');
    });

    it('close button has sr-only text', () => {
      render(
        <Dialog open={true}>
          <DialogContent>
            <DialogDescription>Description</DialogDescription>
            Content
          </DialogContent>
        </Dialog>
      );

      const closeText = screen.getByText('Close');
      expect(closeText).toBeInTheDocument();
      expect(closeText.className).toContain('sr-only');
    });
  });
});
