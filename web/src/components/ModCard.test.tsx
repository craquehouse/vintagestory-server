import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ModCard, formatNumber } from './ModCard';
import type { ModBrowseItem } from '@/api/types';

// Mock mod data for testing
const mockMod: ModBrowseItem = {
  slug: 'carrycapacity',
  name: 'Carry Capacity',
  author: 'copygirl',
  summary: 'Allows picking up chests and other containers while keeping their contents',
  downloads: 50000,
  follows: 500,
  trendingPoints: 100,
  side: 'both',
  modType: 'mod',
  logoUrl: null,
  tags: ['utility', 'qol'],
  lastReleased: '2024-01-15T10:00:00Z',
};

const mockModWithLogo: ModBrowseItem = {
  ...mockMod,
  slug: 'modwithlogo',
  name: 'Mod With Logo',
  logoUrl: 'https://mods.vintagestory.at/assets/modlogo.png',
};

const mockModNoSummary: ModBrowseItem = {
  ...mockMod,
  slug: 'testmod',
  name: 'Test Mod',
  summary: null,
};

describe('formatNumber', () => {
  it('formats small numbers as-is', () => {
    expect(formatNumber(0)).toBe('0');
    expect(formatNumber(1)).toBe('1');
    expect(formatNumber(999)).toBe('999');
  });

  it('formats thousands with K suffix', () => {
    expect(formatNumber(1000)).toBe('1.0K');
    expect(formatNumber(1234)).toBe('1.2K');
    expect(formatNumber(50000)).toBe('50.0K');
    expect(formatNumber(999999)).toBe('1000.0K');
  });

  it('formats millions with M suffix', () => {
    expect(formatNumber(1000000)).toBe('1.0M');
    expect(formatNumber(1234567)).toBe('1.2M');
    expect(formatNumber(10500000)).toBe('10.5M');
  });
});

