import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ModBrowseGrid } from './ModBrowseGrid';
import type { ModBrowseItem } from '@/api/types';

// Mock mod data for testing
const mockMods: ModBrowseItem[] = [
  {
    slug: 'carrycapacity',
    name: 'Carry Capacity',
    author: 'copygirl',
    summary: 'Allows picking up chests and other containers',
    downloads: 50000,
    follows: 500,
    trendingPoints: 100,
    side: 'both',
    modType: 'mod',
    logoUrl: null,
    tags: ['utility', 'qol'],
    lastReleased: '2024-01-15T10:00:00Z',
  },
  {
    slug: 'primitivesurvival',
    name: 'Primitive Survival',
    author: 'Spear and Fang',
    summary: 'Adds primitive survival mechanics like fishing and trapping',
    downloads: 75000,
    follows: 800,
    trendingPoints: 200,
    side: 'both',
    modType: 'mod',
    logoUrl: 'https://example.com/logo.png',
    tags: ['survival', 'fishing', 'traps'],
    lastReleased: '2024-02-01T12:00:00Z',
  },
  {
    slug: 'wildcraft',
    name: 'Wildcraft',
    author: 'gabb',
    summary: null,
    downloads: 30000,
    follows: 200,
    trendingPoints: 50,
    side: 'server',
    modType: 'mod',
    logoUrl: null,
    tags: ['plants', 'foraging'],
    lastReleased: '2024-01-20T08:00:00Z',
  },
];

describe('ModBrowseGrid', () => {
  describe('loading state', () => {
    it('renders skeleton cards when loading', () => {
      render(<ModBrowseGrid mods={[]} isLoading={true} />);

      const grid = screen.getByTestId('mod-browse-grid-loading');
      expect(grid).toBeInTheDocument();

      const skeletons = screen.getAllByTestId('mod-card-skeleton');
      expect(skeletons.length).toBe(8);
    });

    it('does not render actual mods when loading', () => {
      render(<ModBrowseGrid mods={mockMods} isLoading={true} />);

      expect(screen.queryByTestId('mod-card-carrycapacity')).not.toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('renders empty message when no mods', () => {
      render(<ModBrowseGrid mods={[]} isLoading={false} />);

      const empty = screen.getByTestId('mod-browse-grid-empty');
      expect(empty).toBeInTheDocument();
      expect(empty).toHaveTextContent('No mods found matching your criteria');
    });

    it('renders empty message for empty array explicitly', () => {
      render(<ModBrowseGrid mods={[]} />);

      expect(screen.getByTestId('mod-browse-grid-empty')).toBeInTheDocument();
    });
  });

  describe('with mods', () => {
    it('renders grid with mod cards', () => {
      render(<ModBrowseGrid mods={mockMods} isLoading={false} />);

      const grid = screen.getByTestId('mod-browse-grid');
      expect(grid).toBeInTheDocument();

      // Check that all three mods are rendered
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-primitivesurvival')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-wildcraft')).toBeInTheDocument();
    });

    it('defaults isLoading to false', () => {
      render(<ModBrowseGrid mods={mockMods} />);

      // Should render actual grid, not loading state
      expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-browse-grid-loading')).not.toBeInTheDocument();
    });

    it('renders correct number of mod cards', () => {
      render(<ModBrowseGrid mods={mockMods} />);

      const grid = screen.getByTestId('mod-browse-grid');
      // Each mod should have a card
      expect(grid.children.length).toBe(3);
    });
  });

  describe('with single mod', () => {
    it('renders grid with one mod card', () => {
      render(<ModBrowseGrid mods={[mockMods[0]]} />);

      const grid = screen.getByTestId('mod-browse-grid');
      expect(grid).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(grid.children.length).toBe(1);
    });
  });
});
