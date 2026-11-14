import { test, expect, type Page } from '@playwright/test';

/**
 * E2E tests for the Installed mods layout on phones and desktops.
 *
 * Story 16.5 (FR172, VSS-rr5): below the `md` breakpoint (768px) each installed mod is
 * a card with its version, update status and Update action, enable toggle and remove
 * action, and nothing scrolls sideways; at `md` and up the table is unchanged.
 *
 * The installed mods list, the update status, the compatibility lookups and every
 * write (version change, enable/disable, remove) are answered with `page.route`, so the
 * spec reads and changes nothing in the server's data and needs no mod database access.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080): `just test-e2e-web`,
 *   or `just docker restart` then
 *   `cd web && bunx playwright test e2e/installed-mods-phone.spec.ts`
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const INSTALLED = '/game-server/mods/installed';
const PHONE = { width: 390, height: 844 };
const DESKTOP = { width: 1440, height: 900 };

const LONG_NAME = 'An Extraordinarily Long Mod Name That Must Wrap Inside Its Card';

const MODS = [
  { slug: 'longnamemod', name: LONG_NAME, version: '1.0.0-rc.12', enabled: true },
  { slug: 'oldmod', name: 'Old Mod', version: '2.3.4', enabled: true },
  { slug: 'offmod', name: 'Off Mod', version: '0.1.0', enabled: false },
];

const COMPATIBILITY: Record<string, { status: string; message: string; latest: string }> = {
  longnamemod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
  oldmod: {
    status: 'incompatible',
    message: 'Last supported game version: 1.21.1.',
    latest: '1.21.1',
  },
  offmod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
};

function updateStatus(slug: string, name: string, version: string) {
  const offered = slug === 'longnamemod';
  return {
    slug,
    name,
    installed_version: version,
    status: offered ? 'update_available' : 'up_to_date',
    offered_version: offered ? '1.0.0-rc.13' : null,
    offered_compatibility: offered ? 'compatible' : null,
    offered_prerelease: offered ? true : null,
    reason: null,
    checked_at: '2026-11-13T00:00:00Z',
    error: null,
  };
}

/** Serve the installed mods, their update status and lookups; refuse every write. */
async function fakeInstalledMods(page: Page) {
  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');

    if (request.method() === 'GET' && path === '') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            mods: MODS.map(({ slug, name, version, enabled }) => ({
              filename: `${slug}_${version}.zip`,
              slug,
              version,
              enabled,
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
      return;
    }

    if (request.method() === 'GET' && path === '/updates') {
      const updates = MODS.map(({ slug, name, version }) => updateStatus(slug, name, version));
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            game_version: '1.22.7',
            checked_at: '2026-11-13T00:00:00Z',
            update_count: 1,
            mods: updates,
          },
        },
      });
      return;
    }

    const lookup = path.match(/^\/lookup\/([^/]+)$/);
    if (request.method() === 'GET' && lookup) {
      const slug = decodeURIComponent(lookup[1]);
      const mod = MODS.find((item) => item.slug === slug);
      const compatibility = COMPATIBILITY[slug];
      if (!mod || !compatibility) {
        await route.fulfill({ status: 404, json: { detail: { code: 'MOD_NOT_FOUND', message: slug } } });
        return;
      }
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            slug,
            urlalias: null,
            asset_id: 0,
            name: mod.name,
            author: 'Someone',
            description: null,
            latest_version: mod.version,
            downloads: 0,
            follows: 0,
            side: 'Both',
            compatibility: {
              status: compatibility.status,
              game_version: '1.22.7',
              mod_version: mod.version,
              message: compatibility.message,
              latest_supported_game_version: compatibility.latest,
            },
            logo_url: null,
            releases: [],
            tags: [],
            homepage_url: null,
            source_url: null,
            created: null,
            last_released: null,
          },
        },
      });
      return;
    }

    if (request.method() === 'PUT' && path.endsWith('/version')) {
      // Ask for confirmation, so the dialog opens and nothing is installed
      await route.fulfill({
        status: 409,
        json: {
          detail: {
            code: 'MOD_CONFIRMATION_REQUIRED',
            message: 'Confirmation required',
            details: { reasons: ['prerelease'] },
          },
        },
      });
      return;
    }

    if (request.method() !== 'GET') {
      // Never let a write reach the server's data
      await route.fulfill({ status: 500, json: { detail: { code: 'E2E_BLOCKED', message: path } } });
      return;
    }

    await route.continue();
  });
}

