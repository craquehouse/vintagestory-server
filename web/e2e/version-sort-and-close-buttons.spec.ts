import { test, expect, type Locator, type Page } from '@playwright/test';
import { FIXTURE_GAME_VERSION, fetchOnNewConnection, serveConfigKey } from './config-js';

/**
 * E2E tests for version order, sort state for screen readers and close button size.
 *
 * Story 21.5 (FR275-FR277, Epic 21 ADR-8 and ADR-9; VSS-qxxo, VSS-whnb, VSS-nuef):
 * - Installed mods: sorting by Version puts a pre-release before its release and orders
 *   numbers as numbers (`1.0.0-rc.2 < 1.0.0-rc.12 < 1.0.0 < 1.9.0 < 1.10.0`), in the table
 *   (1440px) and on the cards (390px); descending is the exact reverse.
 * - Version page: the same order; a newer pre-release (`1.22.0-rc.12` over an installed
 *   `1.22.0-rc.2`) is marked as newer; selecting `1.21.10` over an installed `1.21.9` is an
 *   upgrade, `1.21.8` a downgrade.
 * - Both tables: `aria-sort` is `ascending` or `descending` on the sorted column and `none`
 *   on the other sortable columns; columns that cannot be sorted have none.
 * - Dialog close buttons (390 and 1440px) and the navigation sheet's (390px) are at least
 *   44 by 44px, their icon is still 16px from the top and right edges, the dialog title
 *   does not reach the button, and the button closes the dialog or sheet.
 *
 * Reads only. The installed mods, their update status, the compatibility lookups and the
 * version list are stubbed with `page.route`, the installed game version is rewritten in
 * the page's server status, and every write to the API is refused, so nothing changes on
 * the stack. No confirm button is clicked; the game server is neither started nor stopped;
 * no screenshot is taken. Untagged: it needs no mod database and no game server.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080), rebuilt from this
 *   branch: `just test-e2e-ci`, or `just docker restart`, then
 *   `cd web && bunx playwright test e2e/version-sort-and-close-buttons.spec.ts` with
 *   VS_API_KEY_ADMIN exported.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const INSTALLED = '/game-server/mods/installed';
const VERSION_PAGE = '/game-server/version';
const HEIGHT = 900;

interface ServerStatusBody {
  status?: string;
  data?: { state?: string; version?: string | null; [field: string]: unknown };
}

/**
 * Show the page an installed game server with the given version: the status request is
 * passed on, `state` becomes `installed` only when it was `not_installed`, and `version`
 * is always replaced. Direct API calls from a test see the real state.
 */
async function pretendVersionInstalled(page: Page, version: string) {
  await page.route('**/api/v1alpha1/server/status', async (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const response = await fetchOnNewConnection(route);
    const body: ServerStatusBody = await response.json();
    if (response.ok() && body.data) {
      const state = body.data.state === 'not_installed' ? 'installed' : body.data.state;
      body.data = { ...body.data, state, version };
    }
    await route.fulfill({ response, json: body });
  });
}

/** Admin key from /config.js, the given game version installed, every write refused. */
async function readOnly(page: Page, installedVersion: string) {
  await serveConfigKey(page, API_KEY);
  await pretendVersionInstalled(page, installedVersion);
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
}

interface FakeMod {
  slug: string;
  name: string;
  version: string;
}

// Name order (alpha, beta, delta, epsilon, gamma) differs from version order
const MODS: FakeMod[] = [
  { slug: 'alphamod', name: 'Alpha Mod', version: '1.10.0' },
  { slug: 'betamod', name: 'Beta Mod', version: '1.0.0' },
  { slug: 'gammamod', name: 'Gamma Mod', version: '1.0.0-rc.12' },
  { slug: 'deltamod', name: 'Delta Mod', version: '1.9.0' },
  { slug: 'epsilonmod', name: 'Epsilon Mod', version: '1.0.0-rc.2' },
];

const BY_VERSION = ['epsilonmod', 'gammamod', 'betamod', 'deltamod', 'alphamod'];

