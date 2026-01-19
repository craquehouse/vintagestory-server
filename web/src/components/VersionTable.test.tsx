/**
 * VersionTable Component Tests
 *
 * VSS-lvp [UI-033]: Table view for version list
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VersionTable } from './VersionTable';
import type { VersionInfo } from '@/api/types';

// Test fixtures - reuse same data structure as VersionGrid tests
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

describe('VersionTable', () => {
  it('renders table with version data', () => {
    render(<VersionTable versions={mockVersions} />);

    const table = screen.getByTestId('version-table');
    expect(table).toBeInTheDocument();

    // Check that all versions are rendered as rows
    expect(screen.getByTestId('version-table-row-1.20.0')).toBeInTheDocument();
    expect(screen.getByTestId('version-table-row-1.19.8')).toBeInTheDocument();
    expect(screen.getByTestId('version-table-row-1.20.1-rc.1')).toBeInTheDocument();
  });

  it('renders all columns with correct data', () => {
    render(<VersionTable versions={mockVersions} />);

    // Check version column
    expect(screen.getByTestId('version-table-version-1.20.0')).toHaveTextContent('1.20.0');

    // Check channel column
    expect(screen.getByTestId('version-table-channel-1.20.0')).toHaveTextContent('Stable');
    expect(screen.getByTestId('version-table-channel-1.20.1-rc.1')).toHaveTextContent('Unstable');

    // Check size column
    expect(screen.getByTestId('version-table-size-1.20.0')).toHaveTextContent('45.2 MB');

    // Check changelog link
    const changelogLink = screen.getByTestId('version-table-changelog-1.20.0');
    expect(changelogLink).toHaveAttribute('href', 'https://wiki.vintagestory.at/1.20.0');
    expect(changelogLink).toHaveAttribute('target', '_blank');
  });

  it('shows loading skeleton when loading', () => {
    render(<VersionTable versions={[]} isLoading={true} />);

    const loadingTable = screen.getByTestId('version-table-loading');
    expect(loadingTable).toBeInTheDocument();

    // Should show skeleton rows
    const skeletonRows = screen.getAllByTestId('version-table-skeleton-row');
    expect(skeletonRows).toHaveLength(8); // SKELETON_COUNT
  });

  it('shows empty state when no versions', () => {
    render(<VersionTable versions={[]} isLoading={false} />);

    const emptyState = screen.getByTestId('version-table-empty');
    expect(emptyState).toBeInTheDocument();
    expect(emptyState).toHaveTextContent('No versions found for this channel.');
  });

  it('shows Installed indicator for installed version', () => {
    render(
      <VersionTable
        versions={mockVersions}
        installedVersion="1.19.8"
      />
    );

    // The installed version row should show the "Installed" indicator
    expect(screen.getByTestId('version-table-installed-1.19.8')).toBeInTheDocument();

    // Other versions should not show installed indicator
    expect(screen.queryByTestId('version-table-installed-1.20.0')).not.toBeInTheDocument();
    expect(screen.queryByTestId('version-table-installed-1.20.1-rc.1')).not.toBeInTheDocument();
  });

  it('shows Latest badge for latest versions', () => {
    render(<VersionTable versions={mockVersions} />);

    // 1.20.0 and 1.20.1-rc.1 are marked as latest
    expect(screen.getByTestId('version-table-latest-1.20.0')).toBeInTheDocument();
    expect(screen.getByTestId('version-table-latest-1.20.1-rc.1')).toBeInTheDocument();

    // 1.19.8 is not latest
    expect(screen.queryByTestId('version-table-latest-1.19.8')).not.toBeInTheDocument();
  });

  it('calls onVersionSelect when Select button is clicked', async () => {
    const user = userEvent.setup();
    const handleSelect = vi.fn();

    render(
      <VersionTable
        versions={mockVersions}
        onVersionSelect={handleSelect}
      />
    );

    const selectButton = screen.getByTestId('version-table-select-1.20.0');
    await user.click(selectButton);

    expect(handleSelect).toHaveBeenCalledTimes(1);
    expect(handleSelect).toHaveBeenCalledWith('1.20.0');
  });

  it('disables Select button when no handler provided', () => {
    render(<VersionTable versions={mockVersions} />);

    const selectButton = screen.getByTestId('version-table-select-1.20.0');
    expect(selectButton).toBeDisabled();
  });

  describe('sorting', () => {
    it('has sortable column headers', () => {
      render(<VersionTable versions={mockVersions} />);

      // Version, Channel, and Size headers should be sortable (have cursor-pointer)
      const versionHeader = screen.getByTestId('version-table-header-version');
      const channelHeader = screen.getByTestId('version-table-header-channel');
      const sizeHeader = screen.getByTestId('version-table-header-filesize');

      expect(versionHeader).toHaveClass('cursor-pointer');
      expect(channelHeader).toHaveClass('cursor-pointer');
      expect(sizeHeader).toHaveClass('cursor-pointer');
    });

    it('defaults to version descending sort', () => {
      render(<VersionTable versions={mockVersions} />);

      // Get all rows
      const rows = screen.getAllByTestId(/^version-table-row-/);

      // First row should be highest version (1.20.1-rc.1 > 1.20.0 > 1.19.8)
      expect(rows[0]).toHaveAttribute('data-testid', 'version-table-row-1.20.1-rc.1');
      expect(rows[1]).toHaveAttribute('data-testid', 'version-table-row-1.20.0');
      expect(rows[2]).toHaveAttribute('data-testid', 'version-table-row-1.19.8');
    });

    it('toggles sort order when clicking column header', async () => {
      const user = userEvent.setup();
      render(<VersionTable versions={mockVersions} />);

      // Default sort is version descending, verify initial state
      let rows = screen.getAllByTestId(/^version-table-row-/);
      expect(rows[0]).toHaveAttribute('data-testid', 'version-table-row-1.20.1-rc.1');

      // Click channel header to sort by channel (which wasn't sorted before)
      const channelHeader = screen.getByTestId('version-table-header-channel');
      await user.click(channelHeader);

      // Get all rows - should now be sorted by channel ascending (stable before unstable)
      rows = screen.getAllByTestId(/^version-table-row-/);
      // Stable versions should come before unstable alphabetically
      expect(rows[2]).toHaveAttribute('data-testid', 'version-table-row-1.20.1-rc.1'); // unstable is last

      // Click channel header again to toggle to descending
      await user.click(channelHeader);

      rows = screen.getAllByTestId(/^version-table-row-/);
      // Unstable should now come first
      expect(rows[0]).toHaveAttribute('data-testid', 'version-table-row-1.20.1-rc.1');
    });

    it('can sort by channel', async () => {
      const user = userEvent.setup();
      render(<VersionTable versions={mockVersions} />);

      const channelHeader = screen.getByTestId('version-table-header-channel');

      // Click to sort by channel
      await user.click(channelHeader);

      // Get all rows
      const rows = screen.getAllByTestId(/^version-table-row-/);

      // With ascending sort, stable comes before unstable alphabetically
      const firstRowChannel = within(rows[0]).getByTestId(/version-table-channel/);
      expect(firstRowChannel).toHaveTextContent('Stable');
    });
  });

  describe('responsive column hiding', () => {
    it('Size column has hidden class for mobile', () => {
      render(<VersionTable versions={mockVersions} />);

      const sizeHeader = screen.getByTestId('version-table-header-filesize');
      expect(sizeHeader).toHaveClass('hidden');
      expect(sizeHeader).toHaveClass('sm:table-cell');
    });
  });

  describe('newer version highlighting', () => {
    it('highlights versions newer than installed', () => {
      render(
        <VersionTable
          versions={mockVersions}
          installedVersion="1.19.8"
        />
      );

      // 1.20.0 and 1.20.1-rc.1 are newer than 1.19.8
      const newerRow = screen.getByTestId('version-table-row-1.20.0');
      expect(newerRow.className).toMatch(/bg-primary/);

      const newerUnstableRow = screen.getByTestId('version-table-row-1.20.1-rc.1');
      expect(newerUnstableRow.className).toMatch(/bg-primary/);
    });

    it('does not highlight installed version', () => {
      render(
        <VersionTable
          versions={mockVersions}
          installedVersion="1.20.0"
        />
      );

      // Installed version should not be highlighted
      const installedRow = screen.getByTestId('version-table-row-1.20.0');
      expect(installedRow.className).not.toMatch(/bg-primary/);
    });

    it('does not highlight older versions', () => {
      render(
        <VersionTable
          versions={mockVersions}
          installedVersion="1.20.0"
        />
      );

      // 1.19.8 is older, should not be highlighted
      const olderRow = screen.getByTestId('version-table-row-1.19.8');
      expect(olderRow.className).not.toMatch(/bg-primary/);
    });

    it('does not highlight any versions when not installed', () => {
      render(
        <VersionTable
          versions={mockVersions}
          installedVersion={null}
        />
      );

      // None should have highlight styling
      const row1 = screen.getByTestId('version-table-row-1.20.0');
      const row2 = screen.getByTestId('version-table-row-1.19.8');
      const row3 = screen.getByTestId('version-table-row-1.20.1-rc.1');

      expect(row1.className).not.toMatch(/bg-primary/);
      expect(row2.className).not.toMatch(/bg-primary/);
      expect(row3.className).not.toMatch(/bg-primary/);
    });
  });

  it('handles null installedVersion gracefully', () => {
    render(
      <VersionTable
        versions={mockVersions}
        installedVersion={null}
      />
    );

    // No installed indicators should be shown
    expect(screen.queryByTestId('version-table-installed-1.20.0')).not.toBeInTheDocument();
    expect(screen.queryByTestId('version-table-installed-1.19.8')).not.toBeInTheDocument();
    expect(screen.queryByTestId('version-table-installed-1.20.1-rc.1')).not.toBeInTheDocument();
  });

  it('handles undefined installedVersion gracefully', () => {
    render(<VersionTable versions={mockVersions} />);

    // No installed indicators should be shown
    expect(screen.queryByTestId('version-table-installed-1.20.0')).not.toBeInTheDocument();
  });

  describe('semantic version comparison', () => {
    // Test case for F1: String comparison would incorrectly say "1.9.0" > "1.10.0"
    it('correctly compares versions where string comparison would fail', () => {
      const versionsWithTrickyNumbers: VersionInfo[] = [
        {
          version: '1.9.0',
          filename: 'vs_server_linux-x64_1.9.0.tar.gz',
          filesize: '40 MB',
          md5: 'abc',
          cdnUrl: 'https://cdn.example.com/1.9.0',
          localUrl: '/local/1.9.0',
          isLatest: false,
          channel: 'stable',
        },
        {
          version: '1.10.0',
          filename: 'vs_server_linux-x64_1.10.0.tar.gz',
          filesize: '41 MB',
          md5: 'def',
          cdnUrl: 'https://cdn.example.com/1.10.0',
          localUrl: '/local/1.10.0',
          isLatest: true,
          channel: 'stable',
        },
      ];

      render(
        <VersionTable
          versions={versionsWithTrickyNumbers}
          installedVersion="1.9.0"
        />
      );

      // 1.10.0 is newer than 1.9.0 (semantic comparison)
      // String comparison would incorrectly say 1.9.0 > 1.10.0
      const newerRow = screen.getByTestId('version-table-row-1.10.0');
      expect(newerRow.className).toMatch(/bg-primary/);

      const installedRow = screen.getByTestId('version-table-row-1.9.0');
      expect(installedRow.className).not.toMatch(/bg-primary/);
    });

    it('handles prerelease versions correctly', () => {
      // 1.20.0 should be newer than 1.20.0-rc.1
      const versionsWithPrerelease: VersionInfo[] = [
        {
          version: '1.20.0-rc.1',
          filename: 'vs_server_linux-x64_1.20.0-rc.1.tar.gz',
          filesize: '40 MB',
          md5: 'abc',
          cdnUrl: 'https://cdn.example.com/1.20.0-rc.1',
          localUrl: '/local/1.20.0-rc.1',
          isLatest: false,
          channel: 'unstable',
        },
        {
          version: '1.20.0',
          filename: 'vs_server_linux-x64_1.20.0.tar.gz',
          filesize: '41 MB',
          md5: 'def',
          cdnUrl: 'https://cdn.example.com/1.20.0',
          localUrl: '/local/1.20.0',
          isLatest: true,
          channel: 'stable',
        },
      ];

      render(
        <VersionTable
          versions={versionsWithPrerelease}
          installedVersion="1.20.0-rc.1"
        />
      );

      // 1.20.0 is newer than 1.20.0-rc.1 (release > prerelease)
      const newerRow = screen.getByTestId('version-table-row-1.20.0');
      expect(newerRow.className).toMatch(/bg-primary/);
    });
  });

  describe('accessibility', () => {
    it('has aria-sort on sorted column', () => {
      render(<VersionTable versions={mockVersions} />);

      // Default sort is version descending
      const versionHeader = screen.getByTestId('version-table-header-version');
      expect(versionHeader).toHaveAttribute('aria-sort', 'descending');

      // Other sortable columns should not have aria-sort initially
      const channelHeader = screen.getByTestId('version-table-header-channel');
      expect(channelHeader).not.toHaveAttribute('aria-sort');
    });

    it('sortable headers are keyboard accessible', async () => {
      const user = userEvent.setup();
      render(<VersionTable versions={mockVersions} />);

      const channelHeader = screen.getByTestId('version-table-header-channel');

      // Sortable headers should have tabIndex
      expect(channelHeader).toHaveAttribute('tabIndex', '0');

      // Focus and press Enter to sort
      channelHeader.focus();
      await user.keyboard('{Enter}');

      // Should now be sorted by channel ascending
      expect(channelHeader).toHaveAttribute('aria-sort', 'ascending');
    });

    it('sort toggles with Space key', async () => {
      const user = userEvent.setup();
      render(<VersionTable versions={mockVersions} />);

      const channelHeader = screen.getByTestId('version-table-header-channel');
      channelHeader.focus();

      // Press Space to sort ascending
      await user.keyboard(' ');
      expect(channelHeader).toHaveAttribute('aria-sort', 'ascending');

      // Press Space again to sort descending
      await user.keyboard(' ');
      expect(channelHeader).toHaveAttribute('aria-sort', 'descending');
    });
  });
});
