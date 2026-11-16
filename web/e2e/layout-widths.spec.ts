import { test, expect, type Locator, type Page } from '@playwright/test';

/**
 * E2E tests for page layouts at tablet and phone widths.
 *
 * Story 17.8 (FR191-FR193; VSS-dp1, VSS-uni, VSS-143):
 * - Installed mods: below `lg` (1024px) each mod is a card, so from 768 to 1023px, with the
 *   sidebar expanded or collapsed, nothing scrolls sideways and every control is inside the
 *   viewport; from 1024px the table is unchanged.
 * - Settings (`/config`): at 320-430px the four tabs wrap inside the content, so the page
 *   does not scroll sideways and every tab can be selected by click and by arrow keys.
 * - The Mods and Version page tab lists fit at 320 and 390px.
 * - Game Settings: from 1024px the title starts at the settings panel's left edge and the
 *   status badge ends at its right edge, inside the same centered 1280px width.
 *
 * Reads only. The installed mods, their update status and the compatibility lookups are
 * stubbed with `page.route` (the three mods of installed-mods-phone.spec.ts), and every
 * write to the API is refused, so no mod or setting changes; the game server is neither
 * started nor stopped; no screenshot is taken. The sidebar state is the `vs_ui_prefs`
 * cookie of a fresh browser context.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) with a game server
 *   installed (for the Game Settings header), rebuilt from this branch:
 *   `just docker restart`, then `cd web && bunx playwright test e2e/layout-widths.spec.ts`
 *   with VS_API_KEY_ADMIN exported (the Scheduled Jobs tab exists only for an Admin key).
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:8080';

const INSTALLED = '/game-server/mods/installed';
const HEIGHT = 900;

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

/** Answer /config.js with the Admin key (Story 17.5) and refuse every write to the API. */
async function readOnly(page: Page) {
  await page.route('**/config.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey: API_KEY })};`,
    })
  );
  await page.route('**/api/**', async (route) => {
    if (route.request().method() !== 'GET') {
      // Never let a write reach the server's data
      await route.fulfill({ status: 500, json: { detail: { code: 'E2E_BLOCKED', message: 'read only' } } });
      return;
    }
    await route.fallback();
  });
}

/** Serve the installed mods, their update status and lookups (registered after readOnly, so it runs first). */
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

    await route.fallback();
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

async function documentOverflow(page: Page): Promise<number> {
  return (await horizontalOverflow(page)).document;
}

async function boxOf(locator: Locator, name: string) {
  const box = await locator.boundingBox();
  if (!box) throw new Error(`No box for ${name}`);
  return box;
}

/** The element's box lies inside [0, width] horizontally (a test ID or a locator). */
async function expectInsideViewport(page: Page, target: string | Locator, width: number) {
  const locator = typeof target === 'string' ? page.getByTestId(target) : target;
  const name = typeof target === 'string' ? target : String(target);
  const box = await boxOf(locator, name);
  expect(box.x, `${name} left at ${width}px`).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width, `${name} right at ${width}px`).toBeLessThanOrEqual(width);
}

/** A page in a fresh context with the sidebar expanded or collapsed (vs_ui_prefs cookie). */
async function openPage(page: Page, width: number, collapsed: boolean, url: string, { mods = false } = {}) {
  await page.context().addCookies([
    {
      name: 'vs_ui_prefs',
      value: encodeURIComponent(JSON.stringify({ sidebarCollapsed: collapsed })),
      url: BASE_URL,
    },
  ]);
  await page.setViewportSize({ width, height: HEIGHT });
  await readOnly(page);
  if (mods) await fakeInstalledMods(page);
  await page.goto(url);
}

const SIDEBAR = [
  { collapsed: false, label: 'sidebar expanded' },
  { collapsed: true, label: 'sidebar collapsed' },
];

test.describe('Installed mods at every width (Story 17.8, AC 1-2)', () => {
  for (const { collapsed, label } of SIDEBAR) {
    for (const width of [320, 390, 430, 768, 900, 1023]) {
      test(`cards with every control inside the viewport at ${width}px, ${label}`, async ({ page }) => {
        await openPage(page, width, collapsed, INSTALLED, { mods: true });

        await expect(page.getByTestId('installed-mod-cards')).toBeVisible({ timeout: 30_000 });
        await expect(page.getByTestId('mod-table')).toHaveCount(0);
        await expect(page.getByTestId('mod-update-button-longnamemod')).toBeVisible();

        expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });

        const card = page.getByTestId('installed-mod-card-longnamemod');
        await expectInsideViewport(page, card.getByText('v1.0.0-rc.12'), width);
        await expectInsideViewport(page, 'mod-update-button-longnamemod', width);
        await expectInsideViewport(page, page.getByTestId('installed-mod-card-offmod').locator('label'), width);
        await expectInsideViewport(page, 'mod-remove-longnamemod', width);
      });
    }

    for (const width of [1024, 1440, 1920]) {
      test(`the table at ${width}px, ${label}`, async ({ page }) => {
        await openPage(page, width, collapsed, INSTALLED, { mods: true });

        const table = page.getByTestId('mod-table');
        await expect(table).toBeVisible({ timeout: 30_000 });
        await expect(page.getByTestId('installed-mod-cards')).toHaveCount(0);
        for (const header of ['Name', 'Version', 'Available', 'Side', 'Compatibility', 'Status']) {
          await expect(table.getByRole('columnheader', { name: header })).toBeVisible();
        }
        await expect(page.getByTestId(/^mod-row-/)).toHaveCount(3);

        const overflow = await horizontalOverflow(page);
        expect(overflow.document).toBe(0);
        // At 1024px the long-name table still scrolls inside its own container (follow-up)
        if (width > 1024) expect(overflow.scrolling).toEqual([]);
      });
    }
  }

  test('the Update action on a card opens the confirmation at 900px, sidebar expanded', async ({ page }) => {
    await openPage(page, 900, false, INSTALLED, { mods: true });

    await page.getByTestId('mod-update-button-longnamemod').click({ timeout: 30_000 });
    await expect(page.getByTestId('version-change-dialog')).toBeVisible();
    await page.getByTestId('version-change-cancel').click();
    await expect(page.getByTestId('version-change-dialog')).toHaveCount(0);
  });
});

