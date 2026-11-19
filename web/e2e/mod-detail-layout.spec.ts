import { test, expect, type Locator, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for the mod detail page on phones, its new-tab links and its description styles.
 *
 * Story 21.6 (FR278-FR280; VSS-woae, VSS-pzj8, VSS-4vbj; Epic 21 ADR-10 and ADR-11):
 * - The ModDB Page, Homepage, Source and Watch trailer links, the description's HTML and SVG
 *   links (an `href` one and an `xlink:href`-only one) and the sidebar's GitHub link are named
 *   "... (opens in a new tab)" in Chromium's accessibility tree; Homepage and Source show a
 *   trailing external-link mark.
 * - At 320, 390 and 430px, in the light and the dark theme, the page does not scroll sideways,
 *   the install card sits below the logo and info at the header's width, the breadcrumb and
 *   the header controls stay inside the viewport, and the version select and the install
 *   button are at least 44px tall. The select is named by its "Version" label.
 * - At 768px the logo, the info and the install card are one row and the page fits.
 * - Description headings, lists, links, quotes, code and tables are styled from the theme
 *   tokens; wide tables and code scroll inside the card, a wide image is no wider than the
 *   card, and an author's inline colour still applies.
 *
 * Reads only. The lookup of `e2elayoutmod` is stubbed with `page.route` (no mod database);
 * every write to the API is refused, so nothing is installed, changed or removed; the game
 * server is neither started nor stopped; no request leaves the manager (the description's
 * image is a `data:` URL and no link is clicked); no screenshot is taken.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080), rebuilt from this branch:
 *   `just docker restart`, then `cd web && bunx playwright test e2e/mod-detail-layout.spec.ts`
 *   with VS_API_KEY_ADMIN exported.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const SLUG = 'e2elayoutmod';
const DETAIL = `/game-server/mods/browse/${SLUG}`;
const NOTE = '(opens in a new tab)';

// A 1x1 PNG, shown 1200px wide by the description
const PNG_DATA_URL =
  'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNkYAAAAAYAAjCB0C8AAAAASUVORK5CYII=';

const LONG_URL = `https://example.com/${'very-long-path-segment-'.repeat(8)}end`;
const LONG_CODE_LINE = `const value = ${'"abcdefghij" + '.repeat(18)}"end";`;
const WIDE_TABLE = `<table><thead><tr>${Array.from(
  { length: 12 },
  (_, i) => `<th>Column heading ${i + 1}</th>`
).join('')}</tr></thead><tbody><tr>${Array.from(
  { length: 12 },
  (_, i) => `<td>A fairly long table cell value number ${i + 1}</td>`
).join('')}</tr></tbody></table>`;

const DESCRIPTION = [
  '<h1>Heading one</h1>',
  '<p>An opening paragraph with <code>inline code</code> and a <a href="https://example.com/docs">Docs</a> link.</p>',
  '<h2>Heading two</h2>',
  '<ul><li>First item<ul><li>Nested item</li></ul></li><li>Second item</li></ul>',
  '<h3>Heading three</h3>',
  '<ol><li>Step one</li><li>Step two</li></ol>',
  '<h4>Heading four</h4>',
  '<blockquote>A quoted remark from the author.</blockquote>',
  '<h5>Heading five</h5>',
  `<pre><code>${LONG_CODE_LINE}</code></pre>`,
  '<h6>Heading six</h6>',
  '<hr>',
  WIDE_TABLE,
  `<p><img width="1200" height="40" alt="Wide banner" src="${PNG_DATA_URL}"></p>`,
  `<p>${LONG_URL}</p>`,
  '<p style="color: rgb(204, 51, 51)" data-e2e="author-styled">Author coloured text.</p>',
  '<svg width="240" height="24"><a href="https://example.com/diagram"><text x="0" y="16">Diagram</text></a></svg>',
  '<svg width="240" height="24"><a xlink:href="https://example.com/diagram-xlink"><text x="0" y="16">Diagram</text></a></svg>',
].join('\n');

