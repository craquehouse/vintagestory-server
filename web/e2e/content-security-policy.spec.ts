import { test, expect, type Page, type WebSocket } from '@playwright/test';
import { serveConfigKey } from './config-js';

/**
 * E2E tests for the web UI's Content-Security-Policy.
 *
 * Story 19.3 (FR213-FR216; VSS-3qb8, VSS-my4c; Epic 19 ADR-6):
 * - `/` and the web UI's paths carry the policy, `nosniff`, `no-referrer` and
 *   `X-Frame-Options: DENY`; `/healthz`, `/readyz` and the API carry no policy (AC 1, 2).
 * - Every main page, in the light and the dark theme, works with no `securitypolicyviolation`
 *   event, no console error and no page error (AC 3). On the mod detail page the `https` and
 *   `data:` description images and the gallery load, the `http` and relative images are shown
 *   as "Image not shown: <alt>" and are never requested (AC 6, 9).
 * - The terminal, a toast and a dialog are styled (AC 3).
 * - The console WebSocket, and the log stream when the stack lists a log file, connect under
 *   `connect-src 'self'` (AC 4).
 * - An injected inline script does not run and a frame on another origin does not load (AC 5).
 *
 * Reads only. Every write to the API is refused, apart from `POST /api/v1alpha1/auth/ws-token`:
 * the console needs a token to open its socket, and the token store is in memory. Nothing is
 * installed or changed; the game server is neither started nor stopped; no screenshot.
 *
 * Stubs (so the spec needs neither a game server nor the mod database):
 * - `GET /api/v1alpha1/server/status`: installed and stopped.
 * - `GET /api/v1alpha1/config/game`: no settings (404 without a game server).
 * - `GET /api/v1alpha1/mods`, `/mods/updates`, `/mods/browse`, `/mods/lookup/<slug>`: one
 *   installed mod, one browse item, and the made-up `e2ecspmod` with three screenshots and the
 *   description under test; `/mods/gameversions` and `/mods/tags`: one version, no tags.
 * - `GET /api/v1alpha1/versions`: an empty version list.
 * - Every request to `https://moddbcdn.vintagestory.at/**` and `https://images.example.com/**`
 *   is answered with a 1x1 PNG.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080), rebuilt from this branch:
 *   `just docker restart`, then `cd web && bunx playwright test e2e/content-security-policy.spec.ts`
 *   with VS_API_KEY_ADMIN exported.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const BASE_URL = process.env.E2E_BASE_URL || 'http://localhost:8080';

// Written out, not imported: a changed directive is a deliberate edit in two places
const POLICY =
  "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; " +
  "img-src 'self' data: https:; font-src 'self'; connect-src 'self'; frame-src 'none'; " +
  "object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'none'";

const IMAGE_NOT_SHOWN = 'Image not shown';
const SLUG = 'e2ecspmod';
const INSTALLED_SLUG = 'e2ecspinstalled';
const CDN = 'https://moddbcdn.vintagestory.at';
const IMAGES = 'https://images.example.com';
const COLOR_SCHEMES: Array<'light' | 'dark'> = ['light', 'dark'];

// A 1x1 PNG
const PNG_BASE64 =
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';
const PNG = Buffer.from(PNG_BASE64, 'base64');

const DESCRIPTION =
  '<p style="color: #c33">Styled</p>' +
  `<img alt="secure" src="${IMAGES}/a.png">` +
  '<img alt="plain" src="http://images.example.com/b.png">' +
  '<img alt="relative" src="/c.png">' +
  `<img alt="inline" src="data:image/png;base64,${PNG_BASE64}">`;

interface Violation {
  directive: string;
  blocked: string;
  source: string;
}

declare global {
  interface Window {
    __cspViolations: Violation[];
    __injected?: boolean;
  }
}

const SERVER_STATUS = {
  status: 'ok',
  data: {
    state: 'installed',
    version: '1.22.7',
    uptime_seconds: null,
    last_exit_code: null,
    available_stable_version: '1.22.7',
    available_unstable_version: null,
    version_last_checked: '2026-11-13T00:00:00Z',
    disk_space: {
      total_gb: 100,
      used_gb: 40,
      available_gb: 60,
      usage_percent: 40,
      warning: false,
    },
  },
};

function lookupBody(slug: string, name: string, description: string | null, screenshots: number) {
  return {
    status: 'ok',
    data: {
      slug,
      urlalias: null,
      asset_id: 0,
      name,
      author: 'Someone',
      description,
      latest_version: '1.0.0',
      install_mod_id: slug,
      downloads: 0,
      follows: 0,
      side: 'Both',
      compatibility: {
        status: 'compatible',
        game_version: '1.22.7',
        mod_version: '1.0.0',
        message: null,
        latest_supported_game_version: '1.22.7',
      },
      logo_url: null,
      releases: [
        {
          version: '1.0.0',
          filename: `${slug}_1.0.0.zip`,
          file_id: 1,
          modidstr: slug,
          downloads: 0,
          game_versions: ['1.22.7'],
          created: '2026-11-01 00:00:00',
          changelog: null,
        },
      ],
      tags: [],
      homepage_url: null,
      source_url: null,
      created: null,
      last_released: null,
      screenshots: Array.from({ length: screenshots }, (_, i) => ({
        image_url: `${CDN}/e2e-csp-${i + 1}.png`,
        thumbnail_url: `${CDN}/e2e-csp-${i + 1}_55_60.png`,
        filename: `e2e-csp-${i + 1}.png`,
      })),
      trailer_url: null,
    },
  };
}

const INSTALLED_BODY = {
  status: 'ok',
  data: {
    mods: [
      {
        filename: `${INSTALLED_SLUG}_1.0.0.zip`,
        slug: INSTALLED_SLUG,
        version: '1.0.0',
        enabled: true,
        installed_at: '2026-11-13T00:00:00Z',
        asset_id: 0,
        name: 'E2E CSP Installed',
        authors: [],
        description: null,
        side: 'Both',
      },
    ],
    pending_restart: false,
  },
};

const UPDATES_BODY = {
  status: 'ok',
  data: {
    game_version: '1.22.7',
    checked_at: '2026-11-13T00:00:00Z',
    update_count: 0,
    mods: [
      {
        slug: INSTALLED_SLUG,
        name: 'E2E CSP Installed',
        installed_version: '1.0.0',
        status: 'up_to_date',
        offered_version: null,
        offered_compatibility: null,
        offered_prerelease: null,
        reason: null,
        checked_at: '2026-11-13T00:00:00Z',
        error: null,
      },
    ],
  },
};

const BROWSE_BODY = {
  status: 'ok',
  data: {
    mods: [
      {
        slug: SLUG,
        mod_ids: [SLUG],
        urlalias: SLUG,
        asset_id: 0,
        name: 'E2E CSP Mod',
        author: 'E2E',
        summary: 'A stubbed browse item',
        downloads: 1,
        follows: 1,
        trending_points: 1,
        side: 'both',
        mod_type: 'mod',
        logo_url: `${CDN}/e2e-csp-logo.png`,
        tags: [],
        last_released: '2026-11-01 00:00:00',
        has_release_for_game_version: true,
      },
    ],
    pagination: {
      page: 1,
      page_size: 20,
      total_items: 1,
      total_pages: 1,
      has_next: false,
      has_prev: false,
    },
    game_version: '1.22.7',
  },
};

interface Recorded {
  consoleErrors: string[];
  pageErrors: string[];
  requests: string[];
}

/**
 * The Admin key through /config.js, every write refused (but the WebSocket token), the
 * stubs above, a securitypolicyviolation listener and a record of errors and requests.
 */
