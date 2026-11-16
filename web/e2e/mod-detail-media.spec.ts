import { test, expect, type Locator, type Page } from '@playwright/test';

/**
 * E2E tests for a mod's screenshots, trailer link and description links on its detail page.
 *
 * Story 18.1 (FR194-FR198; VSS-l4x, VSS-tzl; Epic 18 ADR-1 and ADR-2):
 * - The Screenshots section sits between the header and the description: one image, its
 *   position, Previous and Next (wrapping), thumbnails, arrow keys in the section and in the
 *   dialog (one step per key press), Escape returns focus to the current image.
 * - Only the shown images' full-size files are requested, never with a `Referer` header;
 *   nothing is requested from YouTube and the page has no iframe.
 * - "Watch trailer" opens the API's watch URL in a new tab; description links show an icon
 *   and tell a screen reader they open in a new tab.
 * - At 390px on a touch screen, in the light and the dark theme, the section stays inside the
 *   viewport, does not widen the page, and its controls are at least 44x44px.
 * - The live `betterruins` lookup passes only CDN image URLs and a YouTube watch URL.
 *
 * Reads only. The lookup of `e2emediamod` and the CDN images are stubbed with `page.route`;
 * every write to the API is refused, so nothing is installed, changed or removed; the game
 * server is neither started nor stopped; no screenshot is taken.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080), rebuilt from this branch:
 *   `just docker restart`, then `cd web && bunx playwright test e2e/mod-detail-media.spec.ts`
 *   with VS_API_KEY_ADMIN exported.
 * - Network access to the public mod database for the live test.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const SLUG = 'e2emediamod';
const DETAIL = `/game-server/mods/browse/${SLUG}`;
const CDN = 'https://moddbcdn.vintagestory.at';
const WATCH_URL = 'https://www.youtube.com/watch?v=mJHZH_sThDM';

// A 1x1 PNG
const PNG = Buffer.from(
  'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=',
  'base64'
);

type Variant = 'ten' | 'none' | 'one';

function screenshots(count: number) {
  return Array.from({ length: count }, (_, i) => ({
    image_url: `${CDN}/e2e-${i + 1}.png`,
    thumbnail_url: `${CDN}/e2e-${i + 1}_55_60.png`,
    filename: `e2e-${i + 1}.png`,
  }));
}

function lookupBody(variant: Variant) {
  return {
    status: 'ok',
    data: {
      slug: SLUG,
      urlalias: null,
      asset_id: 0,
      name: 'E2E Media Mod',
      author: 'Someone',
      description: '<p>See the <a href="https://example.com/docs">Docs</a>.</p>',
      latest_version: '1.0.0',
      install_mod_id: SLUG,
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
          filename: `${SLUG}_1.0.0.zip`,
          file_id: 1,
          modidstr: SLUG,
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
      screenshots: screenshots(variant === 'ten' ? 10 : variant === 'one' ? 1 : 0),
      trailer_url: variant === 'ten' ? WATCH_URL : null,
    },
  };
}

/** Answer /config.js with the Admin key (Story 17.5) and refuse every write to the API. */
async function readOnly(page: Page) {
  await page.route('**/config.js', (route) =>
    route.fulfill({
      contentType: 'application/javascript',
      body: `window.__VSM_CONFIG__ = ${JSON.stringify({ apiKey: API_KEY })};`,
    })
  );
  await page.route('**/api/**', async (route) => {
    if (route.request().method() !== 'GET') {
      // Never let a write reach the server's data
      await route.fulfill({ status: 500, json: { detail: { code: 'E2E_BLOCKED', message: 'read only' } } });
      return;
    }
    await route.fallback();
  });
}

interface Recorded {
  cdn: { url: string; referer: string | undefined }[];
  youtube: string[];
}

/**
 * Stub the lookup (the variant can change between page loads) and the CDN, and record
 * CDN and YouTube requests. Registered after readOnly, so these routes run first.
 */
