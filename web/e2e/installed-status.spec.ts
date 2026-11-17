import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for an installed mod's status wherever it is shown.
 *
 * Story 17.4 (FR184-FR185, VSS-49n, VSS-br2):
 * - A browse card shows Installed when any of its entry's mod IDs is installed, as the
 *   detail page does (the Instruments entry ships `instruments`, `vsinstruments` and
 *   `vsinstrumentsbase`; its card's slug is `instruments`).
 * - An installed mod with no stored update data says "Not checked yet", not "Unknown",
 *   in the table (desktop) and on the cards (phone).
 * - A mod installed through the API has a real update status at once, without a
 *   "Check for updates".
 *
 * The first two tests replace the installed mods list (and the update status) with
 * `page.route`, so they install nothing; the browse listing and the lookup come from
 * the live mod database. The real-API test runs serially, installs one mod that was
 * not installed before the run and removes it again; cleanup runs only with a snapshot
 * of the installed mods, so the dev stack ends with the mods it started with.
 *
 * Playwright runs spec files in parallel (`fullyParallel`), and `mode: 'serial'` does
 * not order tests across files. So this spec installs only `playercorpse`, which no
 * other spec installs (`mod-install-release.spec.ts` touches carryon, canjewelry and
 * the instruments mod IDs), and its cleanup removes only what it installed itself.
 * Both specs can run at the same time against one stack.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080): `just test-e2e-web`,
 *   or `just docker restart` then
 *   `cd web && bunx playwright test e2e/installed-status.spec.ts`
 * - Network access to the public mod database.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const HEADERS = { 'X-API-Key': API_KEY };

const INSTALLED = '/game-server/mods/installed';
const PHONE = { width: 390, height: 844 };
const DESKTOP = { width: 1440, height: 900 };

/**
 * Mods the real-API test may install, in order of preference. Only mods no other spec
 * installs, so specs running in parallel never remove each other's installs.
 */
const CANDIDATES = ['playercorpse'];

interface FakeMod {
  slug: string;
  version: string;
}

function installedModJson({ slug, version }: FakeMod) {
  return {
    filename: `${slug}_${version}.zip`,
    slug,
    version,
    enabled: true,
    installed_at: '2026-11-15T00:00:00Z',
    asset_id: 0,
    name: slug,
    authors: [],
    description: null,
    side: 'Both',
  };
}

/** Replace the installed mods list (only `GET /api/v1alpha1/mods`) with the given mods. */
async function fakeInstalledMods(page: Page, mods: FakeMod[]) {
  await page.route(/\/api\/v1alpha1\/mods(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({
      json: { status: 'ok', data: { mods: mods.map(installedModJson), pending_restart: false } },
    });
  });
}

/**
 * Serve one installed mod with no stored update data (`unknown` / `not_checked`); its
 * lookup answers 404 and every write is refused, so nothing in the server changes.
 */
async function fakeNotCheckedMod(page: Page, mod: FakeMod) {
  await page.route(/\/api\/v1alpha1\/mods(\/[^?]*)?(\?.*)?$/, async (route) => {
    const request = route.request();
    const path = new URL(request.url()).pathname.replace('/api/v1alpha1/mods', '');
    if (request.method() === 'GET' && path === '') {
      await route.fulfill({
        json: { status: 'ok', data: { mods: [installedModJson(mod)], pending_restart: false } },
      });
      return;
    }
    if (request.method() === 'GET' && path === '/updates') {
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            game_version: '1.22.7',
            checked_at: null,
            update_count: 0,
            mods: [
              {
                slug: mod.slug,
                name: mod.slug,
                installed_version: mod.version,
                status: 'unknown',
                offered_version: null,
                offered_compatibility: null,
                offered_prerelease: null,
                reason: 'not_checked',
                checked_at: null,
                error: null,
              },
            ],
          },
        },
      });
      return;
    }
    if (request.method() === 'GET' && path.startsWith('/lookup/')) {
      await route.fulfill({
        status: 404,
        json: { detail: { code: 'MOD_NOT_FOUND', message: mod.slug } },
      });
      return;
    }
    await route.fulfill({
      status: 403,
      json: { detail: { code: 'FORBIDDEN', message: 'This test changes nothing' } },
    });
  });
}

async function installedSlugs(request: APIRequestContext): Promise<string[]> {
  const response = await request.get('/api/v1alpha1/mods', { headers: HEADERS });
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as { data: { mods: Array<{ slug: string }> } };
  return body.data.mods.map((mod) => mod.slug);
}