/** Serve the installed mods, their update status and lookups (registered after readOnly, so it runs first). */
async function fakeInstalledMods(page: Page) {
  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    if (request.method() !== 'GET') return route.fallback();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');

    if (path === '') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            mods: MODS.map(({ slug, name, version }) => ({
              filename: `${slug}_${version}.zip`,
              slug,
              version,
              enabled: true,
              installed_at: '2026-11-17T00:00:00Z',
              asset_id: 0,
              name,
              authors: [],
              description: null,
              side: 'Both',
            })),
            pending_restart: false,
          },
        },
      });
      return;
    }

    if (path === '/updates') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            game_version: FIXTURE_GAME_VERSION,
            checked_at: '2026-11-17T00:00:00Z',
            update_count: 0,
            mods: MODS.map(({ slug, name, version }) => ({
              slug,
              name,
              installed_version: version,
              status: 'up_to_date',
              offered_version: null,
              offered_compatibility: null,
              offered_prerelease: null,
              reason: null,
              checked_at: '2026-11-17T00:00:00Z',
              error: null,
            })),
          },
        },
      });
      return;
    }

    const lookup = path.match(/^\/lookup\/([^/]+)$/);
    const mod = lookup && MODS.find((item) => item.slug === decodeURIComponent(lookup[1]));
    if (mod) {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            slug: mod.slug,
            urlalias: null,
            asset_id: 0,
            name: mod.name,
            author: 'Someone',
            description: null,
            latest_version: mod.version,
            downloads: 0,
            follows: 0,
            side: 'Both',
            compatibility: {
              status: 'compatible',
              game_version: FIXTURE_GAME_VERSION,
              mod_version: mod.version,
              message: `Compatible with ${FIXTURE_GAME_VERSION}.`,
              latest_supported_game_version: FIXTURE_GAME_VERSION,
            },
            logo_url: null,
            releases: [],
            tags: [],
            homepage_url: null,
            source_url: null,
            created: null,
            last_released: null,
          },
        },
      });
      return;
    }

    await route.fallback();
  });
}

const VERSIONS: { version: string; channel: 'stable' | 'unstable'; isLatest: boolean }[] = [
  { version: '1.21.9', channel: 'stable', isLatest: false },
  { version: '1.22.0-rc.1', channel: 'unstable', isLatest: false },
  { version: '1.21.8', channel: 'stable', isLatest: false },
  { version: '1.22.0', channel: 'stable', isLatest: true },
  { version: '1.22.0-rc.12', channel: 'unstable', isLatest: true },
  { version: '1.21.10', channel: 'stable', isLatest: false },
  { version: '1.22.0-rc.2', channel: 'unstable', isLatest: false },
];

const VERSIONS_DESCENDING = [
  '1.22.0',
  '1.22.0-rc.12',
  '1.22.0-rc.2',
  '1.22.0-rc.1',
  '1.21.10',
  '1.21.9',
  '1.21.8',
];

/** Serve the version list (registered after readOnly, so it runs first). */
async function fakeVersions(page: Page) {
  await page.route(/\/api\/v1alpha1\/versions(\?.*)?$/, (route) => {
    if (route.request().method() !== 'GET') return route.fallback();
    const channel = new URL(route.request().url()).searchParams.get('channel');
    const versions = VERSIONS.filter((item) => !channel || item.channel === channel).map(
      ({ version, channel: itemChannel, isLatest }) => ({
        version,
        filename: `vs_server_linux-x64_${version}.tar.gz`,
        filesize: '40.2 MB',
        md5: 'abc123',
        cdn_url: `https://cdn.example.invalid/${version}`,
        local_url: `/local/${version}`,
        is_latest: isLatest,
        channel: itemChannel,
      })
    );
    return route.fulfill({
      json: {
        status: 'ok',
        data: { versions, total: versions.length, cached: false, cached_at: null },
      },
    });
  });
}

async function openInstalledMods(page: Page, width: number) {
  await page.setViewportSize({ width, height: HEIGHT });
  await readOnly(page, FIXTURE_GAME_VERSION);
  await fakeInstalledMods(page);
  await page.goto(INSTALLED);
}

async function openVersionPage(page: Page, width: number, installedVersion: string) {
  await page.setViewportSize({ width, height: HEIGHT });
  await readOnly(page, installedVersion);
  await fakeVersions(page);
  await page.goto(VERSION_PAGE);
  await expect(page.getByTestId('version-table')).toBeVisible({ timeout: 30_000 });
  await expect(page.getByTestId('installed-version')).toHaveText(installedVersion);
}

