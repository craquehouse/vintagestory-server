// Story 16.0 Task 4: screenshot game server settings at desktop widths and measure the cards.
//
//   cd web && bun ../_bmad-output/implementation-artifacts/16-0-spike/settings_shots.mjs \
//     > ../_bmad-output/implementation-artifacts/16-0-spike/settings_shots.out.json
//
// Writes settings-<width>.png next to this script, with the server name and password masked.

import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const here = dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const report = [];

for (const width of [1024, 1440, 1920]) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.goto(`${BASE}/game-server/settings`);
  await page.waitForSelector('[data-testid="game-config-panel"]', { timeout: 60000 });
  await page.waitForTimeout(500);
  // Mask instance-specific values (server name in the header and field, password) so the
  // screenshots can be committed to a public repository.
  await page.screenshot({
    path: join(here, `settings-${width}.png`),
    fullPage: true,
    mask: [page.locator('header span.font-semibold'), page.locator('#ServerName'), page.locator('#Password')],
  });
  report.push({
    width,
    ...(await page.evaluate(() => {
      const panel = document.querySelector('[data-testid="game-config-panel"]');
      const groups = [...panel.querySelectorAll(':scope > div > *')];
      return {
        panelWidth: Math.round(panel.getBoundingClientRect().width),
        pageHeight: document.documentElement.scrollHeight,
        groups: groups.map((g) => ({
          title: g.querySelector('h3, [class*="CardTitle"], [data-slot="card-title"]')?.textContent?.trim()
            ?? g.textContent.trim().slice(0, 30),
          width: Math.round(g.getBoundingClientRect().width),
          height: Math.round(g.getBoundingClientRect().height),
          inputs: g.querySelectorAll('input, textarea, button[role="switch"]').length,
        })),
      };
    })),
  });
  await page.close();
}

await browser.close();
console.log(JSON.stringify(report, null, 2));