async function prepare(page: Page): Promise<Recorded> {
  const recorded: Recorded = { consoleErrors: [], pageErrors: [], requests: [] };
  await page.addInitScript(() => {
    window.__cspViolations = [];
    document.addEventListener('securitypolicyviolation', (event) => {
      window.__cspViolations.push({
        directive: event.effectiveDirective,
        blocked: event.blockedURI,
        source: event.sourceFile,
      });
    });
  });
  page.on('console', (message) => {
    if (message.type() === 'error') recorded.consoleErrors.push(message.text());
  });
  page.on('pageerror', (error) => recorded.pageErrors.push(error.message));
  page.on('request', (request) => recorded.requests.push(request.url()));

  await serveConfigKey(page, API_KEY);
  await page.route('**/api/**', async (route) => {
    const request = route.request();
    if (request.method() !== 'GET' && !new URL(request.url()).pathname.endsWith('/ws-token')) {
      // Never let a write reach the server's data
      await route.fulfill({
        status: 500,
        json: { detail: { code: 'E2E_BLOCKED', message: 'read only' } },
      });
      return;
    }
    await route.fallback();
  });
  // Registered after the read-only route, so these run first and fall back to it
  await page.route(/\/api\/v1alpha1\/server\/status(\?.*)?$/, (route) =>
    route.request().method() === 'GET' ? route.fulfill({ json: SERVER_STATUS }) : route.fallback()
  );
  await page.route(/\/api\/v1alpha1\/config\/game(\?.*)?$/, (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({
          json: {
            status: 'ok',
            data: { settings: [], source_file: 'serverconfig.json', last_modified: null },
          },
        })
      : route.fallback()
  );
  // The version list; without it a stack that cannot reach the vendor's API logs a 503
  await page.route(/\/api\/v1alpha1\/versions(\?.*)?$/, (route) =>
    route.request().method() === 'GET'
      ? route.fulfill({
          json: { status: 'ok', data: { versions: [], total: 0, cached: false, cached_at: null } },
        })
      : route.fallback()
  );
  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');
    if (request.method() !== 'GET') return route.fallback();
    if (path === '') return route.fulfill({ json: INSTALLED_BODY });
    if (path === '/updates') return route.fulfill({ json: UPDATES_BODY });
    if (path === '/browse') return route.fulfill({ json: BROWSE_BODY });
    // The browse filters; without these a stack that cannot reach the mod database logs a 502
    if (path === '/gameversions') {
      return route.fulfill({ json: { status: 'ok', data: { versions: ['1.22.7'] } } });
    }
    if (path === '/tags') return route.fulfill({ json: { status: 'ok', data: { tags: [] } } });
    if (path === `/lookup/${SLUG}`) {
      return route.fulfill({ json: lookupBody(SLUG, 'E2E CSP Mod', DESCRIPTION, 3) });
    }
    if (path === `/lookup/${INSTALLED_SLUG}`) {
      return route.fulfill({ json: lookupBody(INSTALLED_SLUG, 'E2E CSP Installed', null, 0) });
    }
    return route.fallback();
  });
  for (const host of [CDN, IMAGES]) {
    await page.route(`${host}/**`, (route) =>
      route.fulfill({ contentType: 'image/png', body: PNG })
    );
  }
  return recorded;
}