/** Test ID suffixes of the elements matching `prefix`, in display order. */
async function order(page: Page, prefix: string): Promise<string[]> {
  const ids = await page
    .getByTestId(new RegExp(`^${prefix}`))
    .evaluateAll((elements) =>
      elements.map((element) => element.getAttribute('data-testid') ?? '')
    );
  return ids.map((id) => id.replace(prefix, ''));
}

async function expectAriaSort(table: Locator, expected: Record<string, string | null>) {
  for (const [name, value] of Object.entries(expected)) {
    const header = table.getByRole('columnheader', { name, exact: true });
    if (value === null) {
      await expect(header, `${name} has no aria-sort`).not.toHaveAttribute('aria-sort');
    } else {
      await expect(header, `${name} aria-sort`).toHaveAttribute('aria-sort', value);
    }
  }
}

async function boxOf(locator: Locator, name: string) {
  const box = await locator.boundingBox();
  if (!box) throw new Error(`No box for ${name}`);
  return box;
}

/** Wait until the dialog or sheet has finished its opening animations. */
async function animationsFinished(container: Locator) {
  await container.evaluate((element) =>
    Promise.all(element.getAnimations({ subtree: true }).map((animation) => animation.finished))
  );
}

/** The close button is at least 44px square and its icon 16px (within 1px) from the top and right edges. */
async function expectCloseButtonGeometry(container: Locator, close: Locator, label: string) {
  const outer = await boxOf(container, label);
  const button = await boxOf(close, `${label} close button`);
  const icon = await boxOf(close.locator('svg'), `${label} close icon`);

  expect(button.width, `${label} close width`).toBeGreaterThanOrEqual(44);
  expect(button.height, `${label} close height`).toBeGreaterThanOrEqual(44);
  expect(Math.abs(icon.width - 16), `${label} icon width`).toBeLessThanOrEqual(1);
  expect(Math.abs(icon.y - outer.y - 16), `${label} icon from top`).toBeLessThanOrEqual(1);
  expect(
    Math.abs(outer.x + outer.width - (icon.x + icon.width) - 16),
    `${label} icon from right`
  ).toBeLessThanOrEqual(1);
  return button;
}

test.describe('Installed mods version sort and aria-sort (Story 21.5, AC 1, 7-9)', () => {
  test('the table sorts versions with pre-releases first and announces the sort at 1440px', async ({
    page,
  }) => {
    await openInstalledMods(page, 1440);
    const table = page.getByTestId('mod-table');
    await expect(table).toBeVisible({ timeout: 30_000 });

    await expectAriaSort(table, {
      Name: 'ascending',
      Version: 'none',
      Status: 'none',
      Available: null,
      Side: null,
      Compatibility: null,
      Actions: null,
    });

    const versionButton = table.getByRole('button', { name: 'Version', exact: true });
    await versionButton.click();
    expect(await order(page, 'mod-row-')).toEqual(BY_VERSION);
    await expectAriaSort(table, { Version: 'ascending', Name: 'none', Status: 'none' });

    await versionButton.click();
    expect(await order(page, 'mod-row-')).toEqual([...BY_VERSION].reverse());
    await expectAriaSort(table, { Version: 'descending', Name: 'none', Status: 'none' });

    const chevrons = table.locator('thead svg');
    await expect(chevrons).toHaveCount(1);
    await expect(chevrons.first()).toHaveAttribute('aria-hidden', 'true');
  });

  test('the cards sort versions with pre-releases first at 390px', async ({ page }) => {
    await openInstalledMods(page, 390);
    await expect(page.getByTestId('installed-mod-cards')).toBeVisible({ timeout: 30_000 });

    await page.getByTestId('installed-mods-sort-column').click();
    await page.getByTestId('installed-mods-sort-option-version').click();
    await expect(page.getByTestId('installed-mods-sort-direction')).toHaveText('Ascending');
    expect(await order(page, 'installed-mod-card-')).toEqual(BY_VERSION);

    await page.getByTestId('installed-mods-sort-direction').click();
    await expect(page.getByTestId('installed-mods-sort-direction')).toHaveText('Descending');
    expect(await order(page, 'installed-mod-card-')).toEqual([...BY_VERSION].reverse());
  });
});

