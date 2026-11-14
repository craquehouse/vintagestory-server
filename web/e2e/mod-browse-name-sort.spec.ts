import { test, expect, type Page, type Response } from '@playwright/test';

/**
 * E2E tests for the mod browser's Name (A-Z) sort.
 *
 * Story 16.8 (FR175, VSS-stm.1): the API sorts by name (ignoring surrounding spaces,
 * letter case and accents) and the browser pages through the result like the other
 * sorts. Before, the web UI asked for 1,000 mods per page, the API answered 422 and
 * the grid stayed empty.
 *
 * Reads only. Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) that can reach the mod
 *   database: `just test-e2e-web`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/mod-browse-name-sort.spec.ts`
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const BROWSE = '/game-server/mods/browse';

interface BrowseMod {
  slug: string;
  name: string;
}

interface BrowsePage {
  url: URL;
  mods: BrowseMod[];
  totalPages: number;
}

/** The API's name sort key (`_name_sort_key` in services/mod_api.py), close enough for ordering checks. */
function nameKey(name: string): string {
  return name
    .trim()
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/ß/g, 'ss');
}

/** Compare by code point, as Python does (not by UTF-16 code unit). */
function compareCodePoints(a: string, b: string): number {
  const left = Array.from(a);
  const right = Array.from(b);
  for (let i = 0; i < Math.min(left.length, right.length); i++) {
    const diff = (left[i].codePointAt(0) ?? 0) - (right[i].codePointAt(0) ?? 0);
    if (diff !== 0) return diff;
  }
  return left.length - right.length;
}

function expectAlphabetical(names: string[]) {
  for (let i = 1; i < names.length; i++) {
    expect(
      compareCodePoints(nameKey(names[i - 1]), nameKey(names[i])),
      `"${names[i - 1]}" should come before "${names[i]}"`
    ).toBeLessThanOrEqual(0);
  }
}

function isBrowseResponse(response: Response): boolean {
  return new URL(response.url()).pathname.endsWith('/api/v1alpha1/mods/browse');
}

/** Every browse request the page makes, with its status. */
function recordBrowseRequests(page: Page): Array<{ url: URL; status: number }> {
  const seen: Array<{ url: URL; status: number }> = [];
  page.on('response', (response) => {
    if (isBrowseResponse(response)) {
      seen.push({ url: new URL(response.url()), status: response.status() });
    }
  });
  return seen;
}

/** Navigate (or act) and return the browse page the API answered with. */
async function loadBrowsePage(page: Page, action: () => Promise<unknown>): Promise<BrowsePage> {
  const [response] = await Promise.all([
    page.waitForResponse((r) => isBrowseResponse(r) && r.status() === 200, { timeout: 30000 }),
    action(),
  ]);
  const body = (await response.json()) as {
    data: { mods: BrowseMod[]; pagination: { total_pages: number } };
  };
  return {
    url: new URL(response.url()),
    mods: body.data.mods,
    totalPages: body.data.pagination.total_pages,
  };
}

/** The cards on screen, in order, match the API's page. */
async function expectCardsMatch(page: Page, mods: BrowseMod[]) {
  await expect(page.getByTestId(`mod-card-${mods[0].slug}`)).toBeVisible({ timeout: 30000 });
  const cardIds = await page
    .locator('[data-testid^="mod-card-name-"]')
    .evaluateAll((elements) => elements.map((el) => el.getAttribute('data-testid')));
  expect(cardIds).toEqual(mods.map((mod) => `mod-card-name-${mod.slug}`));
}

test.describe('Mod browser Name (A-Z) sort', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((apiKey) => {
      localStorage.setItem('apiKey', apiKey);
    }, API_KEY);
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('choosing Name (A-Z) shows the first page alphabetically with page controls', async ({ page }) => {
    const requests = recordBrowseRequests(page);
    await page.goto(BROWSE);
    await expect(page.getByTestId('browse-results-count')).toBeVisible({ timeout: 30000 });

    const first = await loadBrowsePage(page, async () => {
      await page.getByRole('button', { name: /newest/i }).click();
      await page.getByRole('menuitem', { name: 'Name (A-Z)' }).click();
    });

    expect(first.url.searchParams.get('sort')).toBe('name');
    expect(first.mods).toHaveLength(20);
    expectAlphabetical(first.mods.map((mod) => mod.name));
    await expectCardsMatch(page, first.mods);
    await expect(page).toHaveURL(/[?&]sort=name/);
    await expect(page.getByTestId('pagination')).toBeVisible();
    await expect(page.getByTestId('browse-results-count')).toHaveText(/Showing 20 of \d+ mods/);

    for (const request of requests) {
      expect(Number(request.url.searchParams.get('page_size'))).toBeLessThanOrEqual(100);
      expect(request.status).not.toBe(422);
    }
  });

  test('pages 1, 2 and a later page continue the alphabetical order', async ({ page }) => {
    const requests = recordBrowseRequests(page);

    const page1 = await loadBrowsePage(page, () => page.goto(`${BROWSE}?sort=name`));
    await expectCardsMatch(page, page1.mods);

    const page2 = await loadBrowsePage(page, () =>
      page.getByRole('button', { name: 'Go to next page' }).click()
    );
    expect(page2.url.searchParams.get('page')).toBe('2');
    await expect(page).toHaveURL(/[?&]page=2/);
    await expectCardsMatch(page, page2.mods);
    expectAlphabetical([...page1.mods, ...page2.mods].map((mod) => mod.name));

    const later = Math.max(3, Math.floor(page1.totalPages / 2));
    const laterPage = await loadBrowsePage(page, () => page.goto(`${BROWSE}?sort=name&page=${later}`));
    expect(laterPage.url.searchParams.get('page')).toBe(String(later));
    await expectCardsMatch(page, laterPage.mods);
    expectAlphabetical(laterPage.mods.map((mod) => mod.name));
    // The later page starts after page 2 ends
    expect(
      compareCodePoints(
        nameKey(page2.mods[page2.mods.length - 1].name),
        nameKey(laterPage.mods[0].name)
      )
    ).toBeLessThanOrEqual(0);
    await expect(page.getByText(new RegExp(`Page ${later} of ${page1.totalPages}`))).toBeVisible();

    for (const request of requests) {
      expect(request.url.searchParams.get('sort')).toBe('name');
      expect(Number(request.url.searchParams.get('page_size'))).toBeLessThanOrEqual(100);
      expect(request.status).not.toBe(422);
    }
  });

  test('a search with Name (A-Z) lists the matching mods alphabetically', async ({ page }) => {
    const result = await loadBrowsePage(page, () => page.goto(`${BROWSE}?q=farm&sort=name`));

    expect(result.url.searchParams.get('search')).toBe('farm');
    expect(result.url.searchParams.get('sort')).toBe('name');
    expect(result.mods.length).toBeGreaterThan(1);
    expectAlphabetical(result.mods.map((mod) => mod.name));
    await expectCardsMatch(page, result.mods);
  });
});
