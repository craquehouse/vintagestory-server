import { test, expect, type APIRequestContext, type Page, type Route } from '@playwright/test';

/**
 * E2E tests for the file browser with a Monitor key.
 *
 * Story 19.1 (FR208, FR233, Epic 19 ADR-3):
 * - A Monitor key lists and reads the root of the server data directory and `ModConfig`
 *   only; any other directory is 403 FORBIDDEN, and the listings are never cached.
 * - Settings, File Manager shows the line "Some folders are only shown to Admin keys."
 *   to a role other than Admin. It names no folder, and it is not shown to the Admin key
 *   or while the role is loading.
 *
 * The page's key comes from `/config.js` (the web does not read localStorage), so each
 * UI test answers `/config.js` with `page.route` to choose the key the page uses. The
 * stubbed tests also answer `/api/v1alpha1/auth/me` with `page.route`.
 *
 * Reads only: changes nothing in the server data directory, never starts or stops the
 * game server, takes no screenshots, and asserts no instance data in its messages.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) built from this branch:
 *   `just docker restart` then `cd web && bunx playwright test e2e/file-browser-monitor-note.spec.ts`
 * - VS_API_KEY_ADMIN exported (default from docker-compose.dev.yaml); the tests that
 *   need a real Monitor key are skipped, with the reason, when VS_API_KEY_MONITOR is not
 *   exported or is empty.
 */

// API keys from environment or default from docker-compose.dev.yaml
const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const MONITOR_KEY = process.env.VS_API_KEY_MONITOR || '';

const NOTE = 'Some folders are only shown to Admin keys.';
const AUTH_ME = '**/api/v1alpha1/auth/me';
const DIRECTORIES_API = '/api/v1alpha1/config/directories';
const FILES_API = '/api/v1alpha1/config/files';
const NO_MONITOR_KEY = 'VS_API_KEY_MONITOR is not set for this stack';

interface ErrorBody {
  detail: { code: string; message: string };
}

/** Makes the page use `apiKey`, whatever key the stack hands the web UI. */
async function usePageKey(page: Page, apiKey: string) {
  await page.route('**/config.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey })};`,
    })
  );
}

async function stubRole(page: Page, role: string) {
  await page.route(AUTH_ME, (route) =>
    route.fulfill({ json: { status: 'ok', data: { role } } })
  );
}

async function directories(request: APIRequestContext, apiKey: string, directory?: string) {
  const query = directory === undefined ? '' : `?directory=${encodeURIComponent(directory)}`;
  const response = await request.get(`${DIRECTORIES_API}${query}`, {
    headers: { 'X-API-Key': apiKey },
  });
  expect(response.status(), `GET ${DIRECTORIES_API}${query}`).toBe(200);
  expect(response.headers()['cache-control']).toBe('no-store');
  const body: { data: { directories: string[] } } = await response.json();
  return body.data.directories;
}

async function openFileManager(page: Page) {
  await page.goto('/config');
  await page.getByTestId('file-manager-tab').click();
  await expect(page.getByTestId('file-manager-panel')).toBeVisible({ timeout: 30000 });
  await expect(page.getByTestId('file-list')).toBeVisible();
}

const FOLDER_LABEL = ' folder, press Enter to open';
const FILE_LABEL = ' file, press Enter to view';

/** The panel's list as [directories, files], each in order, read from the item labels. */
async function listedItems(page: Page) {
  const labels = await page
    .getByTestId('file-list')
    .getByRole('option')
    .evaluateAll((items) => items.map((item) => item.getAttribute('aria-label') ?? ''));
  const named = (suffix: string) =>
    labels.filter((label) => label.endsWith(suffix)).map((label) => label.slice(0, -suffix.length));
  return [named(FOLDER_LABEL), named(FILE_LABEL)];
}

