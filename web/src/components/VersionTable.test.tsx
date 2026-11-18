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

/** A version row for the Story 21.5 tests. */
function versionInfo(
  version: string,
  channel: VersionInfo['channel'],
  isLatest = false,
  filesize = '40.0 MB'
): VersionInfo {
  return {
    version,
    filename: `vs_server_linux-x64_${version}.tar.gz`,
    filesize,
    md5: 'abc123',
    cdnUrl: `https://cdn.example.com/${version}`,
    localUrl: `/local/${version}`,
    isLatest,
    channel,
  };
}

// Story 21.5: pre-releases with one- and two-digit numbers, and a two-digit patch part
const preReleaseVersions: VersionInfo[] = [
  versionInfo('1.21.9', 'stable'),
  versionInfo('1.22.0-rc.1', 'unstable'),
  versionInfo('1.22.0', 'stable', true),
  versionInfo('1.22.0-rc.12', 'unstable', true),
  versionInfo('1.21.10', 'stable'),
  versionInfo('1.22.0-rc.2', 'unstable'),
];

function rowVersions(): string[] {
  return screen
    .getAllByTestId(/^version-table-row-/)
    .map((row) => (row.getAttribute('data-testid') ?? '').replace('version-table-row-', ''));
}

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
    expect(changelogLink).toHaveAttribute(
      'aria-label',
      'View changelog for version 1.20.0 (opens in a new tab)'
    );
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
    render(<VersionTable versions={mockVersions} installedVersion="1.19.8" />);

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

    render(<VersionTable versions={mockVersions} onVersionSelect={handleSelect} />);

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

    it('orders pre-releases before their release, newest first by default (Story 21.5)', () => {
      render(<VersionTable versions={preReleaseVersions} />);

      expect(rowVersions()).toEqual([
        '1.22.0',
        '1.22.0-rc.12',
        '1.22.0-rc.2',
        '1.22.0-rc.1',
        '1.21.10',
        '1.21.9',
      ]);
    });

    it('sorts versions ascending after two clicks on Version (Story 21.5)', async () => {
      const user = userEvent.setup();
      render(<VersionTable versions={preReleaseVersions} />);

      const versionHeader = screen.getByTestId('version-table-header-version');
      // From the default (descending) one click removes the sort, the next sorts ascending
      await user.click(versionHeader);
      await user.click(versionHeader);

      expect(rowVersions()).toEqual([
        '1.21.9',
        '1.21.10',
        '1.22.0-rc.1',
        '1.22.0-rc.2',
        '1.22.0-rc.12',
        '1.22.0',
      ]);
    });

    it('sorts the Size column by size, not by its text (Story 21.5)', async () => {
      const user = userEvent.setup();
      render(
        <VersionTable
          versions={[
            versionInfo('1.21.1', 'stable', false, '45.9 MB'),
            versionInfo('1.21.2', 'stable', false, '1.1 GB'),
            versionInfo('1.21.3', 'stable', false, '45.10 MB'),
            versionInfo('1.21.4', 'stable', false, '800 KB'),
            versionInfo('1.21.5', 'stable', false, 'unknown'),
          ]}
        />
      );

      const sizeHeader = screen.getByTestId('version-table-header-filesize');
      await user.click(sizeHeader);
      // Sizes that cannot be read come last
      expect(rowVersions()).toEqual(['1.21.4', '1.21.3', '1.21.1', '1.21.2', '1.21.5']);

      await user.click(sizeHeader);
      expect(rowVersions()).toEqual(['1.21.5', '1.21.2', '1.21.1', '1.21.3', '1.21.4']);
    });
  });

  describe('responsive column hiding', () => {
    it('Size column has hidden class for mobile', () => {
      render(<VersionTable versions={mockVersions} />);

      const sizeHeader = screen.getByTestId('version-table-header-filesize');
      expect(sizeHeader).toHaveClass('hidden');
      expect(sizeHeader).toHaveClass('sm:table-cell');

      // Story 21.5: the body cells read the same column meta
      const sizeCell = screen.getByTestId('version-table-size-1.20.0').closest('td');
      expect(sizeCell).toHaveClass('hidden', 'sm:table-cell');
    });
  });

  describe('newer version highlighting', () => {
    it('highlights versions newer than installed', () => {
      render(<VersionTable versions={mockVersions} installedVersion="1.19.8" />);

      // 1.20.0 and 1.20.1-rc.1 are newer than 1.19.8
      const newerRow = screen.getByTestId('version-table-row-1.20.0');
      expect(newerRow.className).toMatch(/bg-primary/);

      const newerUnstableRow = screen.getByTestId('version-table-row-1.20.1-rc.1');
      expect(newerUnstableRow.className).toMatch(/bg-primary/);
    });

    it('does not highlight installed version', () => {
      render(<VersionTable versions={mockVersions} installedVersion="1.20.0" />);

      // Installed version should not be highlighted
      const installedRow = screen.getByTestId('version-table-row-1.20.0');
      expect(installedRow.className).not.toMatch(/bg-primary/);
    });

    it('does not highlight older versions', () => {
      render(<VersionTable versions={mockVersions} installedVersion="1.20.0" />);

      // 1.19.8 is older, should not be highlighted
      const olderRow = screen.getByTestId('version-table-row-1.19.8');
      expect(olderRow.className).not.toMatch(/bg-primary/);
    });

    it('marks pre-releases with higher numbers as newer (Story 21.5)', () => {
      render(<VersionTable versions={preReleaseVersions} installedVersion="1.22.0-rc.2" />);

      for (const newer of ['1.22.0-rc.12', '1.22.0']) {
        expect(screen.getByTestId(`version-table-row-${newer}`).className).toMatch(/bg-primary/);
      }
      for (const notNewer of ['1.22.0-rc.2', '1.22.0-rc.1', '1.21.10']) {
        expect(screen.getByTestId(`version-table-row-${notNewer}`).className).not.toMatch(
          /bg-primary/
        );
      }
    });

    it('does not highlight any versions when not installed', () => {
      render(<VersionTable versions={mockVersions} installedVersion={null} />);

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
    render(<VersionTable versions={mockVersions} installedVersion={null} />);

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

      render(<VersionTable versions={versionsWithTrickyNumbers} installedVersion="1.9.0" />);

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

      render(<VersionTable versions={versionsWithPrerelease} installedVersion="1.20.0-rc.1" />);

      // 1.20.0 is newer than 1.20.0-rc.1 (release > prerelease)
      const newerRow = screen.getByTestId('version-table-row-1.20.0');
      expect(newerRow.className).toMatch(/bg-primary/);
    });
  });

  describe('accessibility', () => {
    it('marks the sorted column and sets none on the other sortable columns', () => {
      render(<VersionTable versions={mockVersions} />);

      // Default sort is version descending
      const versionHeader = screen.getByTestId('version-table-header-version');
      expect(versionHeader).toHaveAttribute('aria-sort', 'descending');

      // Story 21.5: the other sortable columns read none
      const channelHeader = screen.getByTestId('version-table-header-channel');
      expect(channelHeader).toHaveAttribute('aria-sort', 'none');
    });

    describe('aria-sort through the accessibility tree (Story 21.5)', () => {
      function header(name: string) {
        return screen.getByRole('columnheader', { name });
      }

      it('marks Version descending by default, Channel and Size none, the rest nothing', () => {
        render(<VersionTable versions={mockVersions} />);

        expect(header('Version')).toHaveAttribute('aria-sort', 'descending');
        expect(header('Channel')).toHaveAttribute('aria-sort', 'none');
        expect(header('Size')).toHaveAttribute('aria-sort', 'none');
        expect(header('Status')).not.toHaveAttribute('aria-sort');
        expect(header('Actions')).not.toHaveAttribute('aria-sort');
      });

      it('moves aria-sort to Channel when Channel is sorted', async () => {
        const user = userEvent.setup();
        render(<VersionTable versions={mockVersions} />);

        await user.click(header('Channel'));
        expect(header('Channel')).toHaveAttribute('aria-sort', 'ascending');
        expect(header('Version')).toHaveAttribute('aria-sort', 'none');
      });

      it('reads none on every sortable column when a click removes the sort', async () => {
        const user = userEvent.setup();
        render(<VersionTable versions={mockVersions} />);

        await user.click(header('Version'));
        for (const name of ['Version', 'Channel', 'Size']) {
          expect(header(name)).toHaveAttribute('aria-sort', 'none');
        }

        await user.click(header('Version'));
        expect(header('Version')).toHaveAttribute('aria-sort', 'ascending');
      });

      it('hides the sort chevrons from screen readers', () => {
        render(<VersionTable versions={mockVersions} />);

        const chevrons = header('Version').querySelectorAll('svg');
        expect(chevrons).toHaveLength(1);
        expect(chevrons[0]).toHaveAttribute('aria-hidden', 'true');
      });
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

  // Story 21.7 (AC 7): below sm (640px) Channel and Status are shown under the version
  describe('channel and status under the version on phones (Story 21.7)', () => {
    it('shows each row channel badge under the version, as the column shows it', () => {
      render(<VersionTable versions={mockVersions} />);

      for (const { version } of mockVersions) {
        const inline = screen.getByTestId(`version-table-inline-channel-${version}`);
        const column = screen.getByTestId(`version-table-channel-${version}`);
        expect(inline).toHaveTextContent(column.textContent ?? '');
        expect(inline.className).toBe(column.className);
        expect(inline.parentElement).toHaveClass('sm:hidden');
        expect(
          within(screen.getByTestId(`version-table-row-${version}`))
            .getByTestId(`version-table-version-${version}`)
            .closest('td')
        ).toContainElement(inline);
      }
      expect(screen.getByTestId('version-table-inline-channel-1.20.0')).toHaveTextContent('Stable');
      expect(screen.getByTestId('version-table-inline-channel-1.20.1-rc.1')).toHaveTextContent(
        'Unstable'
      );
    });

    it('shows Latest and Installed under the version when they apply, and no dash', () => {
      render(<VersionTable versions={mockVersions} installedVersion="1.19.8" />);

      expect(screen.getByTestId('version-table-inline-latest-1.20.0')).toHaveTextContent('Latest');
      expect(screen.queryByTestId('version-table-inline-installed-1.20.0')).not.toBeInTheDocument();
      expect(screen.getByTestId('version-table-inline-installed-1.19.8')).toHaveTextContent(
        'Installed'
      );
      expect(screen.queryByTestId('version-table-inline-latest-1.19.8')).not.toBeInTheDocument();
      // The same marks as the Status column
      expect(screen.getByTestId('version-table-inline-latest-1.20.0').className).toBe(
        screen.getByTestId('version-table-latest-1.20.0').className
      );
      expect(screen.getByTestId('version-table-inline-installed-1.19.8').className).toBe(
        screen.getByTestId('version-table-installed-1.19.8').className
      );

      const inlineRow = screen.getByTestId('version-table-inline-channel-1.19.8').parentElement;
      expect(inlineRow).not.toHaveTextContent('-');
    });

    it('shows neither mark for a row that is neither latest nor installed', () => {
      render(<VersionTable versions={mockVersions} />);

      expect(screen.queryByTestId('version-table-inline-latest-1.19.8')).not.toBeInTheDocument();
      expect(screen.queryByTestId('version-table-inline-installed-1.19.8')).not.toBeInTheDocument();
      const inlineRow = screen.getByTestId('version-table-inline-channel-1.19.8').parentElement;
      expect(inlineRow).toHaveTextContent(/^Stable$/);
    });

    it('hides the Channel and Status columns below sm, and not Version or Actions', () => {
      render(<VersionTable versions={mockVersions} installedVersion="1.20.0" />);

      for (const id of ['channel', 'status']) {
        expect(screen.getByTestId(`version-table-header-${id}`)).toHaveClass(
          'hidden',
          'sm:table-cell'
        );
      }
      expect(screen.getByTestId('version-table-channel-1.20.0').closest('td')).toHaveClass(
        'hidden',
        'sm:table-cell'
      );
      expect(screen.getByTestId('version-table-latest-1.20.0').closest('td')).toHaveClass(
        'hidden',
        'sm:table-cell'
      );
      for (const id of ['version', 'actions']) {
        expect(screen.getByTestId(`version-table-header-${id}`)).not.toHaveClass('hidden');
      }
      expect(screen.getByTestId('version-table-version-1.20.0').closest('td')).not.toHaveClass(
        'hidden'
      );
      expect(screen.getByTestId('version-table-select-1.20.0').closest('td')).not.toHaveClass(
        'hidden'
      );
    });

    it('hides the same two columns in the loading skeleton', () => {
      render(<VersionTable versions={[]} isLoading />);

      const headers = within(screen.getByTestId('version-table-loading')).getAllByRole(
        'columnheader'
      );
      expect(headers.map((header) => header.textContent)).toEqual([
        'Version',
        'Channel',
        'Size',
        'Status',
        'Actions',
      ]);
      const hidden = [false, true, true, true, false];
      headers.forEach((header, index) => {
        if (hidden[index]) expect(header).toHaveClass('hidden', 'sm:table-cell');
        else expect(header).not.toHaveClass('hidden');
      });
      for (const row of screen.getAllByTestId('version-table-skeleton-row')) {
        const cells = within(row).getAllByRole('cell');
        cells.forEach((cell, index) => {
          if (hidden[index]) expect(cell).toHaveClass('hidden', 'sm:table-cell');
          else expect(cell).not.toHaveClass('hidden');
        });
      }
    });

    it('makes the Select button 44px tall below lg and keeps its action', async () => {
      const user = userEvent.setup();
      const onVersionSelect = vi.fn();
      render(<VersionTable versions={mockVersions} onVersionSelect={onVersionSelect} />);

      const button = screen.getByTestId('version-table-select-1.19.8');
      expect(button).toHaveClass('max-lg:h-11');
      expect(button).toHaveTextContent('Select');
      await user.click(button);
      expect(onVersionSelect).toHaveBeenCalledWith('1.19.8');
    });
  });
});