async function violations(page: Page): Promise<Violation[]> {
  return page.evaluate(() => window.__cspViolations);
}

async function expectClean(page: Page, recorded: Recorded, where: string) {
  expect(await violations(page), `violations on ${where}`).toEqual([]);
  expect(recorded.consoleErrors, `console errors on ${where}`).toEqual([]);
  expect(recorded.pageErrors, `page errors on ${where}`).toEqual([]);
}

/**
 * Contrast ratio of the first "Image not shown" note against the description card's
 * background. Colors go through a canvas, so any CSS color syntax (oklch included) works.
 */
async function noteContrast(page: Page): Promise<number> {
  return page.evaluate(() => {
    const note = document.querySelector(
      '[data-testid="mod-detail-description"] [data-image-not-shown]'
    );
    const card = document.querySelector('[data-testid="mod-detail-description-card"]');
    if (!note || !card) throw new Error('note or card missing');
    const context = document.createElement('canvas').getContext('2d', { willReadFrequently: true });
    if (!context) throw new Error('no canvas');
    const rgb = (color: string) => {
      context.clearRect(0, 0, 1, 1);
      context.fillStyle = color;
      context.fillRect(0, 0, 1, 1);
      return Array.from(context.getImageData(0, 0, 1, 1).data.slice(0, 3));
    };
    const luminance = (color: string) => {
      const [r, g, b] = rgb(color).map((value) => {
        const channel = value / 255;
        return channel <= 0.03928 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4;
      });
      return 0.2126 * r + 0.7152 * g + 0.0722 * b;
    };
    const text = luminance(getComputedStyle(note).color);
    const background = luminance(getComputedStyle(card).backgroundColor);
    return (Math.max(text, background) + 0.05) / (Math.min(text, background) + 0.05);
  });
}

