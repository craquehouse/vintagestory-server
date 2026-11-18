// Story 21.7: measure every page of the web UI at phone and tablet widths (style of
// 17-8-browser/layout_widths.mjs; its helpers are copied, not imported).
//
//   cd web && bun ../_bmad-output/implementation-artifacts/21-7-browser/page_widths.mjs \
//     > ../_bmad-output/implementation-artifacts/21-7-browser/page_widths.<before|after>.json
//
// Reads only: every non-GET API request is refused, so nothing is written, and the game server
// is neither started nor stopped. No screenshots. The output holds numbers, test IDs,
// data-slot names and tag names only (no server name, key, password, mod description or log
// line). The page's API key comes from /config.js (Story 17.5), so /config.js is answered with
// VS_API_KEY_ADMIN. The pages render as installed the way e2e/config-js.ts's
// pretendServerInstalled does (only a `not_installed` status is rewritten).
//
// Stubbed: the installed mods (the three mods of the 17.8 script), the Version page's versions
// and the Scheduled Jobs (as in e2e/layout-widths.spec.ts, Story 21.7). Live: the Dashboard,
// Game Settings, the mod browser, the mod detail page and the console.
//
// For each width (height 900) and each sidebar state (the vs_ui_prefs cookie), in a fresh
// browser context per page and state:
// - documentOverflowX: document.documentElement.scrollWidth - clientWidth (0 = no sideways scroll)
// - scrolling: elements under <main> with overflow-x auto/scroll and scrollWidth > clientWidth,
//   as "testid-or-data-slot-or-tag:scrollWidth/clientWidth"
// - content: the content area's (main) [left, right, width], rounded
// - for the three tab lists the list's height and each trigger's height; for the Scheduled
//   Jobs tab and the Version page the layout (table or cards) and the table container's
//   scrollWidth/clientWidth
// Only one console page has a route (/game-server/console); GameServerPage is rendered by no
// route, so it cannot be measured (Story 21.7 Dev Notes, "ADR against the code").

import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const WIDTHS = [320, 390, 430, 768, 1023];
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

const JOBS = [
  { id: 'mod_cache_refresh', next_run_time: '2026-11-17T12:00:00Z', trigger_type: 'interval', trigger_details: 'every 3600 seconds' },
  { id: 'server_versions_check', next_run_time: null, trigger_type: 'cron', trigger_details: "cron[hour='*/6', minute='0']" },
  { id: 'mod_update_check', next_run_time: '2026-11-17T18:00:00Z', trigger_type: 'interval', trigger_details: 'every 21600 seconds' },
];

