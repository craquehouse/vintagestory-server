// Story 21.7, Task 3 (VSS-vt4): reproduce the lost ArrowRight presses on the Settings tabs
// (style of 17-8-browser/layout_widths.mjs). Two modes, one in-page event log:
//
// Scripted matrix (Task 3.2), Chromium and Firefox:
//   cd web && bun ../_bmad-output/implementation-artifacts/21-7-browser/arrow_keys.mjs \
//     > ../_bmad-output/implementation-artifacts/21-7-browser/arrow_keys.scripted.json
//   (Firefox: `bunx playwright install firefox` once; it changes no project file.)
//
// Real keyboard (Task 3.3; needs a person at the keyboard):
//   cd web && bun ../_bmad-output/implementation-artifacts/21-7-browser/arrow_keys.mjs \
//     --keyboard chromium|firefox [--width 1440|390] [--cpu 6]
//   opens /config in a headed browser at that window width (default 1440) with the same event
//   log. Do the steps (Story 21.7 Dev Notes "Real keyboard steps"), reloading the page before
//   each attempt; each page load is one attempt. Press Enter in this terminal when done: the
//   log is added to ../_bmad-output/implementation-artifacts/21-7-browser/arrow_keys.keyboard.<browser>.json
//   (one session per run, so the 1440px and 390px runs and the --cpu run share the file).
//   --cpu 6 (Chromium only) slows the CPU six times through the DevTools protocol, the same
//   setting as the developer tools' Performance panel (step 4).
//
// Reads only: /config.js is answered with VS_API_KEY_ADMIN, every non-GET API request is
// refused, and the game server is neither started nor stopped. No screenshot. The output holds
// test IDs, key names, numbers and timestamps only.
//
// Event log (installed with addInitScript, so it runs before the app on every load):
// - keydown (capture, on window) of an arrow key: time (performance.now()), key, the target's
//   test ID, the focused element's test ID at dispatch, the number of [role=tab] elements, the
//   serial of the tab list element (a new serial = the list was remounted) and, read in a
//   setTimeout(0), defaultPrevented
// - focusin on a tab, and focusout from a tab to nothing (relatedTarget null): time, test ID
// - listShown: when ui-preferences-tab first appeared; fourthTab: when scheduled-jobs-tab
//   appeared; listMounts: each time a new tab list element appeared (MutationObserver)

