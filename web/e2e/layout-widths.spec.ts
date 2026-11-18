import { test, expect, type Locator, type Page } from '@playwright/test';
import { fetchOnNewConnection, pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for page layouts at tablet and phone widths.
 *
 * Story 17.8 (FR191-FR193; VSS-dp1, VSS-uni, VSS-143):
 * - Installed mods: below `lg` (1024px) each mod is a card, so from 768 to 1023px, with the
 *   sidebar expanded or collapsed, nothing scrolls sideways and every control is inside the
 *   viewport; from 1024px the table is unchanged.
 * Story 18.4 (FR203-FR204; VSS-bgu, VSS-n2u):
 * - From 1024px the table fits its container with a long name, in both sidebar states: the
 *   Name column wraps (and the Update button may drop under the offered version), so the
 *   long-named mod's toggle and remove button are on screen. Where the table has room
 *   (AC 6), names and Available cells stay on one line.
 * - Below `lg` the cards have a sort control that shares the `installedModsSort` preference
 *   with the table headers.
 * - Settings (`/config`): at 320-430px the four tabs wrap inside the content, so the page
 *   does not scroll sideways and every tab can be selected by click and by arrow keys.
 * - The Mods and Version page tab lists fit at 320 and 390px.
 * - Game Settings: from 1024px the title starts at the settings panel's left edge and the
 *   status badge ends at its right edge, inside the same centered 1280px width.
 * Story 21.7 (FR281, FR283; VSS-3ry, VSS-f9y):
 * - The Settings, Mods and Version tab buttons are at least 44px tall below 1024px, and as
 *   before from 1024px (list 36px). At 320-430px the Settings list's two rows sit inside the
 *   list and its panel starts below it.
 * - Scheduled Jobs: from 320 to 1023px, in both sidebar states, each job is a card with its
 *   four values labelled and nothing scrolls sideways; from 1024px the table is unchanged.
 * - Version: at 320-430px the table fits without scrolling; Channel and Status are hidden and
 *   the channel, "Latest" and "Installed" show under the version; "Select" is 44px tall below
 *   1024px and 32px from 1024px.
 * - Console: at 320-430px its controls wrap, so the page does not scroll sideways.
 *
 * Reads only. The installed mods, their update status and the compatibility lookups are
 * stubbed with `page.route` (the three mods of installed-mods-phone.spec.ts), as are the
 * Version page's versions, its installed version and the Scheduled Jobs (Story 21.7); every
 * write to the API is refused, so no mod or setting changes; the game server is neither
 * started nor stopped; no screenshot is taken. The sidebar state is the `vs_ui_prefs`
 * cookie of a fresh browser context.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) with a serverconfig.json
 *   (for the Game Settings header), which the seeded stack and a stack with a game server
 *   both have (the pages are shown as installed by `pretendServerInstalled`), rebuilt
 *   from this branch: `just test-e2e-ci`, or `just docker restart`, then
 *   `cd web && bunx playwright test e2e/layout-widths.spec.ts` with VS_API_KEY_ADMIN
 *   exported (the Scheduled Jobs tab exists only for an Admin key).
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:8080';

const INSTALLED = '/game-server/mods/installed';
const HEIGHT = 900;

const LONG_NAME = 'An Extraordinarily Long Mod Name That Must Wrap Inside Its Card';

interface FakeMod {
  slug: string;
  name: string;
  version: string;
  enabled: boolean;
  /** Offered pre-release update, if any */
  offered?: string;
}

const OTHER_MODS: FakeMod[] = [
  { slug: 'oldmod', name: 'Old Mod', version: '2.3.4', enabled: true },
  { slug: 'offmod', name: 'Off Mod', version: '0.1.0', enabled: false },
];

const MODS: FakeMod[] = [
  {
    slug: 'longnamemod',
    name: LONG_NAME,
    version: '1.0.0-rc.12',
    enabled: true,
    offered: '1.0.0-rc.13',
  },
  ...OTHER_MODS,
];

