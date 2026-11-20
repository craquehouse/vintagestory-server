import { describe, it, expect, vi, beforeAll } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { InstalledModsFilterBar } from './InstalledModsFilterBar';
import { EMPTY_FILTERS, type InstalledModsFilters } from '@/lib/installed-mods-filters';

function renderBar(value: InstalledModsFilters = EMPTY_FILTERS) {
  const handlers = {
    onQueryChange: vi.fn(),
    onCompatChange: vi.fn(),
    onUpdatesChange: vi.fn(),
  };
  render(<InstalledModsFilterBar value={value} {...handlers} />);
  return handlers;
}

describe('InstalledModsFilterBar (Story 24.7)', () => {
  beforeAll(() => {
    // Radix Select needs these in jsdom
    Element.prototype.hasPointerCapture ??= () => false;
    Element.prototype.releasePointerCapture ??= () => {};
    Element.prototype.scrollIntoView ??= () => {};
  });

  it('reports each keystroke in the search box', () => {
    const { onQueryChange } = renderBar();

    fireEvent.change(screen.getByRole('searchbox', { name: /by name or mod ID/ }), {
      target: { value: 'carry' },
    });

    expect(onQueryChange).toHaveBeenCalledWith('carry');
  });

  it('clears the name filter with its button', () => {
    const { onQueryChange } = renderBar({ ...EMPTY_FILTERS, query: 'carry' });

    fireEvent.click(screen.getByRole('button', { name: 'Clear the name filter' }));

    expect(onQueryChange).toHaveBeenCalledWith('');
  });

  it('has no clear button without a name filter', () => {
    renderBar();

    expect(screen.queryByTestId('installed-mods-filter-query-clear')).not.toBeInTheDocument();
  });

  it('chooses a compatibility status', async () => {
    const user = userEvent.setup();
    const { onCompatChange } = renderBar();

    await user.click(screen.getByRole('combobox', { name: 'Compatibility' }));
    await user.click(await screen.findByTestId('installed-mods-filter-compat-incompatible'));
    expect(onCompatChange).toHaveBeenLastCalledWith('incompatible');
  });

  it('chooses All to clear the compatibility filter', async () => {
    const user = userEvent.setup();
    const { onCompatChange } = renderBar({ ...EMPTY_FILTERS, compat: 'compatible' });

    expect(screen.getByRole('combobox', { name: 'Compatibility' })).toHaveTextContent('Compatible');
    await user.click(screen.getByRole('combobox', { name: 'Compatibility' }));
    await user.click(await screen.findByTestId('installed-mods-filter-compat-all'));
    expect(onCompatChange).toHaveBeenLastCalledWith(null);
  });

  it('toggles "Update available" from its label', () => {
    const { onUpdatesChange } = renderBar();

    fireEvent.click(screen.getByText('Update available'));

    expect(onUpdatesChange).toHaveBeenCalledWith(true);
    expect(screen.getByRole('switch', { name: 'Update available' })).toBeInTheDocument();
  });

  it('gives the controls 44px targets on phones', () => {
    renderBar({ ...EMPTY_FILTERS, query: 'x' });

    expect(screen.getByTestId('installed-mods-filter-query')).toHaveClass('max-lg:h-11');
    expect(screen.getByTestId('installed-mods-filter-compat')).toHaveClass('max-lg:min-h-11');
    expect(screen.getByText('Update available')).toHaveClass('max-lg:min-h-11');
  });
});