/** Elements inside the page content that scroll sideways, plus the document itself. */
async function horizontalOverflow(page: Page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const scrolling = [...document.querySelectorAll('main *')]
      .filter((element) => {
        const overflowX = getComputedStyle(element).overflowX;
        return (
          (overflowX === 'auto' || overflowX === 'scroll') &&
          element.scrollWidth > element.clientWidth
        );
      })
      .map((element) => element.getAttribute('data-testid') || element.tagName);
    return { document: root.scrollWidth - root.clientWidth, scrolling };
  });
}

async function expectTouchTarget(page: Page, testId: string) {
  const box = await page.getByTestId(testId).boundingBox();
  expect(box, testId).not.toBeNull();
  expect(box!.width, `${testId} width`).toBeGreaterThanOrEqual(44);
  expect(box!.height, `${testId} height`).toBeGreaterThanOrEqual(44);
}

test.describe('Installed mods on phones (Story 16.5)', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((apiKey) => {
      localStorage.setItem('apiKey', apiKey);
    }, API_KEY);
    await fakeInstalledMods(page);
  });

  test('shows cards without horizontal scrolling at phone width', async ({ page }) => {
    await page.setViewportSize(PHONE);
    await page.goto(INSTALLED);

    const cards = page.getByTestId('installed-mod-cards');
    await expect(cards).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('mod-table')).toHaveCount(0);
    await expect(page.getByTestId(/^installed-mod-card-/)).toHaveCount(3);

    const card = page.getByTestId('installed-mod-card-longnamemod');
    await expect(card).toContainText(LONG_NAME);
    await expect(card).toContainText('v1.0.0-rc.12');
    await expect(page.getByTestId('mod-update-longnamemod')).toContainText('v1.0.0-rc.13');
    await expect(page.getByTestId('mod-update-oldmod')).toHaveText('Up to date');
    await expect(page.getByTestId('mod-latest-supported-oldmod')).toHaveText('Supports up to 1.21.1');
    await expect(page.getByTestId('mod-compatibility-message-oldmod')).toHaveText(
      'Last supported game version: 1.21.1.'
    );
    await expect(page.getByTestId('mod-updates-update-all')).toBeVisible();

    expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
  });

  test('gives every Installed mods control a 44x44px touch target', async ({ page }) => {
    await page.setViewportSize(PHONE);
    await page.goto(INSTALLED);
    await expect(page.getByTestId('mod-update-button-longnamemod')).toBeVisible({ timeout: 30_000 });

    for (const testId of [
      'mod-update-button-longnamemod',
      'mod-remove-longnamemod',
      'mod-updates-update-all',
      'mod-updates-check',
    ]) {
      await expectTouchTarget(page, testId);
    }
    const toggleArea = await page
      .getByTestId('installed-mod-card-offmod')
      .locator('label')
      .boundingBox();
    expect(toggleArea!.width).toBeGreaterThanOrEqual(44);
    expect(toggleArea!.height).toBeGreaterThanOrEqual(44);
  });

  test('card actions open the same dialogs and requests as the table', async ({ page }) => {
    await page.setViewportSize(PHONE);
    await page.goto(INSTALLED);

    await page.getByTestId('mod-update-button-longnamemod').click({ timeout: 30_000 });
    await expect(page.getByTestId('version-change-dialog')).toBeVisible();
    await page.getByTestId('version-change-cancel').click();
    await expect(page.getByTestId('version-change-dialog')).toHaveCount(0);

    await page.getByRole('button', { name: 'Remove Old Mod' }).click();
    await expect(page.getByTestId('remove-dialog')).toBeVisible();
    await page.getByTestId('remove-dialog-cancel').click();
    await expect(page.getByTestId('remove-dialog')).toHaveCount(0);

    // Tapping the label area beside the switch sends the enable request
    const enable = page.waitForRequest(
      (request) => request.method() === 'POST' && request.url().endsWith('/mods/offmod/enable')
    );
    await page.getByTestId('installed-mod-card-offmod').getByText('Disabled').click();
    await enable;
  });

  test('keeps the table at desktop width and switches when the window narrows', async ({ page }) => {
    await page.setViewportSize(DESKTOP);
    await page.goto(INSTALLED);

    const table = page.getByTestId('mod-table');
    await expect(table).toBeVisible({ timeout: 30_000 });
    await expect(page.getByTestId('installed-mod-cards')).toHaveCount(0);
    for (const header of ['Name', 'Version', 'Available', 'Side', 'Compatibility', 'Status']) {
      await expect(table.getByRole('columnheader', { name: header })).toBeVisible();
    }
    await expect(page.getByTestId(/^mod-row-/)).toHaveCount(3);
    expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });

    await page.setViewportSize(PHONE);
    await expect(page.getByTestId('installed-mod-cards')).toBeVisible();
    await expect(table).toHaveCount(0);
  });
});