// Story 18.4 review: the long name offering a longer version string than any of MODS
const LONG_VERSION_MODS: FakeMod[] = [
  {
    slug: 'longnamemod',
    name: LONG_NAME,
    version: '1.0.0-rc.12',
    enabled: true,
    offered: '10.10.10-rc.130',
  },
  ...OTHER_MODS,
];

// Story 18.4: short names only, one of them with an offered pre-release update
const SHORT_MODS: FakeMod[] = [
  { slug: 'shortmod', name: 'Short Mod', version: '1.4.0', enabled: true, offered: '1.5.0-rc.1' },
  ...OTHER_MODS,
];

const COMPATIBILITY: Record<string, { status: string; message: string; latest: string }> = {
  longnamemod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
  oldmod: {
    status: 'incompatible',
    message: 'Last supported game version: 1.21.1.',
    latest: '1.21.1',
  },
  offmod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
  shortmod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
};

function updateStatus({ slug, name, version, offered }: FakeMod) {
  return {
    slug,
    name,
    installed_version: version,
    status: offered ? 'update_available' : 'up_to_date',
    offered_version: offered ?? null,
    offered_compatibility: offered ? 'compatible' : null,
    offered_prerelease: offered ? true : null,
    reason: null,
    checked_at: '2026-11-13T00:00:00Z',
    error: null,
  };
}

/** Admin key from /config.js, server shown as installed (19.7), every write refused. */
async function readOnly(page: Page) {
  await serveConfigKey(page, API_KEY);
  await pretendServerInstalled(page);
  await page.route('**/api/**', async (route) => {
    if (route.request().method() !== 'GET') {
      // Never let a write reach the server's data
      await route.fulfill({
        status: 500,
        json: { detail: { code: 'E2E_BLOCKED', message: 'read only' } },
      });
      return;
    }
    await route.fallback();
  });
}

