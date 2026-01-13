/**
 * ChannelFilter Component Tests
 *
 * Story 13.3: Version List Page
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChannelFilter } from './ChannelFilter';

describe('ChannelFilter', () => {
  it('renders All, Stable, Unstable tabs', () => {
    const handleChange = vi.fn();
    render(<ChannelFilter value={undefined} onChange={handleChange} />);

    expect(screen.getByTestId('channel-filter')).toBeInTheDocument();
    expect(screen.getByTestId('channel-filter-all')).toHaveTextContent('All');
    expect(screen.getByTestId('channel-filter-stable')).toHaveTextContent('Stable');
    expect(screen.getByTestId('channel-filter-unstable')).toHaveTextContent('Unstable');
  });

  it('calls onChange with undefined when All tab is clicked', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<ChannelFilter value="stable" onChange={handleChange} />);

    await user.click(screen.getByTestId('channel-filter-all'));
    expect(handleChange).toHaveBeenCalledWith(undefined);
  });

  it('calls onChange with "stable" when Stable tab is clicked', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<ChannelFilter value={undefined} onChange={handleChange} />);

    await user.click(screen.getByTestId('channel-filter-stable'));
    expect(handleChange).toHaveBeenCalledWith('stable');
  });

  it('calls onChange with "unstable" when Unstable tab is clicked', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();
    render(<ChannelFilter value={undefined} onChange={handleChange} />);

    await user.click(screen.getByTestId('channel-filter-unstable'));
    expect(handleChange).toHaveBeenCalledWith('unstable');
  });

  it('highlights All tab when value is undefined', () => {
    const handleChange = vi.fn();
    render(<ChannelFilter value={undefined} onChange={handleChange} />);

    const allTab = screen.getByTestId('channel-filter-all');
    expect(allTab).toHaveAttribute('data-state', 'active');
  });

  it('highlights Stable tab when value is "stable"', () => {
    const handleChange = vi.fn();
    render(<ChannelFilter value="stable" onChange={handleChange} />);

    const stableTab = screen.getByTestId('channel-filter-stable');
    expect(stableTab).toHaveAttribute('data-state', 'active');
  });

  it('highlights Unstable tab when value is "unstable"', () => {
    const handleChange = vi.fn();
    render(<ChannelFilter value="unstable" onChange={handleChange} />);

    const unstableTab = screen.getByTestId('channel-filter-unstable');
    expect(unstableTab).toHaveAttribute('data-state', 'active');
  });

  it('does not highlight inactive tabs', () => {
    const handleChange = vi.fn();
    render(<ChannelFilter value="stable" onChange={handleChange} />);

    const allTab = screen.getByTestId('channel-filter-all');
    const unstableTab = screen.getByTestId('channel-filter-unstable');

    expect(allTab).toHaveAttribute('data-state', 'inactive');
    expect(unstableTab).toHaveAttribute('data-state', 'inactive');
  });
});
