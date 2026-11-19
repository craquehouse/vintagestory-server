import { test, expect, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for the mod logos and links the API passes on from the mod database.
 *
 * Story 19.6 (FR224, FR225; VSS-2zis; Epic 19 ADR-12):
 * - A mod logo on a browse card, in the install dialog and on the detail page has
 *   `referrerpolicy="no-referrer"`, and the CDN receives no `Referer` header.
 * - The detail page shows the homepage and source links the API returns, and none when
 *   the API returns null; the "ModDB Page" link is always there.
 * - A mod without a logo (the API returns null for a missing or dropped URL) shows the
 *   placeholder.
 *
 * The API's filtering of the mod database's URLs is covered by the API tests: `page.route`
 * acts on the browser's requests, not on the API's requests to the mod database. This spec
 * stubs what the API answers and checks what the admin sees.
 *
 * Every mod database route the pages call is stubbed with `page.route`, so the spec needs
 * neither the mod database nor a game server. Every write to the API is refused, so it
 * changes nothing; the game server is neither started nor stopped; no screenshot is taken.
 * It carries no tag.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080), rebuilt from this branch:
 *   `just docker restart`, then `cd web && bunx playwright test e2e/mod-database-urls.spec.ts`
 *   with VS_API_KEY_ADMIN exported.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const BROWSE = '/game-server/mods/browse';
const CDN = 'https://moddbcdn.vintagestory.at';
const LOGO = `${CDN}/e2e-logo.png`;
const HOMEPAGE = 'https://example.com/home';
const SOURCE = 'https://example.com/src';

// A 1x1 PNG
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
  'base64'
);

function item(slug: string, name: string, logoUrl: string | null) {
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
    logo_url: logoUrl,
    tags: [],
    last_released: '2026-11-01 00:00:00',
    has_release_for_game_version: null,
  };
}

function browseBody() {
  return {
    status: 'ok',
    data: {
      mods: [item('e2e-logo', 'E2E Logo', LOGO), item('e2e-nologo', 'E2E No Logo', null)],
      pagination: {
        page: 1,
        page_size: 20,
        total_items: 2,
        total_pages: 1,
        has_next: false,
        has_prev: false,
      },
      game_version: null,
    },
  };
}

function lookupBody(slug: string, withUrls: boolean) {
  return {
    status: 'ok',
    data: {
      slug,
      urlalias: slug,
      asset_id: 0,
      name: withUrls ? 'E2E Logo' : 'E2E No Logo',
      author: 'E2E',
      description: '<p>A stubbed mod.</p>',
      latest_version: '1.0.0',
      install_mod_id: slug,
      downloads: 0,
      follows: 0,
      side: 'Both',
      compatibility: {
        status: 'compatible',
        game_version: '1.22.7',
        mod_version: '1.0.0',
        message: null,
        latest_supported_game_version: '1.22.7',
      },
      logo_url: withUrls ? LOGO : null,
      releases: [
        {
          version: '1.0.0',
          filename: `${slug}_1.0.0.zip`,
          file_id: 1,
          modidstr: slug,
          downloads: 0,
          game_versions: ['1.22.7'],
          created: '2026-11-01 00:00:00',
          changelog: null,
        },
      ],
      tags: [],
      homepage_url: withUrls ? HOMEPAGE : null,
      source_url: withUrls ? SOURCE : null,
      created: null,
      last_released: null,
      screenshots: [],
      trailer_url: null,
    },
  };
}

/** Admin key from /config.js (19.2), server shown as installed (19.7), every write refused. */
async function readOnly(page: Page) {
  await serveConfigKey(page, API_KEY);
  await pretendServerInstalled(page);
  await page.route('**/api/**', async (route) => {
    if (route.request().method() !== 'GET') {
      // Never let a write reach the server's data
      await route.fulfill({
        status: 500,
        json: { detail: { code: 'E2E_BLOCKED', message: 'read only' } },
      });
      return;
    }
    await route.fallback();
  });
}

/**
 * Stub every mod database route the pages call, and the CDN, recording each CDN request's
 * `Referer`. Registered after readOnly, so these routes run first.
 */
