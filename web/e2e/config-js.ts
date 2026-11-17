import type { APIResponse, Page, Route } from '@playwright/test';

/** Answer /config.js with the given key, whatever key the stack hands the web UI. */
export async function serveConfigKey(page: Page, apiKey: string): Promise<void> {
  await page.route('**/config.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey })};`,
    })
  );
}

/** The game version the page sees on a stack with no game server (the specs' fake data names it). */
export const FIXTURE_GAME_VERSION = '1.22.7';

interface ServerStatusBody {
  status?: string;
  data?: { state?: string; version?: string | null; [field: string]: unknown };
}

/**
 * `route.fetch()` on a connection of its own. `route.fetch()` runs in the test process and
 * reuses a pooled keep-alive connection; the API's uvicorn closes one that has been idle for
 * 5 s (its default `--timeout-keep-alive`), and a reuse that lands just then fails with
 * "socket hang up (ECONNRESET)" (Story 20.5: a probe with 4.90-5.10 s pauses between two
 * status requests had 5 resets in 210 attempts, all at 4.99-5.00 s, on the throwaway
 * container). `connection: close` is passed on to the API, so no connection is reused and
 * the same probe had none in 84 attempts. That removes the cause, so the one retry this
 * helper had (Story 19.7) is gone and any failure fails the test. Every stub that passes a
 * request on to the API uses this helper.
 */
export async function fetchOnNewConnection(route: Route): Promise<APIResponse> {
  const headers = await route.request().allHeaders();
  return route.fetch({ headers: { ...headers, connection: 'close' } });
}

/**
 * Make a stack with no game server look installed (stopped) to the page, so Game Settings,
 * the Mods pages and the Console render their real content (Story 19.7). Only the page's
 * `GET /api/v1alpha1/server/status` is rewritten, and only when the stack answers
 * `not_installed`; a stack with a game server passes through unchanged. Direct API calls
 * from a test (`request.get`) see the real state.
 */
export async function pretendServerInstalled(page: Page): Promise<void> {
  await page.route('**/api/v1alpha1/server/status', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const response = await fetchOnNewConnection(route);
    const body: ServerStatusBody = await response.json();
    if (response.ok() && body.data?.state === 'not_installed') {
      body.data = { ...body.data, state: 'installed', version: FIXTURE_GAME_VERSION };
    }
    await route.fulfill({ response, json: body });
  });
}

/** A 1x1 transparent PNG, the answer to every mod image request in the replay run. */
const PLACEHOLDER_PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
  'base64'
);

/**
 * In the replay run (scripts/e2e-ci.sh sets E2E_MODDB_REPLAY=1), answer the mod database's
 * image host with a 1x1 PNG and abort any request to the mod database itself, so the run
 * sends nothing to the live hosts (Story 20.6, Epic 20 ADR-9). The routes are set on the
 * page's browser context, so a page the test opens later in that context is covered too.
 * Does nothing in any other run: against the dev stack the page loads the real images.
 */
export async function serveModImagePlaceholders(page: Page): Promise<void> {
  if (process.env.E2E_MODDB_REPLAY !== '1') return;
  const context = page.context();
  await context.route('https://moddbcdn.vintagestory.at/**', (route) =>
    route.fulfill({ contentType: 'image/png', body: PLACEHOLDER_PNG })
  );
  await context.route('https://mods.vintagestory.at/**', (route) => route.abort());
}
