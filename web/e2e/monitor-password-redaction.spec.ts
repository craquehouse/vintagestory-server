import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { fetchOnNewConnection, pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for the game server password with a Monitor key.
 *
 * Story 17.5 (FR186, VSS-qed): a Monitor key never receives the game server password.
 * `GET /config/game` gives the Password setting `value: null`, `secret: true` and
 * `configured`; the config file viewer shows `"[redacted]"` for a set password. With a
 * Monitor key, Game Settings shows "Set" or "Not set" instead of a password field; with
 * an Admin key the masked field with its show/hide button is unchanged.
 *
 * The page's key comes from `/config.js` (the web does not read localStorage), so each
 * test answers `/config.js` with `serveConfigKey` (e2e/config-js.ts) to choose the key the
 * page uses.
 *
 * Reads only: changes no setting, never starts or stops the game server, and never
 * prints the password (compared with `includes`, so a failure does not print it).
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080) with a serverconfig.json,
 *   which the seeded stack and a stack with a game server both have (the page is shown as
 *   installed by `pretendServerInstalled`): `just test-e2e-ci`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/monitor-password-redaction.spec.ts`
 * - VS_API_KEY_ADMIN exported (default from docker-compose.dev.yaml); the tests that
 *   need a real Monitor key are skipped, with the reason, when VS_API_KEY_MONITOR is not
 *   exported or is empty.
 */

// API keys from environment or default from docker-compose.dev.yaml
const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const MONITOR_KEY = process.env.VS_API_KEY_MONITOR || '';

const SETTINGS = '/game-server/settings';
const GAME_API = '/api/v1alpha1/config/game';
const SERVERCONFIG_API = '/api/v1alpha1/config/files/serverconfig.json';
const NO_MONITOR_KEY = 'VS_API_KEY_MONITOR is not set for this stack';

interface Setting {
  key: string;
  value: unknown;
  secret?: boolean;
  configured?: boolean;
}

async function getJson(request: APIRequestContext, path: string, apiKey: string) {
  const response = await request.get(path, { headers: { 'X-API-Key': apiKey } });
  expect(response.ok()).toBe(true);
  return { text: await response.text(), body: await response.json() };
}

async function passwordSetting(request: APIRequestContext, apiKey: string) {
  const { text, body } = await getJson(request, GAME_API, apiKey);
  const settings = (body as { data: { settings: Setting[] } }).data.settings;
  const password = settings.find((setting) => setting.key === 'Password');
  if (!password) throw new Error('The game settings have no Password setting');
  return { text, password };
}

/** With the Admin key: the password value (kept in memory only) and whether one is set. */
async function adminPassword(request: APIRequestContext) {
  const { password } = await passwordSetting(request, ADMIN_KEY);
  const value = password.value;
  return { value, isSet: value !== null && value !== '' };
}

async function openSettings(page: Page) {
  await page.goto(SETTINGS);
  await expect(page.getByTestId('game-config-panel')).toBeVisible({ timeout: 30000 });
  await expect(page.locator('#ServerName')).toBeVisible();
}

test.describe('Story 17.5: the server password with a Monitor key', () => {
  test('API: a Monitor key receives no password', async ({ request }) => {
    test.skip(!MONITOR_KEY, NO_MONITOR_KEY);
    const admin = await adminPassword(request);

    const game = await passwordSetting(request, MONITOR_KEY);
    expect(game.password.value).toBeNull();
    expect(game.password.secret).toBe(true);
    expect(game.password.configured).toBe(admin.isSet);

    const file = await getJson(request, SERVERCONFIG_API, MONITOR_KEY);
    const content = (file.body as { data: { content: Record<string, unknown> } }).data.content;
    // Compared as booleans, so a failure cannot print the value
    expect([null, '', '[redacted]'].some((allowed) => allowed === content.Password)).toBe(true);
    expect(content.Password === '[redacted]').toBe(admin.isSet);

    if (typeof admin.value === 'string' && admin.value.length >= 8) {
      expect(game.text.includes(admin.value)).toBe(false);
      expect(file.text.includes(admin.value)).toBe(false);
    }
  });

  test('UI: Game Settings and the file viewer show no password to a Monitor key', async ({
    page,
    request,
  }) => {
    test.skip(!MONITOR_KEY, NO_MONITOR_KEY);
    const admin = await adminPassword(request);
    await serveConfigKey(page, MONITOR_KEY);
    await pretendServerInstalled(page);
    await page.setViewportSize({ width: 1440, height: 900 });

    await openSettings(page);
    await expect(page.getByTestId('secret-setting-status-Password')).toHaveText(
      admin.isSet ? 'Set' : 'Not set'
    );
    await expect(page.locator('#Password')).toHaveCount(0);
    await expect(page.getByRole('button', { name: 'Show password' })).toHaveCount(0);

    await page.goto('/config');
    await page.getByTestId('file-manager-tab').click();
    await expect(page.getByTestId('file-list')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('file-item-serverconfig.json').click();
    const viewer = page.getByTestId('file-viewer-content');
    await expect(viewer).toContainText('"Password":');
    const text = (await viewer.textContent()) ?? '';
    expect(
      ['"Password": null', '"Password": ""', '"Password": "[redacted]"'].some((line) =>
        text.includes(line)
      )
    ).toBe(true);
    if (typeof admin.value === 'string' && admin.value.length >= 8) {
      expect(text.includes(admin.value)).toBe(false);
    }
  });

  for (const configured of [true, false]) {
    test(`UI (stubbed): a withheld password shows "${configured ? 'Set' : 'Not set'}" inside Server Info`, async ({
      page,
    }) => {
      await serveConfigKey(page, ADMIN_KEY);
      await pretendServerInstalled(page);
      await page.route(`**${GAME_API}`, async (route) => {
        if (route.request().method() !== 'GET') return route.fallback();
        const response = await fetchOnNewConnection(route);
        const body = (await response.json()) as { data: { settings: Setting[] } };
        body.data.settings = body.data.settings.map((setting) =>
          setting.key === 'Password'
            ? { ...setting, value: null, secret: true, configured }
            : setting
        );
        await route.fulfill({ response, json: body });
      });

      for (const viewport of [
        { width: 1440, height: 900 },
        { width: 390, height: 844 },
      ]) {
        await page.setViewportSize(viewport);
        await openSettings(page);

        const status = page.getByTestId('secret-setting-status-Password');
        await expect(status).toHaveText(configured ? 'Set' : 'Not set');
        await expect(page.locator('#Password')).toHaveCount(0);
        await expect(page.getByRole('button', { name: 'Show password' })).toHaveCount(0);

        const serverInfo = page.locator('[data-slot="card"]', {
          has: page.locator('[data-slot="card-title"]', { hasText: 'Server Info' }),
        });
        const cardBox = await serverInfo.boundingBox();
        const statusBox = await page.getByTestId('secret-setting-Password').boundingBox();
        if (!cardBox || !statusBox) throw new Error('No box for Server Info or the status');
        expect(statusBox.x).toBeGreaterThanOrEqual(cardBox.x);
        expect(statusBox.x + statusBox.width).toBeLessThanOrEqual(cardBox.x + cardBox.width);
        expect(statusBox.y).toBeGreaterThanOrEqual(cardBox.y);
        expect(statusBox.y + statusBox.height).toBeLessThanOrEqual(cardBox.y + cardBox.height);

        const overflow = await page
          .getByTestId('game-config-panel')
          .evaluate((panel) => panel.scrollWidth - panel.clientWidth);
        expect(overflow, `${viewport.width}px`).toBeLessThanOrEqual(0);
      }
    });
  }

  test('UI: an Admin key keeps the masked password field', async ({ page }) => {
    await serveConfigKey(page, ADMIN_KEY);
    await pretendServerInstalled(page);
    await page.setViewportSize({ width: 1440, height: 900 });

    await openSettings(page);
    await expect(page.locator('#Password')).toHaveAttribute('type', 'password');
    await expect(page.getByRole('button', { name: 'Show password' })).toBeVisible();
    await expect(page.getByTestId('secret-setting-Password')).toHaveCount(0);
  });
});