/** Serve the installed mods, their update status and lookups (registered after readOnly, so it runs first). */
async function fakeInstalledMods(page: Page, mods: FakeMod[] = MODS) {
  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');

    if (request.method() === 'GET' && path === '') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            mods: mods.map(({ slug, name, version, enabled }) => ({
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
      const updates = mods.map(updateStatus);
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
      const mod = mods.find((item) => item.slug === slug);
      const compatibility = COMPATIBILITY[slug];
      if (!mod || !compatibility) {
        await route.fulfill({
          status: 404,
          json: { detail: { code: 'MOD_NOT_FOUND', message: slug } },
        });
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

interface PageOptions {
  /** Stub the installed mods with `fixture` */
  mods?: boolean;
  fixture?: FakeMod[];
  /** Stub the Version page's versions (Story 21.7) */
  versions?: boolean;
  /** Stub the Scheduled Jobs (Story 21.7) */
  jobs?: boolean;
  /** Show this game version as installed (Story 21.7) */
  installed?: string;
}

/** A page in a fresh context with the sidebar expanded or collapsed (vs_ui_prefs cookie). */
async function openPage(
  page: Page,
  width: number,
  collapsed: boolean,
  url: string,
  { mods = false, fixture = MODS, versions = false, jobs = false, installed }: PageOptions = {}
) {
  await page.context().addCookies([
    {
      name: 'vs_ui_prefs',
      value: encodeURIComponent(JSON.stringify({ sidebarCollapsed: collapsed })),
      url: BASE_URL,
    },
  ]);
  await page.setViewportSize({ width, height: HEIGHT });
  await readOnly(page);
  if (mods) await fakeInstalledMods(page, fixture);
  if (versions) await fakeVersions(page);
  if (jobs) await fakeJobs(page);
  if (installed) await installedVersion(page, installed);
  await page.goto(url);
}

const SIDEBAR = [
  { collapsed: false, label: 'sidebar expanded' },
  { collapsed: true, label: 'sidebar collapsed' },
];

test.describe('Installed mods at every width (Story 17.8, AC 1-2)', () => {
  for (const { collapsed, label } of SIDEBAR) {
    for (const width of [320, 390, 430, 768, 900, 1023]) {
      test(`cards with every control inside the viewport at ${width}px, ${label}`, async ({
        page,
      }) => {
        await openPage(page, width, collapsed, INSTALLED, { mods: true });

        await expect(page.getByTestId('installed-mod-cards')).toBeVisible({ timeout: 30_000 });
        await expect(page.getByTestId('mod-table')).toHaveCount(0);
        await expect(page.getByTestId('mod-update-button-longnamemod')).toBeVisible();

        expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });

        const card = page.getByTestId('installed-mod-card-longnamemod');
        await expectInsideViewport(page, card.getByText('v1.0.0-rc.12'), width);
        await expectInsideViewport(page, 'mod-update-button-longnamemod', width);
        await expectInsideViewport(
          page,
          page.getByTestId('installed-mod-card-offmod').locator('label'),
          width
        );
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

        // Story 18.4: no width scrolls, 1024px included
        expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      });
    }
  }

  test('the Update action on a card opens the confirmation at 900px, sidebar expanded', async ({
    page,
  }) => {
    await openPage(page, 900, false, INSTALLED, { mods: true });

    await page.getByTestId('mod-update-button-longnamemod').click({ timeout: 30_000 });
    await expect(page.getByTestId('version-change-dialog')).toBeVisible();
    await page.getByTestId('version-change-cancel').click();
    await expect(page.getByTestId('version-change-dialog')).toHaveCount(0);
  });
});

/** Height of a test ID's box. */
async function heightOf(page: Page, testId: string): Promise<number> {
  return (await boxOf(page.getByTestId(testId), testId)).height;
}

/** Open Installed mods as the table, with every update status rendered. */
async function openTable(page: Page, width: number, collapsed: boolean, fixture: FakeMod[]) {
  await openPage(page, width, collapsed, INSTALLED, { mods: true, fixture });
  await expect(page.getByTestId('mod-table')).toBeVisible({ timeout: 30_000 });
  for (const mod of fixture) {
    await expect(page.getByTestId(`mod-update-${mod.slug}`)).toBeVisible({ timeout: 30_000 });
  }
}

/** Every name and Available cell on one line: names as tall as Off Mod's, Update beside its version. */
async function expectOneLine(page: Page, fixture: FakeMod[], where: string) {
  const oneLine = await heightOf(page, 'mod-link-offmod');
  for (const mod of fixture) {
    expect(
      Math.abs((await heightOf(page, `mod-link-${mod.slug}`)) - oneLine),
      `${mod.slug} name on one line, ${where}`
    ).toBeLessThanOrEqual(1);
    if (mod.offered) {
      const cell = await boxOf(
        page.getByTestId(`mod-update-${mod.slug}`),
        `mod-update-${mod.slug}`
      );
      const button = await boxOf(
        page.getByTestId(`mod-update-button-${mod.slug}`),
        `mod-update-button-${mod.slug}`
      );
      expect(
        Math.abs(button.y + button.height / 2 - (cell.y + cell.height / 2)),
        `${mod.slug} Update button beside its version, ${where}`
      ).toBeLessThanOrEqual(2);
    }
  }
}

test.describe('Installed mods table fits from 1024px (Story 18.4, AC 5-6)', () => {
  for (const { collapsed, label } of SIDEBAR) {
    test(`the long name wraps and its controls are on screen at 1024px, ${label}`, async ({
      page,
    }) => {
      await openTable(page, 1024, collapsed, MODS);

      expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      await expectInsideViewport(page, 'mod-toggle-longnamemod', 1024);
      await expectInsideViewport(page, 'mod-remove-longnamemod', 1024);
      expect(await heightOf(page, 'mod-link-longnamemod')).toBeGreaterThan(
        await heightOf(page, 'mod-link-offmod')
      );
    });

    test(`short names fit at 1024px, ${label}`, async ({ page }) => {
      await openTable(page, 1024, collapsed, SHORT_MODS);

      expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      await expectInsideViewport(page, 'mod-toggle-shortmod', 1024);
      await expectInsideViewport(page, 'mod-remove-shortmod', 1024);
    });

    // Story 18.4 review: the 1024px fit keeps a margin for a longer offered version
    test(`a long name with a long offered version fits at 1024px, ${label}`, async ({ page }) => {
      await openTable(page, 1024, collapsed, LONG_VERSION_MODS);

      await expect(page.getByTestId('mod-update-longnamemod')).toContainText('v10.10.10-rc.130');
      expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      await expectInsideViewport(page, 'mod-toggle-longnamemod', 1024);
      await expectInsideViewport(page, 'mod-remove-longnamemod', 1024);
    });

    for (const width of [1280, 1440, 1920]) {
      test(`short names and the Available cell on one line at ${width}px, ${label}`, async ({
        page,
      }) => {
        await openTable(page, width, collapsed, SHORT_MODS);

        expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
        await expectOneLine(page, SHORT_MODS, `${width}px, ${label}`);
      });
    }
  }

  // AC 6: at 1440px with the sidebar expanded the long name may wrap (measured), so only
  // 1440 collapsed and 1920 in both states keep it on one line
  for (const { width, collapsed, label } of [
    { width: 1440, collapsed: true, label: 'sidebar collapsed' },
    { width: 1920, collapsed: false, label: 'sidebar expanded' },
    { width: 1920, collapsed: true, label: 'sidebar collapsed' },
  ]) {
    test(`the long name and the Available cell on one line at ${width}px, ${label}`, async ({
      page,
    }) => {
      await openTable(page, width, collapsed, MODS);

      expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      await expectOneLine(page, MODS, `${width}px, ${label}`);
    });
  }
});

/** Card slugs in display order. */
async function cardOrder(page: Page): Promise<string[]> {
  const ids = await page
    .getByTestId(/^installed-mod-card-/)
    .evaluateAll((cards) => cards.map((card) => card.getAttribute('data-testid') ?? ''));
  return ids.map((id) => id.replace('installed-mod-card-', ''));
}

/** Table row slugs in display order. */
async function rowOrder(page: Page): Promise<string[]> {
  const ids = await page
    .getByTestId(/^mod-row-/)
    .evaluateAll((rows) => rows.map((row) => row.getAttribute('data-testid') ?? ''));
  return ids.map((id) => id.replace('mod-row-', ''));
}

async function expectSortControl(page: Page, column: string, direction: string) {
  await expect(page.getByTestId('installed-mods-sort-column')).toHaveText(column);
  await expect(page.getByTestId('installed-mods-sort-direction')).toHaveText(direction);
}

const BY_NAME = ['longnamemod', 'offmod', 'oldmod'];
const BY_VERSION = ['offmod', 'longnamemod', 'oldmod'];

test.describe('Sort control above the installed mod cards (Story 18.4, AC 1-4)', () => {
  for (const { width, collapsed, label } of [
    { width: 900, collapsed: false, label: 'sidebar expanded' },
    { width: 390, collapsed: false, label: 'phone' },
  ]) {
    test(`sorts the cards and shares the sort with the table at ${width}px, ${label}`, async ({
      page,
    }) => {
      await openPage(page, width, collapsed, INSTALLED, { mods: true });
      await expect(page.getByTestId('installed-mod-cards')).toBeVisible({ timeout: 30_000 });

      const control = page.getByTestId('installed-mods-sort');
      await expect(control).toBeVisible();
      await expectInsideViewport(page, 'installed-mods-sort-column', width);
      await expectInsideViewport(page, 'installed-mods-sort-direction', width);
      await expect(page.getByRole('combobox', { name: 'Sort by' })).toBeVisible();
      await expectSortControl(page, 'Name', 'Ascending');
      expect(await cardOrder(page)).toEqual(BY_NAME);

      await page.getByTestId('installed-mods-sort-column').click();
      const options = page.getByRole('option');
      await expect(options).toHaveText(['Name', 'Version', 'Status']);
      await page.getByTestId('installed-mods-sort-option-version').click();
      await expectSortControl(page, 'Version', 'Ascending');
      expect(await cardOrder(page)).toEqual(BY_VERSION);

      await page.getByTestId('installed-mods-sort-direction').click();
      await expectSortControl(page, 'Version', 'Descending');
      expect(await cardOrder(page)).toEqual([...BY_VERSION].reverse());

      await page.reload();
      await expect(page.getByTestId('installed-mod-cards')).toBeVisible({ timeout: 30_000 });
      await expectSortControl(page, 'Version', 'Descending');
      expect(await cardOrder(page)).toEqual([...BY_VERSION].reverse());

      await page.setViewportSize({ width: 1024, height: HEIGHT });
      const table = page.getByTestId('mod-table');
      await expect(table).toBeVisible();
      await expect(control).toHaveCount(0);
      expect(await rowOrder(page)).toEqual([...BY_VERSION].reverse());
      await expect(
        table.getByRole('columnheader', { name: 'Version' }).locator('.lucide-chevron-down')
      ).toHaveCount(1);

      await table
        .getByRole('columnheader', { name: 'Name' })
        .getByRole('button', { name: 'Name' })
        .click();
      expect(await rowOrder(page)).toEqual(BY_NAME);
      await page.setViewportSize({ width, height: HEIGHT });
      await expect(control).toBeVisible();
      await expectSortControl(page, 'Name', 'Ascending');
      expect(await cardOrder(page)).toEqual(BY_NAME);
    });
  }
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
      await expectInsideViewport(
        page,
        page.locator('[data-testid="mods-page"] [data-slot="tabs-list"]'),
        width
      );
    });

    test(`the Version page channel tabs fit at ${width}px`, async ({ page }) => {
      await openPage(page, width, false, '/game-server/version');
      await expect(page.getByTestId('channel-filter-tabs')).toBeVisible({ timeout: 30_000 });

      expect(await documentOverflow(page)).toBe(0);
      await expectInsideViewport(page, 'channel-filter-tabs', width);
    });
  }
});

