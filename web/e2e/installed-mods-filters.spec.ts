import { test, expect, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for the installed mods filters (Story 24.7, FR341, FR342).
 *
 * The installed mods list is replaced with `page.route`, so the spec installs nothing
 * and runs on any stack.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL: `just test-e2e-ci e2e/installed-mods-filters.spec.ts`
 */

const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const MODS = [
  { slug: 'carryon', name: 'Carry On' },
  { slug: 'smithingplus', name: 'Smithing Plus' },
];

async function fakeInstalledMods(page: Page) {
  await page.route(/\/api\/v1alpha1\/mods(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({
      json: {
        status: 'ok',
        data: {
          mods: MODS.map(({ slug, name }) => ({
            filename: `${slug}_1.0.0.zip`,
            slug,
            version: '1.0.0',
            enabled: true,
            installed_at: '2026-11-13T00:00:00Z',
            asset_id: 0,
            name,
            authors: [],
            description: null,
            side: 'Both',
          })),
          pending_restart: false,
        },
      },
    });
  });
}

test.describe('Installed mods filters (Story 24.7)', () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
    await fakeInstalledMods(page);
  });

  test('a filtered URL opened directly shows the filtered list', async ({ page }) => {
    await page.goto('/game-server/mods/installed?q=SMITH');

    await expect(page.getByTestId('mod-row-smithingplus')).toBeVisible({ timeout: 30000 });
    await expect(page.getByTestId('mod-row-carryon')).toHaveCount(0);
    await expect(page.getByTestId('installed-mods-filter-query')).toHaveValue('SMITH');
    await expect(page.getByTestId('mod-filter-status')).toHaveText(/Showing 1 of 2 mods/);
  });

  test('typing filters the list and Clear filters shows every mod again', async ({ page }) => {
    await page.goto('/game-server/mods/installed');
    await expect(page.getByTestId('mod-row-carryon')).toBeVisible({ timeout: 30000 });

    await page.getByTestId('installed-mods-filter-query').fill('carry');
    await expect(page.getByTestId('mod-row-smithingplus')).toHaveCount(0);
    await expect(page).toHaveURL(/[?&]q=carry/);

    await page.getByTestId('mod-filter-clear').click();
    await expect(page.getByTestId('mod-row-smithingplus')).toBeVisible();
    await expect(page).not.toHaveURL(/[?&]q=/);
  });
});