test.describe('Installed status is right everywhere (Story 17.4)', () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
  });

  // @moddb: searches the live browse list for Instruments
  test(
    'the Instruments card shows Installed for vsinstrumentsbase, like its detail page',
    { tag: '@moddb' },
    async ({
    page,
  }) => {
    await fakeInstalledMods(page, [{ slug: 'vsinstrumentsbase', version: '2.0.7' }]);
    // Sorted by downloads, Instruments is the first result; by the default (recent)
    // sort it is far down the first page and newer mods would push it off
    await page.goto('/game-server/mods/browse?q=instruments&sort=downloads');

    const card = page.getByTestId('mod-card-instruments');
    await expect(
      card,
      'the live mod database search for "instruments" did not return the Instruments card'
    ).toBeVisible({ timeout: 60_000 });
    await expect(page.getByTestId('mod-card-installed-instruments')).toHaveText('Installed');
    await expect(page.getByTestId('mod-card-install-instruments')).toHaveCount(0);

    await card.click();
    await expect(page).toHaveURL(/\/game-server\/mods\/browse\/instruments/);
    await expect(page.getByTestId('mod-detail-installed-indicator')).toBeVisible({
      timeout: 60_000,
    });
    await expect(page.getByTestId('mod-detail-install-button')).toHaveCount(0);
  });

  for (const [label, viewport] of [
    ['desktop', DESKTOP],
    ['phone', PHONE],
  ] as const) {
    test(`a mod without update data says Not checked yet (${label})`, async ({ page }) => {
      await page.setViewportSize(viewport);
      await fakeNotCheckedMod(page, { slug: 'notcheckedmod', version: '1.0.0' });
      await page.goto(INSTALLED);

      const cell = page.getByTestId('mod-update-notcheckedmod');
      await expect(cell).toBeVisible({ timeout: 30_000 });
      await expect(cell).toContainText('Not checked yet');
      await expect(cell).not.toContainText('Unknown');
      if (label === 'phone') {
        await expect(page.getByTestId('installed-mod-card-notcheckedmod')).toContainText(
          'Not checked yet'
        );
      } else {
        await expect(page.getByTestId('mod-table')).toContainText('Not checked yet');
      }
    });
  }
});

// @moddb @install: installs a real mod from the mod database and removes it again
test.describe(
  'A new install shows its update status at once: real API (Story 17.4)',
  { tag: ['@moddb', '@install'] },
  () => {
  test.describe.configure({ mode: 'serial' });

  let before: string[] = [];
  // Cleanup deletes only what is missing from this snapshot, so it must never run
  // without one: it could otherwise remove a mod that was installed before the run.
  let hasSnapshot = false;
  // What this spec installed; cleanup removes nothing else
  const touched = new Set<string>();

  test.beforeAll(async ({ playwright, baseURL }) => {
    const request = await playwright.request.newContext({ baseURL });
    try {
      before = await installedSlugs(request);
      hasSnapshot = true;
    } finally {
      await request.dispose();
    }
  });

  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
  });

  test.afterEach(async ({ request }) => {
    if (!hasSnapshot) {
      throw new Error('No snapshot of the installed mods; refusing to clean up');
    }
    for (const slug of await installedSlugs(request)) {
      if (touched.has(slug) && !before.includes(slug)) {
        const removed = await request.delete(`/api/v1alpha1/mods/${slug}`, { headers: HEADERS });
        expect(removed.ok(), `cleanup DELETE /mods/${slug}`).toBe(true);
      }
    }
  });

  test('an installed mod has a real update status without a check', async ({ page, request }) => {
    test.setTimeout(120_000);
    const slug = CANDIDATES.find((candidate) => !before.includes(candidate));
    test.skip(slug === undefined, `Already installed on this stack: ${CANDIDATES.join(', ')}`);
    if (slug === undefined) return;

    // Recorded before the request, so cleanup also covers an install whose answer was lost
    touched.add(slug);
    const response = await request.post('/api/v1alpha1/mods', {
      headers: HEADERS,
      data: { slug },
      timeout: 60_000,
    });
    expect(response.status()).toBe(200);
    const installed = (await response.json()) as { data: { slug: string } };
    const modId = installed.data.slug;
    touched.add(modId);

    // No POST /mods/updates/check: the install's own lookup is the update data
    const updates = await request.get('/api/v1alpha1/mods/updates', { headers: HEADERS });
    expect(updates.ok()).toBe(true);
    const body = (await updates.json()) as {
      data: { mods: Array<{ slug: string; status: string; reason: string | null }> };
    };
    const item = body.data.mods.find((mod) => mod.slug === modId);
    expect(item, `${modId} is listed in GET /mods/updates`).toBeDefined();
    expect(item?.status).not.toBe('unknown');

    await page.goto(INSTALLED);
    const cell = page.getByTestId(`mod-update-${modId}`);
    await expect(cell).toBeVisible({ timeout: 30_000 });
    await expect(cell).not.toContainText('Not checked yet');
    await expect(cell).not.toContainText('Unknown');

    const removed = await request.delete(`/api/v1alpha1/mods/${modId}`, { headers: HEADERS });
    expect(removed.ok()).toBe(true);
    expect(await installedSlugs(request)).not.toContain(modId);
  });
});
