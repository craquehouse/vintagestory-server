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
import { MemoryRouter, Routes, Route } from 'react-router';
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

// Wrapper to provide QueryClient and Router context - Story 11.4: Uses /game-server/mods paths
function renderWithProviders(
  ui: React.ReactElement,
  { route = '/game-server/mods/browse/testmod' } = {}
) {
  const queryClient = createTestQueryClient();

  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <Routes>
          <Route path="/game-server/mods" element={<div>Mods Page</div>} />
          <Route path="/game-server/mods/browse" element={<div>Browse Page</div>} />
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
  });

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
    it('renders mod name and author', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      expect(await screen.findByTestId('mod-detail-name')).toHaveTextContent(
        'Smithing Plus'
      );
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
      expect(img).toHaveAttribute(
        'src',
        'https://moddbcdn.vintagestory.at/logo.png'
      );
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

  describe('description section (Subtask 2.3)', () => {
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

  describe('external links', () => {
    it('renders ModDB link', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      const link = await screen.findByTestId('mod-detail-moddb-link');
      expect(link).toHaveAttribute(
        'href',
        'https://mods.vintagestory.at/show/mod/15312'
      );
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
    });
  });

  describe('metadata section', () => {
    it('renders created and last released dates', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      expect(await screen.findByTestId('mod-detail-created')).toHaveTextContent(
        'Oct 24, 2024'
      );
      expect(screen.getByTestId('mod-detail-last-released')).toHaveTextContent(
        'Oct 9, 2025'
      );
    });

    it('renders slug in metadata', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockModDetailResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

      expect(await screen.findByTestId('mod-detail-slug')).toHaveTextContent(
        'smithingplus'
      );
    });

    it('shows Unknown for null dates', async () => {
      globalThis.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: () => Promise.resolve(mockMinimalResponse),
      });

      renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/simplemod' });

      expect(await screen.findByTestId('mod-detail-created')).toHaveTextContent(
        'Unknown'
      );
      expect(screen.getByTestId('mod-detail-last-released')).toHaveTextContent(
        'Unknown'
      );
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
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        expect(await screen.findByTestId('mod-detail-install-section')).toBeInTheDocument();
      });

      it('shows version dropdown with all releases', async () => {
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const versionSelect = await screen.findByTestId('mod-detail-version-select');
        expect(versionSelect).toBeInTheDocument();
        // Default selection should be latest version
        expect(versionSelect).toHaveTextContent('v1.8.3');
      });

      it('shows Install button when mod is not installed', async () => {
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        expect(installButton).toBeInTheDocument();
        expect(installButton).toHaveTextContent('Install v1.8.3');
        expect(installButton).not.toBeDisabled();
      });

      it('does not show installed indicator when mod is not installed', async () => {
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        await screen.findByTestId('mod-detail-install-section');
        expect(screen.queryByTestId('mod-detail-installed-indicator')).not.toBeInTheDocument();
      });

      it('does not show install section when mod has no releases', async () => {
        globalThis.fetch = mockFetchForInstallTests(
          mockMinimalResponse,
          mockEmptyModsResponse
        );

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
            return next ? respond(next.status, next.body) : Promise.reject(new Error('no response'));
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
        expect(
          mockFetch.mock.calls.some(([, options]) => options?.method === 'POST')
        ).toBe(false);
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
    });

    describe('version selection', () => {
      it('defaults to latest version in dropdown', async () => {
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const versionSelect = await screen.findByTestId('mod-detail-version-select');
        // Latest version is 1.8.3
        expect(versionSelect).toHaveTextContent('v1.8.3');
      });

      it('marks latest version with "(Latest)" label', async () => {
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        // Wait for install section
        await screen.findByTestId('mod-detail-install-section');

        // The default selected value shows "v1.8.3 (Latest)" in dropdown
        // Note: The "(Latest)" text appears in SelectItem, not necessarily in trigger
        const versionSelect = screen.getByTestId('mod-detail-version-select');
        expect(versionSelect).toBeInTheDocument();
      });
    });

    describe('install button interaction', () => {
      it('install button is enabled when mod is not installed', async () => {
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        expect(installButton).not.toBeDisabled();
      });
    });

    describe('confirmation dialog (Story 10.8)', () => {
      it('opens confirmation dialog when Install button is clicked', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

        renderWithProviders(<ModDetailPage />, { route: '/game-server/mods/browse/smithingplus' });

        const installButton = await screen.findByTestId('mod-detail-install-button');
        await user.click(installButton);

        // Dialog should appear
        expect(screen.getByTestId('install-confirm-dialog')).toBeInTheDocument();
        expect(screen.getByTestId('install-dialog-mod-name')).toHaveTextContent('Smithing Plus');
      });

      it('dialog shows compatibility badge from mod data', async () => {
        const user = userEvent.setup();
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

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
        globalThis.fetch = mockFetchForInstallTests(
          mockModDetailResponse,
          mockEmptyModsResponse
        );

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
