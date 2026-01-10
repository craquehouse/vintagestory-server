/**
 * Pagination component for navigating through paged results.
 *
 * Features:
 * - Previous/Next buttons with disabled states at boundaries
 * - Page number buttons with ellipsis for large page counts
 * - Current page highlighting
 * - Loading state support
 * - Hidden when only one page exists
 *
 * Story 10.7: Pagination for browse tab results.
 */

import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PaginationProps {
  /** Current page number (1-indexed) */
  currentPage: number;
  /** Total number of pages */
  totalPages: number;
  /** Total number of items (optional, for display) */
  totalItems?: number;
  /** Whether pagination is in loading state */
  isLoading?: boolean;
  /** Callback when page changes */
  onPageChange: (page: number) => void;
}

/**
 * Generate array of page numbers to display with ellipsis.
 *
 * Strategy:
 * - Always show first and last page
 * - Show current page and one neighbor on each side
 * - Use ellipsis ("…") for gaps
 *
 * Example for currentPage=10, totalPages=20:
 * [1, "…", 9, 10, 11, "…", 20]
 */
function getPageNumbers(
  currentPage: number,
  totalPages: number
): (number | '…')[] {
  // If 7 or fewer pages, show all
  if (totalPages <= 7) {
    return Array.from({ length: totalPages }, (_, i) => i + 1);
  }

  const pages: (number | '…')[] = [];

  // Always include first page
  pages.push(1);

  // Calculate range around current page
  const rangeStart = Math.max(2, currentPage - 1);
  const rangeEnd = Math.min(totalPages - 1, currentPage + 1);

  // Add ellipsis if gap after first page
  if (rangeStart > 2) {
    pages.push('…');
  }

  // Add pages in range
  for (let i = rangeStart; i <= rangeEnd; i++) {
    pages.push(i);
  }

  // Add ellipsis if gap before last page
  if (rangeEnd < totalPages - 1) {
    pages.push('…');
  }

  // Always include last page
  if (totalPages > 1) {
    pages.push(totalPages);
  }

  return pages;
}

/**
 * Pagination controls component.
 *
 * Renders previous/next buttons, page numbers with ellipsis,
 * and optional total items count.
 *
 * @example
 * <Pagination
 *   currentPage={pagination.page}
 *   totalPages={pagination.totalPages}
 *   totalItems={pagination.totalItems}
 *   onPageChange={(page) => setPage(page)}
 *   isLoading={isFetching}
 * />
 */
export function Pagination({
  currentPage,
  totalPages,
  totalItems,
  isLoading = false,
  onPageChange,
}: PaginationProps) {
  // Don't render pagination for single page
  if (totalPages <= 1) {
    return null;
  }

  const isFirstPage = currentPage <= 1;
  const isLastPage = currentPage >= totalPages;

  const handlePrevious = () => {
    if (!isFirstPage && !isLoading) {
      onPageChange(currentPage - 1);
    }
  };

  const handleNext = () => {
    if (!isLastPage && !isLoading) {
      onPageChange(currentPage + 1);
    }
  };

  const handlePageClick = (page: number) => {
    if (page !== currentPage && !isLoading) {
      onPageChange(page);
    }
  };

  const pageNumbers = getPageNumbers(currentPage, totalPages);

  return (
    <div
      className="flex flex-col items-center gap-2 sm:flex-row sm:justify-between"
      data-testid="pagination"
    >
      {/* Page info text */}
      <p className="text-sm text-muted-foreground order-2 sm:order-1">
        Page {currentPage} of {totalPages}
        {totalItems !== undefined && ` (${totalItems} mods total)`}
      </p>

      {/* Navigation controls */}
      <div className="flex items-center gap-1 order-1 sm:order-2">
        {/* Previous button */}
        <Button
          variant="outline"
          size="sm"
          onClick={handlePrevious}
          disabled={isFirstPage || isLoading}
          aria-label="Go to previous page"
        >
          <ChevronLeft className="h-4 w-4" />
          <span className="sr-only sm:not-sr-only sm:ml-1">Previous</span>
        </Button>

        {/* Page numbers */}
        <div className="flex items-center gap-1">
          {pageNumbers.map((page, index) =>
            page === '…' ? (
              <span
                key={`ellipsis-${index}`}
                className="px-2 text-muted-foreground"
                aria-hidden="true"
              >
                …
              </span>
            ) : (
              <Button
                key={page}
                variant={page === currentPage ? 'default' : 'ghost'}
                size="sm"
                onClick={() => handlePageClick(page)}
                disabled={page === currentPage || isLoading}
                aria-label={`${page}`}
                aria-current={page === currentPage ? 'page' : undefined}
              >
                {page}
              </Button>
            )
          )}
        </div>

        {/* Next button */}
        <Button
          variant="outline"
          size="sm"
          onClick={handleNext}
          disabled={isLastPage || isLoading}
          aria-label="Go to next page"
        >
          <span className="sr-only sm:not-sr-only sm:mr-1">Next</span>
          <ChevronRight className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}