async function stubMedia(page: Page, initial: Variant) {
  const state = { variant: initial };
  const recorded: Recorded = { cdn: [], youtube: [] };
  await readOnly(page);
  await page.route(new RegExp(`/api/v1alpha1/mods/lookup/${SLUG}(\\?.*)?$`), (route) =>
    route.fulfill({ json: lookupBody(state.variant) })
  );
  await page.route(`${CDN}/**`, (route) => {
    const request = route.request();
    recorded.cdn.push({ url: request.url(), referer: request.headers()['referer'] });
    return route.fulfill({
      contentType: 'image/png',
      headers: { 'cache-control': 'max-age=3600' },
      body: PNG,
    });
  });
  page.on('request', (request) => {
    const host = new URL(request.url()).hostname;
    if (/youtube|ytimg|google/.test(host)) recorded.youtube.push(request.url());
  });
  return { state, recorded };
}

async function openDetail(page: Page) {
  await page.goto(DETAIL);
  await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 30_000 });
}

async function sizeOf(locator: Locator, name: string) {
  const box = await locator.boundingBox();
  if (!box) throw new Error(`No box for ${name}`);
  return box;
}

async function expectTarget44(locator: Locator, name: string) {
  const box = await sizeOf(locator, name);
  expect(box.width, `${name} width`).toBeGreaterThanOrEqual(44);
  expect(box.height, `${name} height`).toBeGreaterThanOrEqual(44);
}

async function expectInside(locator: Locator, name: string, width: number) {
  const box = await sizeOf(locator, name);
  expect(box.x, `${name} left`).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width, `${name} right`).toBeLessThanOrEqual(width);
}

async function documentScrollWidth(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth);
}

