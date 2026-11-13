// Story 16.0 Task 1: probe mod browser restoration and sort behavior.
//
// Runs against the dev stack (`just docker restart`, http://localhost:8080) with a
// game version installed. Writes a JSON report to stdout; progress goes to stderr.
//
//   cd web && bun ../_bmad-output/implementation-artifacts/16-0-spike/browse_probe.mjs \
//     > ../_bmad-output/implementation-artifacts/16-0-spike/browse_probe.out.json
//
// Uses the web package's Playwright install; no new dependencies.

import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const BROWSE = `${BASE}/game-server/mods/browse`;
const log = (...a) => console.error('[probe]', ...a);

async function snapshot(page) {
  return page.evaluate(() => {
    const current = document.querySelector('[data-testid="pagination"] [aria-current="page"]');
    const search = document.querySelector('[data-testid="browse-search-input"]');
    const count = document.querySelector('[data-testid="browse-results-count"]');
    const sortButton = [...document.querySelectorAll('button')].find((b) =>
      b.parentElement?.textContent?.includes('Sort by:'),
    );
    const grid = document.querySelector('[data-testid="mod-browse-grid"]');
    return {
      url: location.pathname + location.search,
      scrollY: Math.round(window.scrollY),
      page: current ? Number(current.textContent) : null,
      search: search ? search.value : null,
      sort: sortButton ? sortButton.textContent.trim() : null,
      resultsText: count ? count.textContent.trim() : null,
      error: document.querySelector('[data-testid="browse-error-message"]')?.textContent?.trim() ?? null,
      cardCount: grid ? grid.children.length : 0,
    };
  });
}

async function waitForGrid(page) {
  await page.waitForSelector('[data-testid="mod-browse-grid"] [data-testid^="mod-card-"]', { timeout: 60000 });
}

async function goToPage(page, n) {
  for (let p = 1; p < n; p++) {
    await page.getByRole('button', { name: 'Go to next page' }).click();
    await page.waitForFunction(
      (want) => document.querySelector('[data-testid="pagination"] [aria-current="page"]')?.textContent === String(want),
      p + 1,
    );
    await waitForGrid(page);
  }
}

// Scroll down, then open the card nearest the vertical middle of the viewport.
async function scrollAndOpenCard(page, scrollTo) {
  await page.evaluate((y) => window.scrollTo(0, y), scrollTo);
  await page.waitForTimeout(300);
  const slug = await page.evaluate(() => {
    const grid = document.querySelector('[data-testid="mod-browse-grid"]');
    const mid = window.innerHeight / 2;
    let best = null;
    let bestDist = Infinity;
    for (const card of grid.children) {
      const r = card.getBoundingClientRect();
      const d = Math.abs(r.top + r.height / 2 - mid);
      if (d < bestDist) {
        bestDist = d;
        best = card.dataset.testid?.replace(/^mod-card-/, '');
      }
    }
    return best;
  });
  const before = await snapshot(page);
  await page.locator(`[data-testid="mod-card-name-${slug}"]`).click();
  await page.waitForURL(/\/mods\/browse\/.+/);
  await page.waitForSelector('[data-testid="mod-detail-back"]', { timeout: 60000 });
  return { slug, before };
}

async function cardVisible(page, slug) {
  return page.evaluate((s) => {
    const el = document.querySelector(`[data-testid="mod-card-${s}"]`);
    if (!el) return 'not-rendered';
    const r = el.getBoundingClientRect();
    return r.bottom > 0 && r.top < window.innerHeight ? 'in-viewport' : 'off-screen';
  }, slug);
}

const RETURNS = {
  backButton: (page) => page.locator('[data-testid="mod-detail-back"]').click(),
  breadcrumb: (page) => page.locator('[data-testid="mod-detail-breadcrumb-browse"]').click(),
  browseTab: (page) => page.locator('[data-testid="browse-tab"]').click(),
  browserBack: (page) => page.goBack(),
};

