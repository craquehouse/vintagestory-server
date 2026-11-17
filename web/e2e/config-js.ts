import type { Page } from '@playwright/test';

/** Answer /config.js with the given key, whatever key the stack hands the web UI. */
export async function serveConfigKey(page: Page, apiKey: string): Promise<void> {
  await page.route('**/config.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey })};`,
    })
  );
}