test.describe('Mod detail media and links (Story 18.1)', () => {
  test.describe('desktop', () => {
    test.use({ viewport: { width: 1440, height: 900 } });

    test('the gallery steps by button, thumbnail and key, in the section and the dialog', async ({
      page,
    }) => {
      const { recorded } = await stubMedia(page, 'ten');
      await openDetail(page);

      const section = page.getByTestId('mod-screenshots');
      await expect(section).toBeVisible();
      const order = await page.evaluate(() => {
        const header = document.querySelector('[data-testid="mod-detail-header"]');
        const gallery = document.querySelector('[data-testid="mod-screenshots"]');
        const description = document.querySelector('[data-testid="mod-detail-description-card"]');
        if (!header || !gallery || !description) return false;
        return (
          (header.compareDocumentPosition(gallery) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0 &&
          (gallery.compareDocumentPosition(description) & Node.DOCUMENT_POSITION_FOLLOWING) !== 0
        );
      });
      expect(order).toBe(true);

      const position = page.getByTestId('mod-screenshot-position');
      await expect(position).toHaveText('1 of 10');
      await page.getByTestId('mod-screenshot-next').click();
      await expect(position).toHaveText('2 of 10');
      await page.getByTestId('mod-screenshot-thumb-4').click();
      await expect(position).toHaveText('5 of 10');
      await page.getByTestId('mod-screenshot-thumb-4').focus();
      await page.keyboard.press('ArrowLeft');
      await expect(position).toHaveText('4 of 10');

      const current = page.getByTestId('mod-screenshot-current');
      await current.focus();
      await page.keyboard.press('Enter');
      const dialog = page.getByTestId('mod-screenshot-dialog');
      await expect(dialog).toBeVisible();
      const dialogPosition = page.getByTestId('mod-screenshot-dialog-position');
      await expect(dialogPosition).toHaveText('4 of 10');
      await expect(page.getByTestId('mod-screenshot-dialog-image')).toHaveAttribute(
        'src',
        `${CDN}/e2e-4.png`
      );
      await page.keyboard.press('ArrowRight');
      await expect(dialogPosition).toHaveText('5 of 10');
      await page.keyboard.press('Escape');
      await expect(dialog).toBeHidden();
      await expect(current).toBeFocused();
      await expect(position).toHaveText('5 of 10');
      await expect(page.getByTestId('mod-screenshot-image')).toHaveAttribute(
        'src',
        `${CDN}/e2e-5.png`
      );

      // Every control is reached with Tab from the current image
      await page.keyboard.press('Tab');
      await expect(page.getByTestId('mod-screenshot-prev')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByTestId('mod-screenshot-next')).toBeFocused();
      await page.keyboard.press('Tab');
      await expect(page.getByTestId('mod-screenshot-thumb-0')).toBeFocused();

      // Only the full-size files of the images shown were requested, without a Referer
      const fullSize = () =>
        [...new Set(recorded.cdn.map((r) => r.url).filter((url) => !url.includes('_55_60')))].sort();
      await expect
        .poll(fullSize)
        .toEqual([1, 2, 4, 5].map((n) => `${CDN}/e2e-${n}.png`).sort());
      expect(recorded.cdn.length).toBeGreaterThan(0);
      expect(recorded.cdn.filter((r) => r.referer !== undefined)).toEqual([]);
      expect(recorded.youtube).toEqual([]);
      await expect(page.locator('iframe')).toHaveCount(0);
    });

    test('the trailer link and description links say they open in a new tab', async ({ page }) => {
      const { recorded } = await stubMedia(page, 'ten');
      await openDetail(page);

      const trailer = page.getByTestId('mod-detail-trailer-link');
      await expect(trailer).toHaveAttribute('href', WATCH_URL);
      await expect(trailer).toHaveAttribute('target', '_blank');
      await expect(trailer).toHaveAttribute('rel', 'noopener noreferrer');
      await expect(page.getByRole('link', { name: 'Watch trailer (opens in a new tab)', exact: true })).toHaveCount(1);

      const description = page.getByTestId('mod-detail-description');
      const docs = description.getByRole('link', { name: 'Docs (opens in a new tab)', exact: true });
      await expect(docs).toHaveCount(1);
      const icon = await docs.evaluate((element) => {
        const style = getComputedStyle(element, '::after');
        return {
          mask: style.getPropertyValue('mask-image') || style.getPropertyValue('-webkit-mask-image'),
          width: parseFloat(style.width),
        };
      });
      expect(icon.mask).toContain('data:image/svg+xml');
      expect(icon.width).toBeGreaterThan(0);

      expect(recorded.youtube).toEqual([]);
      await expect(page.locator('iframe')).toHaveCount(0);
    });

    test('no screenshots show no section; one shows the image without navigation', async ({
      page,
    }) => {
      const { state } = await stubMedia(page, 'none');
      await openDetail(page);
      await expect(page.getByTestId('mod-detail-description-card')).toBeVisible();
      await expect(page.getByTestId('mod-screenshots')).toHaveCount(0);
      await expect(page.getByTestId('mod-detail-trailer-link')).toHaveCount(0);

      state.variant = 'one';
      await openDetail(page);
      await expect(page.getByTestId('mod-screenshot-image')).toBeVisible();
      for (const id of [
        'mod-screenshot-prev',
        'mod-screenshot-next',
        'mod-screenshot-position',
        'mod-screenshot-thumbnails',
      ]) {
        await expect(page.getByTestId(id)).toHaveCount(0);
      }
      await page.getByTestId('mod-screenshot-current').click();
      await expect(page.getByTestId('mod-screenshot-dialog')).toBeVisible();
      await page.keyboard.press('Escape');
      await expect(page.getByTestId('mod-screenshot-dialog')).toBeHidden();
    });
  });

  test.describe('phone', () => {
    test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

    test('the section fits at 390px in the light and the dark theme', async ({ page }) => {
      test.setTimeout(90_000);
      const width = 390;
      const { state } = await stubMedia(page, 'none');
      const colors: string[] = [];

      for (const colorScheme of ['light', 'dark'] as const) {
        await page.emulateMedia({ colorScheme });

        state.variant = 'none';
        await openDetail(page);
        await expect(page.getByTestId('mod-detail-description-card')).toBeVisible();
        if (colorScheme === 'dark') {
          await expect(page.locator('html')).toHaveClass(/\bdark\b/);
        } else {
          await expect(page.locator('html')).not.toHaveClass(/\bdark\b/);
        }
        const withoutScreenshots = await documentScrollWidth(page);

        state.variant = 'ten';
        await openDetail(page);
        const section = page.getByTestId('mod-screenshots');
        await expect(section).toBeVisible();
        const withScreenshots = await documentScrollWidth(page);
        test.info().annotations.push({
          type: 'page width',
          description: `${colorScheme}: ${withoutScreenshots}px without screenshots, ${withScreenshots}px with (viewport ${width}px)`,
        });
        expect(withScreenshots, `${colorScheme}: page width`).toBeLessThanOrEqual(withoutScreenshots);

        await expectInside(section, `${colorScheme}: mod-screenshots`, width);
        await expectTarget44(page.getByTestId('mod-screenshot-prev'), `${colorScheme}: prev`);
        await expectTarget44(page.getByTestId('mod-screenshot-next'), `${colorScheme}: next`);
        await expectTarget44(page.getByTestId('mod-screenshot-thumb-0'), `${colorScheme}: thumb`);

        const strip = page.getByTestId('mod-screenshot-thumbnails');
        const scroll = await strip.evaluate((element) => ({
          scrollWidth: element.scrollWidth,
          clientWidth: element.clientWidth,
          overflowX: getComputedStyle(element).overflowX,
        }));
        expect(scroll.scrollWidth, `${colorScheme}: strip scrolls`).toBeGreaterThan(scroll.clientWidth);
        expect(scroll.overflowX).toBe('auto');

        const position = page.getByTestId('mod-screenshot-position');
        await expect(position).toHaveText('1 of 10');
        colors.push(await position.evaluate((element) => getComputedStyle(element).color));
        await page.getByTestId('mod-screenshot-next').tap();
        await expect(position).toHaveText('2 of 10');

        await page.getByTestId('mod-screenshot-current').tap();
        const dialog = page.getByTestId('mod-screenshot-dialog');
        await expect(dialog).toBeVisible();
        // Measure after the open animation (zoom-in-95 scales the dialog)
        await dialog.evaluate((element) =>
          Promise.all(element.getAnimations().map((animation) => animation.finished))
        );
        await expectTarget44(page.getByTestId('mod-screenshot-dialog-prev'), `${colorScheme}: dialog prev`);
        await expectTarget44(page.getByTestId('mod-screenshot-dialog-next'), `${colorScheme}: dialog next`);
        await expectInside(dialog, `${colorScheme}: dialog`, width);
        await page.keyboard.press('Escape');
        await expect(dialog).toBeHidden();
      }

      // The section follows the theme
      expect(colors).toHaveLength(2);
      expect(colors[1]).not.toBe(colors[0]);
    });
  });

  test('the live betterruins lookup passes only CDN images and a YouTube watch URL', async ({
    page,
  }) => {
    test.setTimeout(90_000);
    await readOnly(page);
    const lookup = page.waitForResponse((response) =>
      response.url().includes('/mods/lookup/betterruins')
    );
    await page.goto('/game-server/mods/browse/betterruins');

    const response = await lookup;
    expect(response.status()).toBe(200);
    const body = (await response.json()) as {
      data: {
        screenshots: { image_url: string; thumbnail_url: string; filename: string }[];
        trailer_url: string | null;
      };
    };
    for (const shot of body.data.screenshots) {
      expect(shot.image_url.startsWith(`${CDN}/`)).toBe(true);
      expect(shot.thumbnail_url.startsWith(`${CDN}/`)).toBe(true);
    }
    if (body.data.trailer_url !== null) {
      expect(body.data.trailer_url).toMatch(/^https:\/\/www\.youtube\.com\/watch\?v=[A-Za-z0-9_-]{11}$/);
    }

    await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 60_000 });
    if (body.data.screenshots.length > 0) {
      await expect(page.getByTestId('mod-screenshots')).toBeVisible();
    } else {
      await expect(page.getByTestId('mod-screenshots')).toHaveCount(0);
    }
  });
});
