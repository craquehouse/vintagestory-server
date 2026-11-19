import { test, expect, type Page } from '@playwright/test';
import { serveConfigKey } from './config-js';

/**
 * E2E tests for browse cards that follow the installed game version.
 *
 * Story 21.4 (FR286; Epic 21 ADR-16; VSS-q38r): when the polled server status reports
 * another installed game version, the browse cards are fetched again without a reload and
 * show the "Has a release for" badges of the new version, within one status poll (5 s),
 * not after the five-minute browse cache time. Polls that report the same version fetch
 * nothing.
 *
 * `GET /api/v1alpha1/server/status` and `GET /api/v1alpha1/mods/browse` are answered with
 * `page.route`, with made-up game versions that the test switches; the page's other mod
 * requests (all GETs) go to the stack. The spec reads and changes nothing in the server's
 * data, needs no mod database and no game server, does not start or stop the game server
 * and takes no screenshot.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080) rebuilt from this branch:
 *   `just test-e2e-ci e2e/browse-version-refresh.spec.ts`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/browse-version-refresh.spec.ts`
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const BROWSE = '/game-server/mods/browse';
const BROWSE_API = /\/api\/v1alpha1\/mods\/browse(\?.*)?$/;
const STATUS_API = '**/api/v1alpha1/server/status';

// Made-up versions, never the stack's own
const VERSION_A = '1.99.1';
const VERSION_B = '1.99.2';

function item(slug: string, name: string, hasRelease: boolean) {
  return {
    slug,
    mod_ids: [slug],
    urlalias: slug,
    asset_id: 0,
    name,
    author: 'E2E',
    summary: 'A stubbed browse item',
    downloads: 1,
    follows: 1,
    trending_points: 1,
    side: 'both',
    mod_type: 'mod',
    logo_url: null,
    tags: [],
    last_released: '2026-11-01 00:00:00',
    has_release_for_game_version: hasRelease,
  };
}

/** e2e-has has a release for version A only, e2e-none for version B only. */
function browseBody(gameVersion: string) {
  const isA = gameVersion === VERSION_A;
  return {
    status: 'ok',
    data: {
      mods: [item('e2e-has', 'E2E Has Release', isA), item('e2e-none', 'E2E No Release', !isA)],
      pagination: {
        page: 1,
        page_size: 20,
        total_items: 2,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
      game_version: gameVersion,
    },
  };
}

/** Stub the status and the browse answer; both follow `stack.version`. */
async function stubStatusAndBrowse(page: Page) {
  const stack = { version: VERSION_A, statusAnswers: 0, browseRequests: 0 };

  await page.route(STATUS_API, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    stack.statusAnswers += 1;
    await route.fulfill({
      json: {
        status: 'ok',
        data: {
          state: 'installed',
          version: stack.version,
          uptime_seconds: null,
          last_exit_code: null,
          available_stable_version: null,
          available_unstable_version: null,
          version_last_checked: null,
          disk_space: null,
        },
      },
    });
  });

  await page.route(BROWSE_API, async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    stack.browseRequests += 1;
    await route.fulfill({ json: browseBody(stack.version) });
  });

  return stack;
}

function isStatusResponse(url: string): boolean {
  return new URL(url).pathname.endsWith('/api/v1alpha1/server/status');
}

test.describe('Browse cards follow the installed game version (Story 21.4)', () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
  });

  test('a version change refreshes the cards within one status poll', async ({ page }) => {
    const stack = await stubStatusAndBrowse(page);
    await page.goto(BROWSE);

    await expect(page.getByTestId('mod-card-game-version-e2e-has')).toHaveText(
      `Has a release for ${VERSION_A}`,
      { timeout: 30_000 }
    );
    await expect(page.getByTestId('mod-card-game-version-e2e-none')).toHaveText(
      `No release for ${VERSION_A}`
    );
    const browseBefore = stack.browseRequests;

    stack.version = VERSION_B;

    await expect(page.getByTestId('mod-card-game-version-e2e-none')).toHaveText(
      `Has a release for ${VERSION_B}`,
      { timeout: 15_000 }
    );
    await expect(page.getByTestId('mod-card-game-version-e2e-has')).toHaveText(
      `No release for ${VERSION_B}`
    );
    expect(stack.browseRequests).toBeGreaterThan(browseBefore);
    expect(new URL(page.url()).pathname).toBe(BROWSE);
  });

  test('polls that report the same version fetch no browse page', async ({ page }) => {
    const stack = await stubStatusAndBrowse(page);
    await page.goto(BROWSE);
    await expect(page.getByTestId('mod-card-game-version-e2e-has')).toHaveText(
      `Has a release for ${VERSION_A}`,
      { timeout: 30_000 }
    );
    const browseBefore = stack.browseRequests;

    await page.waitForResponse((response) => isStatusResponse(response.url()), {
      timeout: 15_000,
    });
    await page.waitForResponse((response) => isStatusResponse(response.url()), {
      timeout: 15_000,
    });

    expect(stack.browseRequests).toBe(browseBefore);
    await expect(page.getByTestId('mod-card-game-version-e2e-has')).toHaveText(
      `Has a release for ${VERSION_A}`
    );
  });
});