import { createInterface } from 'node:readline';
import { readFileSync, writeFileSync, existsSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { chromium, firefox } from '../../../web/node_modules/@playwright/test/index.mjs';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const TABS = ['ui-preferences-tab', 'api-settings-tab', 'file-manager-tab', 'scheduled-jobs-tab'];
const EXPECTED = TABS[3];
const WAITS = [0, 100, 400, 1500];
const GAPS = [0, 10, 30, 100];
const RUNS = 10;
const FOCUS_POINTS = {
  // As soon as the first trigger is visible (before the role query has settled)
  listVisible: 'ui-preferences-tab',
  // As soon as the fourth trigger is visible (the bead's steps)
  fourthVisible: 'scheduled-jobs-tab',
};
const BROWSERS = { chromium, firefox };

function initLog() {
  const log = { events: [], listShown: null, fourthTab: null, listMounts: [] };
  window.__arrowLog = log;
  const report = (entry) => {
    log.events.push(entry);
    if (typeof window.__arrowReport === 'function') window.__arrowReport(entry);
  };
  const testId = (element) => (element && element.getAttribute ? element.getAttribute('data-testid') : null);
  let list = null;
  let serial = 0;
  const watch = () => {
    const current = document.querySelector('[data-testid="settings-page"] [role="tablist"]');
    if (current && current !== list) {
      list = current;
      serial += 1;
      const t = performance.now();
      log.listMounts.push(t);
      report({ type: 'listMount', t, serial, tabs: document.querySelectorAll('[role=tab]').length });
    }
    if (log.listShown === null && document.querySelector('[data-testid="ui-preferences-tab"]')) {
      log.listShown = performance.now();
      report({ type: 'listShown', t: log.listShown });
    }
    if (log.fourthTab === null && document.querySelector('[data-testid="scheduled-jobs-tab"]')) {
      log.fourthTab = performance.now();
      report({ type: 'fourthTab', t: log.fourthTab });
    }
  };
  new MutationObserver(watch).observe(document, { childList: true, subtree: true });
  window.addEventListener(
    'keydown',
    (event) => {
      if (!event.key.startsWith('Arrow')) return;
      const entry = {
        type: 'keydown',
        t: performance.now(),
        key: event.key,
        repeat: event.repeat,
        target: testId(event.target),
        active: testId(document.activeElement),
        tabs: document.querySelectorAll('[role=tab]').length,
        list: serial,
      };
      log.events.push(entry);
      setTimeout(() => {
        entry.defaultPrevented = event.defaultPrevented;
        if (typeof window.__arrowReport === 'function') window.__arrowReport(entry);
      }, 0);
    },
    true
  );
  window.addEventListener(
    'focusin',
    (event) => {
      if (event.target && event.target.getAttribute && event.target.getAttribute('role') === 'tab') {
        report({ type: 'focusin', t: performance.now(), target: testId(event.target) });
      }
    },
    true
  );
  window.addEventListener(
    'focusout',
    (event) => {
      if (event.target && event.target.getAttribute && event.target.getAttribute('role') === 'tab' && !event.relatedTarget) {
        report({ type: 'focusoutToNothing', t: performance.now(), target: testId(event.target) });
      }
    },
    true
  );
  window.addEventListener('pagehide', () => {
    const selected = document.querySelector('[role=tab][aria-selected="true"]');
    report({ type: 'final', t: performance.now(), focused: testId(document.activeElement), selected: testId(selected) });
  });
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

async function finalState(page) {
  return page.evaluate(() => ({
    focused: document.activeElement?.getAttribute('data-testid') ?? null,
    selected: document.querySelector('[role=tab][aria-selected="true"]')?.getAttribute('data-testid') ?? null,
  }));
}

/** Times relative to the list being shown, rounded to 0.1ms. */
function relative(log) {
  const zero = log.listShown ?? 0;
  const round = (t) => Math.round((t - zero) * 10) / 10;
  return {
    fourthTab: log.fourthTab === null ? null : round(log.fourthTab),
    listMounts: log.listMounts.map(round),
    events: log.events.map((entry) => ({ ...entry, t: round(entry.t) })),
  };
}

/** A press is stale when its keydown targets a tab focus has already been asked to leave. */
function staleTargets(events) {
  const keydowns = events.filter((entry) => entry.type === 'keydown');
  return keydowns.filter((entry, index) => index > 0 && entry.target === keydowns[index - 1].target).length;
}

async function scripted() {
  const result = { base: 'E2E_BASE_URL (production build)', runsPerCell: RUNS, browsers: {} };
  for (const [name, type] of Object.entries(BROWSERS)) {
    const browser = await type.launch();
    const summary = { version: browser.version(), cells: [] };
    for (const [focusPoint, focusTestId] of Object.entries(FOCUS_POINTS)) {
      for (const wait of WAITS) {
        for (const gap of GAPS) {
          const cell = { focusPoint, wait, gap, ok: 0, endedOn: {}, staleKeydowns: 0, remounts: 0, tabCountChangedDuringPresses: 0, failing: null };
          for (let run = 0; run < RUNS; run += 1) {
            const context = await browser.newContext({ viewport: { width: 1440, height: 900 } });
            await context.addInitScript(initLog);
            const page = await context.newPage();
            await readOnly(page);
            await page.goto(`${BASE}/config`);
            await page.getByTestId(focusTestId).waitFor({ state: 'visible', timeout: 30000 });
            if (wait) await page.waitForTimeout(wait);
            await page.getByTestId('ui-preferences-tab').focus();
            for (let press = 0; press < 3; press += 1) {
              if (press && gap) await page.waitForTimeout(gap);
              await page.keyboard.press('ArrowRight');
            }
            await page.waitForTimeout(200);
            const end = await finalState(page);
            const log = await page.evaluate(() => window.__arrowLog);
            const keydowns = log.events.filter((entry) => entry.type === 'keydown');
            const ok = end.focused === EXPECTED && end.selected === EXPECTED;
            if (ok) cell.ok += 1;
            const key = `${end.focused}|${end.selected}`;
            cell.endedOn[key] = (cell.endedOn[key] ?? 0) + 1;
            cell.staleKeydowns += staleTargets(log.events);
            cell.remounts += Math.max(0, log.listMounts.length - 1);
            if (new Set(keydowns.map((entry) => entry.tabs)).size > 1) cell.tabCountChangedDuringPresses += 1;
            if (!ok && !cell.failing) cell.failing = { end, ...relative(log) };
            await context.close();
          }
          summary.cells.push(cell);
          process.stderr.write(`${name} ${focusPoint} wait=${wait} gap=${gap}: ${cell.ok}/${RUNS}\n`);
        }
      }
    }
    result.browsers[name] = summary;
    await browser.close();
  }
  console.log(JSON.stringify(result, null, 2));
}

async function keyboard(name, width, cpu) {
  const type = BROWSERS[name];
  if (!type) throw new Error(`--keyboard chromium|firefox, not ${name}`);
  const browser = await type.launch({ headless: false });
  const context = await browser.newContext({ viewport: { width, height: 900 } });
  const attempts = [];
  let current = null;
  await context.exposeFunction('__arrowReport', (entry) => {
    if (entry.type === 'listMount' && entry.serial === 1) {
      current = { attempt: attempts.length + 1, zero: entry.t, events: [] };
      attempts.push(current);
    }
    if (current) current.events.push({ ...entry, t: Math.round((entry.t - current.zero) * 10) / 10 });
  });
  await context.addInitScript(initLog);
  const page = await context.newPage();
  if (cpu && name === 'chromium') {
    const session = await context.newCDPSession(page);
    await session.send('Emulation.setCPUThrottlingRate', { rate: cpu });
  }
  await readOnly(page);
  await page.goto(`${BASE}/config`);
  process.stderr.write(
    `${name} ${browser.version()} at ${width}px${cpu ? `, CPU slowed ${cpu}x` : ''}.\n` +
      'Reload the page before each attempt (F5 / Cmd+R), do the step, note focus and selection.\n' +
      'Press Enter here when done.\n'
  );
  await new Promise((resolve) => createInterface({ input: process.stdin }).once('line', resolve));
  const end = await finalState(page).catch(() => null);
  await browser.close();

  const file = new URL(`./arrow_keys.keyboard.${name}.json`, import.meta.url);
  const record = existsSync(file) ? JSON.parse(readFileSync(file, 'utf8')) : { browser: name, sessions: [] };
  record.sessions.push({
    version: browser.version(),
    width,
    cpuSlowdown: cpu || 1,
    lastPageEnd: end,
    attempts: attempts.map((attempt) => {
      const keydowns = attempt.events.filter((entry) => entry.type === 'keydown');
      const final = attempt.events.findLast((entry) => entry.type === 'final') ?? null;
      return {
        attempt: attempt.attempt,
        keydowns: keydowns.length,
        staleKeydowns: staleTargets(attempt.events),
        listMounts: attempt.events.filter((entry) => entry.type === 'listMount').length,
        final,
        events: attempt.events,
      };
    }),
  });
  writeFileSync(file, `${JSON.stringify(record, null, 2)}\n`);
  process.stderr.write(`Wrote ${attempts.length} attempts to ${fileURLToPath(file)}\n`);
}

const args = process.argv.slice(2);
const option = (flag) => {
  const index = args.indexOf(flag);
  return index === -1 ? null : args[index + 1];
};
if (option('--keyboard')) {
  await keyboard(option('--keyboard'), Number(option('--width') ?? 1440), Number(option('--cpu') ?? 0));
} else {
  await scripted();
}