const PAGES: Array<{ path: string; ready: string }> = [
  { path: '/', ready: 'dashboard-stats-grid' },
  { path: '/game-server/console', ready: 'console-page' },
  { path: '/game-server/mods/browse', ready: `mod-card-${SLUG}` },
  { path: `/game-server/mods/browse/${SLUG}`, ready: 'mod-detail-page' },
  { path: '/game-server/mods/installed', ready: 'installed-tab-content' },
  { path: '/game-server/settings', ready: 'settings-page' },
  { path: '/game-server/version', ready: 'version-page' },
  { path: '/config', ready: 'ui-preferences-tab' },
];

function consoleSocket(socket: WebSocket): boolean {
  return new URL(socket.url()).pathname === '/api/v1alpha1/console/ws';
}

test.describe('Content-Security-Policy', () => {
  test('the web UI pages carry the policy and the API does not (AC 1, 2)', async ({ request }) => {
    for (const path of ['/', '/game-server/mods/browse']) {
      const response = await request.get(path);
      expect(response.status()).toBe(200);
      const headers = response.headers();
      expect(headers['content-security-policy']).toBe(POLICY);
      expect(headers['x-content-type-options']).toBe('nosniff');
      expect(headers['referrer-policy']).toBe('no-referrer');
      expect(headers['x-frame-options']).toBe('DENY');
    }

    for (const [path, headers] of [
      ['/healthz', {}],
      ['/readyz', {}],
      ['/api/v1alpha1/auth/me', { 'X-API-Key': API_KEY }],
    ] as const) {
      const response = await request.get(path, { headers });
      expect(response.status(), path).toBe(200);
      expect(response.headers()['content-security-policy'], path).toBeUndefined();
      expect(response.headers()['content-security-policy-report-only'], path).toBeUndefined();
    }
  });

  for (const colorScheme of COLOR_SCHEMES) {
    test(`every page works under the policy (${colorScheme} theme, AC 3, 6, 9)`, async ({
      page,
    }) => {
      test.setTimeout(120_000);
      await page.emulateMedia({ colorScheme });
      const recorded = await prepare(page);

      for (const { path, ready } of PAGES) {
        await page.goto(path);
        await expect(page.getByTestId(ready).first()).toBeVisible({ timeout: 30_000 });
        await page.waitForLoadState('load');
        expect(await page.evaluate(() => document.documentElement.classList.contains('dark'))).toBe(
          colorScheme === 'dark'
        );

        if (path.endsWith(SLUG)) {
          const description = page.getByTestId('mod-detail-description');
          await expect(description).toContainText(`${IMAGE_NOT_SHOWN}: plain`);
          await expect(description).toContainText(`${IMAGE_NOT_SHOWN}: relative`);
          // The note has its muted style and is readable on the description card
          const note = description.locator('[data-image-not-shown]').first();
          expect(await note.evaluate((element) => getComputedStyle(element).fontStyle)).toBe(
            'italic'
          );
          expect(await noteContrast(page)).toBeGreaterThanOrEqual(4.5);
          for (const alt of ['secure', 'inline']) {
            const image = description.locator(`img[alt="${alt}"]`);
            await expect
              .poll(() => image.evaluate((element: HTMLImageElement) => element.naturalWidth))
              .toBeGreaterThan(0);
          }
          const gallery = page.getByTestId('mod-screenshots').locator('img').first();
          await expect
            .poll(() => gallery.evaluate((element: HTMLImageElement) => element.naturalWidth))
            .toBeGreaterThan(0);
          expect(
            recorded.requests.filter((url) => url.startsWith('http://images.example.com/'))
          ).toEqual([]);
          expect(recorded.requests.filter((url) => new URL(url).pathname === '/c.png')).toEqual([]);
        }

        await expectClean(page, recorded, `${path} (${colorScheme})`);
      }
    });
  }

  test('the terminal, a toast and a dialog are styled (AC 3)', async ({ page }) => {
    const recorded = await prepare(page);

    await page.goto('/game-server/console');
    const terminal = page.locator('.xterm').first();
    await expect(terminal).toBeVisible({ timeout: 30_000 });
    expect(await terminal.evaluate((element) => getComputedStyle(element).position)).toBe(
      'relative'
    );

    await page.goto('/game-server/mods/installed');
    // The toggle sends a write, which the read-only route refuses, so an error toast shows
    await page.getByTestId(`mod-toggle-${INSTALLED_SLUG}`).first().click();
    const toast = page.locator('[data-sonner-toast]').first();
    await expect(toast).toBeVisible();
    expect(
      await toast.evaluate((element) => getComputedStyle(element).backgroundColor)
    ).not.toMatch(/^(transparent|rgba\(0, 0, 0, 0\))$/);

    await page.getByTestId(`mod-remove-${INSTALLED_SLUG}`).first().click();
    const dialog = page.getByTestId('remove-dialog');
    await expect(dialog).toBeVisible();
    expect(
      await dialog.evaluate((element) => getComputedStyle(element).backgroundColor)
    ).not.toMatch(/^(transparent|rgba\(0, 0, 0, 0\))$/);
    await page.getByTestId('remove-dialog-cancel').click();
    await expect(dialog).toBeHidden();

    expect(await violations(page)).toEqual([]);
    expect(recorded.pageErrors).toEqual([]);
    // The refused write logs its own 500, which is the test's doing
    expect(recorded.consoleErrors.filter((text) => !text.includes('500'))).toEqual([]);
  });

  test('the console socket and the log stream connect (AC 4)', async ({ page }) => {
    await prepare(page);

    const socketPromise = page.waitForEvent('websocket', consoleSocket);
    await page.goto('/game-server/console');
    const socket = await socketPromise;
    await page.waitForTimeout(2_000);
    expect(socket.isClosed()).toBe(false);

    await page.getByTestId('source-selector').click();
    // The first item is the live console; any other enabled item is a log file (a stack with
    // none shows a disabled "No log files available")
    const items = page.getByRole('menuitem', { disabled: false });
    if ((await items.count()) > 1) {
      const logPromise = page.waitForEvent(
        'websocket',
        (candidate) => new URL(candidate.url()).pathname === '/api/v1alpha1/console/logs/ws'
      );
      await items.nth(1).click();
      const logSocket = await logPromise;
      await page.waitForTimeout(2_000);
      expect(logSocket.isClosed()).toBe(false);
    } else {
      await page.keyboard.press('Escape');
      test.info().annotations.push({
        type: 'note',
        description: 'The stack lists no log file, so the log stream was not exercised',
      });
    }

    const connect = (await violations(page)).filter((v) => v.directive === 'connect-src');
    expect(connect).toEqual([]);
  });

  test('an injected script does not run and the page cannot be framed (AC 5)', async ({
    page,
    browser,
  }) => {
    await prepare(page);
    await page.goto('/');
    await expect(page.getByTestId('dashboard-stats-grid')).toBeVisible({ timeout: 30_000 });

    await page.evaluate(() => {
      const script = document.createElement('script');
      script.textContent = 'window.__injected = true;';
      document.body.appendChild(script);
    });
    await expect
      .poll(async () => (await violations(page)).map((v) => v.directive))
      .toEqual(['script-src-elem']);
    expect(await page.evaluate(() => window.__injected)).toBeUndefined();

    const context = await browser.newContext();
    try {
      const framing = await context.newPage();
      await framing.route('http://other.test/', (route) =>
        route.fulfill({
          contentType: 'text/html',
          body: `<!doctype html><title>other</title><iframe src="${BASE_URL}/"></iframe>`,
        })
      );
      await framing.goto('http://other.test/');
      await framing.waitForLoadState('load');
      const frame = framing.frames().find((candidate) => candidate !== framing.mainFrame());
      expect(frame).toBeDefined();
      expect(frame?.url().startsWith(BASE_URL)).toBe(false);
      expect(await framing.frameLocator('iframe').locator('#root').count()).toBe(0);
    } finally {
      await context.close();
    }
  });
});
