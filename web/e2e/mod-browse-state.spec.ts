import { test, expect, type Page } from '@playwright/test';

/**
 * E2E tests for the mod browser keeping its state across a mod's detail page.
 *
 * Story 16.1 (Epic 16 ADR-1): search, filters (including the game version), sort and
 * page live in the URL; returning from a detail page by Back to Browse, the Browse
 * breadcrumb, the Browse tab or browser back restores them and scrolls to the card
 * that was opened.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) with a game version
 *   installed: `just test-e2e-web`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/mod-browse-state.spec.ts`
 * - Network access to the public mod database. Cards are picked from the rendered
 *   grid, not hard-coded, because the database changes daily.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const BROWSE = '/game-server/mods/browse';
// Broad enough to give several pages of results with the filters below
const SEARCH = 'food';

interface BrowseState {
  search: string;
  version: string;
}

async function waitForGrid(page: Page) {
  await expect(page.locator('[data-testid="mod-browse-grid"] [data-testid^="mod-card-"]').first()).toBeVisible({
    timeout: 60_000,
  });
}

async function chooseMenuItem(page: Page, trigger: RegExp | string, item: string) {
  await page.getByRole('button', { name: trigger, exact: typeof trigger === 'string' }).click();
  await page.getByRole('menuitem', { name: item, exact: true }).click();
}

/** Set a search, every single-choice filter, the sort, and go to page 2 through the UI. */
async function setUpBrowseState(page: Page): Promise<BrowseState> {
  await page.goto(BROWSE);
  await waitForGrid(page);

  await page.getByTestId('browse-search-input').fill(SEARCH);
  await expect(page).toHaveURL(new RegExp(`[?&]q=${SEARCH}(&|$)`));

  await chooseMenuItem(page, 'Side', 'Both');
  await expect(page).toHaveURL(/[?&]side=both(&|$)/);

  await chooseMenuItem(page, 'Type', 'Code Mod');
  await expect(page).toHaveURL(/[?&]type=mod(&|$)/);

  await page.getByTestId('version-filter-button').click();
  const versionOption = page.locator('[data-testid^="version-option-"]').first();
  const version = ((await versionOption.getAttribute('data-testid')) ?? '').replace('version-option-', '');
  await versionOption.click();
  await expect(page).toHaveURL(new RegExp(`[?&]version=${version.replace(/\./g, '\\.')}(&|$)`));

  await chooseMenuItem(page, /Newest/, 'Most Downloaded');
  await expect(page).toHaveURL(/[?&]sort=downloads(&|$)/);

  await waitForGrid(page);
  const page2Loaded = page.waitForResponse(
    (response) => response.url().includes('/mods/browse?') && response.url().includes('page=2&')
  );
  await page.getByRole('button', { name: 'Go to next page' }).click();
  await expect(page).toHaveURL(/[?&]page=2(&|$)/);
  await page2Loaded;
  await expect(page.locator('[data-testid="pagination"] [aria-current="page"]')).toHaveText('2');
  await page.waitForLoadState('networkidle');
  await waitForGrid(page);

  return { search: SEARCH, version };
}

/** Scroll down and open a card from the lower half of the grid; returns its slug. */
async function openCardBelowTheFold(page: Page): Promise<string> {
  const cards = page.locator('[data-testid="mod-browse-grid"] > [data-testid^="mod-card-"]');
  const count = await cards.count();
  expect(count).toBeGreaterThan(8);
  const card = cards.nth(Math.min(count - 1, 14));
  await card.scrollIntoViewIfNeeded();
  await page.evaluate(() => window.scrollBy(0, 200));
  const slug = ((await card.getAttribute('data-testid')) ?? '').replace('mod-card-', '');
  await page.getByTestId(`mod-card-name-${slug}`).click();
  await expect(page.getByTestId('mod-detail-back')).toBeVisible({ timeout: 60_000 });
  return slug;
}

function expectedBrowseSearch(state: BrowseState): string {
  return `?q=${state.search}&sort=downloads&side=both&type=mod&version=${state.version}&page=2`;
}

async function expectBrowseState(page: Page, state: BrowseState) {
  await expect(page).toHaveURL((url) => url.pathname === BROWSE && url.search === expectedBrowseSearch(state));
  await waitForGrid(page);
  await expect(page.getByTestId('browse-search-input')).toHaveValue(state.search);
  await expect(page.getByTestId('version-filter-button')).toHaveText(`v${state.version}`);
  await expect(page.getByLabel(`Remove version filter: ${state.version}`)).toBeVisible();
  await expect(page.getByLabel('Remove side filter: both')).toBeVisible();
  await expect(page.getByLabel('Remove type filter: mod')).toBeVisible();
  await expect(page.getByRole('button', { name: /Most Downloaded/ })).toBeVisible();
  await expect(page.locator('[data-testid="pagination"] [aria-current="page"]')).toHaveText('2');
}

async function expectCardInViewport(page: Page, slug: string) {
  await expect(page.getByTestId(`mod-card-${slug}`)).toBeInViewport();
  expect(await page.evaluate(() => window.scrollY)).toBeGreaterThan(0);
}

test.describe('Mod browser state survives mod details', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((apiKey) => {
      localStorage.setItem('apiKey', apiKey);
    }, API_KEY);
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  const returns: Array<[string, (page: Page) => Promise<unknown>]> = [
    ['Back to Browse', (page) => page.getByTestId('mod-detail-back').click()],
    ['the Browse breadcrumb', (page) => page.getByTestId('mod-detail-breadcrumb-browse').click()],
    ['the Browse tab', (page) => page.getByTestId('browse-tab').click()],
    ['browser back', (page) => page.goBack()],
  ];

  for (const [name, goBack] of returns) {
    test(`${name} keeps search, filters including game version, sort and page, and returns to the card`, async ({
      page,
    }) => {
      const state = await setUpBrowseState(page);
      const slug = await openCardBelowTheFold(page);

      await goBack(page);

      await expectBrowseState(page, state);
      await expectCardInViewport(page, slug);
    });
  }

  test('refresh keeps the browse state without restoring a position', async ({ page }) => {
    const state = await setUpBrowseState(page);

    await page.reload();

    await expectBrowseState(page, state);
    expect(await page.evaluate(() => window.scrollY)).toBeLessThan(50);
  });

  test('a detour through Installed keeps the state but not the old position', async ({ page }) => {
    const state = await setUpBrowseState(page);
    await openCardBelowTheFold(page);

    // Leave through the Mods breadcrumb (the Installed tab is inert on a detail page: VSS-2oz)
    await page.getByTestId('mod-detail-breadcrumb-mods').click();
    await expect(page).toHaveURL(/\/mods\/installed$/);
    await page.getByTestId('browse-tab').click();

    await expectBrowseState(page, state);
    await page.waitForTimeout(500);
    expect(await page.evaluate(() => window.scrollY)).toBeLessThan(50);
  });

  test('a copied browse link opens the same state in a new page', async ({ page, context }) => {
    const state = await setUpBrowseState(page);

    const copy = await context.newPage();
    await copy.goto(page.url());

    await expectBrowseState(copy, state);
  });
});
