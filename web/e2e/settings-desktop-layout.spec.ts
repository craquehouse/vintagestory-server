import { test, expect, type Page } from '@playwright/test';

/**
 * E2E tests for the game server settings layout.
 *
 * Story 16.6 (FR173, VSS-dfx, Epic 16 ADR-3): the settings panel is at most 1280px wide
 * and centered. From `xl` (1280px) Server Info spans the panel with its fields in two
 * columns, then two independent column stacks: Player Settings and Network on the left,
 * World Settings on the right. Collapsing a group moves only its own column. Number
 * inputs stay narrow at every width. Below `xl` everything is one column.
 *
 * Reads the settings of the running stack and changes none: collapsing a group is UI
 * state only.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080) with a game server
 *   installed: `just test-e2e-web`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/settings-desktop-layout.spec.ts`
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const SETTINGS = '/game-server/settings';

interface Box {
  x: number;
  y: number;
  width: number;
  height: number;
}

async function open(page: Page, width: number, height = 900) {
  await page.setViewportSize({ width, height });
  await page.addInitScript((apiKey) => {
    localStorage.setItem('apiKey', apiKey);
  }, API_KEY);
  await page.goto(SETTINGS);
  await expect(page.getByTestId('game-config-panel')).toBeVisible({ timeout: 30000 });
  await expect(page.locator('#Port')).toBeVisible();
}

const card = (page: Page, title: string) =>
  page.locator('[data-slot="card"]', {
    has: page.locator('[data-slot="card-title"]', { hasText: title }),
  });

async function box(page: Page, title: string): Promise<Box> {
  const b = await card(page, title).boundingBox();
  if (!b) throw new Error(`No box for ${title}`);
  return b;
}

/** Same position and size, each within half a pixel (sub-pixel layout can differ slightly). */
function expectSameBox(actual: Box, expected: Box) {
  for (const key of ['x', 'y', 'width', 'height'] as const) {
    expect(Math.abs(actual[key] - expected[key]), key).toBeLessThanOrEqual(0.5);
  }
}

async function inputWidth(page: Page, id: string): Promise<number> {
  const b = await page.locator(`#${id}`).boundingBox();
  if (!b) throw new Error(`No box for #${id}`);
  return b.width;
}

async function toggle(page: Page, title: string) {
  await page.locator('[data-slot="card-header"][role="button"]', { hasText: title }).click();
}

async function documentOverflowX(page: Page): Promise<number> {
  return page.evaluate(
    () => document.documentElement.scrollWidth - document.documentElement.clientWidth
  );
}

test.describe('Story 16.6: settings layout on desktop', () => {
  for (const width of [1440, 1920]) {
    test(`two columns under a full-width Server Info at ${width}px`, async ({ page }) => {
      await open(page, width);

      const layout = await page.getByTestId('game-config-layout').boundingBox();
      const panel = await page.getByTestId('game-config-panel').boundingBox();
      expect(layout && panel).toBeTruthy();
      expect(layout!.width).toBeLessThanOrEqual(1280);
      // Centered in the panel
      const left = layout!.x - panel!.x;
      const right = panel!.x + panel!.width - (layout!.x + layout!.width);
      expect(Math.abs(left - right)).toBeLessThanOrEqual(1);

      const info = await box(page, 'Server Info');
      const player = await box(page, 'Player Settings');
      const network = await box(page, 'Network');
      const world = await box(page, 'World Settings');

      // Server Info spans both columns
      expect(info.width).toBeCloseTo(layout!.width, 0);
      expect(player.y).toBeGreaterThan(info.y + info.height);

      // Left stack: Player Settings above Network, same left edge and width
      expect(network.x).toBeCloseTo(player.x, 0);
      expect(network.width).toBeCloseTo(player.width, 0);
      expect(network.y).toBeGreaterThan(player.y + player.height);

      // Right stack: World Settings to the right, starting at Player Settings' top
      expect(world.x).toBeGreaterThan(player.x + player.width);
      expect(world.y).toBeCloseTo(player.y, 0);
      expect(world.width).toBeCloseTo(player.width, 0);

      // Server Info fields in two columns
      const name = await page.locator('#ServerName').boundingBox();
      const description = await page.locator('#ServerDescription').boundingBox();
      const welcome = await page.locator('#WelcomeMessage').boundingBox();
      const password = await page.locator('#Password').boundingBox();
      expect(description!.x).toBeGreaterThan(name!.x + name!.width);
      expect(description!.y).toBeCloseTo(name!.y, 0);
      expect(welcome!.x).toBeCloseTo(name!.x, 0);
      expect(welcome!.y).toBeGreaterThan(name!.y);
      expect(password!.x).toBeCloseTo(description!.x, 0);

      // Number inputs stay narrow; text inputs fill their column
      for (const id of ['MaxClients', 'MaxChunkRadius', 'Port']) {
        expect(await inputWidth(page, id)).toBeLessThanOrEqual(320);
      }
      expect(await inputWidth(page, 'Ip')).toBeGreaterThan(320);

      expect(await documentOverflowX(page)).toBe(0);
    });
  }

  test('collapsing a group moves only its own column at 1440px', async ({ page }) => {
    await open(page, 1440);

    const player = await box(page, 'Player Settings');
    const network = await box(page, 'Network');
    const world = await box(page, 'World Settings');

    await toggle(page, 'World Settings');
    await expect(page.locator('#MaxChunkRadius')).toHaveCount(0);
    expectSameBox(await box(page, 'Player Settings'), player);
    expectSameBox(await box(page, 'Network'), network);
    expect((await box(page, 'World Settings')).height).toBeLessThan(world.height);

    await toggle(page, 'World Settings');
    await expect(page.locator('#MaxChunkRadius')).toBeVisible();
    expectSameBox(await box(page, 'World Settings'), world);

    await toggle(page, 'Network');
    await expect(page.locator('#Port')).toHaveCount(0);
    expectSameBox(await box(page, 'World Settings'), world);
    expectSameBox(await box(page, 'Player Settings'), player);
    expect((await box(page, 'Network')).height).toBeLessThan(network.height);
  });

  for (const { width, height } of [
    { width: 1024, height: 900 },
    { width: 390, height: 844 },
  ]) {
    test(`one column at ${width}px`, async ({ page }) => {
      await open(page, width, height);

      const titles = ['Server Info', 'Player Settings', 'Network', 'World Settings'];
      const boxes = await Promise.all(titles.map((t) => box(page, t)));
      for (const b of boxes) {
        expect(b.x).toBeCloseTo(boxes[0].x, 0);
        expect(b.width).toBeCloseTo(boxes[0].width, 0);
      }
      // Stacked top to bottom in this order
      for (let i = 1; i < boxes.length; i++) {
        expect(boxes[i].y).toBeGreaterThan(boxes[i - 1].y + boxes[i - 1].height);
      }

      // Server Info fields in one column
      const name = await page.locator('#ServerName').boundingBox();
      const description = await page.locator('#ServerDescription').boundingBox();
      expect(description!.x).toBeCloseTo(name!.x, 0);
      expect(description!.y).toBeGreaterThan(name!.y);

      expect(await inputWidth(page, 'Port')).toBeLessThanOrEqual(320);
      expect(await documentOverflowX(page)).toBe(0);
    });
  }
});
