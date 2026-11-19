import { test, expect, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for the remove mod dialog while its request runs.
 *
 * Story 21.4 (FR271, FR272; Epic 21 ADR-6):
 * - After confirm the dialog stays open, the confirm button shows "Removing..." and both
 *   buttons are disabled; Escape does not close it; the row is gone behind it.
 * - On success the dialog closes and one toast says "Removed <slug>".
 * - On an error one toast shows the API's message, the dialog offers "Remove" again and
 *   the row is back; Escape then closes it.
 * - The same from a card at phone width, and over the "No mods installed yet" text when
 *   the only mod is removed.
 *
 * The installed mods list, the update status, the compatibility lookups and the DELETE are
 * answered with `page.route` (the DELETE after a delay, with success or a 409, as each test
 * chooses); every other write is refused by the stub. The spec reads and changes nothing
 * in the server's data, needs no mod database and no game server, does not start or stop
 * the game server and takes no screenshot.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080) rebuilt from this branch:
 *   `just test-e2e-ci e2e/mod-remove-dialog.spec.ts`, or `just docker restart` then
 *   `cd web && bunx playwright test e2e/mod-remove-dialog.spec.ts`
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const INSTALLED = '/game-server/mods/installed';
const PHONE = { width: 390, height: 844 };
const DESKTOP = { width: 1440, height: 900 };

/** How long the stubbed DELETE waits before it answers. */
const DELETE_DELAY_MS = 1500;

const BUSY_MESSAGE =
  "Another operation on mod 'e2e-alpha' is in progress. Try again when it has finished.";

interface FakeMod {
  slug: string;
  name: string;
  version: string;
}

const ALPHA: FakeMod = { slug: 'e2e-alpha', name: 'E2E Alpha', version: '1.0.0' };
const BETA: FakeMod = { slug: 'e2e-beta', name: 'E2E Beta', version: '2.0.0' };

type DeleteAnswer = 'success' | 'busy';

/**
 * Serve the installed mods from a list the stub keeps, their update status and lookups;
 * answer each DELETE after a delay with `answer`; refuse every other write.
 */
