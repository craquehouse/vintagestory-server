import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { FilterControls } from './FilterControls';
import type { ModFilters, ModBrowseItem } from '@/api/types';

// Mock mods data for extracting tags
const mockMods: ModBrowseItem[] = [
  {
    slug: 'test-mod',
    name: 'Test Mod',
    author: 'test',
    summary: 'test',
    downloads: 100,
    follows: 10,
    trendingPoints: 5,
    side: 'both',
    modType: 'mod',
    logoUrl: null,
    tags: ['qol', 'utility'],
    lastReleased: '2024-01-01T00:00:00Z',
  },
];

describe('FilterControls', () => {
  const mockOnChange = vi.fn();
  const defaultFilters: ModFilters = {};

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders all filter options', () => {
    render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    // Check for filter labels/buttons
    expect(screen.getByText(/side/i)).toBeInTheDocument();
    expect(screen.getByText(/tags/i)).toBeInTheDocument();
    expect(screen.getByText(/type/i)).toBeInTheDocument();
    // Version filter disabled - API doesn't provide compatibility data
    expect(screen.queryByText(/version/i)).not.toBeInTheDocument();
  });

  it('displays active filter badges when filters are set', () => {
    const filters: ModFilters = {
      side: 'server',
      tags: ['qol', 'utility'],
    };

    render(
      <FilterControls
        filters={filters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    // Check for badge display
    expect(screen.getByText('server')).toBeInTheDocument();
    expect(screen.getByText('qol')).toBeInTheDocument();
    expect(screen.getByText('utility')).toBeInTheDocument();
  });

  it('calls onChange when side filter is selected', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    // Interact with side filter (implementation will determine exact interaction)
    const sideButton = screen.getByRole('button', { name: /side/i });
    await user.click(sideButton);

    // Select "Server" option
    const serverOption = screen.getByRole('menuitem', { name: /server/i });
    await user.click(serverOption);

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ side: 'server' })
    );
  });

  it('calls onChange when tag filter is selected', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    const tagsButton = screen.getByRole('button', { name: /tags/i });
    await user.click(tagsButton);

    const qolOption = screen.getByRole('menuitemcheckbox', { name: /qol/i });
    await user.click(qolOption);

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ tags: ['qol'] })
    );
  });

  it('removes filter when badge close button is clicked', async () => {
    const user = userEvent.setup();
    const filters: ModFilters = {
      side: 'server',
    };

    render(
      <FilterControls
        filters={filters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    const removeButton = screen.getByRole('button', { name: /remove.*server/i });
    await user.click(removeButton);

    expect(mockOnChange).toHaveBeenCalledWith({});
  });

  it('removes individual tag when tag badge is clicked', async () => {
    const user = userEvent.setup();
    const filters: ModFilters = {
      tags: ['qol', 'utility'],
    };

    render(
      <FilterControls
        filters={filters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    const removeQolButton = screen.getByRole('button', { name: /remove.*qol/i });
    await user.click(removeQolButton);

    expect(mockOnChange).toHaveBeenCalledWith({
      tags: ['utility'],
    });
  });

  it('shows no active badges when no filters are set', () => {
    render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    // Should not show any badge close buttons
    expect(screen.queryByRole('button', { name: /remove/i })).not.toBeInTheDocument();
  });

  it.skip('handles version filter selection - DISABLED (requires API enhancement)', async () => {
    // Game version filter disabled until API provides compatibility data
  });

  it('handles mod type filter selection', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    const typeButton = screen.getByRole('button', { name: /type/i });
    await user.click(typeButton);

    const codeModOption = screen.getByRole('menuitem', { name: /code.*mod/i });
    await user.click(codeModOption);

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ modType: 'mod' })
    );
  });

  it('supports multiple tags selection', async () => {
    const user = userEvent.setup();

    const { rerender } = render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    const tagsButton = screen.getByRole('button', { name: /tags/i });
    await user.click(tagsButton);

    // Select first tag
    const qolOption = screen.getByRole('menuitemcheckbox', { name: /qol/i });
    await user.click(qolOption);

    expect(mockOnChange).toHaveBeenCalledWith({ tags: ['qol'] });

    // Simulate parent component updating filters
    rerender(
      <FilterControls
        filters={{ tags: ['qol'] }}
        onChange={mockOnChange}
        availableMods={mockMods}
      />
    );

    // Reopen dropdown for second tag
    await user.click(tagsButton);

    // Select second tag
    const utilityOption = screen.getByRole('menuitemcheckbox', { name: /utility/i });
    await user.click(utilityOption);

    // Should add to existing tags
    expect(mockOnChange).toHaveBeenLastCalledWith({ tags: ['qol', 'utility'] });
  });
});
