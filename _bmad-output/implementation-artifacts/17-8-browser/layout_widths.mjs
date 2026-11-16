// Story 17.8: measure page layouts from phone to wide desktop widths (style of
// 16-6-browser/settings_layout.mjs).
//
//   cd web && bun ../_bmad-output/implementation-artifacts/17-8-browser/layout_widths.mjs \
//     > ../_bmad-output/implementation-artifacts/17-8-browser/layout_widths.<before|after>.json
//
// Reads only. The installed mods and their update status are stubbed with the three mods of
// e2e/installed-mods-phone.spec.ts (a 63-character name with an offered pre-release update, an
// incompatible mod, a disabled mod); every non-GET API request is refused, so nothing is
// written. No screenshots; the output holds numbers and test IDs only (no server name, key or
// password). The page's API key comes from /config.js (Story 17.5), so /config.js is answered
// with VS_API_KEY_ADMIN.
//
// For each width (height 900) and each sidebar state (the vs_ui_prefs cookie), in a fresh
// browser context per page and state:
// - documentOverflowX: document.documentElement.scrollWidth - clientWidth (must be 0)
// - scrolling: elements under <main> with overflow-x auto/scroll and scrollWidth > clientWidth,
//   as "testid-or-data-slot:scrollWidth/clientWidth"
// - key rects as [left, right, width], rounded
// Pages: Installed mods (stubbed), /config and each of its tabs, the Version page (320-430),
// Game Settings (every width; title/header/badge/panel edges). At 1920 with the sidebar
// expanded, the content span of the other pages (for the app-wide maximum width follow-up).
// The Dashboard, Console and mod browser are measured only there, at 1920px, not at
// 320-1023px (Story 17.8 review, L2).

import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const WIDTHS = [320, 390, 430, 768, 900, 1023, 1024, 1440, 1600, 1920];
const CONFIG_TABS = ['ui-preferences', 'api-settings', 'file-manager', 'scheduled-jobs'];

const LONG_NAME = 'An Extraordinarily Long Mod Name That Must Wrap Inside Its Card';
const MODS = [
  { slug: 'longnamemod', name: LONG_NAME, version: '1.0.0-rc.12', enabled: true },
  { slug: 'oldmod', name: 'Old Mod', version: '2.3.4', enabled: true },
  { slug: 'offmod', name: 'Off Mod', version: '0.1.0', enabled: false },
];
const COMPATIBILITY = {
  longnamemod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
  oldmod: { status: 'incompatible', message: 'Last supported game version: 1.21.1.', latest: '1.21.1' },
  offmod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
};

function updateStatus({ slug, name, version }) {
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

/** Answer /config.js with the Admin key and refuse every write to the API. */
async function readOnly(page) {
  await page.route('**/config.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey: API_KEY })};`,
    })
  );
  await page.route('**/api/**', (route) => {
    if (route.request().method() !== 'GET') {
      return route.fulfill({ status: 500, json: { detail: { code: 'MEASURE_BLOCKED', message: 'read only' } } });
    }
    return route.fallback();
  });
}

/** Serve the installed mods, their update status and lookups (registered after readOnly, so it runs first). */
async function fakeInstalledMods(page) {
  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');
    if (request.method() !== 'GET') return route.fallback();
    if (path === '') {
      return route.fulfill({
        json: {
          status: 'ok',
          data: {
            pending_restart: false,
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
          },
        },
      });
    }
    if (path === '/updates') {
      return route.fulfill({
        json: {
          status: 'ok',
          data: { game_version: '1.22.7', checked_at: '2026-11-13T00:00:00Z', update_count: 1, mods: MODS.map(updateStatus) },
        },
      });
    }
    const lookup = path.match(/^\/lookup\/([^/]+)$/);
    if (lookup) {
      const slug = decodeURIComponent(lookup[1]);
      const mod = MODS.find((item) => item.slug === slug);
      const compatibility = COMPATIBILITY[slug];
      if (!mod || !compatibility) {
        return route.fulfill({ status: 404, json: { detail: { code: 'MOD_NOT_FOUND', message: slug } } });
      }
      return route.fulfill({
        json: {
          status: 'ok',
          data: {
            slug, urlalias: null, asset_id: 0, name: mod.name, author: 'Someone', description: null,
            latest_version: mod.version, downloads: 0, follows: 0, side: 'Both',
            compatibility: {
              status: compatibility.status, game_version: '1.22.7', mod_version: mod.version,
              message: compatibility.message, latest_supported_game_version: compatibility.latest,
            },
            logo_url: null, releases: [], tags: [], homepage_url: null, source_url: null, created: null, last_released: null,
          },
        },
      });
    }
    return route.fallback();
  });
}

