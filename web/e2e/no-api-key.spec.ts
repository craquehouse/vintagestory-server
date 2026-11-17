import { test, expect, type Page } from '@playwright/test';
import { serveConfigKey } from './config-js';

/**
 * E2E tests for the web UI without an API key.
 *
 * Story 19.2 (FR210, Epic 19 ADR-5):
 * - With no key from `/config.js`, every path shows the full-page "No API key configured"
 *   screen instead of the app: no sidebar, no request to `/api/` and no WebSocket. The mods
 *   path proves no lookup reaches the mod database.
 * - With a key, the screen is not shown and the app shell renders.
 * - The dev stack hands the page a key itself (`docker-compose.dev.yaml` sets `VS_API_KEY`
 *   to the Admin key); asserted as a boolean so a failure never prints the key.
 *
 * The page's key comes from `/config.js`, so each UI test answers it with `serveConfigKey`
 * (e2e/config-js.ts). The image has no `VITE_API_KEY`, so an empty key is the no-key state;
 * under the Vite dev server this spec is not valid.
 *
 * Reads only: changes nothing, never starts or stops the game server, takes no screenshots.
 * Needs only the stack (no mod database, no game server).
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) built from this branch:
 *   `just docker restart` then `cd web && bunx playwright test e2e/no-api-key.spec.ts`
 * - VS_API_KEY_ADMIN exported (default from docker-compose.dev.yaml).
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

/** Record the page's /api/ requests and WebSockets from now on. */
function recordTraffic(page: Page): { apiRequests: string[]; webSockets: string[] } {
  const apiRequests: string[] = [];
  const webSockets: string[] = [];
  page.on('request', (request) => {
    if (new URL(request.url()).pathname.startsWith('/api/')) {
      apiRequests.push(request.url());
    }
  });
  page.on('websocket', (ws) => webSockets.push(ws.url()));
  return { apiRequests, webSockets };
}

test.describe('No API key (Story 19.2)', () => {
  for (const path of ['/', '/game-server/mods/browse', '/config']) {
    test(`shows the set-up screen and calls nothing on ${path}`, async ({ page }) => {
      await serveConfigKey(page, '');
      const traffic = recordTraffic(page);

      await page.goto(path);

      const screen = page.getByTestId('no-api-key-screen');
      await expect(screen).toBeVisible();
      await expect(
        screen.getByRole('heading', { name: 'No API key configured' })
      ).toBeVisible();
      await expect(screen).toContainText('VS_API_KEY');
      await expect(page.getByRole('navigation')).toHaveCount(0);

      await page.waitForLoadState('networkidle');
      expect(traffic.apiRequests).toEqual([]);
      expect(traffic.webSockets).toEqual([]);
    });
  }

  test('renders the app with a key', async ({ page }) => {
    await serveConfigKey(page, API_KEY);

    await page.goto('/');

    await expect(page.getByRole('navigation').first()).toBeVisible();
    await expect(page.getByTestId('no-api-key-screen')).toHaveCount(0);
  });

  test('the dev stack hands the web UI a key', async ({ request }) => {
    const response = await request.get('/config.js');
    expect(response.status()).toBe(200);

    const match = /window\.__VSM_CONFIG__ = (.*);\s*$/s.exec(await response.text());
    const config: unknown = match ? JSON.parse(match[1]) : null;
    const servesAKey =
      typeof config === 'object' &&
      config !== null &&
      'apiKey' in config &&
      typeof config.apiKey === 'string' &&
      config.apiKey.length > 0;

    expect(servesAKey).toBe(true);
  });
});
