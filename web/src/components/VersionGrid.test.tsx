/**
 * VersionGrid Component Tests
 *
 * Story 13.3: Version List Page
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VersionGrid } from './VersionGrid';
import type { VersionInfo } from '@/api/types';

// Test fixtures
const mockVersions: VersionInfo[] = [
  {
    version: '1.20.0',
    filename: 'vs_server_linux-x64_1.20.0.tar.gz',
    filesize: '45.2 MB',
    md5: 'abc123',
    cdnUrl: 'https://cdn.example.com/1.20.0',
    localUrl: '/local/1.20.0',
    isLatest: true,
    channel: 'stable',
  },
  {
    version: '1.19.8',
    filename: 'vs_server_linux-x64_1.19.8.tar.gz',
    filesize: '40.1 MB',
    md5: 'def456',
    cdnUrl: 'https://cdn.example.com/1.19.8',
    localUrl: '/local/1.19.8',
    isLatest: false,
    channel: 'stable',
  },
  {
    version: '1.20.1-rc.1',
    filename: 'vs_server_linux-x64_1.20.1-rc.1.tar.gz',
    filesize: '46.3 MB',
    md5: 'ghi789',
    cdnUrl: 'https://cdn.example.com/1.20.1-rc.1',
    localUrl: '/local/1.20.1-rc.1',
    isLatest: true,
    channel: 'unstable',
  },
];

describe('VersionGrid', () => {
  it('renders version cards in grid', () => {
    render(<VersionGrid versions={mockVersions} />);

    const grid = screen.getByTestId('version-grid');
    expect(grid).toBeInTheDocument();

    // Check that all versions are rendered
    expect(screen.getByTestId('version-card-1.20.0')).toBeInTheDocument();
    expect(screen.getByTestId('version-card-1.19.8')).toBeInTheDocument();
    expect(screen.getByTestId('version-card-1.20.1-rc.1')).toBeInTheDocument();
  });

  it('shows loading skeleton when loading', () => {
    render(<VersionGrid versions={[]} isLoading={true} />);

    const loadingGrid = screen.getByTestId('version-grid-loading');
    expect(loadingGrid).toBeInTheDocument();

    // Should show skeleton cards
    const skeletons = screen.getAllByTestId('version-card-skeleton');
    expect(skeletons).toHaveLength(8); // SKELETON_COUNT
  });

  it('shows empty state when no versions', () => {
    render(<VersionGrid versions={[]} isLoading={false} />);

    const emptyState = screen.getByTestId('version-grid-empty');
    expect(emptyState).toBeInTheDocument();
    expect(emptyState).toHaveTextContent('No versions found for this channel.');
  });

  it('passes installedVersion to VersionCards', () => {
    render(
      <VersionGrid
        versions={mockVersions}
        installedVersion="1.19.8"
      />
    );

    // The installed version card should show the "Installed" indicator
    const installedCard = screen.getByTestId('version-card-1.19.8');
    expect(installedCard).toBeInTheDocument();

    // Check that the installed indicator is shown (rendered by VersionCard)
    expect(screen.getByTestId('version-card-installed-1.19.8')).toBeInTheDocument();

    // Other versions should not show installed indicator
    expect(screen.queryByTestId('version-card-installed-1.20.0')).not.toBeInTheDocument();
  });

  it('calls onVersionClick when card is clicked', async () => {
    const user = userEvent.setup();
    const handleClick = vi.fn();

    render(
      <VersionGrid
        versions={mockVersions}
        onVersionClick={handleClick}
      />
    );

    const card = screen.getByTestId('version-card-1.20.0');
    await user.click(card);

    expect(handleClick).toHaveBeenCalledTimes(1);
    expect(handleClick).toHaveBeenCalledWith('1.20.0');
  });

  it('does not call onClick when no handler provided', async () => {
    const user = userEvent.setup();

    render(<VersionGrid versions={mockVersions} />);

    // Just verify clicking doesn't cause errors
    const card = screen.getByTestId('version-card-1.20.0');
    await user.click(card);

    // No error should occur
  });

  it('applies responsive grid classes', () => {
    render(<VersionGrid versions={mockVersions} />);

    const grid = screen.getByTestId('version-grid');
    expect(grid).toHaveClass('grid');
    expect(grid).toHaveClass('grid-cols-1');
    expect(grid).toHaveClass('sm:grid-cols-2');
    expect(grid).toHaveClass('lg:grid-cols-3');
    expect(grid).toHaveClass('xl:grid-cols-4');
    expect(grid).toHaveClass('gap-4');
  });

  it('renders cards with correct version data', () => {
    render(<VersionGrid versions={mockVersions} />);

    // Check first version card content
    expect(screen.getByTestId('version-card-version-1.20.0')).toHaveTextContent('1.20.0');
    expect(screen.getByTestId('version-card-filesize-1.20.0')).toHaveTextContent('45.2 MB');
    expect(screen.getByTestId('version-card-channel-1.20.0')).toHaveTextContent('Stable');
    expect(screen.getByTestId('version-card-latest-1.20.0')).toBeInTheDocument();
  });

  it('handles null installedVersion gracefully', () => {
    render(
      <VersionGrid
        versions={mockVersions}
        installedVersion={null}
      />
    );

    // No installed indicators should be shown
    expect(screen.queryByTestId('version-card-installed-1.20.0')).not.toBeInTheDocument();
    expect(screen.queryByTestId('version-card-installed-1.19.8')).not.toBeInTheDocument();
    expect(screen.queryByTestId('version-card-installed-1.20.1-rc.1')).not.toBeInTheDocument();
  });

  it('handles undefined installedVersion gracefully', () => {
    render(<VersionGrid versions={mockVersions} />);

    // No installed indicators should be shown
    expect(screen.queryByTestId('version-card-installed-1.20.0')).not.toBeInTheDocument();
  });
});