async function fakeInstalledMods(page: Page, initial: FakeMod[], answer: DeleteAnswer) {
  let mods = [...initial];
  const deletes: string[] = [];

  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');

    if (request.method() === 'GET' && path === '') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            mods: mods.map(({ slug, name, version }) => ({
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

    if (request.method() === 'GET' && path === '/updates') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            game_version: '1.22.7',
            checked_at: '2026-11-17T00:00:00Z',
            update_count: 0,
            mods: mods.map(({ slug, name, version }) => ({
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
    if (request.method() === 'GET' && lookup) {
      const slug = decodeURIComponent(lookup[1]);
      const mod = initial.find((item) => item.slug === slug);
      if (!mod) {
        await route.fulfill({
          status: 404,
          json: { detail: { code: 'MOD_NOT_FOUND', message: slug } },
        });
        return;
      }
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            slug,
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
              game_version: '1.22.7',
              mod_version: mod.version,
              message: 'Compatible with 1.22.7.',
              latest_supported_game_version: '1.22.7',
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

    const removal = path.match(/^\/([^/]+)$/);
    if (request.method() === 'DELETE' && removal) {
      const slug = decodeURIComponent(removal[1]);
      deletes.push(slug);
      await new Promise((resolve) => setTimeout(resolve, DELETE_DELAY_MS));
      if (answer === 'success') {
        mods = mods.filter((mod) => mod.slug !== slug);
        await route.fulfill({ json: { status: 'ok', data: { slug, pending_restart: false } } });
      } else {
        await route.fulfill({
          status: 409,
          json: { detail: { code: 'MOD_OPERATION_IN_PROGRESS', message: BUSY_MESSAGE } },
        });
      }
      return;
    }

    if (request.method() !== 'GET') {
      // Never let a write reach the server's data
      await route.fulfill({
        status: 500,
        json: { detail: { code: 'E2E_BLOCKED', message: path } },
      });
      return;
    }

    await route.fallback();
  });

  return { deletes };
}

/** While the DELETE waits: the dialog holds with "Removing..." and ignores Escape. */
async function expectRemoving(page: Page, item: ReturnType<Page['getByTestId']>) {
  const dialog = page.getByTestId('remove-dialog');
  const confirm = page.getByTestId('remove-dialog-confirm');
  await expect(confirm).toHaveText('Removing...');
  await expect(confirm).toBeDisabled();
  await expect(page.getByTestId('remove-dialog-cancel')).toBeDisabled();
  await expect(item).toHaveCount(0);
  await page.keyboard.press('Escape');
  await expect(dialog).toBeVisible();
  await expect(confirm).toHaveText('Removing...');
}

test.describe('Remove mod dialog waits for the removal (Story 21.4)', () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
  });

  test('table: stays open until the delayed removal succeeds, then one toast', async ({ page }) => {
    const stub = await fakeInstalledMods(page, [ALPHA, BETA], 'success');
    await page.setViewportSize(DESKTOP);
    await page.goto(INSTALLED);

    await page.getByTestId(`mod-remove-${ALPHA.slug}`).click({ timeout: 30_000 });
    await expect(page.getByTestId('remove-dialog')).toBeVisible();
    await page.getByTestId('remove-dialog-confirm').click();

    await expectRemoving(page, page.getByTestId(`mod-row-${ALPHA.slug}`));

    await expect(page.getByTestId('remove-dialog')).toHaveCount(0, { timeout: 10_000 });
    await expect(page.getByTestId(`mod-row-${ALPHA.slug}`)).toHaveCount(0);
    await expect(page.getByTestId(`mod-row-${BETA.slug}`)).toBeVisible();
    await expect(page.locator('[data-sonner-toast]')).toContainText(`Removed ${ALPHA.slug}`);
    await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);
    expect(stub.deletes).toEqual([ALPHA.slug]);
  });

  test('table: a refused removal shows one toast and offers Remove again', async ({ page }) => {
    const stub = await fakeInstalledMods(page, [ALPHA, BETA], 'busy');
    await page.setViewportSize(DESKTOP);
    await page.goto(INSTALLED);

    await page.getByTestId(`mod-remove-${ALPHA.slug}`).click({ timeout: 30_000 });
    await page.getByTestId('remove-dialog-confirm').click();

    await expectRemoving(page, page.getByTestId(`mod-row-${ALPHA.slug}`));

    const confirm = page.getByTestId('remove-dialog-confirm');
    await expect(confirm).toHaveText('Remove', { timeout: 10_000 });
    await expect(confirm).toBeEnabled();
    await expect(page.getByTestId('remove-dialog-cancel')).toBeEnabled();
    await expect(page.getByTestId('remove-dialog')).toBeVisible();
    await expect(page.getByTestId(`mod-row-${ALPHA.slug}`)).toBeVisible();
    await expect(page.locator('[data-sonner-toast]')).toContainText(BUSY_MESSAGE);
    await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);

    await page.keyboard.press('Escape');
    await expect(page.getByTestId('remove-dialog')).toHaveCount(0);
    await expect(page.getByTestId(`mod-row-${ALPHA.slug}`)).toBeVisible();
    expect(stub.deletes).toEqual([ALPHA.slug]);
  });

  test('cards: removing the only mod holds the dialog over the empty state', async ({ page }) => {
    const stub = await fakeInstalledMods(page, [ALPHA], 'success');
    await page.setViewportSize(PHONE);
    await page.goto(INSTALLED);

    await page.getByRole('button', { name: `Remove ${ALPHA.name}` }).click({ timeout: 30_000 });
    await expect(page.getByTestId('remove-dialog')).toBeVisible();
    await page.getByTestId('remove-dialog-confirm').click();

    await expectRemoving(page, page.getByTestId(`installed-mod-card-${ALPHA.slug}`));
    await expect(page.getByTestId('mod-table-empty')).toBeAttached();

    await expect(page.getByTestId('remove-dialog')).toHaveCount(0, { timeout: 10_000 });
    await expect(page.getByTestId('mod-table-empty')).toBeVisible();
    await expect(page.locator('[data-sonner-toast]')).toContainText(`Removed ${ALPHA.slug}`);
    await expect(page.locator('[data-sonner-toast]')).toHaveCount(1);
    expect(stub.deletes).toEqual([ALPHA.slug]);
  });
});
