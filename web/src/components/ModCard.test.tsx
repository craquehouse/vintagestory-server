import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ModCard } from './ModCard';
import { formatNumber } from '@/lib/utils';
import * as useMods from '@/hooks/use-mods';
import * as useModDetail from '@/hooks/use-mod-detail';
import type { ModBrowseItem } from '@/api/types';

// Mock useInstallMod hook - return default mock for all tests
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

// Helper to create a complete UseQueryResult mock
function createQueryResultMock<T>(overrides: {
  data?: T;
  isLoading?: boolean;
  isError?: boolean;
  error?: Error | null;
  isSuccess?: boolean;
}) {
  const isLoading = overrides.isLoading ?? false;
  const isError = overrides.isError ?? false;
  const isSuccess = overrides.isSuccess ?? false;
  return {
    data: overrides.data,
    isLoading,
    isError,
    error: overrides.error ?? null,
    isSuccess,
    refetch: vi.fn(),
    isFetching: isLoading,
    isRefetching: false,
    isPending: isLoading && !overrides.data,
    isLoadingError: isError && isLoading,
    isRefetchError: false,
    isPlaceholderData: false,
    isFetched: isSuccess || isError,
    isFetchedAfterMount: isSuccess || isError,
    isInitialLoading: isLoading && !overrides.data,
    isStale: false,
    dataUpdatedAt: Date.now(),
    errorUpdatedAt: isError ? Date.now() : 0,
    failureCount: isError ? 1 : 0,
    failureReason: overrides.error ?? null,
    fetchStatus: isLoading ? 'fetching' : 'idle',
    status: isSuccess ? 'success' : isError ? 'error' : isLoading ? 'pending' : 'pending',
    errorUpdateCount: isError ? 1 : 0,
    promise: Promise.resolve(overrides.data),
    isPaused: false,
    isEnabled: true,
  } as ReturnType<typeof useModDetail.useModDetail>;
}

// Mock useModDetail hook - return default mock for all tests
vi.mock('@/hooks/use-mod-detail', () => ({
  useModDetail: vi.fn(() => createQueryResultMock({})),
}));

// Helper to create a QueryClient wrapper
function createWrapper() {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
  );
}

// Mock mod data for testing
const mockMod: ModBrowseItem = {
  slug: 'carrycapacity',
  assetId: 12345,
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
      expect(link).toHaveAttribute('href', 'https://mods.vintagestory.at/show/mod/12345');
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

  describe('install button (Story 10.8)', () => {
    const mockMutate = vi.fn();

    beforeEach(() => {
      vi.clearAllMocks();
      vi.mocked(useMods.useInstallMod).mockReturnValue({
        mutate: mockMutate,
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
      });
      // Default mock for useModDetail - not loading, no data
      vi.mocked(useModDetail.useModDetail).mockReturnValue(createQueryResultMock({}));
    });

    it('does not show install button when installedSlugs is not provided', () => {
      render(<ModCard mod={mockMod} />, { wrapper: createWrapper() });

      expect(screen.queryByTestId('mod-card-install-carrycapacity')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-card-installed-carrycapacity')).not.toBeInTheDocument();
    });

    it('shows Install button when mod is not installed', () => {
      const installedSlugs = new Set<string>();

      render(
        <ModCard mod={mockMod} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      const installButton = screen.getByTestId('mod-card-install-carrycapacity');
      expect(installButton).toBeInTheDocument();
      expect(installButton).toHaveTextContent('Install');
    });

    it('shows Installed indicator when mod is already installed', () => {
      const installedSlugs = new Set(['carrycapacity']);

      render(
        <ModCard mod={mockMod} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      const indicator = screen.getByTestId('mod-card-installed-carrycapacity');
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveTextContent('Installed');
      expect(screen.queryByTestId('mod-card-install-carrycapacity')).not.toBeInTheDocument();
    });

    it('opens confirmation dialog when Install button is clicked', async () => {
      const user = userEvent.setup();
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return mod data (simulating successful fetch)
      vi.mocked(useModDetail.useModDetail).mockReturnValue(createQueryResultMock({
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
              status: 'not_verified',
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
        isSuccess: true,
      }));

      render(
        <ModCard mod={mockMod} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should open
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      expect(screen.getByTestId('install-dialog-mod-name')).toHaveTextContent('Carry Capacity');
    });

    it('does not trigger card onClick when Install button is clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return mod data
      vi.mocked(useModDetail.useModDetail).mockReturnValue(createQueryResultMock({
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
              status: 'not_verified',
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
        isSuccess: true,
      }));

      render(
        <ModCard mod={mockMod} onClick={handleClick} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Card onClick should NOT be called
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('shows loading state when Install button is clicked', async () => {
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return loading state
      vi.mocked(useModDetail.useModDetail).mockReturnValue(createQueryResultMock({
        isLoading: true,
      }));

      render(
        <ModCard mod={mockMod} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      const installButton = screen.getByTestId('mod-card-install-carrycapacity');

      // Button should show loading state
      expect(installButton).toBeDisabled();
      expect(installButton).toHaveTextContent('Loading...');
    });

    it('opens dialog with compatible status after fetch completes', async () => {
      const user = userEvent.setup();
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return compatible mod
      vi.mocked(useModDetail.useModDetail).mockReturnValue(createQueryResultMock({
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
        isSuccess: true,
      }));

      render(
        <ModCard mod={mockMod} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should open with compatible status
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      // Should not show warning for compatible mods
      expect(screen.queryByTestId('install-dialog-warning')).not.toBeInTheDocument();
    });

    it('falls back to not_verified when fetch fails', async () => {
      const user = userEvent.setup();
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return error state
      vi.mocked(useModDetail.useModDetail).mockReturnValue(createQueryResultMock({
        isError: true,
        error: new Error('Network error'),
      }));

      render(
        <ModCard mod={mockMod} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should open with not_verified fallback
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      // Should show warning for not_verified
      expect(screen.getByTestId('install-dialog-warning')).toBeInTheDocument();
    });

    it('uses fetched version instead of LATEST_VERSION', async () => {
      const user = userEvent.setup();
      const installedSlugs = new Set<string>();

      // Mock useModDetail to return mod with specific version
      vi.mocked(useModDetail.useModDetail).mockReturnValue(createQueryResultMock({
        data: {
          status: 'ok',
          data: {
            slug: 'carrycapacity',
            name: 'Carry Capacity',
            author: 'copygirl',
            description: 'Test description',
            latestVersion: '2.3.4',
            downloads: 50000,
            follows: 500,
            side: 'Both',
            compatibility: {
              status: 'not_verified',
              gameVersion: '1.21.6',
              modVersion: '2.3.4',
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
        isSuccess: true,
      }));

      render(
        <ModCard mod={mockMod} installedSlugs={installedSlugs} />,
        { wrapper: createWrapper() }
      );

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should show fetched version
      expect(screen.getByTestId('install-dialog-mod-version')).toHaveTextContent('Version: 2.3.4');
    });

  });
});
