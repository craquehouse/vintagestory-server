import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { VersionCard } from './VersionCard';
import type { VersionInfo } from '@/api/types';

// Mock stable version
const mockStableVersion: VersionInfo = {
  version: '1.21.6',
  filename: 'vs_server_linux-x64_1.21.6.tar.gz',
  filesize: '40.2 MB',
  md5: 'abc123',
  cdnUrl: 'https://cdn.example.com/stable/1.21.6',
  localUrl: '/downloads/stable/1.21.6',
  isLatest: true,
  channel: 'stable',
};

// Mock unstable version
const mockUnstableVersion: VersionInfo = {
  version: '1.22.0-rc1',
  filename: 'vs_server_linux-x64_1.22.0-rc1.tar.gz',
  filesize: '41.0 MB',
  md5: 'def456',
  cdnUrl: 'https://cdn.example.com/unstable/1.22.0-rc1',
  localUrl: '/downloads/unstable/1.22.0-rc1',
  isLatest: true,
  channel: 'unstable',
};

// Mock older stable version (not latest)
const mockOlderVersion: VersionInfo = {
  version: '1.21.5',
  filename: 'vs_server_linux-x64_1.21.5.tar.gz',
  filesize: '39.8 MB',
  md5: 'ghi789',
  cdnUrl: 'https://cdn.example.com/stable/1.21.5',
  localUrl: '/downloads/stable/1.21.5',
  isLatest: false,
  channel: 'stable',
};

