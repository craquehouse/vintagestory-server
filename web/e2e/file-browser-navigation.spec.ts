import { test, expect, type Page, type APIRequestContext } from '@playwright/test';

/**
 * E2E tests for directory navigation in the File Manager (Settings → File Manager).
 *
 * Story 16.7 (FR174, VSS-8lh): the current path is a breadcrumb of clickable segments
 * (`serverdata › Logs › Archive`) that replaces the Back button. Also the directory
 * navigation test of VSS-3mr.
 *
 * Read-only: the nested path is discovered through the directory listing API, so the
 * spec does not depend on fixed directory names, and nothing in serverdata is created,
 * changed or deleted.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) whose serverdata has
 *   at least one directory inside another (a game server that has run has, e.g.,
 *   `Logs/Archive`): `just test-e2e-web`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/file-browser-navigation.spec.ts`
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const DIRECTORIES_API = '/api/v1alpha1/config/directories';
/** Most directory listings requested while looking for a nested path. */
const MAX_LISTINGS = 60;
const MAX_DEPTH = 3;

async function listDirectories(request: APIRequestContext, path: string[]): Promise<string[]> {
  const query = path.length ? `?directory=${encodeURIComponent(path.join('/'))}` : '';
  const response = await request.get(`${DIRECTORIES_API}${query}`, {
    headers: { 'X-API-Key': API_KEY },
  });
  expect(response.ok(), `GET ${DIRECTORIES_API}${query}`).toBeTruthy();
  const body = (await response.json()) as { data: { directories: string[] } };
  // The panel hides directories starting with '.'
  return body.data.directories.filter((name) => !name.startsWith('.'));
}

/**
 * Breadth-first search for the deepest visible directory path (up to MAX_DEPTH levels).
 * Fails when serverdata has no directory inside another.
 */
async function findNestedPath(request: APIRequestContext): Promise<string[]> {
  const queue: string[][] = [[]];
  let deepest: string[] = [];
  let listings = 0;
  while (queue.length && listings < MAX_LISTINGS) {
    const path = queue.shift()!;
    listings += 1;
    for (const name of await listDirectories(request, path)) {
      const child = [...path, name];
      if (child.length > deepest.length) deepest = child;
      if (child.length < MAX_DEPTH) queue.push(child);
    }
    if (deepest.length === MAX_DEPTH) break;
  }
  if (deepest.length < 2) {
    throw new Error('serverdata needs a directory inside another directory (e.g. Logs/Archive)');
  }
  return deepest;
}

async function openFileManager(page: Page, width: number, height = 900) {
  await page.setViewportSize({ width, height });
  await page.addInitScript((apiKey) => {
    localStorage.setItem('apiKey', apiKey);
  }, API_KEY);
  await page.goto('/config');
  await page.getByTestId('file-manager-tab').click();
  await expect(page.getByTestId('file-manager-panel')).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId('file-list')).toBeVisible();
}

const breadcrumb = (page: Page) => page.getByRole('navigation', { name: 'Breadcrumb' });
const current = (page: Page) => page.getByTestId('path-breadcrumb-current');

/** Opens each directory of `path` from the list, checking the breadcrumb at each level. */
async function openPath(page: Page, path: string[]) {
  for (let level = 0; level < path.length; level += 1) {
    await page.getByTestId(`file-item-${path[level]}`).click();
    await expect(current(page)).toHaveText(path[level]);
    await expect(current(page)).toHaveAttribute('aria-current', 'page');
    await expect(breadcrumb(page).getByRole('button')).toHaveText([
      'serverdata',
      ...path.slice(0, level),
    ]);
  }
}

async function documentOverflowX(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

test.describe('Story 16.7: file browser breadcrumbs', () => {
  let nestedPath: string[];

  test.beforeAll(async ({ request }) => {
    nestedPath = await findNestedPath(request);
  });

  test('shows the path as segments and jumps to the root in one click', async ({ page }) => {
    await openFileManager(page, 1280);

    // At the root: only the current location, no Back button
    await expect(current(page)).toHaveText('serverdata');
    await expect(breadcrumb(page).getByRole('button')).toHaveCount(0);
    await expect(page.getByTestId('file-manager-back')).toHaveCount(0);

    await openPath(page, nestedPath);
    await expect(page.getByTestId('file-manager-back')).toHaveCount(0);

    await page.getByTestId('path-breadcrumb-root').click();

    await expect(current(page)).toHaveText('serverdata');
    await expect(breadcrumb(page).getByRole('button')).toHaveCount(0);
    await expect(page.getByTestId(`file-item-${nestedPath[0]}`)).toBeVisible();
  });

  test('jumps to an ancestor segment', async ({ page }) => {
    await openFileManager(page, 1280);
    await openPath(page, nestedPath);

    await page.getByTestId('path-breadcrumb-segment-0').click();

    await expect(current(page)).toHaveText(nestedPath[0]);
    await expect(breadcrumb(page).getByRole('button')).toHaveText(['serverdata']);
    await expect(page.getByTestId(`file-item-${nestedPath[1]}`)).toBeVisible();
    await expect(page.getByTestId('file-viewer-empty')).toBeVisible();
  });

  test('navigates with the keyboard and keeps focus on the breadcrumb', async ({ page }) => {
    await openFileManager(page, 1280);
    await openPath(page, nestedPath);

    await page.getByTestId('path-breadcrumb-root').focus();
    await page.keyboard.press('Tab');
    await expect(page.getByTestId('path-breadcrumb-segment-0')).toBeFocused();
    await page.keyboard.press('Enter');

    await expect(current(page)).toHaveText(nestedPath[0]);
    await expect(current(page)).toBeFocused();
    await expect(page.getByTestId(`file-item-${nestedPath[1]}`)).toBeVisible();
  });

  test('stays inside the panel on a phone and adds no sideways scrolling', async ({ page }) => {
    await openFileManager(page, 390, 844);
    const overflowAtRoot = await documentOverflowX(page);

    await openPath(page, nestedPath);

    const panel = await page.getByTestId('file-manager-panel').boundingBox();
    const nav = await breadcrumb(page).boundingBox();
    if (!panel || !nav) throw new Error('No box for the panel or the breadcrumb');
    expect(nav.x).toBeGreaterThanOrEqual(panel.x - 0.5);
    expect(nav.x + nav.width).toBeLessThanOrEqual(panel.x + panel.width + 0.5);

    const listOverflow = await breadcrumb(page)
      .locator('ol')
      .evaluate((list) => list.scrollWidth - list.clientWidth);
    expect(listOverflow).toBeLessThanOrEqual(0);

    // Every segment is inside the panel (long names truncate, segments wrap)
    for (const segment of await breadcrumb(page).locator('li').all()) {
      const b = await segment.boundingBox();
      if (!b) throw new Error('No box for a breadcrumb segment');
      expect(b.x + b.width).toBeLessThanOrEqual(panel.x + panel.width + 0.5);
    }

    expect(await documentOverflowX(page)).toBe(overflowAtRoot);
  });
});
