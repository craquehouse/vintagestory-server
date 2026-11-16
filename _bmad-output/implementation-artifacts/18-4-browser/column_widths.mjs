// Story 18.4: measure the installed mods table's columns at 1024px and wider (stubs and
// helpers from 17-8-browser/layout_widths.mjs, which stays unchanged as Story 17.8's record).
//
//   cd web && bun ../_bmad-output/implementation-artifacts/18-4-browser/column_widths.mjs \
//     > ../_bmad-output/implementation-artifacts/18-4-browser/column_widths.<before|after>.json
//
// Reads only. The installed mods, their update status and lookups are stubbed; every non-GET
// API request is refused, so nothing is written. No screenshots; the output holds numbers and
// test IDs only (no server name, key or password). /config.js is answered with
// VS_API_KEY_ADMIN.
//
// Fixtures: "long" is Story 17.8's (a 63-character name with an offered pre-release update,
// an incompatible mod, a disabled mod); "short" replaces the long name with `Short Mod`, which
// still offers a pre-release update (the SHORT_MODS of e2e/layout-widths.spec.ts); "longVersion"
// is "long" with the offered version 10.10.10-rc.130 (LONG_VERSION_MODS of the e2e).
//
// For each fixture, width (height 900) and sidebar state (the vs_ui_prefs cookie), in a fresh
// browser context:
// - documentOverflowX: document.documentElement.scrollWidth - clientWidth
// - scrolling: elements under <main> with overflow-x auto/scroll and scrollWidth > clientWidth
// - table: [scrollWidth, clientWidth] of [data-slot="table-container"]
// - columns: each thead th's width, by its text ("(actions)" for the last)
// - rowHeights: each fixture row's height, by slug
// - toggleInside / removeInside: whether the first mod's toggle and remove button end inside
//   the viewport

import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const WIDTHS = [1024, 1280, 1440, 1920];

const LONG_NAME = 'An Extraordinarily Long Mod Name That Must Wrap Inside Its Card';
const OTHER_MODS = [
  { slug: 'oldmod', name: 'Old Mod', version: '2.3.4', enabled: true },
  { slug: 'offmod', name: 'Off Mod', version: '0.1.0', enabled: false },
];
const FIXTURES = {
  long: [
    { slug: 'longnamemod', name: LONG_NAME, version: '1.0.0-rc.12', enabled: true, offered: '1.0.0-rc.13' },
    ...OTHER_MODS,
  ],
  // Story 18.4 review: the long name offering a longer version string (margin check)
  longVersion: [
    { slug: 'longnamemod', name: LONG_NAME, version: '1.0.0-rc.12', enabled: true, offered: '10.10.10-rc.130' },
    ...OTHER_MODS,
  ],
  short: [
    { slug: 'shortmod', name: 'Short Mod', version: '1.4.0', enabled: true, offered: '1.5.0-rc.1' },
    ...OTHER_MODS,
  ],
};
const COMPATIBILITY = {
  longnamemod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
  shortmod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
  oldmod: { status: 'incompatible', message: 'Last supported game version: 1.21.1.', latest: '1.21.1' },
  offmod: { status: 'compatible', message: 'Compatible with 1.22.7.', latest: '1.22.7' },
};

function updateStatus({ slug, name, version, offered }) {
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
async function fakeInstalledMods(page, mods) {
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
          },
        },
      });
    }
    if (path === '/updates') {
      return route.fulfill({
        json: {
          status: 'ok',
          data: { game_version: '1.22.7', checked_at: '2026-11-13T00:00:00Z', update_count: 1, mods: mods.map(updateStatus) },
        },
      });
    }
    const lookup = path.match(/^\/lookup\/([^/]+)$/);
    if (lookup) {
      const slug = decodeURIComponent(lookup[1]);
      const mod = mods.find((item) => item.slug === slug);
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

async function measure(page, mods, width) {
  return page.evaluate(
    ({ slugs, first, width }) => {
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
      const container = document.querySelector('[data-slot="table-container"]');
      const columns = {};
      for (const th of document.querySelectorAll('[data-testid="mod-table"] thead th')) {
        const label = th.textContent.trim() === 'Actions' || !th.textContent.trim() ? '(actions)' : th.textContent.trim();
        columns[label] = Math.round(th.getBoundingClientRect().width);
      }
      const rowHeights = {};
      for (const slug of slugs) {
        const row = document.querySelector(`[data-testid="mod-row-${slug}"]`);
        rowHeights[slug] = row ? Math.round(row.getBoundingClientRect().height) : null;
      }
      const inside = (testId) => {
        const element = document.querySelector(`[data-testid="${testId}"]`);
        if (!element) return null;
        const r = element.getBoundingClientRect();
        return r.left >= 0 && r.right <= width;
      };
      return {
        documentOverflowX: root.scrollWidth - root.clientWidth,
        scrolling,
        table: container ? [container.scrollWidth, container.clientWidth] : null,
        columns,
        rowHeights,
        toggleInside: inside(`mod-toggle-${first}`),
        removeInside: inside(`mod-remove-${first}`),
      };
    },
    { slugs: mods.map((mod) => mod.slug), first: mods[0].slug, width }
  );
}

const browser = await chromium.launch();
const rows = [];
for (const [fixture, mods] of Object.entries(FIXTURES)) {
  for (const collapsed of [false, true]) {
    for (const width of WIDTHS) {
      const context = await browser.newContext({ viewport: { width, height: 900 } });
      await context.addCookies([
        { name: 'vs_ui_prefs', value: encodeURIComponent(JSON.stringify({ sidebarCollapsed: collapsed })), url: BASE },
      ]);
      const page = await context.newPage();
      await readOnly(page);
      await fakeInstalledMods(page, mods);
      await page.goto(BASE + '/game-server/mods/installed');
      await page.waitForSelector('[data-testid="mod-table"]', { timeout: 30000 });
      await page.waitForSelector(`[data-testid="mod-update-${mods[0].slug}"]`, { timeout: 30000 });
      await page.waitForTimeout(800);
      rows.push({ fixture, width, sidebar: collapsed ? 'collapsed' : 'expanded', ...(await measure(page, mods, width)) });
      await context.close();
    }
  }
}
await browser.close();
console.log(JSON.stringify(rows, null, 2));