function lookupBody() {
  return {
    status: 'ok',
    data: {
      slug: SLUG,
      urlalias: null,
      asset_id: 0,
      name: 'An Extremely Long Mod Name That Keeps Going Past The Edge',
      author: 'Someone',
      description: DESCRIPTION,
      latest_version: '1.0.0',
      install_mod_id: SLUG,
      downloads: 123456,
      follows: 7890,
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
      tags: ['Library', 'Utility', 'Worldgen', 'Crafting'],
      homepage_url: 'https://example.com/home',
      source_url: 'https://example.com/source',
      created: null,
      last_released: null,
      screenshots: [],
      trailer_url: 'https://www.youtube-nocookie.com/embed/mJHZH_sThDM',
    },
  };
}

/** The hosts of the manager under test: the E2E base URL's and the loopback names. */
function managerHosts(): Set<string> {
  const hosts = new Set(['127.0.0.1', 'localhost']);
  hosts.add(new URL(process.env.E2E_BASE_URL || 'http://localhost:9080').hostname);
  return hosts;
}

/**
 * Admin key from /config.js, server shown as installed (19.7), every write refused, the
 * lookup stubbed. Returns the requests that left the manager (expected: none).
 */
async function stubDetail(page: Page): Promise<string[]> {
  const outside: string[] = [];
  const local = managerHosts();
  page.on('request', (request) => {
    const url = new URL(request.url());
    if (['http:', 'https:'].includes(url.protocol) && !local.has(url.hostname)) {
      outside.push(request.url());
    }
  });
  await serveConfigKey(page, API_KEY);
  await pretendServerInstalled(page);
  await page.route('**/api/**', async (route) => {
    if (route.request().method() !== 'GET') {
      // Never let a write reach the server's data
      await route.fulfill({
        status: 500,
        json: { detail: { code: 'E2E_BLOCKED', message: 'read only' } },
      });
      return;
    }
    await route.fallback();
  });
  // Registered after the read-only route, so it runs first
  await page.route(new RegExp(`/api/v1alpha1/mods/lookup/${SLUG}(\\?.*)?$`), (route) =>
    route.fulfill({ json: lookupBody() })
  );
  return outside;
}

async function openDetail(page: Page) {
  await page.goto(DETAIL);
  await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('mod-detail-description')).toBeVisible();
}

async function useTheme(page: Page, colorScheme: 'light' | 'dark') {
  await page.emulateMedia({ colorScheme });
  if (colorScheme === 'dark') {
    await expect(page.locator('html')).toHaveClass(/\bdark\b/);
  } else {
    await expect(page.locator('html')).not.toHaveClass(/\bdark\b/);
  }
}

async function boxOf(locator: Locator, name: string) {
  const box = await locator.boundingBox();
  if (!box) throw new Error(`No box for ${name}`);
  return box;
}

async function expectInside(locator: Locator, name: string, width: number) {
  const box = await boxOf(locator, name);
  expect(box.x, `${name} left`).toBeGreaterThanOrEqual(0);
  expect(box.x + box.width, `${name} right`).toBeLessThanOrEqual(width);
}

async function documentScrollWidth(page: Page): Promise<number> {
  return page.evaluate(() => document.documentElement.scrollWidth);
}