const VERSIONS = [
  { version: '1.22.7', channel: 'stable', is_latest: true },
  { version: '1.22.7-rc.12', channel: 'unstable', is_latest: false },
  { version: '1.22.6', channel: 'stable', is_latest: false },
  { version: '1.21.6-pre.1', channel: 'unstable', is_latest: false },
].map(({ version, channel, is_latest }) => ({
  version,
  filename: `vs_server_linux-x64_${version}.tar.gz`,
  filesize: '40.2 MB',
  md5: '0'.repeat(32),
  cdn_url: `https://cdn.example.com/${channel}/${version}`,
  local_url: `/downloads/${channel}/${version}`,
  is_latest,
  channel,
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
          data: { game_version: GAME_VERSION, checked_at: '2026-11-13T00:00:00Z', update_count: 1, mods: MODS.map(updateStatus) },
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
              status: compatibility.status, game_version: GAME_VERSION, mod_version: mod.version,
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

/** Serve the version list, filtered by ?channel= (registered after readOnly). */
async function fakeVersions(page) {
  await page.route(/\/api\/v1alpha1\/versions(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const channel = new URL(route.request().url()).searchParams.get('channel');
    const versions = channel ? VERSIONS.filter((item) => item.channel === channel) : VERSIONS;
    return route.fulfill({
      json: { status: 'ok', data: { versions, total: versions.length, cached: true, cached_at: null } },
    });
  });
}

/** Serve the Scheduled Jobs (registered after readOnly). */
async function fakeJobs(page) {
  await page.route(/\/api\/v1alpha1\/jobs(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    return route.fulfill({ json: { status: 'ok', data: { jobs: JOBS } } });
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

/** Height of the first tab list inside `scope` and of each of its triggers, as {testid: height}. */
async function tabHeights(page, scope) {
  return page.evaluate((s) => {
    const list = document.querySelector(`${s} [data-slot="tabs-list"]`);
    if (!list) return null;
    const triggers = {};
    for (const trigger of list.querySelectorAll('[data-slot="tabs-trigger"]')) {
      triggers[trigger.getAttribute('data-testid') || 'trigger'] = Math.round(trigger.getBoundingClientRect().height * 10) / 10;
    }
    return { list: Math.round(list.getBoundingClientRect().height * 10) / 10, triggers };
  }, scope);
}

/** The table container's scrollWidth/clientWidth inside `scope`, or null. */
async function tableContainer(page, scope) {
  return page.evaluate((s) => {
    const container = document.querySelector(`${s} [data-slot="table-container"]`);
    return container ? `${container.scrollWidth}/${container.clientWidth}` : null;
  }, scope);
}

const browser = await chromium.launch();

async function open(width, collapsed, url, waitFor, { mods = false, versions = false, jobs = false } = {}) {
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  await context.addCookies([
    { name: 'vs_ui_prefs', value: encodeURIComponent(JSON.stringify({ sidebarCollapsed: collapsed })), url: BASE },
  ]);
  const page = await context.newPage();
  await readOnly(page);
  if (mods) await fakeInstalledMods(page);
  if (versions) await fakeVersions(page);
  if (jobs) await fakeJobs(page);
  await page.goto(BASE + url);
  await page.waitForSelector(waitFor, { timeout: 30000 });
  await page.waitForTimeout(800);
  return { context, page };
}

/** Measure one page in a fresh context; `extra` adds page-specific numbers. */
async function measure(width, collapsed, url, waitFor, options = {}, extra = async () => ({})) {
  const { context, page } = await open(width, collapsed, url, waitFor, options);
  try {
    return { ...(await overflow(page)), content: await rect(page, 'main'), ...(await extra(page)) };
  } catch (error) {
    return { error: String(error.message).split('\n')[0] };
  } finally {
    await context.close();
  }
}

const rows = [];
for (const collapsed of [false, true]) {
  for (const width of WIDTHS) {
    const row = { width, sidebar: collapsed ? 'collapsed' : 'expanded', pages: {} };
    const at = (name, value) => {
      row.pages[name] = value;
    };

    at('dashboard', await measure(width, collapsed, '/', '[data-testid="dashboard-stats-grid"]'));

    at(
      'version',
      await measure(width, collapsed, '/game-server/version', '[data-testid="version-table"]', { versions: true }, async (page) => ({
        tabs: await tabHeights(page, '[data-testid="version-page"]'),
        layout: (await page.locator('[data-testid="version-table"]').count()) ? 'table' : 'none',
        tableContainer: await tableContainer(page, '[data-testid="version-page"]'),
        selectButton: await page.evaluate(() => {
          const button = document.querySelector('[data-testid^="version-table-select-"]');
          return button ? Math.round(button.getBoundingClientRect().height * 10) / 10 : null;
        }),
      }))
    );

    at('gameSettings', await measure(width, collapsed, '/game-server/settings', '[data-testid="game-config-layout"]'));

    at(
      'modsInstalled',
      await measure(
        width,
        collapsed,
        '/game-server/mods/installed',
        '[data-testid="mod-table"], [data-testid="installed-mod-cards"]',
        { mods: true },
        async (page) => ({
          tabs: await tabHeights(page, '[data-testid="mods-page"]'),
          layout: (await page.locator('[data-testid="mod-table"]').count()) ? 'table' : 'cards',
        })
      )
    );

    at(
      'modsBrowse',
      await measure(width, collapsed, '/game-server/mods/browse', '[data-testid="browse-results-count"]', {}, async (page) => ({
        tabs: await tabHeights(page, '[data-testid="mods-page"]'),
      }))
    );

    at('modDetail', await measure(width, collapsed, '/game-server/mods/browse/carryon', '[data-testid="mod-detail-header"]'));

    at('console', await measure(width, collapsed, '/game-server/console', '[data-testid="console-page"]'));

    {
      const { context, page } = await open(width, collapsed, '/config', '[data-testid="scheduled-jobs-tab"]', { jobs: true });
      const config = { tabs: await tabHeights(page, '[data-testid="settings-page"]'), content: await rect(page, 'main'), panels: {} };
      for (const tab of CONFIG_TABS) {
        const trigger = page.getByTestId(`${tab}-tab`);
        if (!(await trigger.count())) continue;
        await trigger.click();
        await page.waitForSelector(`[data-testid="${tab}-panel"]`, { timeout: 30000 });
        await page.waitForTimeout(500);
        const panel = { ...(await overflow(page)) };
        if (tab === 'scheduled-jobs') {
          panel.layout = (await page.locator('[data-testid="jobs-table"]').count())
            ? 'table'
            : (await page.locator('[data-testid="job-cards"]').count())
              ? 'cards'
              : 'none';
          panel.tableContainer = await tableContainer(page, '[data-testid="scheduled-jobs-panel"]');
        }
        config.panels[tab] = panel;
      }
      at('settings', config);
      await context.close();
    }

    rows.push(row);
  }
}

await browser.close();
console.log(JSON.stringify({ widths: rows }, null, 2));
