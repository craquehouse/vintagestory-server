// Story 16.6: measure the game server settings layout (adapted from 16-0-spike/settings_shots.mjs).
//
//   cd web && bun ../_bmad-output/implementation-artifacts/16-6-browser/settings_layout.mjs \
//     > ../_bmad-output/implementation-artifacts/16-6-browser/settings_layout.<before|after>.json
//
// For each width: panel box, page height, document overflow, every card's box, the widths of
// the number and text inputs, and at 1280px and wider the card boxes after collapsing World
// Settings and after collapsing Network (each is expanded again afterwards). Collapsing is UI
// state only; no setting is changed. With SHOTS_DIR set, writes settings-<width>.png there with
// the server name and password masked.

import { chromium } from '../../../web/node_modules/@playwright/test/index.mjs';
import { join } from 'node:path';

const BASE = process.env.E2E_BASE_URL || 'http://localhost:8080';
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const SHOTS_DIR = process.env.SHOTS_DIR;
const WIDTHS = [390, 1024, 1280, 1440, 1920];
const INPUTS = ['ServerName', 'ServerDescription', 'WelcomeMessage', 'Password', 'MaxClients', 'MaxChunkRadius', 'Port', 'Ip'];

const browser = await chromium.launch();
const report = [];

async function cards(page) {
  return page.evaluate(() => {
    const panel = document.querySelector('[data-testid="game-config-panel"]');
    return [...panel.querySelectorAll('[data-slot="card"]')].map((card) => {
      const r = card.getBoundingClientRect();
      return {
        title: card.querySelector('[data-slot="card-title"]')?.textContent?.trim(),
        x: Math.round(r.left + window.scrollX),
        y: Math.round(r.top + window.scrollY),
        width: Math.round(r.width),
        height: Math.round(r.height),
      };
    });
  });
}

async function toggle(page, title) {
  await page.locator('[data-slot="card-header"][role="button"]', { hasText: title }).click();
  await page.waitForTimeout(200);
}

for (const width of WIDTHS) {
  const page = await browser.newPage({ viewport: { width, height: 900 } });
  await page.addInitScript((key) => localStorage.setItem('apiKey', key), API_KEY);
  await page.goto(`${BASE}/game-server/settings`);
  await page.waitForSelector('[data-testid="game-config-panel"]', { timeout: 60000 });
  await page.waitForTimeout(500);
  if (SHOTS_DIR) {
    await page.screenshot({
      path: join(SHOTS_DIR, `settings-${width}.png`),
      fullPage: true,
      mask: [page.locator('header span.font-semibold'), page.locator('#ServerName'), page.locator('#Password')],
    });
  }
  const entry = {
    width,
    ...(await page.evaluate((ids) => {
      const panel = document.querySelector('[data-testid="game-config-panel"]');
      const box = (el) => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return { x: Math.round(r.left), width: Math.round(r.width) };
      };
      const firstCard = panel.querySelector('[data-slot="card"]');
      return {
        panel: box(panel),
        content: box(firstCard?.parentElement ?? null),
        pageHeight: document.documentElement.scrollHeight,
        documentOverflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        inputs: Object.fromEntries(ids.map((id) => [id, box(document.getElementById(id))?.width ?? null])),
      };
    }, INPUTS)),
    cards: await cards(page),
  };
  if (width >= 1280) {
    await toggle(page, 'World Settings');
    entry.worldCollapsed = await cards(page);
    await toggle(page, 'World Settings');
    await toggle(page, 'Network');
    entry.networkCollapsed = await cards(page);
    await toggle(page, 'Network');
  }
  report.push(entry);
  await page.close();
}

await browser.close();
console.log(JSON.stringify(report, null, 2));