test.describe('Mod detail page layout, links and description (Story 21.6)', () => {
  test.describe('desktop', () => {
    test.use({ viewport: { width: 1440, height: 900 } });

    test('every new-tab link says so, SVG description links included', async ({ page }) => {
      const outside = await stubDetail(page);
      await openDetail(page);

      for (const name of ['ModDB Page', 'Homepage', 'Source', 'Watch trailer']) {
        const link = page.getByRole('link', { name: `${name} ${NOTE}`, exact: true });
        await expect(link, name).toHaveCount(1);
        await expect(link, name).toHaveAttribute('target', '_blank');
        await expect(link, name).toHaveAttribute('rel', 'noopener noreferrer');
      }
      await expect(page.getByTestId('mod-detail-homepage-new-tab-mark')).toBeVisible();
      await expect(page.getByTestId('mod-detail-source-new-tab-mark')).toBeVisible();

      const description = page.getByTestId('mod-detail-description');
      await expect(
        description.getByRole('link', { name: `Docs ${NOTE}`, exact: true })
      ).toHaveCount(1);
      // ADR-10 decision 5: Chromium names both SVG links from their <title>
      const diagrams = description.getByRole('link', { name: `Diagram ${NOTE}`, exact: true });
      await expect(diagrams).toHaveCount(2);
      await expect(diagrams.nth(1)).toHaveAttribute('href', 'https://example.com/diagram-xlink');

      await expect(page.getByRole('link', { name: `GitHub ${NOTE}`, exact: true })).toHaveCount(1);

      // The version select is named by its label, not its value
      await expect(page.getByRole('combobox', { name: 'Version', exact: true })).toBeVisible();
      expect(outside).toEqual([]);
    });
  });

  for (const width of [320, 390, 430]) {
    test.describe(`phone ${width}px`, () => {
      test.use({ viewport: { width, height: 844 }, hasTouch: true });

      test('the page fits and the header stacks, in the light and the dark theme', async ({
        page,
      }) => {
        test.setTimeout(60_000);
        const outside = await stubDetail(page);
        for (const colorScheme of ['light', 'dark'] as const) {
          await openDetail(page);
          await useTheme(page, colorScheme);

          expect(await documentScrollWidth(page), `${colorScheme} scrollWidth`).toBe(width);

          const header = await boxOf(page.getByTestId('mod-detail-header'), 'header');
          const summary = await boxOf(page.getByTestId('mod-detail-summary'), 'summary');
          const install = await boxOf(page.getByTestId('mod-detail-install-section'), 'install');
          expect(install.y, 'install card below the summary').toBeGreaterThanOrEqual(
            summary.y + summary.height - 1
          );
          expect(Math.abs(install.width - header.width), 'install card width').toBeLessThanOrEqual(
            1
          );

          await expectInside(page.getByTestId('mod-detail-breadcrumb'), 'breadcrumb', width);
          await expectInside(page.getByTestId('mod-detail-back'), 'back button', width);
          for (const id of [
            'mod-detail-moddb-link',
            'mod-detail-homepage-link',
            'mod-detail-source-link',
            'mod-detail-trailer-link',
            'mod-detail-version-select',
            'mod-detail-install-button',
          ]) {
            await expectInside(page.getByTestId(id), id, width);
          }
          for (const id of [
            'mod-detail-version-select',
            'mod-detail-install-button',
            'mod-detail-back',
          ]) {
            const box = await boxOf(page.getByTestId(id), id);
            expect(box.height, `${id} height`).toBeGreaterThanOrEqual(44);
          }
        }
        expect(outside).toEqual([]);
      });
    });
  }

  test.describe('tablet 768px', () => {
    test.use({ viewport: { width: 768, height: 1024 } });

    test('logo, info and install card stay in one row and the page fits', async ({ page }) => {
      const outside = await stubDetail(page);
      await openDetail(page);

      expect(await documentScrollWidth(page)).toBe(768);
      const logo = await boxOf(page.getByTestId('mod-detail-logo'), 'logo');
      const summary = await boxOf(page.getByTestId('mod-detail-summary'), 'summary');
      const install = await boxOf(page.getByTestId('mod-detail-install-section'), 'install');
      expect(Math.abs(install.y - logo.y), 'install card top').toBeLessThanOrEqual(1);
      expect(install.x, 'install card right of the info').toBeGreaterThanOrEqual(
        summary.x + summary.width - 1
      );
      expect(install.x + install.width).toBeLessThanOrEqual(768);
      expect(outside).toEqual([]);
    });
  });

  test.describe('description at 390px', () => {
    test.use({ viewport: { width: 390, height: 844 }, hasTouch: true });

    test('the description is typeset from the theme and wide content stays in the card', async ({
      page,
    }) => {
      test.setTimeout(60_000);
      const outside = await stubDetail(page);
      const linkColours: string[] = [];

      for (const colorScheme of ['light', 'dark'] as const) {
        await openDetail(page);
        await useTheme(page, colorScheme);
        expect(await documentScrollWidth(page), `${colorScheme} scrollWidth`).toBe(390);

        const styles = await page.evaluate(() => {
          const root = document.querySelector<HTMLElement>(
            '[data-testid="mod-detail-description"]'
          );
          const title = document.querySelector('[data-testid="mod-detail-name"]');
          if (!root || !title) throw new Error('description or title missing');
          const pick = (selector: string) => {
            const element = root.querySelector(selector);
            if (!element) throw new Error(`missing ${selector}`);
            return getComputedStyle(element);
          };
          // Probes resolve a theme token to the colour the browser computes for it
          const token = (property: 'color' | 'backgroundColor', value: string) => {
            const probe = document.createElement('span');
            probe.style[property] = value;
            root.appendChild(probe);
            const resolved = getComputedStyle(probe)[property];
            probe.remove();
            return resolved;
          };
          const headings = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6'].map((tag) => {
            const style = pick(tag);
            return { tag, size: parseFloat(style.fontSize), weight: Number(style.fontWeight) };
          });
          const link = pick('p a');
          const quote = pick('blockquote');
          return {
            titleSize: parseFloat(getComputedStyle(title).fontSize),
            bodySize: parseFloat(pick('p').fontSize),
            headings,
            ul: { type: pick('ul').listStyleType, padding: parseFloat(pick('ul').paddingLeft) },
            nested: pick('ul ul').listStyleType,
            ol: { type: pick('ol').listStyleType, padding: parseFloat(pick('ol').paddingLeft) },
            link: { decoration: link.textDecorationLine, color: link.color },
            primary: token('color', 'var(--primary)'),
            quote: {
              width: parseFloat(quote.borderLeftWidth),
              color: quote.borderLeftColor,
            },
            border: token('color', 'var(--border)'),
            code: pick('p code').backgroundColor,
            muted: token('backgroundColor', 'var(--muted)'),
            cell: pick('td').borderTopColor,
            author: pick('[data-e2e="author-styled"]').color,
          };
        });

        for (const heading of styles.headings) {
          expect(heading.size, `${heading.tag} size`).toBeGreaterThan(styles.bodySize);
          expect(heading.weight, `${heading.tag} weight`).toBeGreaterThanOrEqual(600);
        }
        expect(styles.headings[0].size, 'h1 below the page title').toBeLessThan(styles.titleSize);
        expect(styles.ul.type).toBe('disc');
        expect(styles.nested).toBe('circle');
        expect(styles.ol.type).toBe('decimal');
        expect(styles.ul.padding).toBeGreaterThan(0);
        expect(styles.ol.padding).toBeGreaterThan(0);
        expect(styles.link.decoration).toBe('underline');
        expect(styles.link.color).toBe(styles.primary);
        expect(styles.quote.width).toBeGreaterThan(0);
        expect(styles.quote.color).toBe(styles.border);
        expect(styles.code).toBe(styles.muted);
        expect(styles.cell).toBe(styles.border);
        expect(styles.author).toBe('rgb(204, 51, 51)');
        linkColours.push(styles.link.color);

        // Wide content scrolls inside the card or shrinks to it
        const card = await boxOf(page.getByTestId('mod-detail-description'), 'description');
        for (const selector of ['table', 'pre']) {
          const element = page.getByTestId('mod-detail-description').locator(selector);
          const scroll = await element.evaluate((el) => ({
            scrollWidth: el.scrollWidth,
            clientWidth: el.clientWidth,
          }));
          expect(scroll.scrollWidth, `${selector} scrolls`).toBeGreaterThan(scroll.clientWidth);
          const box = await boxOf(element, selector);
          expect(box.x + box.width, `${selector} right`).toBeLessThanOrEqual(
            card.x + card.width + 0.5
          );
        }
        const image = await boxOf(
          page.getByTestId('mod-detail-description').locator('img'),
          'image'
        );
        expect(image.width).toBeLessThanOrEqual(card.width + 0.5);
      }

      expect(linkColours[0], 'link colour differs between the themes').not.toBe(linkColours[1]);
      expect(outside).toEqual([]);
    });
  });
});
