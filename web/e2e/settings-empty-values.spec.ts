import { test, expect, type APIRequestContext } from '@playwright/test';

/**
 * E2E tests for game settings with no value and the masked password.
 *
 * Story 16.8 (FR176, VSS-7ed): settings whose value in serverconfig.json is null
 * (Description, Password, IP Address on a fresh server) are empty fields, never the
 * text "null", and the password is masked with a show/hide toggle.
 *
 * Reads only; changes no setting. Each test needs the setting it checks to have no
 * value on the running stack and is skipped, with the reason, when it has one.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) with a game server
 *   installed: `just test-e2e-web`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/settings-empty-values.spec.ts`
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const SETTINGS = '/game-server/settings';

const EMPTY_FIELDS = [
  { key: 'ServerDescription', label: 'Description' },
  { key: 'Password', label: 'Password' },
  { key: 'Ip', label: 'IP Address' },
];

async function settingValues(request: APIRequestContext): Promise<Map<string, unknown>> {
  const response = await request.get('/api/v1alpha1/config/game', {
    headers: { 'X-API-Key': API_KEY },
  });
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as {
    data: { settings: Array<{ key: string; value: unknown }> };
  };
  return new Map(body.data.settings.map((setting) => [setting.key, setting.value]));
}

test.describe('Game settings with no value', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((apiKey) => {
      localStorage.setItem('apiKey', apiKey);
    }, API_KEY);
    await page.setViewportSize({ width: 1440, height: 900 });
  });

  test('settings with no value are empty fields, never "null"', async ({ page, request }) => {
    const values = await settingValues(request);
    const empty = EMPTY_FIELDS.filter(({ key }) => values.get(key) === null);
    test.skip(empty.length === 0, 'Description, Password and IP Address all have values on this stack');

    await page.goto(SETTINGS);
    await expect(page.getByTestId('game-config-panel')).toBeVisible({ timeout: 30000 });

    for (const { label } of empty) {
      await expect(page.getByLabel(label, { exact: true })).toHaveValue('');
    }
    const inputValues = await page
      .locator('[data-testid="game-config-panel"] input')
      .evaluateAll((inputs) => inputs.map((input) => (input as HTMLInputElement).value));
    expect(inputValues).not.toContain('null');
    await expect(page.getByTestId('game-config-panel')).not.toContainText('null');
  });

  test('the password is masked and can be shown and hidden', async ({ page }) => {
    await page.goto(SETTINGS);
    await expect(page.getByTestId('game-config-panel')).toBeVisible({ timeout: 30000 });

    const password = page.getByLabel('Password', { exact: true });
    await expect(password).toHaveAttribute('type', 'password');
    await expect(password).toHaveAttribute('autocomplete', 'new-password');

    await page.getByRole('button', { name: 'Show password' }).click();
    await expect(password).toHaveAttribute('type', 'text');
    await expect(page.getByRole('button', { name: 'Hide password' })).toHaveAttribute(
      'aria-pressed',
      'true'
    );

    await page.getByRole('button', { name: 'Hide password' }).click();
    await expect(password).toHaveAttribute('type', 'password');

    // The server name is not masked
    await expect(page.getByLabel('Server Name', { exact: true })).toHaveAttribute('type', 'text');
  });
});