describe('VersionCard', () => {
  describe('rendering (AC: 1)', () => {
    it('renders the version number prominently', () => {
      render(<VersionCard version={mockStableVersion} />);

      const versionNumber = screen.getByTestId('version-card-version-1.21.6');
      expect(versionNumber).toBeInTheDocument();
      expect(versionNumber).toHaveTextContent('1.21.6');
    });

    it('renders the file size', () => {
      render(<VersionCard version={mockStableVersion} />);

      const filesize = screen.getByTestId('version-card-filesize-1.21.6');
      expect(filesize).toBeInTheDocument();
      expect(filesize).toHaveTextContent('40.2 MB');
    });

    it('renders stable channel badge for stable versions', () => {
      render(<VersionCard version={mockStableVersion} />);

      const channel = screen.getByTestId('version-card-channel-1.21.6');
      expect(channel).toBeInTheDocument();
      expect(channel).toHaveTextContent('Stable');
    });

    it('renders unstable channel badge for unstable versions', () => {
      render(<VersionCard version={mockUnstableVersion} />);

      const channel = screen.getByTestId('version-card-channel-1.22.0-rc1');
      expect(channel).toBeInTheDocument();
      expect(channel).toHaveTextContent('Unstable');
    });

    it('renders the card with correct test id', () => {
      render(<VersionCard version={mockStableVersion} />);

      expect(screen.getByTestId('version-card-1.21.6')).toBeInTheDocument();
    });
  });

  describe('installed badge (AC: 2)', () => {
    it('shows Installed badge when version matches installed version', () => {
      render(
        <VersionCard version={mockStableVersion} installedVersion="1.21.6" />
      );

      const installed = screen.getByTestId('version-card-installed-1.21.6');
      expect(installed).toBeInTheDocument();
      expect(installed).toHaveTextContent('Installed');
    });

    it('does not show Installed badge when version differs from installed', () => {
      render(
        <VersionCard version={mockStableVersion} installedVersion="1.21.5" />
      );

      expect(
        screen.queryByTestId('version-card-installed-1.21.6')
      ).not.toBeInTheDocument();
    });

    it('does not show Installed badge when installedVersion is null', () => {
      render(<VersionCard version={mockStableVersion} installedVersion={null} />);

      expect(
        screen.queryByTestId('version-card-installed-1.21.6')
      ).not.toBeInTheDocument();
    });

    it('does not show Installed badge when installedVersion is not provided', () => {
      render(<VersionCard version={mockStableVersion} />);

      expect(
        screen.queryByTestId('version-card-installed-1.21.6')
      ).not.toBeInTheDocument();
    });
  });

  describe('latest badge (AC: 3)', () => {
    it('shows Latest badge when isLatest is true', () => {
      render(<VersionCard version={mockStableVersion} />);

      const latest = screen.getByTestId('version-card-latest-1.21.6');
      expect(latest).toBeInTheDocument();
      expect(latest).toHaveTextContent('Latest');
    });

    it('does not show Latest badge when isLatest is false', () => {
      render(<VersionCard version={mockOlderVersion} />);

      expect(
        screen.queryByTestId('version-card-latest-1.21.5')
      ).not.toBeInTheDocument();
    });

    it('shows both Latest and Installed badges when appropriate', () => {
      render(
        <VersionCard version={mockStableVersion} installedVersion="1.21.6" />
      );

      expect(screen.getByTestId('version-card-latest-1.21.6')).toBeInTheDocument();
      expect(screen.getByTestId('version-card-installed-1.21.6')).toBeInTheDocument();
    });
  });

  describe('click handling (AC: 4)', () => {
    it('calls onClick handler when card is clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<VersionCard version={mockStableVersion} onClick={handleClick} />);

      const card = screen.getByTestId('version-card-1.21.6');
      await user.click(card);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('has cursor-pointer styling when onClick is provided', () => {
      const handleClick = vi.fn();
      render(<VersionCard version={mockStableVersion} onClick={handleClick} />);

      const card = screen.getByTestId('version-card-1.21.6');
      expect(card.className).toContain('cursor-pointer');
    });

    it('has hover shadow transition when onClick is provided', () => {
      const handleClick = vi.fn();
      render(<VersionCard version={mockStableVersion} onClick={handleClick} />);

      const card = screen.getByTestId('version-card-1.21.6');
      expect(card.className).toContain('transition-shadow');
    });

    it('does not have cursor-pointer when onClick is not provided', () => {
      render(<VersionCard version={mockStableVersion} />);

      const card = screen.getByTestId('version-card-1.21.6');
      expect(card.className).not.toContain('cursor-pointer');
    });

    it('does not have transition-shadow when onClick is not provided', () => {
      render(<VersionCard version={mockStableVersion} />);

      const card = screen.getByTestId('version-card-1.21.6');
      expect(card.className).not.toContain('transition-shadow');
    });
  });

  describe('channel badge styling', () => {
    it('stable badge has green styling', () => {
      render(<VersionCard version={mockStableVersion} />);

      const channel = screen.getByTestId('version-card-channel-1.21.6');
      const badge = channel.querySelector('[data-slot="badge"]');
      expect(badge).toBeInTheDocument();
      // Check for green-related class
      expect(badge?.className).toMatch(/green/);
    });

    it('unstable badge has yellow styling', () => {
      render(<VersionCard version={mockUnstableVersion} />);

      const channel = screen.getByTestId('version-card-channel-1.22.0-rc1');
      const badge = channel.querySelector('[data-slot="badge"]');
      expect(badge).toBeInTheDocument();
      // Check for yellow-related class
      expect(badge?.className).toMatch(/yellow/);
    });
  });

  /**
   * Story 13.5: Newer version highlighting
   *
   * AC 3: Newer versions should be visually highlighted
   */
  describe('newer version highlighting (Story 13.5)', () => {
    it('highlights card when isNewer is true', () => {
      render(
        <VersionCard version={mockStableVersion} installedVersion="1.21.5" isNewer={true} />
      );

      const card = screen.getByTestId('version-card-1.21.6');
      // Should have ring styling for highlight
      expect(card.className).toMatch(/ring/);
    });

    it('does not highlight card when isNewer is false', () => {
      render(
        <VersionCard version={mockOlderVersion} installedVersion="1.21.6" isNewer={false} />
      );

      const card = screen.getByTestId('version-card-1.21.5');
      // Should not have ring styling
      expect(card.className).not.toMatch(/ring-2/);
    });

    it('does not highlight installed version', () => {
      render(
        <VersionCard version={mockStableVersion} installedVersion="1.21.6" isNewer={false} />
      );

      const card = screen.getByTestId('version-card-1.21.6');
      // Should not have ring styling
      expect(card.className).not.toMatch(/ring-2/);
    });

    it('does not highlight when isNewer is not provided', () => {
      render(<VersionCard version={mockStableVersion} />);

      const card = screen.getByTestId('version-card-1.21.6');
      // Should not have ring styling
      expect(card.className).not.toMatch(/ring-2/);
    });
  });

  describe('with different version data', () => {
    it('handles pre-release version numbers', () => {
      const preRelease: VersionInfo = {
        ...mockUnstableVersion,
        version: '1.22.0-pre.5',
      };

      render(<VersionCard version={preRelease} />);

      expect(screen.getByTestId('version-card-1.22.0-pre.5')).toBeInTheDocument();
      expect(
        screen.getByTestId('version-card-version-1.22.0-pre.5')
      ).toHaveTextContent('1.22.0-pre.5');
    });

    it('handles small file sizes', () => {
      const smallVersion: VersionInfo = {
        ...mockStableVersion,
        version: '1.0.0',
        filesize: '15.5 MB',
      };

      render(<VersionCard version={smallVersion} />);

      expect(screen.getByTestId('version-card-filesize-1.0.0')).toHaveTextContent(
        '15.5 MB'
      );
    });

    it('handles large file sizes', () => {
      const largeVersion: VersionInfo = {
        ...mockStableVersion,
        version: '2.0.0',
        filesize: '125.8 MB',
      };

      render(<VersionCard version={largeVersion} />);

      expect(screen.getByTestId('version-card-filesize-2.0.0')).toHaveTextContent(
        '125.8 MB'
      );
    });
  });
});