test.describe('Story 19.1: the file browser with a Monitor key', () => {
  test('UI (stubbed Monitor role): the note names no folder and fits at phone width', async ({
    page,
    request,
  }) => {
    const adminDirectories = await directories(request, ADMIN_KEY);
    await usePageKey(page, ADMIN_KEY);
    await stubRole(page, 'monitor');

    for (const viewport of [
      { width: 1440, height: 900 },
      { width: 390, height: 844 },
    ]) {
      await page.setViewportSize(viewport);
      await openFileManager(page);

      const note = page.getByTestId('file-manager-admin-note');
      await expect(note).toHaveText(NOTE);
      await expect(
        page.getByTestId('file-manager-panel').getByTestId('file-manager-admin-note')
      ).toHaveCount(1);
      const words = new Set(NOTE.replace(/[.]/g, '').split(' '));
      expect(adminDirectories.filter((name) => words.has(name))).toEqual([]);

      const overflow = await page.evaluate(
        () => document.documentElement.scrollWidth - document.documentElement.clientWidth
      );
      expect(overflow, `${viewport.width}px`).toBe(0);
    }
  });

  test('UI: no note for the Admin key', async ({ page }) => {
    await usePageKey(page, ADMIN_KEY);
    await page.setViewportSize({ width: 1440, height: 900 });

    const authMe = page.waitForResponse((response) => response.url().endsWith('/auth/me'));
    await openFileManager(page);
    expect((await authMe).ok()).toBe(true);
    await expect(page.getByTestId('file-manager-admin-note')).toHaveCount(0);
  });

  test('UI: no note while the role is loading', async ({ page }) => {
    await usePageKey(page, ADMIN_KEY);
    await page.setViewportSize({ width: 1440, height: 900 });
    const held: Route[] = [];
    const hold = (route: Route) => {
      held.push(route);
    };
    await page.route(AUTH_ME, hold);

    await openFileManager(page);
    await expect.poll(() => held.length).toBeGreaterThan(0);
    await expect(page.getByTestId('file-manager-admin-note')).toHaveCount(0);

    await page.unroute(AUTH_ME, hold);
    for (const route of held) await route.abort().catch(() => undefined);
  });

  test('API: a real Monitor key lists the root and ModConfig only', async ({ request }) => {
    test.skip(!MONITOR_KEY, NO_MONITOR_KEY);
    const adminDirectories = await directories(request, ADMIN_KEY);

    const monitorDirectories = await directories(request, MONITOR_KEY);
    expect(monitorDirectories.every((name) => name === 'ModConfig')).toBe(true);
    expect(monitorDirectories.every((name) => adminDirectories.includes(name))).toBe(true);

    const missing = `no-such-dir-${Date.now()}`;
    for (const directory of ['Playerdata', 'playerdata', 'Saves', missing]) {
      for (const api of [DIRECTORIES_API, FILES_API]) {
        const url = `${api}?directory=${encodeURIComponent(directory)}`;
        const response = await request.get(url, { headers: { 'X-API-Key': MONITOR_KEY } });
        expect(response.status(), url).toBe(403);
        const error: ErrorBody = await response.json();
        expect(error.detail.code).toBe('FORBIDDEN');
        expect(response.headers()['cache-control']).toBe('no-store');
      }
    }

    const log = `${FILES_API}/Logs/server-main.log`;
    const monitorLog = await request.get(log, { headers: { 'X-API-Key': MONITOR_KEY } });
    expect(monitorLog.status()).toBe(403);
    const adminLog = await request.get(log, { headers: { 'X-API-Key': ADMIN_KEY } });
    expect(adminLog.status()).toBe(400);
    const adminError: ErrorBody = await adminLog.json();
    expect(adminError.detail.code).toBe('CONFIG_FILE_NOT_SUPPORTED');

    const serverconfig = await request.get(`${FILES_API}/serverconfig.json`, {
      headers: { 'X-API-Key': MONITOR_KEY },
    });
    expect(serverconfig.status()).toBe(200);

    const files = await request.get(FILES_API, { headers: { 'X-API-Key': MONITOR_KEY } });
    expect(files.status()).toBe(200);
    expect(files.headers()['cache-control']).toBe('no-store');
  });

  test('UI: a real Monitor key sees the note and only what the API lists', async ({
    page,
    request,
  }) => {
    test.skip(!MONITOR_KEY, NO_MONITOR_KEY);
    const expectedDirectories = (await directories(request, MONITOR_KEY)).filter(
      (name) => !name.startsWith('.')
    );
    const filesResponse = await request.get(FILES_API, { headers: { 'X-API-Key': MONITOR_KEY } });
    expect(filesResponse.status()).toBe(200);
    const filesBody: { data: { files: string[] } } = await filesResponse.json();
    const expectedFiles = filesBody.data.files;
    await usePageKey(page, MONITOR_KEY);
    await page.setViewportSize({ width: 1440, height: 900 });

    await openFileManager(page);
    await expect(page.getByTestId('file-manager-admin-note')).toHaveText(NOTE);
    await expect.poll(() => listedItems(page)).toEqual([expectedDirectories, expectedFiles]);
  });
});
