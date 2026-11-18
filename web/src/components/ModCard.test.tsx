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
  modIds: ['carrycapacity'],
  urlalias: 'carrycapacity',
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
  hasReleaseForGameVersion: null,
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
    it('renders the mod name', () => {
      render(<ModCard mod={mockMod} />);

      const nameSpan = screen.getByTestId('mod-card-name-carrycapacity');
      expect(nameSpan).toBeInTheDocument();
      expect(nameSpan).toHaveTextContent('Carry Capacity');
      // Without onClick, should NOT have cursor-pointer or button role
      expect(nameSpan.className).not.toContain('cursor-pointer');
      expect(nameSpan).not.toHaveAttribute('role');
    });

    it('renders the mod name as interactive when onClick provided', () => {
      const handleClick = vi.fn();
      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const nameSpan = screen.getByTestId('mod-card-name-carrycapacity');
      expect(nameSpan).toBeInTheDocument();
      expect(nameSpan.className).toContain('cursor-pointer');
      expect(nameSpan).toHaveAttribute('role', 'button');
      expect(nameSpan).toHaveAttribute('tabIndex', '0');
    });

    it('renders external link icon separately from mod name', () => {
      render(<ModCard mod={mockMod} />);

      const link = screen.getByTestId('mod-card-link-carrycapacity');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://mods.vintagestory.at/show/mod/12345');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
      expect(link).toHaveAttribute('title', 'Open on ModDB');
      expect(link).toHaveAttribute(
        'aria-label',
        'Open Carry Capacity on ModDB (opens in a new tab)'
      );
      // Link should NOT contain the mod name text (it's just the icon)
      expect(link).not.toHaveTextContent('Carry Capacity');
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

    // VSS-qal: SideBadge integration test
    it('renders SideBadge with correct side value', () => {
      render(<ModCard mod={mockMod} />);

      const sideContainer = screen.getByTestId('mod-card-side-carrycapacity');
      expect(sideContainer).toBeInTheDocument();
      // mockMod has side: 'both', so both badges should show
      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
    });

    it('renders SideBadge for client-only mod', () => {
      const clientOnlyMod = { ...mockMod, side: 'client' as const };
      render(<ModCard mod={clientOnlyMod} />);

      expect(screen.getByTestId('side-badge-client')).toBeInTheDocument();
      expect(screen.queryByTestId('side-badge-server')).not.toBeInTheDocument();
    });

    it('renders SideBadge for server-only mod', () => {
      const serverOnlyMod = { ...mockMod, side: 'server' as const };
      render(<ModCard mod={serverOnlyMod} />);

      expect(screen.queryByTestId('side-badge-client')).not.toBeInTheDocument();
      expect(screen.getByTestId('side-badge-server')).toBeInTheDocument();
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
      // Story 19.6: the CDN gets no Referer
      expect(image).toHaveAttribute('referrerpolicy', 'no-referrer');
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

    it('calls onClick handler when mod name is clicked (navigates to detail)', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const nameSpan = screen.getByTestId('mod-card-name-carrycapacity');
      await user.click(nameSpan);

      // Clicking mod name should bubble up and trigger card onClick
      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('calls onClick when Enter key is pressed on mod name', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const nameSpan = screen.getByTestId('mod-card-name-carrycapacity');
      nameSpan.focus();
      await user.keyboard('{Enter}');

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('calls onClick when Space key is pressed on mod name', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();

      render(<ModCard mod={mockMod} onClick={handleClick} />);

      const nameSpan = screen.getByTestId('mod-card-name-carrycapacity');
      nameSpan.focus();
      await user.keyboard(' ');

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('does nothing when mod name clicked and onClick is undefined', async () => {
      const user = userEvent.setup();

      // Render without onClick handler
      render(<ModCard mod={mockMod} />);

      const nameSpan = screen.getByTestId('mod-card-name-carrycapacity');

      // Should not throw when clicked
      await user.click(nameSpan);

      // Name span should not have button role when onClick is undefined
      expect(nameSpan).not.toHaveAttribute('role');
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

    it('does not show install button when installedMods is not provided', () => {
      render(<ModCard mod={mockMod} />, { wrapper: createWrapper() });

      expect(screen.queryByTestId('mod-card-install-carrycapacity')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-card-installed-carrycapacity')).not.toBeInTheDocument();
    });

    describe('an entry with several mod IDs (Story 17.4)', () => {
      const instrumentsMod: ModBrowseItem = {
        ...mockMod,
        slug: 'instruments',
        modIds: ['instruments', 'vsinstruments', 'vsinstrumentsbase'],
        name: 'Instruments',
      };

      it('shows Installed when a mod ID other than the first is installed', () => {
        render(<ModCard mod={instrumentsMod} installedMods={[{ slug: 'vsinstrumentsbase' }]} />, {
          wrapper: createWrapper(),
        });

        expect(screen.getByTestId('mod-card-installed-instruments')).toHaveTextContent('Installed');
        expect(screen.queryByTestId('mod-card-install-instruments')).not.toBeInTheDocument();
      });

      it('shows Installed when the installed mod ID differs only in case', () => {
        render(<ModCard mod={instrumentsMod} installedMods={[{ slug: 'VSInstrumentsBase' }]} />, {
          wrapper: createWrapper(),
        });

        expect(screen.getByTestId('mod-card-installed-instruments')).toBeInTheDocument();
        expect(screen.queryByTestId('mod-card-install-instruments')).not.toBeInTheDocument();
      });

      it('shows the Install button when only another entry is installed', () => {
        render(<ModCard mod={instrumentsMod} installedMods={[{ slug: 'smithingplus' }]} />, {
          wrapper: createWrapper(),
        });

        expect(screen.getByTestId('mod-card-install-instruments')).toBeInTheDocument();
        expect(screen.queryByTestId('mod-card-installed-instruments')).not.toBeInTheDocument();
      });

      it('shows the Install button when nothing is installed', () => {
        render(<ModCard mod={instrumentsMod} installedMods={[]} />, {
          wrapper: createWrapper(),
        });

        expect(screen.getByTestId('mod-card-install-instruments')).toBeInTheDocument();
        expect(screen.queryByTestId('mod-card-installed-instruments')).not.toBeInTheDocument();
      });
    });

    it('shows Install button when mod is not installed', () => {
      const installedMods: { slug: string }[] = [];

      render(<ModCard mod={mockMod} installedMods={installedMods} />, { wrapper: createWrapper() });

      const installButton = screen.getByTestId('mod-card-install-carrycapacity');
      expect(installButton).toBeInTheDocument();
      expect(installButton).toHaveTextContent('Install');
    });

    it('shows Installed indicator when mod is already installed', () => {
      const installedMods = [{ slug: 'carrycapacity' }];

      render(<ModCard mod={mockMod} installedMods={installedMods} />, { wrapper: createWrapper() });

      const indicator = screen.getByTestId('mod-card-installed-carrycapacity');
      expect(indicator).toBeInTheDocument();
      expect(indicator).toHaveTextContent('Installed');
      expect(screen.queryByTestId('mod-card-install-carrycapacity')).not.toBeInTheDocument();
    });

    it('opens confirmation dialog when Install button is clicked', async () => {
      const user = userEvent.setup();
      const installedMods: { slug: string }[] = [];

      // Mock useModDetail to return mod data (simulating successful fetch)
      vi.mocked(useModDetail.useModDetail).mockReturnValue(
        createQueryResultMock({
          data: {
            status: 'ok',
            data: {
              slug: 'carrycapacity',
              name: 'Carry Capacity',
              author: 'copygirl',
              description: 'Test description',
              latestVersion: '1.5.0',
              installModId: 'carrycapacity',
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
        })
      );

      render(<ModCard mod={mockMod} installedMods={installedMods} />, { wrapper: createWrapper() });

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should open
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      expect(screen.getByTestId('install-dialog-mod-name')).toHaveTextContent('Carry Capacity');
    });

    it('does not trigger card onClick when Install button is clicked', async () => {
      const user = userEvent.setup();
      const handleClick = vi.fn();
      const installedMods: { slug: string }[] = [];

      // Mock useModDetail to return mod data
      vi.mocked(useModDetail.useModDetail).mockReturnValue(
        createQueryResultMock({
          data: {
            status: 'ok',
            data: {
              slug: 'carrycapacity',
              name: 'Carry Capacity',
              author: 'copygirl',
              description: 'Test description',
              latestVersion: '1.5.0',
              installModId: 'carrycapacity',
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
        })
      );

      render(<ModCard mod={mockMod} onClick={handleClick} installedMods={installedMods} />, {
        wrapper: createWrapper(),
      });

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Card onClick should NOT be called
      expect(handleClick).not.toHaveBeenCalled();
    });

    it('shows loading state when Install button is clicked', async () => {
      const installedMods: { slug: string }[] = [];

      // Mock useModDetail to return loading state
      vi.mocked(useModDetail.useModDetail).mockReturnValue(
        createQueryResultMock({
          isLoading: true,
        })
      );

      render(<ModCard mod={mockMod} installedMods={installedMods} />, { wrapper: createWrapper() });

      const installButton = screen.getByTestId('mod-card-install-carrycapacity');

      // Button should show loading state
      expect(installButton).toBeDisabled();
      expect(installButton).toHaveTextContent('Loading...');
    });

    it('opens dialog with compatible status after fetch completes', async () => {
      const user = userEvent.setup();
      const installedMods: { slug: string }[] = [];

      // Mock useModDetail to return compatible mod
      vi.mocked(useModDetail.useModDetail).mockReturnValue(
        createQueryResultMock({
          data: {
            status: 'ok',
            data: {
              slug: 'carrycapacity',
              name: 'Carry Capacity',
              author: 'copygirl',
              description: 'Test description',
              latestVersion: '1.5.0',
              installModId: 'carrycapacity',
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
        })
      );

      render(<ModCard mod={mockMod} installedMods={installedMods} />, { wrapper: createWrapper() });

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should open with compatible status
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      // Should not show warning for compatible mods
      expect(screen.queryByTestId('install-dialog-warning')).not.toBeInTheDocument();
    });

    it('falls back to not_verified when fetch fails', async () => {
      const user = userEvent.setup();
      const installedMods: { slug: string }[] = [];

      // Mock useModDetail to return error state
      vi.mocked(useModDetail.useModDetail).mockReturnValue(
        createQueryResultMock({
          isError: true,
          error: new Error('Network error'),
        })
      );

      render(<ModCard mod={mockMod} installedMods={installedMods} />, { wrapper: createWrapper() });

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should open with not_verified fallback
      expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
      // Should show warning for not_verified
      expect(screen.getByTestId('install-dialog-warning')).toBeInTheDocument();
    });

    it('shows the version a plain install picks, from the fetched details', async () => {
      const user = userEvent.setup();
      const installedMods: { slug: string }[] = [];

      // Mock useModDetail to return mod with specific version
      vi.mocked(useModDetail.useModDetail).mockReturnValue(
        createQueryResultMock({
          data: {
            status: 'ok',
            data: {
              slug: 'carrycapacity',
              name: 'Carry Capacity',
              author: 'copygirl',
              description: 'Test description',
              latestVersion: '2.3.4',
              installModId: 'carrycapacity',
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
        })
      );

      render(<ModCard mod={mockMod} installedMods={installedMods} />, { wrapper: createWrapper() });

      await user.click(screen.getByTestId('mod-card-install-carrycapacity'));

      // Dialog should show fetched version
      expect(screen.getByTestId('install-dialog-mod-version')).toHaveTextContent('Version: 2.3.4');
    });

    describe('Story 17.2: the install request follows the lookup', () => {
      it('installs the install mod ID at the lookup latest version', async () => {
        const user = userEvent.setup();
        vi.mocked(useModDetail.useModDetail).mockReturnValue(
          createQueryResultMock({
            data: {
              status: 'ok',
              data: {
                slug: 'carrycapacity',
                name: 'Carry Capacity',
                author: 'copygirl',
                description: null,
                latestVersion: '1.4.0',
                installModId: 'carrycapacityplus',
                downloads: 1,
                follows: 0,
                side: 'Both',
                compatibility: {
                  status: 'compatible',
                  gameVersion: '1.21.6',
                  modVersion: '1.4.0',
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
          })
        );

        render(<ModCard mod={mockMod} installedMods={[]} />, {
          wrapper: createWrapper(),
        });
        await user.click(screen.getByTestId('mod-card-install-carrycapacity'));
        expect(screen.getByTestId('install-dialog-mod-version')).toHaveTextContent(
          'Version: 1.4.0'
        );
        await user.click(screen.getByTestId('install-dialog-confirm'));

        expect(mockMutate).toHaveBeenCalledWith(
          { slug: 'carrycapacityplus', version: '1.4.0' },
          expect.anything()
        );
      });

      it('sends the card slug when the lookup has an empty install mod ID', async () => {
        const user = userEvent.setup();
        vi.mocked(useModDetail.useModDetail).mockReturnValue(
          createQueryResultMock({
            data: {
              status: 'ok',
              data: {
                slug: 'carrycapacity',
                name: 'Carry Capacity',
                author: 'copygirl',
                description: null,
                latestVersion: null,
                installModId: '',
                downloads: 1,
                follows: 0,
                side: 'Both',
                compatibility: {
                  status: 'not_verified',
                  gameVersion: '1.21.6',
                  modVersion: 'unknown',
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
          })
        );

        render(<ModCard mod={mockMod} installedMods={[]} />, {
          wrapper: createWrapper(),
        });
        await user.click(screen.getByTestId('mod-card-install-carrycapacity'));
        await user.click(screen.getByTestId('install-dialog-confirm'));

        expect(mockMutate).toHaveBeenCalledWith(
          { slug: 'carrycapacity', version: undefined },
          expect.anything()
        );
      });

      it('sends the card slug and no version when the details fail', async () => {
        const user = userEvent.setup();
        vi.mocked(useModDetail.useModDetail).mockReturnValue(
          createQueryResultMock({
            isError: true,
            error: new Error('Network error'),
          })
        );

        render(<ModCard mod={mockMod} installedMods={[]} />, {
          wrapper: createWrapper(),
        });
        await user.click(screen.getByTestId('mod-card-install-carrycapacity'));
        expect(screen.getByTestId('install-dialog-mod-version')).toHaveTextContent(
          'Version: Latest'
        );
        await user.click(screen.getByTestId('install-dialog-confirm'));

        expect(mockMutate).toHaveBeenCalledWith(
          { slug: 'carrycapacity', version: undefined },
          expect.anything()
        );
      });
    });
  });

  describe('game version indicator (Story 18.3)', () => {
    const hasRelease: ModBrowseItem = { ...mockMod, hasReleaseForGameVersion: true };
    const noRelease: ModBrowseItem = { ...mockMod, hasReleaseForGameVersion: false };

    it('shows a badge when the entry has a release for the game version', () => {
      render(<ModCard mod={hasRelease} gameVersion="1.22.7" />);

      const indicator = screen.getByTestId('mod-card-game-version-carrycapacity');
      expect(indicator).toHaveTextContent('Has a release for 1.22.7');
      expect(indicator).toHaveAttribute('data-has-release', 'true');
      expect(screen.getByTestId('mod-card-carrycapacity')).not.toHaveTextContent(/compatible/i);
    });

    it('shows muted text when the entry has no release for the game version', () => {
      render(<ModCard mod={noRelease} gameVersion="1.22.7" />);

      const indicator = screen.getByTestId('mod-card-game-version-carrycapacity');
      expect(indicator).toHaveTextContent('No release for 1.22.7');
      expect(indicator).toHaveAttribute('data-has-release', 'false');
      expect(screen.getByTestId('mod-card-carrycapacity')).not.toHaveTextContent(/compatible/i);
    });

    it('shows nothing when the flag is not known', () => {
      render(<ModCard mod={mockMod} gameVersion="1.22.7" />);

      expect(screen.queryByTestId('mod-card-game-version-carrycapacity')).not.toBeInTheDocument();
    });

    it('shows nothing when the game version is null or not passed', () => {
      const { unmount } = render(<ModCard mod={hasRelease} gameVersion={null} />);
      expect(screen.queryByTestId('mod-card-game-version-carrycapacity')).not.toBeInTheDocument();
      unmount();

      render(<ModCard mod={hasRelease} />);
      expect(screen.queryByTestId('mod-card-game-version-carrycapacity')).not.toBeInTheDocument();
    });

    it('shows the indicator beside the install footer', () => {
      render(<ModCard mod={hasRelease} gameVersion="1.22.7" installedMods={[]} />, {
        wrapper: createWrapper(),
      });

      expect(screen.getByTestId('mod-card-game-version-carrycapacity')).toHaveTextContent(
        'Has a release for 1.22.7'
      );
      expect(screen.getByTestId('mod-card-install-carrycapacity')).toBeInTheDocument();
    });
  });
});
