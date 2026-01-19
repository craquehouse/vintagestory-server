import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ModBrowseGrid } from './ModBrowseGrid';
import * as useModDetail from '@/hooks/use-mod-detail';
import type { ModBrowseItem } from '@/api/types';

// Helper to create a QueryClient wrapper (queryClient created outside to prevent per-render recreation)
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  const Wrapper = ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
  return Wrapper;
}

// Mock useInstallMod hook (needed by InstallConfirmDialog used in ModCard)
vi.mock('@/hooks/use-mods', async () => {
  const actual = await vi.importActual('@/hooks/use-mods');
  return {
    ...actual,
    useInstallMod: vi.fn(() => ({
      mutate: vi.fn(),
      isPending: false,
      isError: false,
      error: null,
      isSuccess: false,
      isIdle: true,
      data: undefined,
      variables: undefined,
      reset: vi.fn(),
      status: 'idle',
      mutateAsync: vi.fn(),
      context: undefined,
      failureCount: 0,
      failureReason: null,
      submittedAt: 0,
      isPaused: false,
    })),
  };
});

// Mock useModDetail hook (needed by ModCard for lazy loading compatibility)
vi.mock('@/hooks/use-mod-detail', async () => {
  const actual = await vi.importActual('@/hooks/use-mod-detail');
  return {
    ...actual,
    useModDetail: vi.fn(() => ({
      data: undefined,
      isLoading: false,
      isError: false,
      error: null,
      isSuccess: false,
      isFetching: false,
      isRefetching: false,
      isPending: false,
      isLoadingError: false,
      isRefetchError: false,
      status: 'success',
      fetchStatus: 'idle',
      refetch: vi.fn(),
      dataUpdatedAt: 0,
      errorUpdateCount: 0,
      errorUpdatedAt: 0,
      failureCount: 0,
      failureReason: null,
    })),
  };
});