async function stubModDatabase(page: Page) {
  const cdn: { url: string; referer: string | undefined }[] = [];
  await readOnly(page);
  await page.route(/\/api\/v1alpha1\/mods\/browse(\?.*)?$/, (route) =>
    route.fulfill({ json: browseBody() })
  );
  await page.route(/\/api\/v1alpha1\/mods\/gameversions(\?.*)?$/, (route) =>
    route.fulfill({ json: { status: 'ok', data: { versions: ['1.22.7'] } } })
  );
  await page.route(/\/api\/v1alpha1\/mods\/tags(\?.*)?$/, (route) =>
    route.fulfill({ json: { status: 'ok', data: { tags: [] } } })
  );
  await page.route(/\/api\/v1alpha1\/mods\/lookup\/e2e-logo(\?.*)?$/, (route) =>
    route.fulfill({ json: lookupBody('e2e-logo', true) })
  );
  await page.route(/\/api\/v1alpha1\/mods\/lookup\/e2e-nologo(\?.*)?$/, (route) =>
    route.fulfill({ json: lookupBody('e2e-nologo', false) })
  );
  await page.route(`${CDN}/**`, (route) => {
    const request = route.request();
    cdn.push({ url: request.url(), referer: request.headers()['referer'] });
    return route.fulfill({ contentType: 'image/png', body: PNG });
  });
  return cdn;
}

test.describe('Mod logos and links from the mod database (Story 19.6)', () => {
  test('browse cards and the install dialog load the logo without a referrer', async ({ page }) => {
    const cdn = await stubModDatabase(page);
    await page.goto(BROWSE);

    const logo = page.getByTestId('mod-card-logo-e2e-logo');
    await expect(logo).toBeVisible({ timeout: 30_000 });
    await expect(logo).toHaveAttribute('referrerpolicy', 'no-referrer');
    await expect(page.getByTestId('mod-card-placeholder-e2e-nologo')).toBeVisible();

    await page.getByTestId('mod-card-install-e2e-logo').click();
    const dialogLogo = page.getByTestId('install-dialog-logo');
    await expect(dialogLogo).toBeVisible();
    await expect(dialogLogo).toHaveAttribute('referrerpolicy', 'no-referrer');
    await page.getByTestId('install-dialog-cancel').click();
    await expect(page.getByTestId('install-confirm-dialog')).toBeHidden();

    await expect.poll(() => cdn.length).toBeGreaterThan(0);
    expect(cdn.filter((r) => r.referer !== undefined)).toEqual([]);
  });

  test('the detail page shows the logo without a referrer and the https links', async ({
    page,
  }) => {
    const cdn = await stubModDatabase(page);
    await page.goto(`${BROWSE}/e2e-logo`);
    await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 30_000 });

    const logo = page.getByTestId('mod-detail-logo').locator('img');
    await expect(logo).toBeVisible();
    await expect(logo).toHaveAttribute('referrerpolicy', 'no-referrer');
    await expect(page.getByTestId('mod-detail-homepage-link')).toHaveAttribute('href', HOMEPAGE);
    await expect(page.getByTestId('mod-detail-source-link')).toHaveAttribute('href', SOURCE);

    await expect.poll(() => cdn.length).toBeGreaterThan(0);
    expect(cdn.filter((r) => r.referer !== undefined)).toEqual([]);
  });

  test('the detail page without a logo or links shows the placeholder and the ModDB link', async ({
    page,
  }) => {
    await stubModDatabase(page);
    await page.goto(`${BROWSE}/e2e-nologo`);
    await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 30_000 });

    await expect(page.getByTestId('mod-detail-logo')).toBeVisible();
    await expect(page.getByTestId('mod-detail-logo').locator('img')).toHaveCount(0);
    await expect(page.getByTestId('mod-detail-homepage-link')).toHaveCount(0);
    await expect(page.getByTestId('mod-detail-source-link')).toHaveCount(0);
    await expect(page.getByTestId('mod-detail-moddb-link')).toBeVisible();
  });
});
