import { test, expect, type Page } from '@playwright/test';
import { serveConfigKey } from './config-js';

/**
 * E2E tests for the mod operations the API refuses to protect a mod's file.
 *
 * Story 19.4 (FR218, FR219, FR222; Epic 19 ADR-8, ADR-9): enabling, disabling or
 * changing the version of a mod is refused with 409 when the name its file would get is
 * taken (`MOD_FILE_CONFLICT`), or when the mod's own file is gone (`MOD_FILE_MISSING`).
 * The Installed page shows the API's message in a toast and the switch keeps the mod's
 * previous state.
 *
 * Every mod route is stubbed with `page.route`: the installed list, the update status,
 * the lookups and the three writes. Any other mod request is refused with 403, so nothing
 * changes on the server, and no mod database is needed. (The real installed list is not
 * compared here: other specs install and remove mods in parallel.)
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080): `just test-e2e-web`,
 *   or `just docker restart` then
 *   `cd web && bunx playwright test e2e/mod-file-refusals.spec.ts`, with
 *   VS_API_KEY_ADMIN exported.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const INSTALLED = '/game-server/mods/installed';
const DESKTOP = { width: 1440, height: 900 };

const ENABLE_CONFLICT =
  "Cannot enable 'beta': a file named beta_1.0.0.zip already exists in the mods directory.";
const DISABLE_MISSING =
  "Cannot disable 'alpha': its file alpha_1.0.0.zip is no longer in the mods directory. " +
  'Remove the mod and install it again.';
const VERSION_CONFLICT =
  "Cannot change the version of 'alpha': a file named alpha_1.1.0.zip already exists in " +
  'the mods directory.';

function installedModJson(slug: string, enabled: boolean) {
  return {
    filename: enabled ? `${slug}_1.0.0.zip` : `${slug}_1.0.0.zip.disabled`,
    slug,
    version: '1.0.0',
    enabled,
    installed_at: '2026-11-15T00:00:00Z',
    asset_id: 0,
    name: slug,
    authors: [],
    description: null,
    side: 'Both',
  };
}

function updateItem(slug: string, offered: string | null) {
  return {
    slug,
    name: slug,
    installed_version: '1.0.0',
    status: offered ? 'update_available' : 'up_to_date',
    offered_version: offered,
    offered_compatibility: offered ? 'compatible' : null,
    offered_prerelease: offered ? false : null,
    reason: null,
    checked_at: '2026-11-15T00:00:00Z',
    error: null,
  };
}

function refusal(code: string, message: string) {
  return { status: 409, json: { detail: { code, message } } };
}

/**
 * Serve `alpha` (enabled, update to 1.1.0 offered) and `beta` (disabled), and refuse the
 * three writes as the API does. Returns the writes the page sent, as "METHOD /path".
 */
async function stubMods(page: Page): Promise<string[]> {
  const writes: string[] = [];
  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');
    if (method === 'GET' && path === '') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            mods: [installedModJson('alpha', true), installedModJson('beta', false)],
            pending_restart: false,
          },
        },
      });
      return;
    }
    if (method === 'GET' && path === '/updates') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            game_version: '1.22.7',
            checked_at: '2026-11-15T00:00:00Z',
            update_count: 1,
            mods: [updateItem('alpha', '1.1.0'), updateItem('beta', null)],
          },
        },
      });
      return;
    }
    if (method === 'GET' && path.startsWith('/lookup/')) {
      await route.fulfill({
        status: 404,
        json: { detail: { code: 'MOD_NOT_FOUND', message: path } },
      });
      return;
    }
    if (method !== 'GET') {
      writes.push(`${method} ${path}`);
    }
    if (method === 'POST' && path === '/beta/enable') {
      await route.fulfill(refusal('MOD_FILE_CONFLICT', ENABLE_CONFLICT));
      return;
    }
    if (method === 'POST' && path === '/alpha/disable') {
      await route.fulfill(refusal('MOD_FILE_MISSING', DISABLE_MISSING));
      return;
    }
    if (method === 'PUT' && path === '/alpha/version') {
      await route.fulfill(refusal('MOD_FILE_CONFLICT', VERSION_CONFLICT));
      return;
    }
    await route.fulfill({
      status: 403,
      json: { detail: { code: 'FORBIDDEN', message: 'This test changes nothing' } },
    });
  });
  return writes;
}

function toastWith(page: Page, title: string, message: string) {
  return page
    .locator('[data-sonner-toast]')
    .filter({ hasText: title })
    .filter({ hasText: message });
}

test.describe('Mod file refusals on the Installed page (Story 19.4)', () => {
  let writes: string[] = [];

  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    writes = await stubMods(page);
    await page.setViewportSize(DESKTOP);
    await page.goto(INSTALLED);
    await expect(page.getByTestId('mod-toggle-alpha')).toBeVisible({ timeout: 30_000 });
  });

  test('enabling a mod whose file name is taken shows the conflict', async ({ page }) => {
    const toggle = page.getByTestId('mod-toggle-beta');
    await expect(toggle).not.toBeChecked();

    await toggle.click();

    await expect(toastWith(page, 'Error', ENABLE_CONFLICT)).toBeVisible();
    await expect(toggle).toBeChecked({ checked: false });
    expect(writes).toEqual(['POST /beta/enable']);
  });

  test('disabling a mod whose file is gone says what to do', async ({ page }) => {
    const toggle = page.getByTestId('mod-toggle-alpha');
    await expect(toggle).toBeChecked();

    await toggle.click();

    await expect(toastWith(page, 'Error', DISABLE_MISSING)).toBeVisible();
    await expect(toggle).toBeChecked();
    expect(writes).toEqual(['POST /alpha/disable']);
  });

  test('updating to a release whose file name is taken shows the conflict', async ({ page }) => {
    await page.getByTestId('mod-update-button-alpha').click();

    await expect(toastWith(page, 'Failed to update alpha', VERSION_CONFLICT)).toBeVisible();
    expect(writes).toEqual(['PUT /alpha/version']);
  });
});