/** The Version page's four versions (Story 21.7); the vendor's list is empty in CI's first pass. */
const VERSIONS = [
  { version: '1.22.7', channel: 'stable', isLatest: true },
  { version: '1.22.7-rc.12', channel: 'unstable', isLatest: false },
  { version: '1.22.6', channel: 'stable', isLatest: false },
  { version: '1.21.6-pre.1', channel: 'unstable', isLatest: false },
];

/** Serve the version list, filtered by `?channel=` (registered after readOnly, so it runs first). */
async function fakeVersions(page: Page) {
  await page.route(/\/api\/v1alpha1\/versions(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    const channel = new URL(route.request().url()).searchParams.get('channel');
    const versions = VERSIONS.filter((item) => !channel || item.channel === channel).map(
      ({ version, channel: itemChannel, isLatest }) => ({
        version,
        filename: `vs_server_linux-x64_${version}.tar.gz`,
        filesize: '40.2 MB',
        md5: '0'.repeat(32),
        cdn_url: `https://cdn.example.com/${itemChannel}/${version}`,
        local_url: `/downloads/${itemChannel}/${version}`,
        is_latest: isLatest,
        channel: itemChannel,
      })
    );
    await route.fulfill({
      json: {
        status: 'ok',
        data: { versions, total: versions.length, cached: true, cached_at: null },
      },
    });
  });
}