// Mock mod data for testing
const mockMods: ModBrowseItem[] = [
  {
    slug: 'carrycapacity',
    assetId: 12345,
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
    assetId: 23456,
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
    assetId: 34567,
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
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('loading state', () => {
    it('renders skeleton cards when loading', () => {
      render(<ModBrowseGrid mods={[]} isLoading={true} />, { wrapper: createWrapper() });

      const grid = screen.getByTestId('mod-browse-grid-loading');
      expect(grid).toBeInTheDocument();

      const skeletons = screen.getAllByTestId('mod-card-skeleton');
      expect(skeletons.length).toBe(8);
    });

    it('does not render actual mods when loading', () => {
      render(<ModBrowseGrid mods={mockMods} isLoading={true} />, { wrapper: createWrapper() });

      expect(screen.queryByTestId('mod-card-carrycapacity')).not.toBeInTheDocument();
    });
  });

  describe('empty state', () => {
    it('renders empty message when no mods', () => {
      render(<ModBrowseGrid mods={[]} isLoading={false} />, { wrapper: createWrapper() });

      const empty = screen.getByTestId('mod-browse-grid-empty');
      expect(empty).toBeInTheDocument();
      expect(empty).toHaveTextContent('No mods found matching your criteria');
    });

    it('renders empty message for empty array explicitly', () => {
      render(<ModBrowseGrid mods={[]} />, { wrapper: createWrapper() });

      expect(screen.getByTestId('mod-browse-grid-empty')).toBeInTheDocument();
    });
  });

  describe('with mods', () => {
    it('renders grid with mod cards', () => {
      render(<ModBrowseGrid mods={mockMods} isLoading={false} />, { wrapper: createWrapper() });

      const grid = screen.getByTestId('mod-browse-grid');
      expect(grid).toBeInTheDocument();

      // Check that all three mods are rendered
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-primitivesurvival')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-wildcraft')).toBeInTheDocument();
    });

    it('defaults isLoading to false', () => {
      render(<ModBrowseGrid mods={mockMods} />, { wrapper: createWrapper() });

      // Should render actual grid, not loading state
      expect(screen.getByTestId('mod-browse-grid')).toBeInTheDocument();
      expect(screen.queryByTestId('mod-browse-grid-loading')).not.toBeInTheDocument();
    });

    it('renders correct number of mod cards', () => {
      render(<ModBrowseGrid mods={mockMods} />, { wrapper: createWrapper() });

      const grid = screen.getByTestId('mod-browse-grid');
      // Each mod should have a card
      expect(grid.children.length).toBe(3);
    });
  });

  describe('with single mod', () => {
    it('renders grid with one mod card', () => {
      render(<ModBrowseGrid mods={[mockMods[0]]} />, { wrapper: createWrapper() });

      const grid = screen.getByTestId('mod-browse-grid');
      expect(grid).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-carrycapacity')).toBeInTheDocument();
      expect(grid.children.length).toBe(1);
    });
  });

  describe('onModClick handler', () => {
    it('calls onModClick with slug when card is clicked', async () => {
      const user = userEvent.setup();
      const handleModClick = vi.fn();

      render(<ModBrowseGrid mods={mockMods} onModClick={handleModClick} />, { wrapper: createWrapper() });

      const card = screen.getByTestId('mod-card-carrycapacity');
      await user.click(card);

      expect(handleModClick).toHaveBeenCalledTimes(1);
      expect(handleModClick).toHaveBeenCalledWith('carrycapacity');
    });

    it('calls onModClick with correct slug for each card', async () => {
      const user = userEvent.setup();
      const handleModClick = vi.fn();

      render(<ModBrowseGrid mods={mockMods} onModClick={handleModClick} />, { wrapper: createWrapper() });

      // Click second card
      const secondCard = screen.getByTestId('mod-card-primitivesurvival');
      await user.click(secondCard);

      expect(handleModClick).toHaveBeenCalledWith('primitivesurvival');
    });

    it('does not provide onClick to cards when onModClick is not provided', () => {
      render(<ModBrowseGrid mods={mockMods} />, { wrapper: createWrapper() });

      // Cards should exist but not have cursor-pointer styling
      const card = screen.getByTestId('mod-card-carrycapacity');
      expect(card.className).not.toContain('cursor-pointer');
    });

    it('provides onClick to cards when onModClick is provided', () => {
      const handleModClick = vi.fn();
      render(<ModBrowseGrid mods={mockMods} onModClick={handleModClick} />, { wrapper: createWrapper() });

      // Cards should have cursor-pointer styling when clickable
      const card = screen.getByTestId('mod-card-carrycapacity');
      expect(card.className).toContain('cursor-pointer');
    });
  });

  describe('installedSlugs prop (F8)', () => {
    it('passes installedSlugs to ModCard components', () => {
      const installedSlugs = new Set(['carrycapacity', 'wildcraft']);

      render(<ModBrowseGrid mods={mockMods} installedSlugs={installedSlugs} />, { wrapper: createWrapper() });

      // Installed mods should show "Installed" indicator
      expect(screen.getByTestId('mod-card-installed-carrycapacity')).toBeInTheDocument();
      expect(screen.getByTestId('mod-card-installed-wildcraft')).toBeInTheDocument();

      // Non-installed mod should show Install button
      expect(screen.getByTestId('mod-card-install-primitivesurvival')).toBeInTheDocument();
    });

    it('does not pass installedSlugs when not provided', () => {
      render(<ModBrowseGrid mods={mockMods} />, { wrapper: createWrapper() });

      // No install buttons or installed indicators should be visible
      expect(screen.queryByTestId('mod-card-install-carrycapacity')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-card-installed-carrycapacity')).not.toBeInTheDocument();
    });
  });

  describe('lazy loading integration (F10)', () => {
    it('triggers useModDetail when install button is clicked on card in grid', async () => {
      const user = userEvent.setup();
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return compatible data after click
      vi.mocked(useModDetail.useModDetail).mockReturnValue({
        data: {
          status: 'ok',
          data: {
            slug: 'carrycapacity',
            name: 'Carry Capacity',
            author: 'copygirl',
            description: 'Test description',
            latestVersion: '1.5.0',
            downloads: 50000,
            follows: 500,
            side: 'Both',
            compatibility: {
              status: 'compatible',
              gameVersion: '1.21.6',
              modVersion: '1.5.0',
              message: '',
            },
            logoUrl: null,
            releases: [],
            tags: [],
            homepageUrl: null,
            sourceUrl: null,
            created: null,
            lastReleased: null,
          },
        },
        isLoading: false,
        isError: false,
        error: null,
        isSuccess: true,
        isFetching: false,
        isRefetching: false,
        isPending: false,
        isLoadingError: false,
        isRefetchError: false,
        isPlaceholderData: false,
        isFetched: true,
        isFetchedAfterMount: true,
        isInitialLoading: false,
        isStale: false,
        status: 'success',
        fetchStatus: 'idle',
        refetch: vi.fn(),
        dataUpdatedAt: Date.now(),
        errorUpdateCount: 0,
        errorUpdatedAt: 0,
        failureCount: 0,
        failureReason: null,
        promise: Promise.resolve({} as never),
        isPaused: false,
        isEnabled: true,
      } as unknown as ReturnType<typeof useModDetail.useModDetail>);

      render(<ModBrowseGrid mods={mockMods} installedSlugs={installedSlugs} />, { wrapper: createWrapper() });

      // Click install on first card
      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should open with fetched compatibility
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      // Compatible mods should not show warning
      expect(screen.queryByTestId('install-dialog-warning')).not.toBeInTheDocument();
    });
  });

  describe('error handling (F12)', () => {
    it('handles useModDetail error gracefully in grid context', async () => {
      const user = userEvent.setup();
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return error state
      vi.mocked(useModDetail.useModDetail).mockReturnValue({
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error('Network failure'),
        isSuccess: false,
        isFetching: false,
        isRefetching: false,
        isPending: false,
        isLoadingError: true,
        isRefetchError: false,
        isPlaceholderData: false,
        isFetched: true,
        isFetchedAfterMount: true,
        isInitialLoading: false,
        isStale: false,
        status: 'error',
        fetchStatus: 'idle',
        refetch: vi.fn(),
        dataUpdatedAt: 0,
        errorUpdateCount: 1,
        errorUpdatedAt: Date.now(),
        failureCount: 1,
        failureReason: new Error('Network failure'),
        promise: Promise.resolve({} as never),
        isPaused: false,
        isEnabled: true,
      } as unknown as ReturnType<typeof useModDetail.useModDetail>);

      render(<ModBrowseGrid mods={mockMods} installedSlugs={installedSlugs} />, { wrapper: createWrapper() });

      // Click install button
      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should still open with fallback compatibility
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      // Should show not_verified warning as fallback
      expect(screen.getByTestId('install-dialog-warning')).toBeInTheDocument();
    });
  });
});