test.describe('Version page order, newer mark and aria-sort (Story 21.5, AC 2-3, 8-9)', () => {
  test('sorts pre-releases before their release and marks newer pre-releases at 1440px', async ({
    page,
  }) => {
    await openVersionPage(page, 1440, '1.22.0-rc.2');
    const table = page.getByTestId('version-table');

    expect(await order(page, 'version-table-row-')).toEqual(VERSIONS_DESCENDING);
    await expectAriaSort(table, {
      Version: 'descending',
      Channel: 'none',
      Size: 'none',
      Status: null,
      Actions: null,
    });

    const newer = /(^|\s)bg-primary\/5(\s|$)/;
    await expect(page.getByTestId('version-table-row-1.22.0-rc.12')).toHaveClass(newer);
    await expect(page.getByTestId('version-table-row-1.22.0')).toHaveClass(newer);
    await expect(page.getByTestId('version-table-row-1.22.0-rc.1')).not.toHaveClass(newer);
    await expect(page.getByTestId('version-table-row-1.22.0-rc.2')).not.toHaveClass(newer);

    // From the default (descending) one click removes the sort, the next sorts ascending
    const versionHeader = table.getByRole('columnheader', { name: 'Version', exact: true });
    await versionHeader.click();
    await expectAriaSort(table, { Version: 'none', Channel: 'none', Size: 'none' });
    await versionHeader.click();
    expect(await order(page, 'version-table-row-')).toEqual([...VERSIONS_DESCENDING].reverse());
    await expectAriaSort(table, { Version: 'ascending', Channel: 'none', Size: 'none' });

    const chevrons = table.locator('thead svg');
    await expect(chevrons).toHaveCount(1);
    await expect(chevrons.first()).toHaveAttribute('aria-hidden', 'true');
  });

  test('calls 1.21.10 over 1.21.9 an upgrade and 1.21.8 a downgrade (AC 6)', async ({ page }) => {
    await openVersionPage(page, 1440, '1.21.9');
    const dialog = page.getByTestId('install-version-dialog');

    await page.getByTestId('version-table-select-1.21.10').click();
    await expect(dialog).toBeVisible();
    await expect(dialog.getByTestId('dialog-title')).toHaveText('Upgrade Server Version');
    await expect(dialog.getByTestId('downgrade-warning')).toHaveCount(0);
    await page.keyboard.press('Escape');
    await expect(dialog).toBeHidden();

    await page.getByTestId('version-table-select-1.21.8').click();
    await expect(dialog).toBeVisible();
    await expect(dialog.getByTestId('dialog-title')).toHaveText('Downgrade Server Version');
    await expect(dialog.getByTestId('downgrade-warning')).toBeVisible();
  });
});

test.describe('Close buttons at least 44px (Story 21.5, AC 11)', () => {
  for (const width of [390, 1440]) {
    test(`the install dialog's close button at ${width}px`, async ({ page }) => {
      await openVersionPage(page, width, '1.21.9');
      await page.getByTestId('version-table-select-1.21.8').click();
      const dialog = page.getByTestId('install-version-dialog');
      await expect(dialog).toBeVisible();
      await animationsFinished(dialog);

      const close = dialog.getByRole('button', { name: 'Close', exact: true });
      const button = await expectCloseButtonGeometry(dialog, close, `dialog at ${width}px`);

      const title = await dialog.getByTestId('dialog-title').evaluate((element) => {
        const range = document.createRange();
        range.selectNodeContents(element);
        const rect = range.getBoundingClientRect();
        return { x: rect.x, y: rect.y, width: rect.width, height: rect.height };
      });
      const overlaps =
        title.x < button.x + button.width &&
        button.x < title.x + title.width &&
        title.y < button.y + button.height &&
        button.y < title.y + title.height;
      expect(overlaps, `title text clear of the close button at ${width}px`).toBe(false);

      await close.click();
      await expect(dialog).toBeHidden();
    });
  }

  test("the navigation sheet's close button at 390px", async ({ page }) => {
    await openInstalledMods(page, 390);
    await page.getByRole('button', { name: 'Open menu' }).click();
    const sheet = page.getByRole('dialog', { name: 'Navigation menu' });
    await expect(sheet).toBeVisible();
    await animationsFinished(sheet);

    const close = sheet.getByRole('button', { name: 'Close', exact: true });
    await expectCloseButtonGeometry(sheet, close, 'navigation sheet');

    await close.click();
    await expect(sheet).toBeHidden();
  });
});