/** Three Scheduled Jobs (Story 21.7): a long job ID and a cron schedule must wrap in a card. */
const JOBS = [
  {
    id: 'mod_cache_refresh',
    next_run_time: '2026-11-17T12:00:00Z',
    trigger_type: 'interval',
    trigger_details: 'every 3600 seconds',
  },
  {
    id: 'server_versions_check',
    next_run_time: null,
    trigger_type: 'cron',
    trigger_details: "cron[hour='*/6', minute='0']",
  },
  {
    id: 'mod_update_check',
    next_run_time: '2026-11-17T18:00:00Z',
    trigger_type: 'interval',
    trigger_details: 'every 21600 seconds',
  },
];

/** Serve the Scheduled Jobs (registered after readOnly, so it runs first). */
async function fakeJobs(page: Page) {
  await page.route(/\/api\/v1alpha1\/jobs(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    await route.fulfill({ json: { status: 'ok', data: { jobs: JOBS } } });
  });
}

/**
 * Show `version` as the installed game version on every stack, so the latest row is also the
 * installed row (registered after pretendServerInstalled, so it runs first).
 */
async function installedVersion(page: Page, version: string) {
  await page.route('**/api/v1alpha1/server/status', async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    const response = await fetchOnNewConnection(route);
    const body: { data?: Record<string, unknown> } = await response.json();
    body.data = { ...body.data, state: 'installed', version };
    await route.fulfill({ response, json: body });
  });
}

