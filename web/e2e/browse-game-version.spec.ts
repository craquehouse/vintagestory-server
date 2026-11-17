import { test, expect, type Page, type Response } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for the game version indicator on mod browser cards.
 *
 * Story 18.3 (FR201, FR202, Epic 18 ADR-3; VSS-4f3):
 * - A card whose entry has a release tagged for the installed game version shows a badge
 *   "Has a release for <version>"; one without shows muted text "No release for <version>";
 *   an unknown flag, or an unknown version, shows nothing. Never "Compatible" or
 *   "Incompatible".
 * - Both indicators stay inside the card at phone width (390px), in the light and the
 *   dark theme.
 * - Live: the cards agree with the browse response, whether or not a game server is
 *   installed on the stack.
 *
 * Reads only. The first three tests stub `GET /api/v1alpha1/mods/browse` with
 * `page.route`; everything else is live. The spec installs nothing, writes nothing, does
 * not start or stop the game server and takes no screenshot.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) rebuilt from this branch:
 *   `just test-e2e-web`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/browse-game-version.spec.ts`
 * - Network access to the public mod database for the live test, which is tagged
 *   `@moddb-live` and runs only locally (e2e/README.md).
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const BROWSE = '/game-server/mods/browse';
const BROWSE_API = /\/api\/v1alpha1\/mods\/browse(\?.*)?$/;
const PHONE = { width: 390, height: 844 };
const COLOR_SCHEMES: Array<'light' | 'dark'> = ['light', 'dark'];

interface LiveBrowseBody {
  data: {
    game_version: string | null;
    mods: Array<{ slug: string; has_release_for_game_version: boolean | null }>;
  };
}

function item(slug: string, name: string, hasRelease: boolean | null) {
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

function browseBody(gameVersion: string | null) {
  const known = gameVersion !== null;
  return {
    status: 'ok',
    data: {
      mods: [
        item('e2e-has', 'E2E Has Release', known ? true : null),
        item('e2e-none', 'E2E No Release', known ? false : null),
        item('e2e-unknown', 'E2E Unknown', null),
      ],
      pagination: {
        page: 1,
        page_size: 20,
        total_items: 3,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
      game_version: gameVersion,
    },
  };
}

async function stubBrowse(page: Page, gameVersion: string | null) {
  await page.route(BROWSE_API, (route) => route.fulfill({ json: browseBody(gameVersion) }));
}

async function openBrowse(page: Page) {
  await page.goto(BROWSE);
  await expect(page.getByTestId('mod-card-e2e-has')).toBeVisible({ timeout: 30_000 });
}

function isBrowseResponse(response: Response): boolean {
  return new URL(response.url()).pathname.endsWith('/api/v1alpha1/mods/browse');
}

test.describe('Game version indicator on browse cards', () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
  });

  test('shows the badge, the muted text and nothing for true, false and null', async ({
    page,
  }) => {
    await stubBrowse(page, '1.22.7');
    await openBrowse(page);

    await expect(page.getByTestId('mod-card-game-version-e2e-has')).toHaveText(
      'Has a release for 1.22.7'
    );
    await expect(page.getByTestId('mod-card-game-version-e2e-none')).toHaveText(
      'No release for 1.22.7'
    );
    await expect(page.getByTestId('mod-card-game-version-e2e-unknown')).toHaveCount(0);
    await expect(page.getByTestId('mod-browse-grid')).not.toContainText(/compatible/i);
  });

  test('shows no indicator when the game version is not known', async ({ page }) => {
    await stubBrowse(page, null);
    await openBrowse(page);

    await expect(page.getByTestId('mod-card-e2e-none')).toBeVisible();
    await expect(page.locator('[data-testid^="mod-card-game-version-"]')).toHaveCount(0);
  });

  for (const colorScheme of COLOR_SCHEMES) {
    test(`indicators stay inside the card at phone width (${colorScheme} theme)`, async ({
      page,
    }) => {
      await page.setViewportSize(PHONE);
      await page.emulateMedia({ colorScheme });
      await stubBrowse(page, '1.22.7');
      await openBrowse(page);

      const isDark = await page.evaluate(() =>
        document.documentElement.classList.contains('dark')
      );
      expect(isDark).toBe(colorScheme === 'dark');

      for (const slug of ['e2e-has', 'e2e-none']) {
        const indicator = page.getByTestId(`mod-card-game-version-${slug}`);
        await indicator.scrollIntoViewIfNeeded();
        await expect(indicator).toBeVisible();
        const box = await indicator.boundingBox();
        const card = await page.getByTestId(`mod-card-${slug}`).boundingBox();
        expect(box).not.toBeNull();
        expect(card).not.toBeNull();
        if (box && card) {
          expect(box.x).toBeGreaterThanOrEqual(card.x);
          expect(box.y).toBeGreaterThanOrEqual(card.y);
          expect(box.x + box.width).toBeLessThanOrEqual(card.x + card.width);
          expect(box.y + box.height).toBeLessThanOrEqual(card.y + card.height);
        }
      }

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      );
      expect(overflow).toBeLessThanOrEqual(0);
    });
  }

  // @moddb-live: compares the cards with a live browse response; on recorded answers (and a
  // stack with no game server) game_version is null, so it would check nothing
  test('live: the cards agree with the browse response', { tag: '@moddb-live' }, async ({ page }) => {
    const browse = page.waitForResponse(
      (r) =>
        isBrowseResponse(r) &&
        r.status() === 200 &&
        new URL(r.url()).searchParams.get('search') === 'carry on',
      { timeout: 60_000 }
    );
    await page.goto(`${BROWSE}?q=carry+on&sort=downloads`);
    const body: LiveBrowseBody = await (await browse).json();
    const gameVersion = body.data.game_version;
    const mods = body.data.mods;
    expect(mods.length).toBeGreaterThan(0);
    await expect(page.getByTestId(`mod-card-${mods[0].slug}`)).toBeVisible({ timeout: 30_000 });

    test.info().annotations.push({
      type: 'game_version',
      description:
        gameVersion === null
          ? 'null (no server installed, version without a tag, or mod database unavailable): no indicators expected'
          : `${gameVersion}: indicators checked against the response`,
    });

    if (gameVersion === null) {
      await expect(page.locator('[data-testid^="mod-card-game-version-"]')).toHaveCount(0);
      return;
    }
    for (const mod of mods) {
      const indicator = page.getByTestId(`mod-card-game-version-${mod.slug}`);
      if (mod.has_release_for_game_version === true) {
        await expect(indicator).toHaveText(`Has a release for ${gameVersion}`);
      } else if (mod.has_release_for_game_version === false) {
        await expect(indicator).toHaveText(`No release for ${gameVersion}`);
      } else {
        await expect(indicator).toHaveCount(0);
      }
    }
  });
});
