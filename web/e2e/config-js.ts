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
 * `route.fetch()`, tried once more when the first attempt fails. A full run against the dev
 * stack once had the connection reset (ECONNRESET), which the browser itself would retry.
 * Any error is retried once, including an abort when the page closes at the end of a test;
 * a second failure propagates, so a fetch that keeps failing still fails the test.
 */
async function fetchWithOneRetry(route: Route): Promise<APIResponse> {
  try {
    return await route.fetch();
  } catch {
    return route.fetch();
  }
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
    const response = await fetchWithOneRetry(route);
    const body: ServerStatusBody = await response.json();
    if (response.ok() && body.data?.state === 'not_installed') {
      body.data = { ...body.data, state: 'installed', version: FIXTURE_GAME_VERSION };
    }
    await route.fulfill({ response, json: body });
  });
}