describe('ModCard', () => {
  describe('rendering', () => {
    it('renders the mod name as a link', () => {
      render(<ModCard mod={mockMod} />);

      const link = screen.getByTestId('mod-card-link-carrycapacity');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://mods.vintagestory.at/carrycapacity');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
      expect(link).toHaveTextContent('Carry Capacity');
    });

    it('renders the author name', () => {
      render(<ModCard mod={mockMod} />);

      const author = screen.getByTestId('mod-card-author-carrycapacity');
      expect(author).toBeInTheDocument();
      expect(author).toHaveTextContent('by copygirl');
    });

    it('renders the summary when present', () => {
      render(<ModCard mod={mockMod} />);

      const summary = screen.getByTestId('mod-card-summary-carrycapacity');
      expect(summary).toBeInTheDocument();
      expect(summary).toHaveTextContent('Allows picking up chests');
    });

    it('does not render summary when null', () => {
      render(<ModCard mod={mockModNoSummary} />);

      expect(screen.queryByTestId('mod-card-summary-testmod')).not.toBeInTheDocument();
    });

    it('renders download count', () => {
      render(<ModCard mod={mockMod} />);

      const downloads = screen.getByTestId('mod-card-downloads-carrycapacity');
      expect(downloads).toBeInTheDocument();
      expect(downloads).toHaveTextContent('50.0K');
    });

    it('renders follower count', () => {
      render(<ModCard mod={mockMod} />);

      const follows = screen.getByTestId('mod-card-follows-carrycapacity');
      expect(follows).toBeInTheDocument();
      expect(follows).toHaveTextContent('500');
    });

    it('renders trending points', () => {
      render(<ModCard mod={mockMod} />);

      const trending = screen.getByTestId('mod-card-trending-carrycapacity');
      expect(trending).toBeInTheDocument();
      expect(trending).toHaveTextContent('100');
    });

    it('renders the card with correct test id', () => {
      render(<ModCard mod={mockMod} />);

      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
    });
  });

  describe('with different mod data', () => {
    it('handles high download counts', () => {
      const popularMod: ModBrowseItem = {
        ...mockMod,
        slug: 'popular',
        downloads: 2500000,
        follows: 15000,
        trendingPoints: 5000,
      };

      render(<ModCard mod={popularMod} />);

      expect(screen.getByTestId('mod-card-downloads-popular')).toHaveTextContent('2.5M');
      expect(screen.getByTestId('mod-card-follows-popular')).toHaveTextContent('15.0K');
      expect(screen.getByTestId('mod-card-trending-popular')).toHaveTextContent('5.0K');
    });

    it('handles low counts (no suffix)', () => {
      const unpopularMod: ModBrowseItem = {
        ...mockMod,
        slug: 'new',
        downloads: 50,
        follows: 5,
        trendingPoints: 10,
      };

      render(<ModCard mod={unpopularMod} />);

      expect(screen.getByTestId('mod-card-downloads-new')).toHaveTextContent('50');
      expect(screen.getByTestId('mod-card-follows-new')).toHaveTextContent('5');
      expect(screen.getByTestId('mod-card-trending-new')).toHaveTextContent('10');
    });

    it('handles zero counts', () => {
      const noActivityMod: ModBrowseItem = {
        ...mockMod,
        slug: 'empty',
        downloads: 0,
        follows: 0,
        trendingPoints: 0,
      };

      render(<ModCard mod={noActivityMod} />);

      expect(screen.getByTestId('mod-card-downloads-empty')).toHaveTextContent('0');
      expect(screen.getByTestId('mod-card-follows-empty')).toHaveTextContent('0');
      expect(screen.getByTestId('mod-card-trending-empty')).toHaveTextContent('0');
    });
  });

  describe('thumbnail display (AC 1, 4)', () => {
    it('displays logo image when logoUrl is provided', () => {
      render(<ModCard mod={mockModWithLogo} />);

      const image = screen.getByTestId('mod-card-logo-modwithlogo');
      expect(image).toBeInTheDocument();
      expect(image).toHaveAttribute('src', 'https://mods.vintagestory.at/assets/modlogo.png');
      expect(image).toHaveAttribute('alt', 'Mod With Logo thumbnail');
    });

    it('displays placeholder icon when logoUrl is null', () => {
      render(<ModCard mod={mockMod} />);

      const placeholder = screen.getByTestId('mod-card-placeholder-carrycapacity');
      expect(placeholder).toBeInTheDocument();
      // Logo image should not exist
      expect(screen.queryByTestId('mod-card-logo-carrycapacity')).not.toBeInTheDocument();
    });

    it('displays thumbnail in correct aspect ratio container', () => {
      render(<ModCard mod={mockModWithLogo} />);

      const thumbnail = screen.getByTestId('mod-card-thumbnail-modwithlogo');
      expect(thumbnail).toBeInTheDocument();
      // Check for aspect ratio styling (CSS class)
      expect(thumbnail.className).toContain('aspect-');
    });
  });

  describe('compatibility badge display (AC 2)', () => {
    it('displays compatibility badge with not_verified status by default', () => {
      render(<ModCard mod={mockMod} />);

      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).toBeInTheDocument();
      expect(badge).toHaveAttribute('data-status', 'not_verified');
      expect(badge).toHaveTextContent('Not verified');
    });

    it('displays compatibility badge for mod with logo', () => {
      render(<ModCard mod={mockModWithLogo} />);

      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).toBeInTheDocument();
    });
  });

  describe('click navigation (AC 3)', () => {
    it('calls onClick handler when card is clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const card = screen.getByTestId('mod-card-carrycapacity');
      await user.click(card);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('has cursor-pointer styling when onClick is provided', () => {
      const handleClick = vi.fn();
      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const card = screen.getByTestId('mod-card-carrycapacity');
      expect(card.className).toContain('cursor-pointer');
    });

    it('has hover shadow transition when onClick is provided', () => {
      const handleClick = vi.fn();
      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const card = screen.getByTestId('mod-card-carrycapacity');
      expect(card.className).toContain('transition-shadow');
    });

    it('does NOT call onClick when external link is clicked (event bubbling)', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const externalLink = screen.getByTestId('mod-card-link-carrycapacity');
      await user.click(externalLink);

      // External link click should NOT trigger card onClick
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('does not have cursor-pointer when onClick is not provided', () => {
      render(<ModCard mod={mockMod} />);

      const card = screen.getByTestId('mod-card-carrycapacity');
      expect(card.className).not.toContain('cursor-pointer');
    });
  });
});