/** Tab heights at every width below lg (Story 21.7, AC 1). */
const TAB_WIDTHS = [
  { width: 320, collapsed: false, label: 'sidebar expanded' },
  { width: 390, collapsed: false, label: 'sidebar expanded' },
  { width: 430, collapsed: false, label: 'sidebar expanded' },
  { width: 768, collapsed: false, label: 'sidebar expanded' },
  { width: 768, collapsed: true, label: 'sidebar collapsed' },
  { width: 1023, collapsed: false, label: 'sidebar expanded' },
  { width: 1023, collapsed: true, label: 'sidebar collapsed' },
];

interface TabList {
  name: string;
  url: string;
  /** Selector of the tab list */
  list: string;
  /** Test ID that shows the page is ready */
  ready: string;
  triggers: string[];
  options: PageOptions;
}

/** The three tab lists: where each is, what to wait for, and its triggers. */
const TAB_LISTS: TabList[] = [
  {
    name: 'Settings',
    url: '/config',
    list: '[data-testid="settings-page"] [data-slot="tabs-list"]',
    ready: 'scheduled-jobs-tab',
    triggers: CONFIG_TABS.map((tab) => `${tab}-tab`),
    options: {},
  },
  {
    name: 'Mods',
    url: INSTALLED,
    list: '[data-testid="mods-page"] [data-slot="tabs-list"]',
    ready: 'installed-tab',
    triggers: ['installed-tab', 'browse-tab'],
    options: { mods: true },
  },
  {
    name: 'Version channel filter',
    url: '/game-server/version',
    list: '[data-testid="channel-filter-tabs"]',
    ready: 'version-table',
    triggers: ['channel-filter-all', 'channel-filter-stable', 'channel-filter-unstable'],
    options: { versions: true },
  },
];

/** Open a page with one of the three tab lists, its data stubbed. */
async function openTabList(page: Page, width: number, collapsed: boolean, tabList: TabList) {
  await openPage(page, width, collapsed, tabList.url, tabList.options);
  await expect(page.getByTestId(tabList.ready)).toBeVisible({ timeout: 30_000 });
}