async function overflow(page) {
  return page.evaluate(() => {
    const root = document.documentElement;
    const scrolling = [...document.querySelectorAll('main *')]
      .filter((element) => {
        const overflowX = getComputedStyle(element).overflowX;
        return (overflowX === 'auto' || overflowX === 'scroll') && element.scrollWidth > element.clientWidth;
      })
      .map(
        (element) =>
          `${element.getAttribute('data-testid') || element.getAttribute('data-slot') || element.tagName}:${element.scrollWidth}/${element.clientWidth}`
      );
    return { documentOverflowX: root.scrollWidth - root.clientWidth, scrolling };
  });
}

async function rect(page, selector) {
  return page.evaluate((s) => {
    const element = document.querySelector(s);
    if (!element) return null;
    const r = element.getBoundingClientRect();
    return [Math.round(r.left), Math.round(r.right), Math.round(r.width)];
  }, selector);
}

const browser = await chromium.launch();

async function open(width, collapsed, url, waitFor, { mods = false } = {}) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  await context.addCookies([
    { name: 'vs_ui_prefs', value: encodeURIComponent(JSON.stringify({ sidebarCollapsed: collapsed })), url: BASE },
  ]);
  const page = await context.newPage();
  await readOnly(page);
  if (mods) await fakeInstalledMods(page);
  await page.goto(BASE + url);
  await page.waitForSelector(waitFor, { timeout: 30000 });
  await page.waitForTimeout(500);
  return { context, page };
}

const rows = [];
for (const collapsed of [false, true]) {
  for (const width of WIDTHS) {
    const row = { width, sidebar: collapsed ? 'collapsed' : 'expanded' };

    {
      const { context, page } = await open(width, collapsed, '/game-server/mods/installed', '[data-testid="mod-table"], [data-testid="installed-mod-cards"]', { mods: true });
      row.installedMods = {
        layout: (await page.locator('[data-testid="mod-table"]').count()) ? 'table' : 'cards',
        ...(await overflow(page)),
        table: await rect(page, '[data-testid="mod-table"]'),
        tableContainer: await rect(page, '[data-slot="table-container"]'),
        cards: await rect(page, '[data-testid="installed-mod-cards"]'),
        tabsList: await rect(page, '[data-slot="tabs-list"]'),
      };
      await context.close();
    }

    {
      const { context, page } = await open(width, collapsed, '/config', '[data-testid="ui-preferences-panel"]');
      row.config = { tabsList: await rect(page, '[data-slot="tabs-list"]'), tabs: {} };
      for (const tab of CONFIG_TABS) {
        const trigger = page.getByTestId(`${tab}-tab`);
        if (!(await trigger.count())) continue;
        // force: before Task 3 a trigger can sit outside the viewport
        await trigger.click({ force: true });
        await page.waitForSelector(`[data-testid="${tab}-panel"]`, { timeout: 30000 });
        await page.waitForTimeout(300);
        row.config.tabs[tab] = {
          selected: await trigger.getAttribute('aria-selected'),
          trigger: await rect(page, `[data-testid="${tab}-tab"]`),
          ...(await overflow(page)),
        };
      }
      await context.close();
    }

    if (width <= 430) {
      const { context, page } = await open(width, collapsed, '/game-server/version', '[data-testid="channel-filter-tabs"]');
      row.version = { tabsList: await rect(page, '[data-testid="channel-filter-tabs"]'), ...(await overflow(page)) };
      await context.close();
    }

    {
      const { context, page } = await open(width, collapsed, '/game-server/settings', '[data-testid="game-config-layout"]');
      // settings-page-header from Task 4; before it, the page's first child is the header row
      const header = (await page.locator('[data-testid="settings-page-header"]').count())
        ? '[data-testid="settings-page-header"]'
        : '[data-testid="settings-page"] > div:first-child';
      row.gameSettings = {
        title: await rect(page, '[data-testid="settings-page"] h1'),
        header: await rect(page, header),
        badge: await rect(page, `${header} > :last-child`),
        panel: await rect(page, '[data-testid="game-config-layout"]'),
        ...(await overflow(page)),
      };
      await context.close();
    }

    rows.push(row);
  }
}

// Content span of the other pages at 1920 with the sidebar expanded (app-wide maximum width)
const wide = [];
for (const url of ['/', '/game-server/console', '/game-server/version', '/game-server/mods/browse', '/config']) {
  const { context, page } = await open(1920, false, url, 'main > div > *');
  await page.waitForTimeout(1500);
  wide.push({
    url,
    content: await page.evaluate(() => {
      // the page's own root, inside main's p-4 md:p-6 wrapper
      const r = document.querySelector('main > div > *')?.getBoundingClientRect();
      return r ? [Math.round(r.left), Math.round(r.right), Math.round(r.width)] : null;
    }),
    ...(await overflow(page)),
  });
  await context.close();
}

await browser.close();
console.log(JSON.stringify({ widths: rows, wideAt1920: wide }, null, 2));
