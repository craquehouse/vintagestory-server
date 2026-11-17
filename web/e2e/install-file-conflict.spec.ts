import { test, expect, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey, serveModImagePlaceholders } from './config-js';

/**
 * E2E tests for an install refused because its file name is in use.
 *
 * Story 18.2 (FR199, Epic 18 ADR-4): when the release file of the mod being installed
 * has the same name as a file already in the mods directory, the API refuses with
 * 409 `MOD_FILE_CONFLICT` and a message naming the file. The install dialog shows that
 * message in the "Installation failed" toast and stays open.
 *
 * The install POST is stubbed with `page.route` to return the 409, and the installed
 * mods list is stubbed as empty, so nothing is installed and the dev stack ends as it
 * started. Mod details and browse results come from the mod database (live, or the
 * recorded answers in CI).
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080): `just test-e2e-web`,
 *   or `just docker restart` then
 *   `cd web && bunx playwright test e2e/install-file-conflict.spec.ts`
 * - Network access to the public mod database. The card in the browse test is read from
 *   the rendered grid, not hard-coded, because the database changes daily.
 *   In CI the `@moddb` tests run on recorded answers instead (e2e/README.md).
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const STUB_FILE = 'Stub-1.0.0.zip';

function conflictMessage(slug: string): string {
  return `Cannot install '${slug}': a file named ${STUB_FILE} already exists in the mods directory.`;
}

/** Replace the installed mods list (only `GET /api/v1alpha1/mods`) with no mods. */
async function fakeNoInstalledMods(page: Page) {
  await page.route(/\/api\/v1alpha1\/mods(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    await route.fulfill({ json: { status: 'ok', data: { mods: [], pending_restart: false } } });
  });
}

/** Refuse `POST /api/v1alpha1/mods` with 409 MOD_FILE_CONFLICT; returns the requested slugs. */
async function stubConflict(page: Page): Promise<string[]> {
  const posted: string[] = [];
  await page.route(/\/api\/v1alpha1\/mods(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }
    const body: { slug: string } = route.request().postDataJSON();
    posted.push(body.slug);
    await route.fulfill({
      status: 409,
      json: { detail: { code: 'MOD_FILE_CONFLICT', message: conflictMessage(body.slug) } },
    });
  });
  return posted;
}

async function firstCardSlug(page: Page): Promise<string> {
  const card = page.locator('[data-testid="mod-browse-grid"] > [data-testid^="mod-card-"]').first();
  await expect(card).toBeVisible({ timeout: 60_000 });
  return ((await card.getAttribute('data-testid')) ?? '').replace('mod-card-', '');
}

async function expectRefusalShown(page: Page, slug: string, posted: string[]) {
  const toast = page.locator('[data-sonner-toast]').filter({ hasText: 'Installation failed' });
  await expect(toast).toBeVisible();
  await expect(toast).toContainText(
    `a file named ${STUB_FILE} already exists in the mods directory`
  );
  await expect(toast).toContainText(`Cannot install '${slug}'`);
  await expect(page.getByTestId('install-confirm-dialog')).toBeVisible();
  expect(posted).toEqual([slug]);
}

// @moddb: opens the carryon entry and the browse list
test.describe(
  'Install refused when the file name is in use (Story 18.2)',
  { tag: '@moddb' },
  () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await serveModImagePlaceholders(page);
    await pretendServerInstalled(page);
  });

  test('detail page shows the refusal and keeps the dialog open', async ({ page }) => {
    test.setTimeout(120_000);
    await fakeNoInstalledMods(page);
    const posted = await stubConflict(page);

    await page.goto('/game-server/mods/browse/carryon');
    const install = page.getByTestId('mod-detail-install-button');
    await expect(install).toBeVisible({ timeout: 60_000 });
    await install.click();
    await page.getByTestId('install-dialog-confirm').click();

    await expectRefusalShown(page, 'carryon', posted);
  });

  test('browse card shows the refusal and keeps the dialog open', async ({ page }) => {
    test.setTimeout(120_000);
    await fakeNoInstalledMods(page);
    const posted = await stubConflict(page);

    await page.goto('/game-server/mods/browse?q=carry&sort=downloads');
    const slug = await firstCardSlug(page);
    const install = page.getByTestId(`mod-card-install-${slug}`);
    await expect(install).toBeVisible({ timeout: 60_000 });
    await install.click();
    await page.getByTestId('install-dialog-confirm').click();

    await expectRefusalShown(page, slug, posted);
  });
});