test.describe('Tab heights (Story 21.7, AC 1-2)', () => {
  for (const tabList of TAB_LISTS) {
    for (const { width, collapsed, label } of TAB_WIDTHS) {
      test(`${tabList.name} tabs are at least 44px tall at ${width}px, ${label}`, async ({
        page,
      }) => {
        await openTabList(page, width, collapsed, tabList);

        for (const trigger of tabList.triggers) {
          const box = await boxOf(page.getByTestId(trigger), trigger);
          expect(box.height, `${trigger} height at ${width}px`).toBeGreaterThanOrEqual(44);
          await expectInsideViewport(page, trigger, width);
        }
        expect(await documentOverflow(page)).toBe(0);
      });
    }

    test(`${tabList.name} tabs are as before at 1024px`, async ({ page }) => {
      await openTabList(page, 1024, false, tabList);

      const list = await boxOf(page.locator(tabList.list), `${tabList.name} tab list`);
      expect(list.height).toBe(36);
      for (const trigger of tabList.triggers) {
        const box = await boxOf(page.getByTestId(trigger), trigger);
        expect(box.height, `${trigger} height at 1024px`).toBeLessThan(36);
      }
    });
  }

  // Below md the sidebar is a sheet, so its state does not matter
  for (const width of [320, 390, 430]) {
    test(`the Settings tabs wrap inside their list at ${width}px`, async ({ page }) => {
      await openTabList(page, width, false, TAB_LISTS[0]);
      const listLocator = page.locator(TAB_LISTS[0].list);
      const activePanel = page.locator(
        '[data-testid="settings-page"] [data-slot="tabs-content"][data-state="active"]'
      );

      const list = await boxOf(listLocator, 'Settings tab list');
      expect(list.height, 'two rows').toBeGreaterThan(88);
      for (const trigger of TAB_LISTS[0].triggers) {
        const box = await boxOf(page.getByTestId(trigger), trigger);
        expect(box.x, `${trigger} left`).toBeGreaterThanOrEqual(list.x);
        expect(box.x + box.width, `${trigger} right`).toBeLessThanOrEqual(list.x + list.width);
        expect(box.y, `${trigger} top`).toBeGreaterThanOrEqual(list.y);
        expect(box.y + box.height, `${trigger} bottom`).toBeLessThanOrEqual(list.y + list.height);
      }
      const panel = await boxOf(activePanel, 'active panel');
      expect(panel.y, 'panel below the list').toBeGreaterThanOrEqual(list.y + list.height);

      await page.getByTestId('scheduled-jobs-tab').click();
      await expect(page.getByTestId('scheduled-jobs-tab')).toHaveAttribute('aria-selected', 'true');
      const lastPanel = await boxOf(activePanel, 'active panel after the last tab');
      const listAfter = await boxOf(listLocator, 'Settings tab list');
      expect(lastPanel.y, 'panel below the list').toBeGreaterThanOrEqual(
        listAfter.y + listAfter.height
      );
      expect(await documentOverflow(page)).toBe(0);
    });
  }
});

/** Every width below lg in both sidebar states (Story 21.7, AC 6). */
const BELOW_LG = [320, 390, 430, 768, 1023];

test.describe('Scheduled Jobs below lg (Story 21.7, AC 6)', () => {
  for (const { collapsed, label } of SIDEBAR) {
    for (const width of BELOW_LG) {
      test(`each job is a card at ${width}px, ${label}`, async ({ page }) => {
        await openPage(page, width, collapsed, '/config', { jobs: true });
        await page.getByTestId('scheduled-jobs-tab').click({ timeout: 30_000 });

        await expect(page.getByTestId('job-cards')).toBeVisible({ timeout: 30_000 });
        await expect(page.getByTestId('jobs-table')).toHaveCount(0);
        const cards = page.getByTestId(/^job-card-/);
        await expect(cards).toHaveCount(JOBS.length);
        for (const job of JOBS) {
          const card = page.getByTestId(`job-card-${job.id}`);
          for (const label of ['Job Name', 'Schedule', 'Next Run', 'Status']) {
            await expect(card.getByText(label, { exact: true })).toBeVisible();
          }
          const cardBox = await boxOf(card, `job-card-${job.id}`);
          for (const prefix of ['job-name', 'job-schedule', 'job-next-run', 'job-status']) {
            const value = await boxOf(card.getByTestId(`${prefix}-${job.id}`), prefix);
            expect(value.x, `${prefix}-${job.id} left`).toBeGreaterThanOrEqual(cardBox.x);
            expect(value.x + value.width, `${prefix}-${job.id} right`).toBeLessThanOrEqual(
              cardBox.x + cardBox.width
            );
          }
        }
        await expect(page.getByTestId('job-next-run-server_versions_check')).toHaveText('Never');
        expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      });
    }

    test(`the table at 1024px, ${label}`, async ({ page }) => {
      await openPage(page, 1024, collapsed, '/config', { jobs: true });
      await page.getByTestId('scheduled-jobs-tab').click({ timeout: 30_000 });

      const table = page.getByTestId('jobs-table');
      await expect(table).toBeVisible({ timeout: 30_000 });
      await expect(page.getByTestId('job-cards')).toHaveCount(0);
      for (const header of ['Job Name', 'Schedule', 'Next Run', 'Status']) {
        await expect(table.getByRole('columnheader', { name: header })).toBeVisible();
      }
    });
  }
});

