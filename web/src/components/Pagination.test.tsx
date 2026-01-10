/**
 * Tests for Pagination component.
 *
 * Story 10.7: Pagination controls for browse tab.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Pagination } from './Pagination';

describe('Pagination', () => {
  describe('rendering', () => {
    it('renders current page and total pages', () => {
      render(
        <Pagination
          currentPage={3}
          totalPages={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByText(/Page 3 of 10/)).toBeInTheDocument();
    });

    it('renders previous and next buttons', () => {
      render(
        <Pagination
          currentPage={3}
          totalPages={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByRole('button', { name: /previous/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /next/i })).toBeInTheDocument();
    });

    it('renders page number buttons', () => {
      render(
        <Pagination
          currentPage={1}
          totalPages={5}
          onPageChange={() => {}}
        />
      );

      // Should show page numbers 1-5
      expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '2' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '3' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '4' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '5' })).toBeInTheDocument();
    });

    it('highlights current page button', () => {
      render(
        <Pagination
          currentPage={3}
          totalPages={5}
          onPageChange={() => {}}
        />
      );

      const currentPageButton = screen.getByRole('button', { name: '3' });
      // Current page should have different styling (data-variant="default" for primary)
      expect(currentPageButton).toHaveAttribute('data-variant', 'default');

      // Other pages should be ghost variant
      const otherPageButton = screen.getByRole('button', { name: '2' });
      expect(otherPageButton).toHaveAttribute('data-variant', 'ghost');
    });
  });

  describe('disabled states', () => {
    it('disables previous button on first page', () => {
      render(
        <Pagination
          currentPage={1}
          totalPages={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByRole('button', { name: /previous/i })).toBeDisabled();
    });

    it('disables next button on last page', () => {
      render(
        <Pagination
          currentPage={10}
          totalPages={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
    });

    it('enables both buttons when in middle of pages', () => {
      render(
        <Pagination
          currentPage={5}
          totalPages={10}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByRole('button', { name: /previous/i })).not.toBeDisabled();
      expect(screen.getByRole('button', { name: /next/i })).not.toBeDisabled();
    });
  });

  describe('single page', () => {
    it('does not render pagination for single page', () => {
      const { container } = render(
        <Pagination
          currentPage={1}
          totalPages={1}
          onPageChange={() => {}}
        />
      );

      // Should render nothing when there's only one page
      expect(container.firstChild).toBeNull();
    });
  });

  describe('interactions', () => {
    it('calls onPageChange when clicking previous button', async () => {
      const user = userEvent.setup();
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={5}
          totalPages={10}
          onPageChange={onPageChange}
        />
      );

      await user.click(screen.getByRole('button', { name: /previous/i }));

      expect(onPageChange).toHaveBeenCalledWith(4);
    });

    it('calls onPageChange when clicking next button', async () => {
      const user = userEvent.setup();
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={5}
          totalPages={10}
          onPageChange={onPageChange}
        />
      );

      await user.click(screen.getByRole('button', { name: /next/i }));

      expect(onPageChange).toHaveBeenCalledWith(6);
    });

    it('calls onPageChange when clicking a page number', async () => {
      const user = userEvent.setup();
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={1}
          totalPages={5}
          onPageChange={onPageChange}
        />
      );

      await user.click(screen.getByRole('button', { name: '3' }));

      expect(onPageChange).toHaveBeenCalledWith(3);
    });

    it('does not call onPageChange when clicking current page', async () => {
      const user = userEvent.setup();
      const onPageChange = vi.fn();

      render(
        <Pagination
          currentPage={3}
          totalPages={5}
          onPageChange={onPageChange}
        />
      );

      await user.click(screen.getByRole('button', { name: '3' }));

      expect(onPageChange).not.toHaveBeenCalled();
    });
  });

  describe('ellipsis for many pages', () => {
    it('shows ellipsis when there are many pages', () => {
      render(
        <Pagination
          currentPage={10}
          totalPages={20}
          onPageChange={() => {}}
        />
      );

      // Should show ellipsis (typically represented as "...")
      expect(screen.getAllByText('…').length).toBeGreaterThan(0);
    });

    it('shows first and last page numbers with ellipsis', () => {
      render(
        <Pagination
          currentPage={10}
          totalPages={20}
          onPageChange={() => {}}
        />
      );

      // First page should always be visible
      expect(screen.getByRole('button', { name: '1' })).toBeInTheDocument();

      // Last page should always be visible
      expect(screen.getByRole('button', { name: '20' })).toBeInTheDocument();

      // Current page should be visible
      expect(screen.getByRole('button', { name: '10' })).toBeInTheDocument();
    });

    it('shows pages around current page', () => {
      render(
        <Pagination
          currentPage={10}
          totalPages={20}
          onPageChange={() => {}}
        />
      );

      // Should show pages around current (9, 10, 11)
      expect(screen.getByRole('button', { name: '9' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '10' })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: '11' })).toBeInTheDocument();
    });
  });

  describe('loading state', () => {
    it('shows loading state when isLoading is true', () => {
      render(
        <Pagination
          currentPage={1}
          totalPages={10}
          onPageChange={() => {}}
          isLoading={true}
        />
      );

      // Buttons should be disabled during loading
      expect(screen.getByRole('button', { name: /next/i })).toBeDisabled();
    });

    it('disables all page buttons during loading', () => {
      render(
        <Pagination
          currentPage={5}
          totalPages={10}
          onPageChange={() => {}}
          isLoading={true}
        />
      );

      // All numbered buttons should be disabled (page 4 is adjacent to current page 5)
      const pageButton = screen.getByRole('button', { name: '4' });
      expect(pageButton).toBeDisabled();
    });
  });

  describe('total items display', () => {
    it('shows total items when provided', () => {
      render(
        <Pagination
          currentPage={1}
          totalPages={10}
          totalItems={541}
          onPageChange={() => {}}
        />
      );

      expect(screen.getByText(/541/)).toBeInTheDocument();
    });
  });
});
