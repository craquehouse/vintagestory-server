/**
 * Tests for ModDetailPage component.
 *
 * Story 10.6: Verifies mod detail view renders correctly with
 * sanitized HTML description, releases list, and all metadata.
 * Story 11.4: Updated to /game-server/mods paths.
 */

import { describe, it, expect, vi, beforeAll, beforeEach, afterEach } from 'vitest';
import { render, screen, within, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Routes, Route, useLocation, type InitialEntry } from 'react-router';
import { ModDetailPage } from './ModDetailPage';

// Create a fresh QueryClient for each test
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });
}

/** Story 16.1: Shows where a link back into the browser landed, and with which state. */
function BrowseLanding() {
  const location = useLocation();
  const state = location.state as { fromModDetail?: unknown } | null;
  return (
    <div>
      Browse Page
      <span data-testid="landing-search">{location.search}</span>
      <span data-testid="landing-from-detail">{String(state?.fromModDetail === true)}</span>
    </div>
  );
}

/** Story 16.1: A browse state with search, sort, filters, game version and page. */
const BROWSE_SEARCH =
  '?q=smithing&sort=downloads&side=both&tags=Crafting&type=mod&version=1.21.2&page=2';

// Wrapper to provide QueryClient and Router context - Story 11.4: Uses /game-server/mods paths
function renderWithProviders(
  ui: React.ReactElement,
  { route = '/game-server/mods/browse/testmod' }: { route?: InitialEntry } = {}
) {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/game-server/mods" element={<div>Mods Page</div>} />
          <Route path="/game-server/mods/browse" element={<BrowseLanding />} />
          <Route path="/game-server/mods/browse/:slug" element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

// Mock mod detail response with all fields
const mockModDetailResponse = {
  status: 'ok',
  data: {
    slug: 'smithingplus',
    asset_id: 15312,
    name: 'Smithing Plus',
    author: 'jayu',
    description: '<p>Enhanced smithing mechanics with <strong>bold text</strong></p>',
    latest_version: '1.8.3',
    install_mod_id: 'smithingplus',
    downloads: 204656,
    follows: 2348,
    side: 'Both',
    compatibility: {
      status: 'compatible',
      game_version: '1.21.3',
      mod_version: '1.8.3',
      message: 'Compatible with current server version',
    },
    logo_url: 'https://moddbcdn.vintagestory.at/logo.png',
    releases: [
      {
        version: '1.8.3',
        filename: 'smithingplus_1.8.3.zip',
        file_id: 59176,
        modidstr: 'smithingplus',
        downloads: 49726,
        game_versions: ['1.21.0', '1.21.1', '1.21.2', '1.21.3'],
        created: '2025-10-09 21:28:57',
        changelog: '<ul><li>Bug fixes</li></ul>',
      },
      {
        version: '1.8.2',
        filename: 'smithingplus_1.8.2.zip',
        file_id: 57894,
        modidstr: 'smithingplus',
        downloads: 31245,
        game_versions: ['1.21.0', '1.21.1'],
        created: '2025-09-15 14:22:11',
        changelog: null,
      },
    ],
    tags: ['Crafting', 'QoL', 'Utility'],
    homepage_url: 'https://example.com/smithingplus',
    source_url: 'https://github.com/user/smithingplus',
    created: '2024-10-24 01:06:14',
    last_released: '2025-10-09 21:28:57',
  },
};

// Minimal mock response for basic tests
const mockMinimalResponse = {
  status: 'ok',
  data: {
    slug: 'simplemod',
    asset_id: 99999,
    name: 'Simple Mod',
    author: 'author1',
    description: null,
    latest_version: '1.0.0',
    install_mod_id: 'simplemod',
    downloads: 100,
    follows: 10,
    side: 'Server',
    compatibility: {
      status: 'not_verified',
      game_version: '1.21.3',
      mod_version: '1.0.0',
      message: 'Compatibility not verified',
    },
    logo_url: null,
    releases: [],
    tags: [],
    homepage_url: null,
    source_url: null,
    created: null,
    last_released: null,
  },
};

describe('ModDetailPage', () => {
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.resetAllMocks();
    import.meta.env.VITE_API_KEY = 'test-api-key';
    import.meta.env.VITE_API_BASE_URL = 'http://localhost:8080';
  });

  afterEach(() => {
    globalThis.fetch = originalFetch;
    vi.unstubAllGlobals();
  });

  /** Story 21.6: new tests stub fetch with vi.stubGlobal (project-context, Story 20.2). */
  function stubDetail(overrides: Record<string, unknown> = {}) {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: { ...mockModDetailResponse.data, ...overrides },
          }),
      })
    );
  }

  describe('loading state', () => {
    it('shows loading skeleton while fetching', () => {
      // Delay the response to keep in loading state
      globalThis.fetch = vi.fn().mockImplementation(
        () =>
          new Promise(() => {
            /* never resolves */
          })
      );

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      expect(screen.getByTestId('mod-detail-loading')).toBeInTheDocument();
    });

    it('stacks the header skeleton below md (Story 21.6)', () => {
      vi.stubGlobal(
        'fetch',
        vi.fn().mockImplementation(
          () =>
            new Promise(() => {
              /* never resolves */
            })
        )
      );

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const header = screen.getByTestId('mod-detail-loading-header');
      expect(header).toHaveClass('flex-col', 'md:flex-row');
    });
  });

  describe('error state', () => {
    it('shows error message when fetch fails', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        json: () =>
          Promise.resolve({
            detail: { code: 'MOD_NOT_FOUND', message: 'Mod not found' },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/nonexistent' });

      expect(await screen.findByTestId('mod-detail-error')).toBeInTheDocument();
      expect(screen.getByText('Failed to load mod details')).toBeInTheDocument();
    });
  });

  describe('incomplete API data (UI-063)', () => {
    it.each([
      ['an empty object', {}],
      ['missing compatibility', { ...mockMinimalResponse.data, compatibility: undefined }],
      ['missing tags', { ...mockMinimalResponse.data, tags: undefined }],
      ['missing releases', { ...mockMinimalResponse.data, releases: undefined }],
    ])('shows an error instead of crashing for %s', async (_label, data) => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve({ status: 'ok', data }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

      expect(await screen.findByTestId('mod-detail-error')).toBeInTheDocument();
      expect(screen.getByText('The server returned incomplete mod details')).toBeInTheDocument();
    });
  });

  describe('header section (Subtask 2.2)', () => {
    it('stacks the header below md and keeps one row from md up (Story 21.6)', async () => {
      stubDetail();

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const header = await screen.findByTestId('mod-detail-header');
      expect(header).toHaveClass('flex', 'flex-col', 'md:flex-row');
      const summary = screen.getByTestId('mod-detail-summary');
      expect(summary).toHaveClass('flex-wrap', 'md:flex-nowrap', 'min-w-0');
      expect(summary).toContainElement(screen.getByTestId('mod-detail-logo'));
      expect(summary).toContainElement(screen.getByTestId('mod-detail-name'));
      expect(screen.getByTestId('mod-detail-stats')).toHaveClass('flex-wrap');

      const install = screen.getByTestId('mod-detail-install-section');
      expect(header).toContainElement(install);
      expect(summary).not.toContainElement(install);
      expect(install).toHaveClass('w-full', 'md:w-64', 'md:shrink-0');
      expect(screen.getByTestId('mod-detail-version-select')).toHaveClass(
        'w-full',
        'max-lg:min-h-11'
      );
      expect(screen.getByTestId('mod-detail-install-button')).toHaveClass('max-lg:min-h-11');
    });

    it('wraps the breadcrumb and gives Back to Browse a 44px target below lg (Story 21.6)', async () => {
      stubDetail();

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const breadcrumb = await screen.findByTestId('mod-detail-breadcrumb');
      expect(breadcrumb).toHaveClass('flex-wrap', 'min-w-0');
      expect(screen.getByTestId('mod-detail-breadcrumb-name')).toHaveClass(
        'min-w-0',
        'break-words'
      );
      expect(screen.getByTestId('mod-detail-back')).toHaveClass('max-lg:min-h-11');
      expect(screen.getByTestId('mod-detail-slug')).toHaveClass('break-all');
    });

    it('renders mod name and author', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      expect(await screen.findByTestId('mod-detail-name')).toHaveTextContent('Smithing Plus');
      expect(screen.getByTestId('mod-detail-author')).toHaveTextContent('by jayu');
    });

    it('renders mod logo when available', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      await screen.findByTestId('mod-detail-page');
      const logo = screen.getByTestId('mod-detail-logo');
      const img = logo.querySelector('img');
      expect(img).toHaveAttribute('src', 'https://moddbcdn.vintagestory.at/logo.png');
      // Story 19.6: the CDN gets no Referer
      expect(img).toHaveAttribute('referrerpolicy', 'no-referrer');
    });

    it('renders placeholder when no logo', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockMinimalResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

      await screen.findByTestId('mod-detail-page');
      const logo = screen.getByTestId('mod-detail-logo');
      const img = logo.querySelector('img');
      expect(img).not.toBeInTheDocument();
    });

    it('renders stats (downloads, follows)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const stats = await screen.findByTestId('mod-detail-stats');
      // Downloads formatted as 204.7K
      expect(stats).toHaveTextContent('204.7K');
      // Follows formatted as 2.3K
      expect(stats).toHaveTextContent('2.3K');
      // VSS-qal: Side now shows as badges instead of "Side: Both" text
      expect(stats).toHaveTextContent('Client');
      expect(stats).toHaveTextContent('Server');
      expect(stats).toHaveTextContent('Version: 1.8.3');
    });

    it('renders tags as badges', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const tags = await screen.findByTestId('mod-detail-tags');
      expect(tags).toHaveTextContent('Crafting');
      expect(tags).toHaveTextContent('QoL');
      expect(tags).toHaveTextContent('Utility');
    });

    it('renders compatibility badge', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      await screen.findByTestId('mod-detail-page');
      const badge = screen.getByTestId('compatibility-badge');
      expect(badge).toHaveAttribute('data-status', 'compatible');
    });
  });

  describe('compatibility of the evaluated release (Story 16.3)', () => {
    function withCompatibility(compatibility: Record<string, unknown>, latestVersion = '1.8.3') {
      return {
        ...mockModDetailResponse,
        data: {
          ...mockModDetailResponse.data,
          latest_version: latestVersion,
          compatibility: {
            game_version: '1.22.7',
            mod_version: '1.8.3',
            latest_supported_game_version: null,
            ...compatibility,
          },
        },
      };
    }

    async function renderWith(body: unknown) {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(body),
      });
      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
      await screen.findByTestId('mod-detail-page');
    }

    it('shows the incompatible message with the last supported version', async () => {
      await renderWith(
        withCompatibility({
          status: 'incompatible',
          message: 'Last supported game version: 1.21.1.',
          latest_supported_game_version: '1.21.1',
        })
      );

      expect(screen.getByTestId('mod-detail-compatibility-message')).toHaveTextContent(
        'Last supported game version: 1.21.1.'
      );
    });

    it('shows the not verified message', async () => {
      await renderWith(
        withCompatibility({
          status: 'not_verified',
          message:
            'Mod not explicitly verified for version 1.22.7. May still work. Last tagged for 1.22.6.',
          latest_supported_game_version: '1.22.6',
        })
      );

      expect(screen.getByTestId('mod-detail-compatibility-message')).toHaveTextContent(
        'Last tagged for 1.22.6.'
      );
    });

    it('shows no message for a compatible mod', async () => {
      await renderWith(withCompatibility({ status: 'compatible', message: null }));

      expect(screen.queryByTestId('mod-detail-compatibility-message')).not.toBeInTheDocument();
    });

    it('header version is the release the badge describes, not the entry newest', async () => {
      // e.g. an installed mod ID whose newest release is older than the entry's newest
      await renderWith(
        withCompatibility(
          {
            status: 'incompatible',
            mod_version: '1.8.2',
            message: 'Last supported game version: 1.21.1.',
          },
          '1.8.3'
        )
      );

      expect(screen.getByTestId('mod-detail-stats')).toHaveTextContent('Version: 1.8.2');
    });
  });

  describe('description section (Subtask 2.3)', () => {
    it('styles the description by .mod-description alone, no prose classes (Story 21.6)', async () => {
      stubDetail({
        description: '<h2>Setup</h2><p style="color: #c33">Author colour</p>',
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const description = await screen.findByTestId('mod-detail-description');
      expect(description).toHaveClass('mod-description');
      expect(description.className).not.toMatch(/\bprose/);
      expect(description.className).not.toMatch(/\bmax-w-none\b/);
      // The author's inline style is kept, so it applies over the description rules
      expect(within(description).getByText('Author colour')).toHaveAttribute(
        'style',
        'color: #c33'
      );
    });

    it('marks description links that open in a new tab (Story 18.1, VSS-tzl)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: {
              ...mockModDetailResponse.data,
              description:
                '<p>Needs <a href="https://mods.vintagestory.at/carryonlib">CarryOn Lib</a></p>',
            },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const description = await screen.findByTestId('mod-detail-description');
      expect(description).toHaveClass('mod-description');
      // jsdom trims the note's leading space when it computes the accessible name;
      // the E2E test checks the exact name in a browser
      const link = within(description).getByRole('link', {
        name: /^CarryOn Lib ?\(opens in a new tab\)$/,
      });
      expect(link).toHaveTextContent('CarryOn Lib (opens in a new tab)', {
        normalizeWhitespace: false,
      });
    });

    it('renders sanitized HTML description', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const description = await screen.findByTestId('mod-detail-description');
      // Should contain the sanitized HTML
      expect(description.innerHTML).toContain('Enhanced smithing mechanics');
      expect(description.innerHTML).toContain('<strong>');
    });

    it('removes potentially dangerous HTML tags', async () => {
      const responseWithScript = {
        ...mockModDetailResponse,
        data: {
          ...mockModDetailResponse.data,
          description:
            '<p>Safe text</p><script>alert("xss")</script><img onerror="alert()" src="x">',
        },
      };

      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(responseWithScript),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const description = await screen.findByTestId('mod-detail-description');
      // Should not contain script tag
      expect(description.innerHTML).not.toContain('<script>');
      // Should not contain onerror attribute
      expect(description.innerHTML).not.toContain('onerror');
      // Should contain safe text
      expect(description.innerHTML).toContain('Safe text');
    });

    it('opens description links in a new tab with rel="noopener noreferrer" (Story 16.4)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: {
              ...mockModDetailResponse.data,
              description:
                '<p>Requires <a href="https://mods.vintagestory.at/commonlib" rel="noopener">CommonLib</a></p>',
            },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const description = await screen.findByTestId('mod-detail-description');
      const link = description.querySelector('a');
      expect(link).toHaveAttribute('href', 'https://mods.vintagestory.at/commonlib');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('removes style elements that would restyle the app (Story 16.4)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: {
              ...mockModDetailResponse.data,
              description: '<p>Safe text</p><style>body { display: none }</style>',
            },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const description = await screen.findByTestId('mod-detail-description');
      expect(description.querySelector('style')).toBeNull();
      expect(description).toHaveTextContent('Safe text');
    });

    it('shows no description message when null', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockMinimalResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

      expect(await screen.findByTestId('mod-detail-no-description')).toHaveTextContent(
        'No description available'
      );
    });
  });

  describe('releases section (Subtask 2.4)', () => {
    it('renders releases list with version and date', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const releasesList = await screen.findByTestId('mod-detail-releases-list');

      // Check first release
      const release1 = within(releasesList).getByTestId('mod-detail-release-1.8.3');
      expect(release1).toHaveTextContent('v1.8.3');
      expect(release1).toHaveTextContent('Oct 9, 2025');
      expect(release1).toHaveTextContent('49.7K'); // downloads formatted

      // Check second release
      const release2 = within(releasesList).getByTestId('mod-detail-release-1.8.2');
      expect(release2).toHaveTextContent('v1.8.2');
      expect(release2).toHaveTextContent('Sep 15, 2025');
    });

    it('shows "Latest" badge on newest release', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const releasesList = await screen.findByTestId('mod-detail-releases-list');
      const latestRelease = within(releasesList).getByTestId('mod-detail-release-1.8.3');
      expect(latestRelease).toHaveTextContent('Latest');

      // Second release should not have Latest badge
      const olderRelease = within(releasesList).getByTestId('mod-detail-release-1.8.2');
      expect(olderRelease).not.toHaveTextContent('Latest');
    });

    it('displays compatible game versions', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const releasesList = await screen.findByTestId('mod-detail-releases-list');
      const release1 = within(releasesList).getByTestId('mod-detail-release-1.8.3');
      // Should show compressed range for 4+ versions
      expect(release1).toHaveTextContent('Compatible: 1.21.0 - 1.21.3');
    });

    it('shows release count in header', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const releasesCard = await screen.findByTestId('mod-detail-releases-card');
      expect(releasesCard).toHaveTextContent('Releases (2)');
    });

    it('shows no releases message when empty', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockMinimalResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

      expect(await screen.findByTestId('mod-detail-no-releases')).toHaveTextContent(
        'No releases available'
      );
    });
  });

  describe('screenshots (Story 18.1)', () => {
    beforeAll(() => {
      // jsdom has no scrollIntoView; the gallery scrolls the selected thumbnail into view
      Element.prototype.scrollIntoView ??= () => {};
    });

    const screenshots = [1, 2, 3].map((n) => ({
      image_url: `https://moddbcdn.vintagestory.at/s${n}.png`,
      thumbnail_url: `https://moddbcdn.vintagestory.at/s${n}_55_60.png`,
      filename: `s${n}.png`,
    }));

    it('renders the section after the header and before the description', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: { ...mockModDetailResponse.data, screenshots },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const section = await screen.findByTestId('mod-screenshots');
      const header = screen.getByTestId('mod-detail-header');
      const description = screen.getByTestId('mod-detail-description-card');
      expect(
        header.compareDocumentPosition(section) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
      expect(
        section.compareDocumentPosition(description) & Node.DOCUMENT_POSITION_FOLLOWING
      ).toBeTruthy();
      expect(within(section).getByTestId('mod-screenshot-position')).toHaveTextContent('1 of 3');
      expect(within(section).getByTestId('mod-screenshot-image')).toHaveAttribute(
        'src',
        'https://moddbcdn.vintagestory.at/s1.png'
      );
    });

    it('renders no section for an empty list', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: { ...mockModDetailResponse.data, screenshots: [] },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      await screen.findByTestId('mod-detail-description-card');
      expect(screen.queryByTestId('mod-screenshots')).not.toBeInTheDocument();
    });

    it('renders the page without a section when the response has no list', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      await screen.findByTestId('mod-detail-description-card');
      expect(screen.queryByTestId('mod-screenshots')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-detail-error')).not.toBeInTheDocument();
    });
  });

  describe('external links', () => {
    it('renders ModDB link', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const link = await screen.findByTestId('mod-detail-moddb-link');
      expect(link).toHaveAttribute('href', 'https://mods.vintagestory.at/show/mod/15312');
      expect(link).toHaveAttribute('target', '_blank');
    });

    it('renders homepage link when available', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const link = await screen.findByTestId('mod-detail-homepage-link');
      expect(link).toHaveAttribute('href', 'https://example.com/smithingplus');
    });

    it('renders source link when available', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const link = await screen.findByTestId('mod-detail-source-link');
      expect(link).toHaveAttribute('href', 'https://github.com/user/smithingplus');
    });

    it('does not render optional links when null', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockMinimalResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

      await screen.findByTestId('mod-detail-page');
      expect(screen.queryByTestId('mod-detail-homepage-link')).not.toBeInTheDocument();
      expect(screen.queryByTestId('mod-detail-source-link')).not.toBeInTheDocument();
      // Story 19.6: null links and logo leave the placeholder and the ModDB link
      expect(screen.getByTestId('mod-detail-logo').querySelector('img')).toBeNull();
      expect(screen.getByTestId('mod-detail-moddb-link')).toBeInTheDocument();
      // Story 18.1: a response without `trailer_url` has no trailer link
      expect(screen.queryByTestId('mod-detail-trailer-link')).not.toBeInTheDocument();
    });

    it('renders the trailer link with the API URL (Story 18.1)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: {
              ...mockModDetailResponse.data,
              trailer_url: 'https://www.youtube-nocookie.com/embed/mJHZH_sThDM',
            },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const link = await screen.findByTestId('mod-detail-trailer-link');
      expect(link).toHaveAttribute('href', 'https://www.youtube-nocookie.com/embed/mJHZH_sThDM');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
      expect(screen.getByRole('link', { name: 'Watch trailer (opens in a new tab)' })).toBe(link);
      expect(document.querySelector('iframe')).toBeNull();
    });

    it('names every header link as opening in a new tab (Story 21.6)', async () => {
      stubDetail({ trailer_url: 'https://www.youtube-nocookie.com/embed/mJHZH_sThDM' });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      await screen.findByTestId('mod-detail-moddb-link');
      for (const [name, testId] of [
        ['ModDB Page', 'mod-detail-moddb-link'],
        ['Homepage', 'mod-detail-homepage-link'],
        ['Source', 'mod-detail-source-link'],
        ['Watch trailer', 'mod-detail-trailer-link'],
      ]) {
        const link = screen.getByRole('link', { name: `${name} (opens in a new tab)` });
        expect(link).toBe(screen.getByTestId(testId));
        expect(link).toHaveAttribute('target', '_blank');
        expect(link).toHaveAttribute('rel', 'noopener noreferrer');
      }
      expect(screen.getByTestId('mod-detail-homepage-link')).toContainElement(
        screen.getByTestId('mod-detail-homepage-new-tab-mark')
      );
      expect(screen.getByTestId('mod-detail-source-link')).toContainElement(
        screen.getByTestId('mod-detail-source-new-tab-mark')
      );
    });

    it('gives an SVG link in the description its new-tab title (Story 21.6)', async () => {
      stubDetail({
        description:
          '<svg><a xlink:href="https://example.com/diagram"><text>Diagram</text></a></svg>',
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const description = await screen.findByTestId('mod-detail-description');
      const link = description.querySelector('svg a');
      expect(link).toHaveAttribute('href', 'https://example.com/diagram');
      expect(link?.firstElementChild?.localName).toBe('title');
      expect(link?.firstElementChild).toHaveTextContent('Diagram (opens in a new tab)');
    });

    it('renders no trailer link when trailer_url is null (Story 18.1)', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () =>
          Promise.resolve({
            ...mockModDetailResponse,
            data: { ...mockModDetailResponse.data, trailer_url: null },
          }),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      await screen.findByTestId('mod-detail-moddb-link');
      expect(screen.queryByTestId('mod-detail-trailer-link')).not.toBeInTheDocument();
      expect(document.querySelector('iframe')).toBeNull();
    });
  });

  describe('metadata section', () => {
    it('renders created and last released dates', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      expect(await screen.findByTestId('mod-detail-created')).toHaveTextContent('Oct 24, 2024');
      expect(screen.getByTestId('mod-detail-last-released')).toHaveTextContent('Oct 9, 2025');
    });

    it('renders slug in metadata', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      expect(await screen.findByTestId('mod-detail-slug')).toHaveTextContent('smithingplus');
    });

    it('shows Unknown for null dates', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockMinimalResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

      expect(await screen.findByTestId('mod-detail-created')).toHaveTextContent('Unknown');
      expect(screen.getByTestId('mod-detail-last-released')).toHaveTextContent('Unknown');
    });
  });

  describe('route params', () => {
    it('extracts slug from URL params', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      await screen.findByTestId('mod-detail-page');

      // Verify fetch was called with correct slug
      expect(globalThis.fetch).toHaveBeenCalledWith(
        'http://localhost:8080/api/v1alpha1/mods/lookup/smithingplus',
        expect.any(Object)
      );
    });
  });

  describe('install/update section (Task 3)', () => {
    // Mock response for installed mods list
    const mockInstalledModsResponse = {
      status: 'ok',
      data: {
        mods: [
          {
            name: 'Smithing Plus',
            slug: 'smithingplus',
            version: '1.8.2',
            enabled: true,
            side: 'Both',
          },
        ],
        pending_restart: false,
      },
    };

    const mockEmptyModsResponse = {
      status: 'ok',
      data: {
        mods: [],
        pending_restart: false,
      },
    };

    // Helper to mock both mod detail and installed mods endpoints
    function mockFetchForInstallTests(
      detailResponse: typeof mockModDetailResponse | typeof mockMinimalResponse,
      modsResponse: typeof mockInstalledModsResponse | typeof mockEmptyModsResponse
    ) {
      return vi.fn().mockImplementation((url: string) => {
        if (url.includes('/api/v1alpha1/mods/lookup/')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(detailResponse),
          });
        }
        if (url.includes('/api/v1alpha1/mods')) {
          return Promise.resolve({
            ok: true,
            json: () => Promise.resolve(modsResponse),
          });
        }
        return Promise.reject(new Error(`Unexpected URL: ${url}`));
      });
    }

    describe('not installed state (AC: 2)', () => {
      it('shows install section when mod has releases', async () => {
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        expect(await screen.findByTestId('mod-detail-install-section')).toBeInTheDocument();
      });

      it('shows version dropdown with all releases', async () => {
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const versionSelect = await screen.findByTestId('mod-detail-version-select');
        expect(versionSelect).toBeInTheDocument();
        // Default selection should be latest version
        expect(versionSelect).toHaveTextContent('v1.8.3');
      });

      it('shows Install button when mod is not installed', async () => {
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        expect(installButton).toBeInTheDocument();
        expect(installButton).toHaveTextContent('Install v1.8.3');
        expect(installButton).not.toBeDisabled();
      });

      it('does not show installed indicator when mod is not installed', async () => {
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        await screen.findByTestId('mod-detail-install-section');
        expect(screen.queryByTestId('mod-detail-installed-indicator')).not.toBeInTheDocument();
      });

      it('does not show install section when mod has no releases', async () => {
        globalThis.fetch = mockFetchForInstallTests(mockMinimalResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

        await screen.findByTestId('mod-detail-page');
        expect(screen.queryByTestId('mod-detail-install-section')).not.toBeInTheDocument();
      });
    });

    describe('installed state (Story 14.3)', () => {
      beforeAll(() => {
        // Radix Select needs these in jsdom
        Element.prototype.hasPointerCapture ??= () => false;
        Element.prototype.releasePointerCapture ??= () => {};
        Element.prototype.scrollIntoView ??= () => {};
      });

      function installedAt(version: string) {
        return {
          status: 'ok',
          data: {
            mods: [
              { name: 'Smithing Plus', slug: 'smithingplus', version, enabled: true, side: 'Both' },
            ],
            pending_restart: false,
          },
        };
      }

      function updateStatus(status: string, offered: string | null = null) {
        return {
          status: 'ok',
          data: {
            game_version: '1.21.3',
            checked_at: null,
            update_count: status === 'update_available' ? 1 : 0,
            mods: [
              {
                slug: 'smithingplus',
                name: 'Smithing Plus',
                installed_version: '1.8.2',
                status,
                offered_version: offered,
                offered_compatibility: offered ? 'compatible' : null,
                offered_prerelease: offered ? false : null,
                reason: null,
                checked_at: null,
                error: null,
              },
            ],
          },
        };
      }

      const withOtherModid = {
        ...mockModDetailResponse,
        data: {
          ...mockModDetailResponse.data,
          releases: [
            {
              version: '9.9.9',
              filename: 'otherid_9.9.9.zip',
              file_id: 1,
              modidstr: 'otherid',
              downloads: 1,
              game_versions: ['1.21.3'],
              created: '2025-11-01 00:00:00',
              changelog: null,
            },
            ...mockModDetailResponse.data.releases,
          ],
        },
      };

      function mockInstalled({
        detail = mockModDetailResponse as unknown,
        mods,
        updates,
        versionResponses = [],
      }: {
        detail?: unknown;
        mods: unknown;
        updates: unknown;
        versionResponses?: Array<{ status: number; body: unknown }>;
      }) {
        const queue = [...versionResponses];
        return vi.fn().mockImplementation((url: string, options?: RequestInit) => {
          const respond = (status: number, body: unknown) =>
            Promise.resolve({
              ok: status < 400,
              status,
              statusText: status < 400 ? 'OK' : 'Conflict',
              json: () => Promise.resolve(body),
            });
          if (url.includes('/version') && options?.method === 'PUT') {
            const next = queue.shift();
            return next
              ? respond(next.status, next.body)
              : Promise.reject(new Error('no response'));
          }
          if (url.includes('/mods/lookup/')) return respond(200, detail);
          if (url.includes('/mods/updates')) return respond(200, updates);
          if (url.endsWith('/api/v1alpha1/mods')) {
            if (options?.method === 'POST') return Promise.reject(new Error('install attempted'));
            return respond(200, mods);
          }
          return Promise.reject(new Error(`Unexpected URL: ${url}`));
        });
      }

      const changed = (version: string) => ({
        status: 200,
        body: {
          status: 'ok',
          data: {
            slug: 'smithingplus',
            previous_version: '1.8.2',
            version,
            filename: `smithingplus_${version}.zip`,
            compatibility: 'compatible',
            changed: true,
            pending_restart: false,
          },
        },
      });

      function putBodies(mockFetch: ReturnType<typeof vi.fn>) {
        return mockFetch.mock.calls
          .filter(([, options]) => options?.method === 'PUT')
          .map(([, options]) => JSON.parse(options.body));
      }

      it('fits the version section like the install section (Story 21.6)', async () => {
        const user = userEvent.setup();
        vi.stubGlobal(
          'fetch',
          mockInstalled({
            mods: installedAt('1.8.2'),
            updates: updateStatus('update_available', '1.8.3'),
          })
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        expect(await screen.findByTestId('mod-detail-update-button')).toHaveClass(
          'max-lg:min-h-11'
        );
        expect(screen.getByTestId('mod-detail-install-section')).toHaveClass(
          'w-full',
          'md:w-64',
          'md:shrink-0'
        );
        expect(screen.getByTestId('mod-detail-version-select')).toHaveClass(
          'w-full',
          'max-lg:min-h-11'
        );

        await user.click(screen.getByTestId('mod-detail-version-select'));
        await user.click(await screen.findByRole('option', { name: /v1\.8\.2/ }));
        expect(screen.getByTestId('mod-detail-current-button')).toHaveClass('max-lg:min-h-11');
      });

      it('gives the Switch button a 44px target below lg (Story 21.6)', async () => {
        const user = userEvent.setup();
        vi.stubGlobal(
          'fetch',
          mockInstalled({
            mods: installedAt('1.8.2'),
            updates: updateStatus('up_to_date'),
          })
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        await user.click(await screen.findByTestId('mod-detail-version-select'));
        await user.click(await screen.findByRole('option', { name: /v1\.8\.3/ }));
        expect(screen.getByTestId('mod-detail-switch-button')).toHaveClass('max-lg:min-h-11');
      });

      it('shows the installed version', async () => {
        globalThis.fetch = mockInstalled({
          mods: installedAt('1.8.2'),
          updates: updateStatus('up_to_date'),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const indicator = await screen.findByTestId('mod-detail-installed-indicator');
        expect(indicator).toHaveTextContent('Installed: v1.8.2');
        expect(screen.queryByTestId('mod-detail-install-button')).not.toBeInTheDocument();
      });

      it('offers the update from the update status', async () => {
        globalThis.fetch = mockInstalled({
          mods: installedAt('1.8.2'),
          updates: updateStatus('update_available', '1.8.3'),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const updateButton = await screen.findByTestId('mod-detail-update-button');
        expect(updateButton).toHaveTextContent('Update to v1.8.3');
        expect(updateButton).not.toBeDisabled();
      });

      it('offers no update when a newer release is not offered', async () => {
        globalThis.fetch = mockInstalled({
          mods: installedAt('1.8.2'),
          updates: updateStatus('blocked'),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const current = await screen.findByTestId('mod-detail-current-button');
        expect(current).toBeDisabled();
        expect(screen.queryByTestId('mod-detail-update-button')).not.toBeInTheDocument();
        expect(screen.getByTestId('mod-detail-version-select')).toHaveTextContent('v1.8.2');
      });

      it('updates through the version change API, never install', async () => {
        const user = userEvent.setup();
        const mockFetch = mockInstalled({
          mods: installedAt('1.8.2'),
          updates: updateStatus('update_available', '1.8.3'),
          versionResponses: [changed('1.8.3')],
        });
        globalThis.fetch = mockFetch;

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
        await user.click(await screen.findByTestId('mod-detail-update-button'));

        await waitFor(() => {
          expect(putBodies(mockFetch)).toEqual([{ version: '1.8.3', confirm: false }]);
        });
        expect(screen.queryByTestId('install-confirm-dialog')).not.toBeInTheDocument();
        expect(mockFetch.mock.calls.some(([, options]) => options?.method === 'POST')).toBe(false);
      });

      it('lists only releases with the installed mod ID', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockInstalled({
          detail: withOtherModid,
          mods: installedAt('1.8.2'),
          updates: updateStatus('up_to_date'),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
        await user.click(await screen.findByTestId('mod-detail-version-select'));

        const options = await screen.findAllByRole('option');
        expect(options.map((o) => o.textContent)).toEqual([
          'v1.8.3 (Latest)',
          'v1.8.2 (Installed)',
        ]);
      });

      it('switches to another version with the confirmation flow', async () => {
        const user = userEvent.setup();
        const mockFetch = mockInstalled({
          mods: installedAt('1.8.3'),
          updates: updateStatus('up_to_date'),
          versionResponses: [
            {
              status: 409,
              body: {
                detail: {
                  code: 'MOD_CONFIRMATION_REQUIRED',
                  message: 'Confirmation required',
                  details: { reasons: ['older'], compatibility: 'not_verified' },
                },
              },
            },
            changed('1.8.2'),
          ],
        });
        globalThis.fetch = mockFetch;

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
        await user.click(await screen.findByTestId('mod-detail-version-select'));
        await user.click(await screen.findByRole('option', { name: 'v1.8.2' }));
        await user.click(screen.getByTestId('mod-detail-switch-button'));

        expect(await screen.findByText('Switch Smithing Plus to v1.8.2?')).toBeInTheDocument();
        expect(
          screen.getByText(
            'v1.8.2 is older than the installed v1.8.3. Worlds saved with a newer version may not load correctly.'
          )
        ).toBeInTheDocument();
        await user.click(screen.getByTestId('version-change-confirm'));

        await waitFor(() => {
          expect(putBodies(mockFetch)).toEqual([
            { version: '1.8.2', confirm: false },
            { version: '1.8.2', confirm: true },
          ]);
        });
      });

      it('cancelling a switch makes no further request', async () => {
        const user = userEvent.setup();
        const mockFetch = mockInstalled({
          mods: installedAt('1.8.3'),
          updates: updateStatus('up_to_date'),
          versionResponses: [
            {
              status: 409,
              body: {
                detail: {
                  code: 'MOD_CONFIRMATION_REQUIRED',
                  message: 'Confirmation required',
                  details: { reasons: ['older'] },
                },
              },
            },
          ],
        });
        globalThis.fetch = mockFetch;

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
        await user.click(await screen.findByTestId('mod-detail-version-select'));
        await user.click(await screen.findByRole('option', { name: 'v1.8.2' }));
        await user.click(screen.getByTestId('mod-detail-switch-button'));
        await user.click(await screen.findByTestId('version-change-cancel'));

        await waitFor(() => {
          expect(screen.queryByTestId('version-change-dialog')).not.toBeInTheDocument();
        });
        expect(putBodies(mockFetch)).toHaveLength(1);
      });

      it('lists a re-uploaded version once', async () => {
        const user = userEvent.setup();
        const [latest, older] = mockModDetailResponse.data.releases;
        globalThis.fetch = mockInstalled({
          detail: {
            ...mockModDetailResponse,
            data: {
              ...mockModDetailResponse.data,
              releases: [latest, older, { ...older, file_id: 1, filename: 'reupload.zip' }],
            },
          },
          mods: installedAt('1.8.2'),
          updates: updateStatus('up_to_date'),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
        await user.click(await screen.findByTestId('mod-detail-version-select'));

        const options = await screen.findAllByRole('option');
        expect(options.map((o) => o.textContent)).toEqual([
          'v1.8.3 (Latest)',
          'v1.8.2 (Installed)',
        ]);
      });

      it('explains when no release has the installed mod ID', async () => {
        globalThis.fetch = mockInstalled({
          detail: {
            ...mockModDetailResponse,
            data: {
              ...mockModDetailResponse.data,
              releases: [withOtherModid.data.releases[0]],
            },
          },
          mods: installedAt('1.8.2'),
          updates: updateStatus('unknown'),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        expect(await screen.findByTestId('mod-detail-no-own-releases')).toHaveTextContent(
          'The mod database lists no releases for mod ID smithingplus.'
        );
        expect(screen.queryByTestId('mod-detail-version-select')).not.toBeInTheDocument();
      });

      describe('Story 16.2: an entry with several mod IDs', () => {
        // Shaped like the Instruments entry (fixture mod_instruments.json): the browse
        // slug is `instruments`, but the newest releases belong to other mod IDs.
        const release = (modidstr: string, version: string) => ({
          version,
          filename: `${modidstr}_${version}.zip`,
          file_id: version.length + modidstr.length,
          modidstr,
          downloads: 1,
          game_versions: ['1.21.6'],
          created: '2025-11-01 00:00:00',
          changelog: null,
        });
        const instrumentsEntry = {
          ...mockModDetailResponse,
          data: {
            ...mockModDetailResponse.data,
            slug: 'instruments',
            name: 'Instruments',
            // Story 17.2: what a plain install of `instruments` picks
            install_mod_id: 'instruments',
            latest_version: '1.2.2',
            releases: [
              release('vsinstrumentsbase', '2.0.7'),
              release('vsinstrumentsbase', '2.0.6'),
              release('vsinstruments', '1.2.7'),
              release('vsinstruments', '1.2.6'),
              release('instruments', '1.2.2'),
              release('instruments', '1.0.1'),
            ],
          },
        };
        const route = '/game-server/mods/browse/instruments';

        function installedMods(...mods: Array<[string, string]>) {
          return {
            status: 'ok',
            data: {
              mods: mods.map(([slug, version]) => ({
                name: slug,
                slug,
                version,
                enabled: true,
                side: 'Both',
              })),
              pending_restart: false,
            },
          };
        }

        function updatesFor(slug: string, installedVersion: string, offered: string | null) {
          const base = updateStatus(offered ? 'update_available' : 'up_to_date', offered);
          return {
            ...base,
            data: {
              ...base.data,
              mods: [
                { ...base.data.mods[0], slug, name: slug, installed_version: installedVersion },
              ],
            },
          };
        }

        async function versionOptions(user: ReturnType<typeof userEvent.setup>) {
          await user.click(await screen.findByTestId('mod-detail-version-select'));
          const options = await screen.findAllByRole('option');
          return options.map((o) => o.textContent);
        }

        it('shows the installed state when the installed mod ID is not the browse slug', async () => {
          globalThis.fetch = mockInstalled({
            detail: instrumentsEntry,
            mods: installedMods(['othermod', '1.0.0'], ['vsinstrumentsbase', '2.0.6']),
            updates: updatesFor('vsinstrumentsbase', '2.0.6', null),
          });

          renderWithProviders(<ModDetailPage />, { route });

          expect(await screen.findByTestId('mod-detail-installed-indicator')).toHaveTextContent(
            'Installed: v2.0.6'
          );
          expect(screen.queryByTestId('mod-detail-install-button')).not.toBeInTheDocument();
        });

        it('lists only the installed mod ID releases and updates that mod ID', async () => {
          const user = userEvent.setup();
          const mockFetch = mockInstalled({
            detail: instrumentsEntry,
            mods: installedMods(['vsinstrumentsbase', '2.0.6']),
            updates: updatesFor('vsinstrumentsbase', '2.0.6', '2.0.7'),
            versionResponses: [changed('2.0.7')],
          });
          globalThis.fetch = mockFetch;

          renderWithProviders(<ModDetailPage />, { route });

          expect(await screen.findByTestId('mod-detail-update-button')).toHaveTextContent(
            'Update to v2.0.7'
          );
          // Story 17.2: the installed mod ID is not the install mod ID, so no "(Latest)"
          expect(await versionOptions(user)).toEqual(['v2.0.7', 'v2.0.6 (Installed)']);
          await user.keyboard('{Escape}');
          await user.click(screen.getByTestId('mod-detail-update-button'));

          await waitFor(() => {
            expect(putBodies(mockFetch)).toEqual([{ version: '2.0.7', confirm: false }]);
          });
          const putUrls = mockFetch.mock.calls
            .filter(([, options]) => options?.method === 'PUT')
            .map(([url]) => url as string);
          expect(putUrls).toHaveLength(1);
          expect(putUrls[0]).toMatch(/\/mods\/vsinstrumentsbase\/version$/);
        });

        it('recognizes an installed middle mod ID', async () => {
          const user = userEvent.setup();
          globalThis.fetch = mockInstalled({
            detail: instrumentsEntry,
            mods: installedMods(['vsinstruments', '1.2.6']),
            updates: updatesFor('vsinstruments', '1.2.6', null),
          });

          renderWithProviders(<ModDetailPage />, { route });

          expect(await screen.findByTestId('mod-detail-installed-indicator')).toHaveTextContent(
            'Installed: v1.2.6'
          );
          expect(await versionOptions(user)).toEqual(['v1.2.7', 'v1.2.6 (Installed)']);
        });

        it('prefers the installed mod whose ID is the URL slug', async () => {
          globalThis.fetch = mockInstalled({
            detail: instrumentsEntry,
            mods: installedMods(['vsinstrumentsbase', '2.0.6'], ['instruments', '1.0.1']),
            updates: updatesFor('instruments', '1.0.1', null),
          });

          renderWithProviders(<ModDetailPage />, { route });

          expect(await screen.findByTestId('mod-detail-installed-indicator')).toHaveTextContent(
            'Installed: v1.0.1'
          );
        });

        it('otherwise prefers the installed mod ID with the newest release', async () => {
          globalThis.fetch = mockInstalled({
            detail: instrumentsEntry,
            mods: installedMods(['vsinstruments', '1.2.6'], ['vsinstrumentsbase', '2.0.6']),
            updates: updatesFor('vsinstrumentsbase', '2.0.6', null),
          });

          renderWithProviders(<ModDetailPage />, { route });

          expect(await screen.findByTestId('mod-detail-installed-indicator')).toHaveTextContent(
            'Installed: v2.0.6'
          );
        });

        it('shows the install flow when no mod ID of the entry is installed', async () => {
          globalThis.fetch = mockInstalled({
            detail: instrumentsEntry,
            mods: installedMods(['smithingplus', '1.8.2']),
            updates: updatesFor('smithingplus', '1.8.2', null),
          });

          renderWithProviders(<ModDetailPage />, { route });

          expect(await screen.findByTestId('mod-detail-install-button')).toBeInTheDocument();
          expect(screen.queryByTestId('mod-detail-installed-indicator')).not.toBeInTheDocument();
        });
      });
    });

    describe('version selection', () => {
      it('defaults to latest version in dropdown', async () => {
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const versionSelect = await screen.findByTestId('mod-detail-version-select');
        // Latest version is 1.8.3
        expect(versionSelect).toHaveTextContent('v1.8.3');
      });
    });

    describe('Story 17.2: install picks the right release', () => {
      beforeAll(() => {
        // Radix Select needs these in jsdom
        Element.prototype.hasPointerCapture ??= () => false;
        Element.prototype.releasePointerCapture ??= () => {};
        Element.prototype.scrollIntoView ??= () => {};
      });

      const release = (modidstr: string, version: string, fileId: number | null = 1) => ({
        version,
        filename: fileId ? `${modidstr}_${version}.zip` : '',
        file_id: fileId,
        modidstr,
        downloads: 1,
        game_versions: ['1.21.3'],
        created: '2025-11-01 00:00:00',
        changelog: null,
      });

      function entry(
        fields: {
          slug: string;
          install_mod_id: string;
          latest_version: string | null;
        },
        releases: ReturnType<typeof release>[]
      ) {
        return {
          ...mockModDetailResponse,
          data: { ...mockModDetailResponse.data, ...fields, name: fields.slug, releases },
        };
      }

      const instrumentsEntry = entry(
        { slug: 'instruments', install_mod_id: 'instruments', latest_version: '1.2.2' },
        [
          release('vsinstrumentsbase', '2.0.7'),
          release('vsinstrumentsbase', '1.0.1'),
          release('vsinstruments', '1.2.7'),
          release('instruments', '1.2.2'),
          release('instruments', '1.0.1'),
        ]
      );

      const carryonEntry = entry(
        { slug: 'carryon', install_mod_id: 'carryon', latest_version: '1.14.3' },
        [release('carryon', '2.0.0-rc.1'), release('carryon', '1.14.3')]
      );

      /** Lookup, installed mods and updates; records POST /mods bodies and answers ok. */
      function mockEntry(detail: unknown, installed: unknown[] = [], updateMods: unknown[] = []) {
        return vi.fn().mockImplementation((url: string, options?: RequestInit) => {
          const respond = (body: unknown) =>
            Promise.resolve({
              ok: true,
              status: 200,
              statusText: 'OK',
              json: () => Promise.resolve(body),
            });
          if (url.includes('/mods/lookup/')) return respond(detail);
          if (url.includes('/mods/updates')) {
            return respond({
              status: 'ok',
              data: {
                game_version: '1.21.3',
                checked_at: null,
                update_count: updateMods.length,
                mods: updateMods,
              },
            });
          }
          if (url.endsWith('/api/v1alpha1/mods')) {
            if (options?.method === 'POST') {
              const body = JSON.parse(String(options.body)) as { slug: string; version?: string };
              return respond({
                status: 'ok',
                data: {
                  slug: body.slug,
                  version: body.version ?? 'x',
                  filename: 'stub.zip',
                  compatibility: 'compatible',
                  pending_restart: false,
                },
              });
            }
            return respond({ status: 'ok', data: { mods: installed, pending_restart: false } });
          }
          return Promise.reject(new Error(`Unexpected URL: ${url}`));
        });
      }

      function postBodies(mockFetch: ReturnType<typeof vi.fn>) {
        return mockFetch.mock.calls
          .filter(([, options]) => options?.method === 'POST')
          .map(([, options]) => JSON.parse(options.body));
      }

      async function optionTexts(user: ReturnType<typeof userEvent.setup>) {
        await user.click(await screen.findByTestId('mod-detail-version-select'));
        const options = await screen.findAllByRole('option');
        return options.map((o) => o.textContent);
      }

      async function installAndConfirm(user: ReturnType<typeof userEvent.setup>) {
        await user.click(screen.getByTestId('mod-detail-install-button'));
        await user.click(await screen.findByTestId('install-dialog-confirm'));
      }

      it('lists only the install mod ID releases and installs its latest version', async () => {
        const user = userEvent.setup();
        const mockFetch = mockEntry(instrumentsEntry);
        globalThis.fetch = mockFetch;

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/instruments' });

        expect(await screen.findByTestId('mod-detail-version-select')).toHaveTextContent('v1.2.2');
        expect(await optionTexts(user)).toEqual(['v1.2.2 (Latest)', 'v1.0.1']);
        await user.keyboard('{Escape}');
        await installAndConfirm(user);

        await waitFor(() => {
          expect(postBodies(mockFetch)).toEqual([{ slug: 'instruments', version: '1.2.2' }]);
        });
      });

      it('preselects the newest stable release and still offers a newer pre-release', async () => {
        const user = userEvent.setup();
        const mockFetch = mockEntry(carryonEntry);
        globalThis.fetch = mockFetch;

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/carryon' });

        expect(await screen.findByTestId('mod-detail-version-select')).toHaveTextContent('v1.14.3');
        expect(await optionTexts(user)).toEqual(['v2.0.0-rc.1', 'v1.14.3 (Latest)']);
        await user.click(screen.getByRole('option', { name: 'v2.0.0-rc.1' }));
        await installAndConfirm(user);

        await waitFor(() => {
          expect(postBodies(mockFetch)).toEqual([{ slug: 'carryon', version: '2.0.0-rc.1' }]);
        });
      });

      it('puts the Releases list "Latest" badge on the release a plain install picks', async () => {
        globalThis.fetch = mockEntry(carryonEntry);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/carryon' });

        const stable = await screen.findByTestId('mod-detail-release-1.14.3');
        expect(within(stable).getByText('Latest')).toBeInTheDocument();
        expect(
          within(screen.getByTestId('mod-detail-release-2.0.0-rc.1')).queryByText('Latest')
        ).not.toBeInTheDocument();
      });

      it('installs the install mod ID, not the entry slug', async () => {
        const user = userEvent.setup();
        const mockFetch = mockEntry(
          entry({ slug: 'instruments', install_mod_id: 'vsinstruments', latest_version: '1.2.7' }, [
            release('vsinstrumentsbase', '2.0.7'),
            release('vsinstruments', '1.2.7'),
            release('instruments', '1.2.2'),
          ])
        );
        globalThis.fetch = mockFetch;

        renderWithProviders(<ModDetailPage />, {
          route: '/game-server/mods/browse/vsinstruments',
        });
        await screen.findByTestId('mod-detail-install-button');
        await installAndConfirm(user);

        await waitFor(() => {
          expect(postBodies(mockFetch)).toEqual([{ slug: 'vsinstruments', version: '1.2.7' }]);
        });
      });

      it('lists a release without a file disabled', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockEntry(
          entry({ slug: 'demo', install_mod_id: 'demo', latest_version: '1.0.0' }, [
            release('demo', '2.0.0', null),
            release('demo', '1.0.0'),
          ])
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/demo' });

        expect(await optionTexts(user)).toEqual(['v2.0.0 (no file)', 'v1.0.0 (Latest)']);
        expect(screen.getByRole('option', { name: 'v2.0.0 (no file)' })).toHaveAttribute(
          'aria-disabled',
          'true'
        );
        expect(screen.getByRole('option', { name: 'v1.0.0 (Latest)' })).not.toHaveAttribute(
          'aria-disabled'
        );
      });

      it('disables Install when no release has a file', async () => {
        globalThis.fetch = mockEntry(
          entry({ slug: 'demo', install_mod_id: 'demo', latest_version: null }, [
            release('demo', '2.0.0', null),
            release('demo', '1.0.0', 0),
          ])
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/demo' });

        const button = await screen.findByTestId('mod-detail-install-button');
        expect(button).toBeDisabled();
        expect(button).toHaveTextContent('No downloadable release');
      });

      it('renders an entry whose mod IDs share a version without duplicate keys', async () => {
        const errors = vi.spyOn(console, 'error').mockImplementation(() => {});
        try {
          globalThis.fetch = mockEntry(instrumentsEntry);

          renderWithProviders(<ModDetailPage />, {
            route: '/game-server/mods/browse/instruments',
          });
          await screen.findByTestId('mod-detail-releases-list');

          // vsinstrumentsbase and instruments both list 1.0.1
          const duplicateKeys = errors.mock.calls.filter((call) =>
            call.some((arg) => String(arg).includes('same key'))
          );
          expect(duplicateKeys).toEqual([]);
        } finally {
          errors.mockRestore();
        }
      });

      it('does not offer an update to a release without a file (review M1)', async () => {
        const user = userEvent.setup();
        const mockFetch = mockEntry(
          entry({ slug: 'smithingplus', install_mod_id: 'smithingplus', latest_version: '1.8.2' }, [
            release('smithingplus', '1.8.3', null),
            release('smithingplus', '1.8.2'),
          ]),
          [
            {
              name: 'Smithing Plus',
              slug: 'smithingplus',
              version: '1.8.2',
              enabled: true,
              side: 'Both',
            },
          ],
          [
            {
              slug: 'smithingplus',
              name: 'Smithing Plus',
              installed_version: '1.8.2',
              status: 'update_available',
              offered_version: '1.8.3',
              offered_compatibility: 'compatible',
              offered_prerelease: false,
              reason: null,
              checked_at: null,
              error: null,
            },
          ]
        );

        globalThis.fetch = mockFetch;

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
        await screen.findByTestId('mod-detail-installed-indicator');
        await waitFor(() => {
          expect(mockFetch.mock.calls.some(([url]) => String(url).endsWith('/mods/updates'))).toBe(
            true
          );
        });

        expect(await optionTexts(user)).toEqual([
          'v1.8.3 (no file)',
          'v1.8.2 (Latest) (Installed)',
        ]);
        expect(screen.getByRole('option', { name: 'v1.8.3 (no file)' })).toHaveAttribute(
          'aria-disabled',
          'true'
        );
        await user.keyboard('{Escape}');
        // The update status has loaded by now; the offer has no file, so it is not
        // preselected and the action is the disabled "Installed" button
        expect(screen.getByTestId('mod-detail-version-select')).toHaveTextContent('v1.8.2');
        expect(screen.getByTestId('mod-detail-current-button')).toBeDisabled();
        expect(screen.queryByTestId('mod-detail-update-button')).not.toBeInTheDocument();
      });

      it('labels "(Latest)" in the installed list when the installed mod ID is the install mod ID', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockEntry(
          entry({ slug: 'smithingplus', install_mod_id: 'smithingplus', latest_version: '1.8.3' }, [
            release('smithingplus', '1.9.0-rc.1'),
            release('smithingplus', '1.8.3'),
            release('smithingplus', '1.8.2'),
            release('smithingplus', '1.8.1', null),
          ]),
          [
            {
              name: 'Smithing Plus',
              slug: 'smithingplus',
              version: '1.8.2',
              enabled: true,
              side: 'Both',
            },
          ]
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });
        await screen.findByTestId('mod-detail-installed-indicator');

        expect(await optionTexts(user)).toEqual([
          'v1.9.0-rc.1',
          'v1.8.3 (Latest)',
          'v1.8.2 (Installed)',
          'v1.8.1 (no file)',
        ]);
        expect(screen.getByRole('option', { name: 'v1.8.1 (no file)' })).toHaveAttribute(
          'aria-disabled',
          'true'
        );
      });
    });

    describe('install button interaction', () => {
      it('install button is enabled when mod is not installed', async () => {
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        expect(installButton).not.toBeDisabled();
      });
    });

    describe('confirmation dialog (Story 10.8)', () => {
      it('opens confirmation dialog when Install button is clicked', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        await user.click(installButton);

        // Dialog should appear
        expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
        expect(screen.getByTestId('install-dialog-mod-name')).toHaveTextContent('Smithing Plus');
      });

      it('dialog shows compatibility badge from mod data', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        await user.click(installButton);

        // Get the badge inside the dialog
        const dialog = screen.getByTestId('install-confirm-dialog');
        const dialogBadge = within(dialog).getByTestId('compatibility-badge');
        expect(dialogBadge).toHaveAttribute('data-status', 'compatible');
      });

      it('dialog closes when Cancel is clicked', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockFetchForInstallTests(mockModDetailResponse, mockEmptyModsResponse);

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        await user.click(installButton);

        // Dialog should be open
        expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();

        // Click cancel
        await user.click(screen.getByTestId('install-dialog-cancel'));

        // Dialog should be closed
        expect(screen.queryByTestId('install-confirm-dialog')).not.toBeInTheDocument();
      });
    });
  });

  describe('navigation (Task 4)', () => {
    describe('back button (Subtask 4.2)', () => {
      it('renders back button', async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const backButton = await screen.findByTestId('mod-detail-back');
        expect(backButton).toBeInTheDocument();
        expect(backButton).toHaveTextContent('Back to Browse');
      });

      it('back button is clickable', async () => {
        const user = userEvent.setup();
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const backButton = await screen.findByTestId('mod-detail-back');
        // Just verify it can be clicked without error
        await user.click(backButton);
      });
    });

    describe('Story 16.1: returning to the browser keeps its state', () => {
      const browseSearch = BROWSE_SEARCH;
      const openedFromBrowse = {
        pathname: '/game-server/mods/browse/smithingplus',
        state: { browseSearch },
      };

      beforeEach(() => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });
      });

      it('Back to Browse returns to the search, sort and filters including the game version', async () => {
        const user = userEvent.setup();
        renderWithProviders(<ModDetailPage />, { route: openedFromBrowse });

        await user.click(await screen.findByTestId('mod-detail-back'));

        expect(screen.getByTestId('landing-search')).toHaveTextContent(browseSearch);
        expect(screen.getByTestId('landing-from-detail')).toHaveTextContent('true');
      });

      it('the Browse breadcrumb links to the same browse state and marks the return', async () => {
        const user = userEvent.setup();
        renderWithProviders(<ModDetailPage />, { route: openedFromBrowse });

        const browseLink = await screen.findByTestId('mod-detail-breadcrumb-browse');
        expect(browseLink).toHaveAttribute('href', `/game-server/mods/browse${browseSearch}`);

        await user.click(browseLink);

        expect(screen.getByTestId('landing-search')).toHaveTextContent(browseSearch);
        expect(screen.getByTestId('landing-from-detail')).toHaveTextContent('true');
      });

      it('returns to the default browser when the page was opened directly', async () => {
        const user = userEvent.setup();
        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        expect(await screen.findByTestId('mod-detail-breadcrumb-browse')).toHaveAttribute(
          'href',
          '/game-server/mods/browse'
        );

        await user.click(screen.getByTestId('mod-detail-back'));

        expect(screen.getByTestId('landing-search')).toBeEmptyDOMElement();
        expect(screen.getByTestId('landing-from-detail')).toHaveTextContent('true');
      });

      it('ignores navigation state that is not a browse search', async () => {
        renderWithProviders(<ModDetailPage />, {
          route: {
            pathname: '/game-server/mods/browse/smithingplus',
            state: { browseSearch: '//evil.example/path' },
          },
        });

        expect(await screen.findByTestId('mod-detail-breadcrumb-browse')).toHaveAttribute(
          'href',
          '/game-server/mods/browse'
        );
      });
    });

    describe('Story 17.1: error states lead back to the browser', () => {
      const errorResponses: [string, () => unknown][] = [
        [
          'a failed lookup',
          () => ({
            ok: false,
            status: 500,
            json: () =>
              Promise.resolve({ detail: { code: 'INTERNAL_ERROR', message: 'Server error' } }),
          }),
        ],
        [
          'a response with no mod',
          () => ({ ok: true, json: () => Promise.resolve({ status: 'ok' }) }),
        ],
        [
          'incomplete mod details',
          () => ({ ok: true, json: () => Promise.resolve({ status: 'ok', data: {} }) }),
        ],
      ];

      it.each(errorResponses)(
        'after %s, Back to Browse returns to the browse state it was opened from',
        async (_label, response) => {
          globalThis.fetch = vi.fn().mockResolvedValue(response());
          const user = userEvent.setup();
          renderWithProviders(<ModDetailPage />, {
            route: {
              pathname: '/game-server/mods/browse/brokenmod',
              state: { browseSearch: BROWSE_SEARCH },
            },
          });

          expect(await screen.findByTestId('mod-detail-error')).toBeInTheDocument();
          await user.click(screen.getByTestId('mod-detail-back'));

          expect(screen.getByTestId('landing-search')).toHaveTextContent(BROWSE_SEARCH);
          expect(screen.getByTestId('landing-from-detail')).toHaveTextContent('true');
        }
      );

      it.each(errorResponses)(
        'after %s, Back to Browse returns to the default browser when opened directly',
        async (_label, response) => {
          globalThis.fetch = vi.fn().mockResolvedValue(response());
          const user = userEvent.setup();
          renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/brokenmod' });

          expect(await screen.findByTestId('mod-detail-error')).toBeInTheDocument();
          await user.click(screen.getByTestId('mod-detail-back'));

          expect(screen.getByTestId('landing-search')).toBeEmptyDOMElement();
          expect(screen.getByTestId('landing-from-detail')).toHaveTextContent('true');
        }
      );
    });

    describe('breadcrumb navigation (Subtask 4.3)', () => {
      it('renders breadcrumb navigation', async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const breadcrumb = await screen.findByTestId('mod-detail-breadcrumb');
        expect(breadcrumb).toBeInTheDocument();
      });

      it('breadcrumb shows Mods link', async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const modsLink = await screen.findByTestId('mod-detail-breadcrumb-mods');
        expect(modsLink).toHaveTextContent('Mods');
        expect(modsLink).toHaveAttribute('href', '/game-server/mods');
      });

      it('breadcrumb shows Browse link', async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const browseLink = await screen.findByTestId('mod-detail-breadcrumb-browse');
        expect(browseLink).toHaveTextContent('Browse');
        expect(browseLink).toHaveAttribute('href', '/game-server/mods/browse');
      });

      it('breadcrumb shows current mod name', async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const modName = await screen.findByTestId('mod-detail-breadcrumb-name');
        expect(modName).toHaveTextContent('Smithing Plus');
      });

      it('breadcrumb has proper accessibility label', async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const breadcrumb = await screen.findByTestId('mod-detail-breadcrumb');
        expect(breadcrumb).toHaveAttribute('aria-label', 'Breadcrumb');
      });
    });

    describe('route integration (Subtask 4.1, 4.4)', () => {
      it('extracts slug from URL params', async () => {
        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(mockModDetailResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        await screen.findByTestId('mod-detail-page');

        // Verify fetch was called with correct slug
        expect(globalThis.fetch).toHaveBeenCalledWith(
          'http://localhost:8080/api/v1alpha1/mods/lookup/smithingplus',
          expect.any(Object)
        );
      });

      it('handles different slug values', async () => {
        const differentModResponse = {
          ...mockModDetailResponse,
          data: {
            ...mockModDetailResponse.data,
            slug: 'anothermod',
            name: 'Another Mod',
          },
        };

        globalThis.fetch = vi.fn().mockResolvedValue({
          ok: true,
          json: () => Promise.resolve(differentModResponse),
        });

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/anothermod' });

        await screen.findByTestId('mod-detail-page');

        expect(globalThis.fetch).toHaveBeenCalledWith(
          'http://localhost:8080/api/v1alpha1/mods/lookup/anothermod',
          expect.any(Object)
        );

        expect(screen.getByTestId('mod-detail-name')).toHaveTextContent('Another Mod');
      });
    });
  });
});