/** Open the Version page with the four versions, 1.22.7 installed. */
async function openVersions(page: Page, width: number, collapsed: boolean) {
  await openPage(page, width, collapsed, '/game-server/version', {
    versions: true,
    installed: '1.22.7',
  });
  await expect(page.getByTestId('version-table')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('version-table-installed-1.22.7')).toHaveCount(1);
}

test.describe('Version table on phones (Story 21.7, AC 7)', () => {
  // Below md the sidebar is a sheet, so its state does not matter
  for (const width of [320, 390, 430]) {
    test(`the table fits and shows each row's channel at ${width}px`, async ({ page }) => {
      await openVersions(page, width, false);

      expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      await expect(page.getByTestId('version-table-header-channel')).toBeHidden();
      await expect(page.getByTestId('version-table-header-status')).toBeHidden();
      for (const { version, channel } of VERSIONS) {
        await expect(page.getByTestId(`version-table-inline-channel-${version}`)).toHaveText(
          channel === 'stable' ? 'Stable' : 'Unstable'
        );
        const select = page.getByTestId(`version-table-select-${version}`);
        expect((await boxOf(select, version)).height).toBeGreaterThanOrEqual(44);
        await expectInsideViewport(page, select, width);
      }
      await expect(page.getByTestId('version-table-inline-latest-1.22.7')).toBeVisible();
      await expect(page.getByTestId('version-table-inline-installed-1.22.7')).toBeVisible();
    });
  }

  for (const { collapsed, label } of SIDEBAR) {
    test(`the Channel column is back at 768px, ${label}`, async ({ page }) => {
      await openVersions(page, 768, collapsed);

      await expect(page.getByTestId('version-table-header-channel')).toBeVisible();
      await expect(page.getByTestId('version-table-inline-channel-1.22.7')).toBeHidden();
      expect(await horizontalOverflow(page)).toEqual({ document: 0, scrolling: [] });
      const select = page.getByTestId('version-table-select-1.22.7');
      expect((await boxOf(select, 'Select')).height).toBeGreaterThanOrEqual(44);
    });
  }

  test('the Select button is 32px tall at 1024px', async ({ page }) => {
    await openVersions(page, 1024, false);

    const select = page.getByTestId('version-table-select-1.22.7');
    expect((await boxOf(select, 'Select')).height).toBe(32);
  });
});

test.describe('Console header on phones (Story 21.7, AC 8)', () => {
  // Measured before the fix: the document scrolled 170, 100 and 60px sideways
  for (const width of [320, 390, 430]) {
    test(`the console's controls wrap inside the page at ${width}px`, async ({ page }) => {
      await openPage(page, width, false, '/game-server/console');
      await expect(page.getByTestId('console-panel')).toBeVisible({ timeout: 30_000 });

      expect(await documentOverflow(page)).toBe(0);
      await expectInsideViewport(page, 'source-selector', width);
      await expectInsideViewport(page, 'console-font-increase', width);
      await expectInsideViewport(
        page,
        page.getByTestId('console-page').getByRole('button', { name: /restart/i }),
        width
      );
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
