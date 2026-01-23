import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { userEvent } from '@testing-library/user-event';
import { FilterControls } from './FilterControls';
import type { ModFilters } from '@/api/types';

// VSS-y7u: Tags now come from API via useModTags, not extracted from mods
const mockTags = ['qol', 'utility'];

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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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
        availableTags={mockTags}
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

  it('deselects tag when clicking on already selected tag', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={{ tags: ['qol', 'utility'] }}
        onChange={mockOnChange}
        availableTags={mockTags}
      />
    );

    const tagsButton = screen.getByRole('button', { name: /tags/i });
    await user.click(tagsButton);

    // Click on already selected tag to deselect it
    const qolOption = screen.getByRole('menuitemcheckbox', { name: /qol/i });
    await user.click(qolOption);

    // Should remove 'qol' from tags
    expect(mockOnChange).toHaveBeenCalledWith({ tags: ['utility'] });
  });

  // VSS-y7u: New tests for loading/error states
  it('shows loading state when tags are loading', () => {
    render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableTags={[]}
        tagsLoading={true}
      />
    );

    const tagsButton = screen.getByTestId('tags-filter-button');
    expect(tagsButton).toBeDisabled();
    expect(tagsButton).toHaveTextContent('Loading...');
  });

  it('shows error message when tags fail to load', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={defaultFilters}
        onChange={mockOnChange}
        availableTags={[]}
        tagsError={true}
      />
    );

    const tagsButton = screen.getByTestId('tags-filter-button');
    await user.click(tagsButton);

    expect(screen.getByText('Failed to load tags')).toBeInTheDocument();
  });
});

// VSS-1u2: Installed version tests
describe('installed version', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('shows installed version first in dropdown with label', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={{}}
        onChange={mockOnChange}
        gameVersions={['1.21.2', '1.21.1', '1.21.3']}
        installedVersion="1.21.3"
      />
    );

    const versionButton = screen.getByTestId('version-filter-button');
    await user.click(versionButton);

    // Should show installed version with "(Installed)" label
    expect(screen.getByText('(Installed)')).toBeInTheDocument();

    // First option should be the installed version
    const menuItems = screen.getAllByRole('menuitem');
    expect(menuItems[0]).toHaveTextContent('1.21.3');
    expect(menuItems[0]).toHaveTextContent('(Installed)');
  });

  it('does not show (Installed) label when no installed version', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={{}}
        onChange={mockOnChange}
        gameVersions={['1.21.3', '1.21.2', '1.21.1']}
        installedVersion={null}
      />
    );

    const versionButton = screen.getByTestId('version-filter-button');
    await user.click(versionButton);

    expect(screen.queryByText('(Installed)')).not.toBeInTheDocument();
  });

  it('calls onChange when version is selected', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={{}}
        onChange={mockOnChange}
        gameVersions={['1.21.3', '1.21.2', '1.21.1']}
      />
    );

    const versionButton = screen.getByTestId('version-filter-button');
    await user.click(versionButton);

    const versionOption = screen.getByTestId('version-option-1.21.2');
    await user.click(versionOption);

    expect(mockOnChange).toHaveBeenCalledWith(
      expect.objectContaining({ gameVersion: '1.21.2' })
    );
  });

  it('removes game version filter when badge close button is clicked', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={{ gameVersion: '1.21.3' }}
        onChange={mockOnChange}
        gameVersions={['1.21.3', '1.21.2', '1.21.1']}
      />
    );

    const removeButton = screen.getByRole('button', {
      name: /remove.*version.*1\.21\.3/i,
    });
    await user.click(removeButton);

    expect(mockOnChange).toHaveBeenCalledWith({});
  });
});

describe('mod type filter', () => {
  const mockOnChange = vi.fn();

  beforeEach(() => {
    mockOnChange.mockClear();
  });

  it('removes mod type filter when badge close button is clicked', async () => {
    const user = userEvent.setup();

    render(
      <FilterControls
        filters={{ modType: 'mod' }}
        onChange={mockOnChange}
      />
    );

    const removeButton = screen.getByRole('button', {
      name: /remove.*type.*filter:.*mod/i,
    });
    await user.click(removeButton);

    expect(mockOnChange).toHaveBeenCalledWith({});
  });
});
