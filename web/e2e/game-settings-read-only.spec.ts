import { test, expect, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for Game Settings with a key that is not Admin.
 *
 * Story 23.3 (FR313, VSS-7z3, Epic 23 ADR-6): only an Admin key can change game settings,
 * so with any other key every field and switch is disabled and the note "Only an Admin key
 * can change settings." is shown once, instead of editable fields that fail with
 * "Update failed" after typing.
 *
 * The page's key comes from `/config.js`, answered with `serveConfigKey`. The stubbed test
 * answers `/api/v1alpha1/auth/me` with the monitor role and so runs on any stack; the test
 * with a real Monitor key is skipped, with the reason, when VS_API_KEY_MONITOR is not set.
 *
 * Reads only: changes no setting and never starts or stops the game server.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080) with a serverconfig.json
 *   (the page is shown as installed by `pretendServerInstalled`): `just test-e2e-ci`, or
 *   `just docker restart` then `cd web && bunx playwright test e2e/game-settings-read-only.spec.ts`
 */

const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const MONITOR_KEY = process.env.VS_API_KEY_MONITOR || '';

const SETTINGS = '/game-server/settings';
const NOTE = 'Only an Admin key can change settings.';
const NO_MONITOR_KEY = 'VS_API_KEY_MONITOR is not set for this stack';

async function openSettings(page: Page) {
  await page.goto(SETTINGS);
  await expect(page.getByTestId('game-config-panel')).toBeVisible({ timeout: 30000 });
}

async function expectReadOnly(page: Page) {
  await expect(page.getByTestId('game-config-read-only-note')).toHaveText(NOTE);
  await expect(page.locator('#ServerName')).toBeDisabled();
  const switches = page.getByRole('switch');
  const count = await switches.count();
  for (let index = 0; index < count; index += 1) {
    await expect(switches.nth(index)).toBeDisabled();
  }
}

test.describe('Game Settings are read-only for keys that are not Admin (Story 23.3)', () => {
  test('UI (stubbed Monitor role): fields disabled and the note shown', async ({ page }) => {
    await serveConfigKey(page, ADMIN_KEY);
    await pretendServerInstalled(page);
    await page.route('**/api/v1alpha1/auth/me', (route) =>
      route.fulfill({ json: { status: 'ok', data: { role: 'monitor' } } })
    );
    const posts: string[] = [];
    page.on('request', (request) => {
      if (request.method() === 'POST') posts.push(request.url());
    });

    await openSettings(page);
    await expectReadOnly(page);

    expect(posts).toEqual([]);
  });

  test('UI: no note and editable fields for the Admin key', async ({ page }) => {
    await serveConfigKey(page, ADMIN_KEY);
    await pretendServerInstalled(page);

    await openSettings(page);

    await expect(page.locator('#ServerName')).toBeEnabled();
    await expect(page.getByTestId('game-config-read-only-note')).toHaveCount(0);
  });

  test('UI: a real Monitor key sees the settings read-only', async ({ page }) => {
    test.skip(!MONITOR_KEY, NO_MONITOR_KEY);
    await serveConfigKey(page, MONITOR_KEY);
    await pretendServerInstalled(page);

    await openSettings(page);
    await expectReadOnly(page);
  });
});
