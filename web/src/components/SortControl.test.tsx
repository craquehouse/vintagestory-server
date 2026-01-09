import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { SortControl } from './SortControl';
import type { BrowseSortOption } from '@/api/types';

describe('SortControl', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with default sort value', () => {
    render(<SortControl value="recent" onChange={mockOnChange} />);

    expect(screen.getByText('Sort by:')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /newest/i })).toBeInTheDocument();
  });

  it('displays current sort option label', () => {
    render(<SortControl value="downloads" onChange={mockOnChange} />);

    expect(screen.getByRole('button', { name: /most downloaded/i })).toBeInTheDocument();
  });

  it('shows all sort options when opened', async () => {
    const user = userEvent.setup();

    render(<SortControl value="recent" onChange={mockOnChange} />);

    const sortButton = screen.getByRole('button');
    await user.click(sortButton);

    expect(screen.getByRole('menuitem', { name: /newest/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /most downloaded/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /trending/i })).toBeInTheDocument();
    expect(screen.getByRole('menuitem', { name: /name.*a-z/i })).toBeInTheDocument();
  });

  it('calls onChange when a sort option is selected', async () => {
    const user = userEvent.setup();

    render(<SortControl value="recent" onChange={mockOnChange} />);

    const sortButton = screen.getByRole('button');
    await user.click(sortButton);

    const downloadsOption = screen.getByRole('menuitem', { name: /most downloaded/i });
    await user.click(downloadsOption);

    expect(mockOnChange).toHaveBeenCalledWith('downloads');
  });

  it('handles switching between different sort options', async () => {
    const user = userEvent.setup();

    const { rerender } = render(
      <SortControl value="recent" onChange={mockOnChange} />
    );

    // Select downloads
    const sortButton = screen.getByRole('button');
    await user.click(sortButton);
    await user.click(screen.getByRole('menuitem', { name: /most downloaded/i }));

    expect(mockOnChange).toHaveBeenCalledWith('downloads');

    // Simulate parent updating value
    rerender(<SortControl value="downloads" onChange={mockOnChange} />);

    // Verify new value is displayed
    expect(screen.getByRole('button', { name: /most downloaded/i })).toBeInTheDocument();
  });

  it('supports all sort options', async () => {
    const user = userEvent.setup();
    const sortOptions: Array<{ value: BrowseSortOption; label: RegExp }> = [
      { value: 'recent', label: /newest/i },
      { value: 'downloads', label: /most downloaded/i },
      { value: 'trending', label: /trending/i },
    ];

    for (const { value, label } of sortOptions) {
      const { rerender, unmount } = render(
        <SortControl value={value} onChange={mockOnChange} />
      );

      const sortButton = screen.getByRole('button');
      expect(sortButton).toHaveTextContent(label);

      unmount();
    }
  });

  it('defaults to "Newest" when value is "recent"', () => {
    render(<SortControl value="recent" onChange={mockOnChange} />);

    expect(screen.getByRole('button', { name: /newest/i })).toBeInTheDocument();
  });
});