async function roundTrip(context, { name, returnVia, pageNo = 3, search = null, throttle = false, scrollTo = 1500 }) {
  const page = await context.newPage();
  if (throttle) {
    const cdp = await context.newCDPSession(page);
    await cdp.send('Network.enable');
    // DevTools "Slow 4G" preset
    await cdp.send('Network.emulateNetworkConditions', {
      offline: false,
      latency: 562.5,
      downloadThroughput: (1.4 * 1024 * 1024) / 8,
      uploadThroughput: (675 * 1024) / 8,
    });
  }
  await page.goto(BROWSE);
  await waitForGrid(page);
  if (search) {
    await page.locator('[data-testid="browse-search-input"]').fill(search);
    await page.waitForTimeout(1500);
    await waitForGrid(page);
  }
  await goToPage(page, pageNo);
  const { slug, before } = await scrollAndOpenCard(page, scrollTo);
  await RETURNS[returnVia](page);
  await page.waitForURL(/\/mods\/browse$/);
  await waitForGrid(page);
  // Sample after the grid renders: just after the 100 ms restore timeout, then later.
  const at = {};
  let elapsed = 0;
  for (const ms of [150, 1000, 3000]) {
    await page.waitForTimeout(ms - elapsed);
    elapsed = ms;
    at[`${ms}ms`] = { ...(await snapshot(page)), openedCard: await cardVisible(page, slug) };
  }
  await page.close();
  return { name, returnVia, search, throttle, opened: slug, before, after: at };
}

async function staleRestore(context) {
  const page = await context.newPage();
  await page.goto(BROWSE);
  await waitForGrid(page);
  await goToPage(page, 3);
  const { slug, before } = await scrollAndOpenCard(page, 1500);
  // Leave through the sidebar-equivalent route, then come back later.
  await page.goto(`${BASE}/game-server/settings`);
  await page.waitForTimeout(1000);
  await page.goto(`${BASE}/game-server/mods/installed`);
  await page.waitForTimeout(1000);
  await page.locator('[data-testid="browse-tab"]').click();
  await page.waitForURL(/\/mods\/browse$/);
  await waitForGrid(page);
  await page.waitForTimeout(1000);
  const after = { ...(await snapshot(page)), openedCard: await cardVisible(page, slug) };
  await page.close();
  return { name: 'stale-restore', opened: slug, before, after };
}

async function sorts(context) {
  const results = [];
  for (const label of ['Newest', 'Most Downloaded', 'Trending', 'Name (A-Z)']) {
    const page = await context.newPage();
    const responses = [];
    page.on('response', (r) => {
      if (r.url().includes('/api/v1alpha1/mods/browse')) {
        responses.push({ status: r.status(), query: new URL(r.url()).search });
      }
    });
    await page.goto(BROWSE);
    await waitForGrid(page);
    responses.length = 0;
    await page.getByRole('button', { name: /Newest/ }).click();
    await page.getByRole('menuitem', { name: label }).click();
    await page.waitForTimeout(4000);
    results.push({ sort: label, responses, state: await snapshot(page) });
    await page.close();
  }
  return results;
}

const browser = await chromium.launch();
const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
const report = { base: BASE, ranAt: new Date().toISOString(), roundTrips: [], stale: null, sorts: null };

for (const returnVia of Object.keys(RETURNS)) {
  log('default', returnVia);
  report.roundTrips.push(await roundTrip(context, { name: `default-${returnVia}`, returnVia }));
}
log('throttled backButton');
report.roundTrips.push(await roundTrip(context, { name: 'throttled-backButton', returnVia: 'backButton', throttle: true }));
log('throttled browserBack');
report.roundTrips.push(await roundTrip(context, { name: 'throttled-browserBack', returnVia: 'browserBack', throttle: true }));
log('search backButton');
report.roundTrips.push(await roundTrip(context, { name: 'search-backButton', returnVia: 'backButton', search: 'food', pageNo: 2, scrollTo: 900 }));
log('stale restore');
report.stale = await staleRestore(context);
log('sorts');
report.sorts = await sorts(context);

await browser.close();
console.log(JSON.stringify(report, null, 2));
