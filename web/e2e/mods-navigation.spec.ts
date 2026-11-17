import { test, expect, type Page, type Request } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey, serveModImagePlaceholders } from './config-js';

/**
 * E2E tests for navigating the Mods pages.
 *
 * Story 17.7: on a mod's detail page the Browse tab is the active tab, the Installed
 * tab opens the installed list, and the Browse tab opens the browse state (Epic 16
 * ADR-1 decision 3). A browse link whose page is beyond the results is replaced by the
 * last page, without a new history entry and without a second request.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080): `just docker restart`
 *   then `cd web && bunx playwright test e2e/mods-navigation.spec.ts`
 * - Network access to the public mod database. Cards are picked from the rendered
 *   grid, not hard-coded, because the database changes daily.
 *   In CI the `@moddb` tests run on recorded answers instead (e2e/README.md).
 * - Read-only: nothing is installed, removed or changed.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const BROWSE = '/game-server/mods/browse';
const INSTALLED = '/game-server/mods/installed';
const BROWSE_SEARCH = '?q=food&sort=downloads';
const NO_MATCH = 'zzqqxxnomodmatches';

async function waitForGrid(page: Page) {
  await expect(
    page.locator('[data-testid="mod-browse-grid"] [data-testid^="mod-card-"]').first()
  ).toBeVisible({
    timeout: 60_000,
  });
}

/** Slug of the first card in the grid. */
async function firstCardSlug(page: Page): Promise<string> {
  const card = page.locator('[data-testid="mod-browse-grid"] > [data-testid^="mod-card-"]').first();
  return ((await card.getAttribute('data-testid')) ?? '').replace('mod-card-', '');
}

/** Collects every browse request the page makes. */
function collectBrowseRequests(page: Page): Request[] {
  const requests: Request[] = [];
  page.on('request', (request) => {
    if (request.url().includes('/api/v1alpha1/mods/browse?')) requests.push(request);
  });
  return requests;
}

/** Waits long enough for a second browse request to have started, if one were coming. */
async function settle(page: Page) {
  await page.waitForTimeout(1500);
}

// @moddb: navigates between browse pages and mod details
test.describe('Mods navigation', { tag: '@moddb' }, () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await serveModImagePlaceholders(page);
    await pretendServerInstalled(page);
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('on a mod detail page Browse is the active tab, Installed opens the list, Browse returns', async ({
    page,
  }) => {
    await page.goto(`${BROWSE}${BROWSE_SEARCH}`);
    await waitForGrid(page);
    const slug = await firstCardSlug(page);
    await page.getByTestId(`mod-card-name-${slug}`).click();
    await expect(page.getByTestId('mod-detail-back')).toBeVisible({ timeout: 60_000 });

    await expect(page.getByTestId('browse-tab')).toHaveAttribute('aria-selected', 'true');
    await expect(page.getByTestId('installed-tab')).toHaveAttribute('aria-selected', 'false');

    // One history entry per tab click, so back returns to the detail page
    await page.getByTestId('installed-tab').click();
    await expect(page).toHaveURL((url) => url.pathname === INSTALLED);
    await expect(page.getByTestId('installed-tab-content')).toBeVisible();

    await page.goBack();
    await expect(page.getByTestId('mod-detail-back')).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('browse-tab')).toHaveAttribute('aria-selected', 'true');

    // The active Browse tab returns to the state the mod was opened from, adding one entry
    await page.getByTestId('browse-tab').click();
    await expect(page).toHaveURL((url) => url.pathname === BROWSE && url.search === BROWSE_SEARCH);
    await waitForGrid(page);
    await page.goBack();
    await expect(page.getByTestId('mod-detail-back')).toBeVisible({ timeout: 60_000 });
  });

  test('the Browse tab on a detail page opened directly opens the default browser', async ({
    page,
    context,
  }) => {
    await page.goto(`${BROWSE}${BROWSE_SEARCH}`);
    await waitForGrid(page);
    const slug = await firstCardSlug(page);

    // A new page has its own, empty sessionStorage: no browse state to return to
    const direct = await context.newPage();
    // Routes set on `page` do not apply to a new page; the images' routes are on the context
    await serveConfigKey(direct, API_KEY);
    await pretendServerInstalled(direct);
    await direct.setViewportSize({ width: 1440, height: 900 });
    await direct.goto(`${BROWSE}/${slug}`);
    await expect(direct.getByTestId('mod-detail-back')).toBeVisible({ timeout: 60_000 });
    await expect(direct.getByTestId('browse-tab')).toHaveAttribute('aria-selected', 'true');

    await direct.getByTestId('browse-tab').click();

    await expect(direct).toHaveURL((url) => url.pathname === BROWSE && url.search === '');
    await waitForGrid(direct);
  });

  test('a browse link past the last page opens the last page without a new history entry', async ({
    page,
  }) => {
    await page.goto(INSTALLED);
    await expect(page.getByTestId('installed-tab-content')).toBeVisible();
    const historyBefore = await page.evaluate(() => history.length);
    const requests = collectBrowseRequests(page);

    const firstResponse = page.waitForResponse((response) =>
      response.url().includes('/api/v1alpha1/mods/browse?')
    );
    await page.goto(`${BROWSE}${BROWSE_SEARCH}&page=9999`);
    const body: { data: { pagination: { total_pages: number } } } = await (
      await firstResponse
    ).json();
    const totalPages = body.data.pagination.total_pages;

    const expectedSearch = totalPages > 1 ? `${BROWSE_SEARCH}&page=${totalPages}` : BROWSE_SEARCH;
    await expect(page).toHaveURL((url) => url.pathname === BROWSE && url.search === expectedSearch);
    await waitForGrid(page);
    if (totalPages > 1) {
      await expect(page.locator('[data-testid="pagination"] [aria-current="page"]')).toHaveText(
        String(totalPages)
      );
      await expect(page.getByTestId('pagination')).toContainText(
        `Page ${totalPages} of ${totalPages}`
      );
    }
    await settle(page);
    expect(requests).toHaveLength(1);
    expect(await page.evaluate(() => history.length)).toBe(historyBefore + 1);

    await page.goBack();
    await expect(page).toHaveURL((url) => url.pathname === INSTALLED);
  });

  test('a browse link past the end of a search without results opens page 1', async ({ page }) => {
    const requests = collectBrowseRequests(page);

    await page.goto(`${BROWSE}?q=${NO_MATCH}&page=3`);

    await expect(page).toHaveURL(
      (url) => url.pathname === BROWSE && url.search === `?q=${NO_MATCH}`
    );
    await expect(page.getByTestId('mod-browse-grid-empty')).toBeVisible({ timeout: 60_000 });
    await settle(page);
    expect(requests).toHaveLength(1);
  });
});
