import { test, expect, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey, serveModImagePlaceholders } from './config-js';

/**
 * E2E tests for mod detail pages that cannot fail on bad mod database data.
 *
 * Story 17.1 (FR177, FR178, Epic 17 ADR-1):
 * - `canjewelry` has releases with `"fileid": null`; its detail page opens and lists them.
 * - When a mod's details fail to load, Back to Browse on the error state returns to the
 *   same browse state as Back to Browse on the loaded page.
 *
 * The failing lookup is simulated with `page.route` for one mod only; everything else
 * comes from the mod database (live, or the recorded answers in CI).
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080): `just test-e2e-web`,
 *   or `just docker restart` then
 *   `cd web && bunx playwright test e2e/mod-detail-bad-data.spec.ts`
 * - Network access to the public mod database. The card in the second test is read from
 *   the rendered grid, not hard-coded, because the database changes daily.
 *   In CI the `@moddb` tests run on recorded answers instead (e2e/README.md).
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const BROWSE = '/game-server/mods/browse';
const BROWSE_SEARCH = '?q=jewelry&sort=downloads';

interface LookupRelease {
  version: string;
  file_id: number | null;
}

async function waitForGrid(page: Page) {
  await expect(
    page.locator('[data-testid="mod-browse-grid"] > [data-testid^="mod-card-"]').first()
  ).toBeVisible({ timeout: 60_000 });
}

async function firstCardSlug(page: Page): Promise<string> {
  const card = page.locator('[data-testid="mod-browse-grid"] > [data-testid^="mod-card-"]').first();
  return ((await card.getAttribute('data-testid')) ?? '').replace('mod-card-', '');
}

function escapeRegExp(value: string): string {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

// @moddb: opens mod database entries whose data is known to be bad
test.describe('Mod detail pages cannot fail on bad data', { tag: '@moddb' }, () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await serveModImagePlaceholders(page);
    await pretendServerInstalled(page);
  });

  test('a mod with releases that have no file opens and lists those releases', async ({ page }) => {
    const lookup = page.waitForResponse((response) =>
      response.url().includes('/mods/lookup/canjewelry')
    );
    await page.goto(`${BROWSE}/canjewelry`);

    const response = await lookup;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as { data: { releases: LookupRelease[] } };

    await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('mod-detail-error')).toHaveCount(0);

    const withoutFile = body.data.releases.filter((release) => release.file_id === null);
    for (const release of withoutFile) {
      await expect(page.getByTestId(`mod-detail-release-${release.version}`)).toBeAttached();
    }
  });

  test('Back to Browse on a failed mod returns to the same browse state as on a loaded mod', async ({
    page,
  }) => {
    test.setTimeout(120_000);
    await page.goto(`${BROWSE}${BROWSE_SEARCH}`);
    await waitForGrid(page);
    const slug = await firstCardSlug(page);
    expect(slug).not.toBe('');

    const failingLookup = new RegExp(`/api/v1alpha1/mods/lookup/${escapeRegExp(slug)}(\\?.*)?$`);
    await page.route(failingLookup, (route) =>
      route.fulfill({
        status: 500,
        json: { detail: { code: 'INTERNAL_ERROR', message: 'Simulated lookup failure' } },
      })
    );

    await page.getByTestId(`mod-card-name-${slug}`).click();
    // React Query retries a failed lookup three times before showing the error
    await expect(page.getByTestId('mod-detail-error')).toBeVisible({ timeout: 30_000 });
    await page.getByTestId('mod-detail-back').click();
    await waitForGrid(page);
    const fromError = new URL(page.url());

    await page.unroute(failingLookup);
    await page.getByTestId(`mod-card-name-${slug}`).click();
    await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 60_000 });
    await page.getByTestId('mod-detail-back').click();
    await waitForGrid(page);
    const fromPage = new URL(page.url());

    expect(`${fromError.pathname}${fromError.search}`).toBe(`${BROWSE}${BROWSE_SEARCH}`);
    expect(`${fromPage.pathname}${fromPage.search}`).toBe(`${BROWSE}${BROWSE_SEARCH}`);
  });
});
