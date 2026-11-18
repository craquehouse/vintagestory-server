// Story 21.8: measure the page content's width and position on wide screens (frame of
// 21-7-browser/page_widths.mjs; its helpers are copied, not imported).
//
//   cd web && bun ../_bmad-output/implementation-artifacts/21-8-browser/content_widths.mjs \
//     > ../_bmad-output/implementation-artifacts/21-8-browser/content_widths.<before|after>.json
//
// Reads only: every non-GET API request is refused, so nothing is written, and the game server
// is neither started nor stopped. No screenshots. The output holds numbers and test IDs only
// (no server name, key, password, mod description or log line). /config.js is answered with
// VS_API_KEY_ADMIN; the pages render as installed the way e2e/config-js.ts's
// pretendServerInstalled does (only a `not_installed` status is rewritten).
//
// Stubbed: the installed mods (the three mods of e2e/layout-widths.spec.ts), the mod browser
// (eight made-up mods, no logos, one game version, no tags) and the mod detail page of the
// first of them. Live: the Dashboard, the Version page, Game Settings, /config and the console.
//
// For each width (height 900) and each sidebar state (the vs_ui_prefs cookie
// `{ sidebar: 'expanded' | 'collapsed' }`), in a fresh browser context per page and state:
// - content: the page content's [left, right, width], rounded. That is the padding div's
//   content box (`main > div`, left + 24 to right - 24 from md); after Task 4 it is also
//   `pageContent`, the `page-content` wrapper's box (absent before Task 4)
// - sidebar: the fixed sidebar's width; header: the header bar's [left, right]
// - documentOverflowX and `scrolling` (elements under <main> that scroll sideways)
// - per page one or more key elements' [left, right, width] (and the long-named mod's name
//   height against a one-line name on the installed mods table)

import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const WIDTHS = [1024, 1280, 1440, 1920, 2560];
const CONFIG_TABS = ['ui-preferences', 'api-settings', 'file-manager', 'scheduled-jobs'];
const GAME_VERSION = '1.22.7';

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

const BROWSE_MODS = Array.from({ length: 8 }, (_, index) => ({
  slug: `widthmod${index + 1}`,
  mod_ids: [`widthmod${index + 1}`],
  urlalias: `widthmod${index + 1}`,
  asset_id: 0,
  name: `Width Mod ${index + 1}`,
  author: 'E2E',
  summary: 'A stubbed browse item',
  downloads: 1,
  follows: 1,
  trending_points: 1,
  side: 'both',
  mod_type: 'mod',
  logo_url: null,
  tags: [],
  last_released: '2026-11-01 00:00:00',
  has_release_for_game_version: true,
}));

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

function lookupBody(slug, name, version, compatibility) {
  return {
    status: 'ok',
    data: {
      slug, urlalias: null, asset_id: 0, name, author: 'Someone', description: null,
      latest_version: version, downloads: 0, follows: 0, side: 'Both',
      compatibility: {
        status: compatibility.status, game_version: GAME_VERSION, mod_version: version,
        message: compatibility.message, latest_supported_game_version: compatibility.latest,
      },
      logo_url: null, releases: [], tags: [], homepage_url: null, source_url: null, created: null, last_released: null,
    },
  };
}

/** Answer /config.js with the Admin key, show the server as installed, refuse every write to the API. */
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
  // As e2e/config-js.ts pretendServerInstalled: only a not_installed answer is rewritten
  await page.route('**/api/v1alpha1/server/status', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const headers = await route.request().allHeaders();
    const response = await route.fetch({ headers: { ...headers, connection: 'close' } });
    const body = await response.json();
    if (response.ok() && body.data?.state === 'not_installed') {
      body.data = { ...body.data, state: 'installed', version: GAME_VERSION };
    }
    return route.fulfill({ response, json: body });
  });
}

/** Serve the installed mods, their updates, the browser and the lookups (registered after readOnly). */
async function fakeMods(page) {
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
              filename: `${slug}_${version}.zip`, slug, version, enabled,
              installed_at: '2026-11-13T00:00:00Z', asset_id: 0, name, authors: [], description: null, side: 'Both',
            })),
          },
        },
      });
    }
    if (path === '/updates') {
      return route.fulfill({
        json: {
          status: 'ok',
          data: { game_version: GAME_VERSION, checked_at: '2026-11-13T00:00:00Z', update_count: 1, mods: MODS.map(updateStatus) },
        },
      });
    }
    if (path === '/browse') {
      return route.fulfill({
        json: {
          status: 'ok',
          data: {
            mods: BROWSE_MODS,
            pagination: { page: 1, page_size: 20, total_items: BROWSE_MODS.length, total_pages: 1, has_next: false, has_prev: false },
            game_version: GAME_VERSION,
          },
        },
      });
    }
    if (path === '/gameversions') return route.fulfill({ json: { status: 'ok', data: { versions: [GAME_VERSION] } } });
    if (path === '/tags') return route.fulfill({ json: { status: 'ok', data: { tags: [] } } });
    const lookup = path.match(/^\/lookup\/([^/]+)$/);
    if (lookup) {
      const slug = decodeURIComponent(lookup[1]);
      const mod = MODS.find((item) => item.slug === slug);
      if (mod && COMPATIBILITY[slug]) return route.fulfill({ json: lookupBody(slug, mod.name, mod.version, COMPATIBILITY[slug]) });
      const browsed = BROWSE_MODS.find((item) => item.slug === slug);
      if (browsed) {
        return route.fulfill({ json: lookupBody(slug, browsed.name, '1.0.0', COMPATIBILITY.offmod) });
      }
      return route.fulfill({ status: 404, json: { detail: { code: 'MOD_NOT_FOUND', message: slug } } });
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

/** The layout's numbers: the padding div's content box, page-content, the sidebar and the header. */
async function layout(page) {
  return page.evaluate(() => {
    const round = (value) => Math.round(value);
    const padding = document.querySelector('main > div');
    let content = null;
    if (padding) {
      const r = padding.getBoundingClientRect();
      const style = getComputedStyle(padding);
      const left = r.left + parseFloat(style.paddingLeft);
      const right = r.right - parseFloat(style.paddingRight);
      content = [round(left), round(right), round(right - left)];
    }
    const box = (selector) => {
      const element = document.querySelector(selector);
      if (!element) return null;
      const r = element.getBoundingClientRect();
      return [round(r.left), round(r.right), round(r.width)];
    };
    const sidebar = box('[data-testid="desktop-sidebar"]') ?? box('.fixed.inset-y-0');
    return {
      content,
      pageContent: box('[data-testid="page-content"]'),
      sidebar: sidebar ? sidebar[2] : null,
      header: box('header'),
    };
  });
}

const browser = await chromium.launch();

async function open(width, collapsed, url, waitFor) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  await context.addCookies([
    { name: 'vs_ui_prefs', value: encodeURIComponent(JSON.stringify({ sidebar: collapsed ? 'collapsed' : 'expanded' })), url: BASE },
  ]);
  const page = await context.newPage();
  await readOnly(page);
  await fakeMods(page);
  await page.goto(BASE + url);
  await page.waitForSelector(waitFor, { timeout: 30000 });
  await page.waitForTimeout(800);
  return { context, page };
}