const CONFIG_TABS = ['ui-preferences', 'api-settings', 'file-manager', 'scheduled-jobs'];

test.describe('Settings tabs on phones (Story 17.8, AC 3)', () => {
  // Below md the sidebar is a sheet, so its state does not matter
  for (const width of [320, 390, 430]) {
    test(`every tab fits and can be selected by click at ${width}px`, async ({ page }) => {
      await openPage(page, width, false, '/config');
      await expect(page.getByTestId('ui-preferences-panel')).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId('scheduled-jobs-tab')).toBeVisible();

      expect(await documentOverflow(page)).toBe(0);
      for (const tab of CONFIG_TABS) {
        await expectInsideViewport(page, `${tab}-tab`, width);
      }

      for (const tab of CONFIG_TABS) {
        const trigger = page.getByTestId(`${tab}-tab`);
        await trigger.click();
        await expect(trigger).toHaveAttribute('aria-selected', 'true');
        await expect(page.getByTestId(`${tab}-panel`)).toBeVisible({ timeout: 30_000 });
        await expectInsideViewport(page, `${tab}-tab`, width);
        expect(await documentOverflow(page), `document overflow on ${tab}`).toBe(0);
      }
    });

    test(`the arrow keys select each tab at ${width}px`, async ({ page }) => {
      await openPage(page, width, false, '/config');
      await expect(page.getByTestId('ui-preferences-panel')).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId('scheduled-jobs-tab')).toBeVisible();

      await page.getByTestId('ui-preferences-tab').focus();
      for (const tab of CONFIG_TABS.slice(1)) {
        await page.keyboard.press('ArrowRight');
        const trigger = page.getByTestId(`${tab}-tab`);
        await expect(trigger).toBeFocused();
        await expect(trigger).toHaveAttribute('aria-selected', 'true');
        await expectInsideViewport(page, `${tab}-tab`, width);
      }
      expect(await documentOverflow(page)).toBe(0);
    });
  }
});

test.describe('Other tab lists on phones (Story 17.8, AC 4)', () => {
  for (const width of [320, 390]) {
    test(`the Mods tabs fit at ${width}px`, async ({ page }) => {
      await openPage(page, width, false, INSTALLED, { mods: true });
      await expect(page.getByTestId('installed-mod-cards')).toBeVisible({ timeout: 30_000 });

      expect(await documentOverflow(page)).toBe(0);
      await expectInsideViewport(page, page.locator('[data-testid="mods-page"] [data-slot="tabs-list"]'), width);
    });

    test(`the Version page channel tabs fit at ${width}px`, async ({ page }) => {
      await openPage(page, width, false, '/game-server/version');
      await expect(page.getByTestId('channel-filter-tabs')).toBeVisible({ timeout: 30_000 });

      expect(await documentOverflow(page)).toBe(0);
      await expectInsideViewport(page, 'channel-filter-tabs', width);
    });
  }
});

test.describe('Game Settings title row on wide screens (Story 17.8, AC 5)', () => {
  for (const { collapsed, label } of SIDEBAR) {
    for (const width of [1024, 1440, 1600, 1920]) {
      test(`title and badge line up with the panel at ${width}px, ${label}`, async ({ page }) => {
        await openPage(page, width, collapsed, '/game-server/settings');
        const header = page.getByTestId('settings-page-header');
        await expect(header).toBeVisible({ timeout: 30_000 });
        const layout = page.getByTestId('game-config-layout');
        await expect(layout).toBeVisible({ timeout: 30_000 });

        const title = await boxOf(header.locator('h1'), 'title');
        const badge = await boxOf(header.locator(':scope > :last-child'), 'status badge');
        const panel = await boxOf(layout, 'game-config-layout');

        expect(Math.abs(title.x - panel.x), 'title left vs panel left').toBeLessThanOrEqual(1);
        expect(
          Math.abs(badge.x + badge.width - (panel.x + panel.width)),
          'badge right vs panel right'
        ).toBeLessThanOrEqual(1);
        expect(panel.width).toBeLessThanOrEqual(1280);
        expect(await documentOverflow(page)).toBe(0);
      });
    }
  }
});