/** Measure one page in a fresh context; `keys` are selectors of key elements to record. */
async function measure(width, collapsed, url, waitFor, keys = {}, extra = async () => ({})) {
  const { context, page } = await open(width, collapsed, url, waitFor);
  try {
    const elements = {};
    for (const [name, selector] of Object.entries(keys)) elements[name] = await rect(page, selector);
    return { ...(await layout(page)), ...(await overflow(page)), elements, ...(await extra(page)) };
  } catch (error) {
    return { error: String(error.message).split('\n')[0] };
  } finally {
    await context.close();
  }
}

async function height(page, testId) {
  return page.evaluate((id) => {
    const element = document.querySelector(`[data-testid="${id}"]`);
    return element ? Math.round(element.getBoundingClientRect().height * 10) / 10 : null;
  }, testId);
}

const rows = [];
for (const collapsed of [false, true]) {
  for (const width of WIDTHS) {
    const row = { width, sidebar: collapsed ? 'collapsed' : 'expanded', pages: {} };
    const at = (name, value) => {
      row.pages[name] = value;
    };

    at(
      'dashboard',
      await measure(width, collapsed, '/', '[data-testid="dashboard-stats-grid"]', {
        statsGrid: '[data-testid="dashboard-stats-grid"]',
        chartCard: '[data-testid="metrics-chart-card"]',
      })
    );

    at('version', await measure(width, collapsed, '/game-server/version', '[data-testid="version-page"]', { versionPage: '[data-testid="version-page"]' }));

    at(
      'gameSettings',
      await measure(width, collapsed, '/game-server/settings', '[data-testid="game-config-layout"]', {
        gameConfigLayout: '[data-testid="game-config-layout"]',
      })
    );

    at(
      'modsInstalled',
      await measure(
        width,
        collapsed,
        '/game-server/mods/installed',
        '[data-testid="mod-table"], [data-testid="installed-mod-cards"]',
        { modTable: '[data-testid="mod-table"]' },
        async (page) => ({
          longNameHeight: await height(page, 'mod-link-longnamemod'),
          oneLineNameHeight: await height(page, 'mod-link-offmod'),
        })
      )
    );

    at(
      'modsBrowse',
      await measure(width, collapsed, '/game-server/mods/browse', '[data-testid="mod-card-widthmod5"]', {
        grid: '[data-testid="mod-browse-grid"]',
        firstCard: '[data-testid="mod-card-widthmod1"]',
        fifthCard: '[data-testid="mod-card-widthmod5"]',
      }, async (page) => ({
        cardTops: await page.evaluate(() =>
          [1, 4, 5].map((n) => {
            const card = document.querySelector(`[data-testid="mod-card-widthmod${n}"]`);
            return card ? Math.round(card.getBoundingClientRect().top) : null;
          })
        ),
      }))
    );

    at(
      'modDetail',
      await measure(width, collapsed, '/game-server/mods/browse/widthmod1', '[data-testid="mod-detail-header"]', {
        modDetailPage: '[data-testid="mod-detail-page"]',
      })
    );

    at('console', await measure(width, collapsed, '/game-server/console', '[data-testid="console-page"]', { consolePanel: '[data-testid="console-panel"]' }));

    {
      const { context, page } = await open(width, collapsed, '/config', '[data-testid="ui-preferences-panel"]');
      const config = { ...(await layout(page)), panels: {} };
      for (const tab of CONFIG_TABS) {
        const trigger = page.getByTestId(`${tab}-tab`);
        if (!(await trigger.count())) continue;
        await trigger.click();
        await page.waitForSelector(`[data-testid="${tab}-panel"]`, { timeout: 30000 });
        await page.waitForTimeout(500);
        config.panels[tab] = { ...(await overflow(page)), panel: await rect(page, `[data-testid="${tab}-panel"]`) };
      }
      at('settings', config);
      await context.close();
    }

    rows.push(row);
  }
}

await browser.close();
console.log(JSON.stringify({ widths: rows }, null, 2));
