import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for which release Install picks.
 *
 * Story 17.2 (FR179-FR181, Epic 17 ADR-2): Install takes the newest stable release
 * with a downloadable file of the mod ID that was asked for, the lookup reports that
 * release as `latest_version` with `install_mod_id`, and the web's version lists,
 * "(Latest)" label and install requests follow it.
 *
 * Expected versions are computed from the live lookup response, never hard-coded,
 * because the mod database changes. The UI tests stub the installed mods list and
 * `POST /api/v1alpha1/mods`, so they install nothing. The real-API tests run serially
 * and remove anything they install; each is skipped if a mod it touches was already
 * installed before the run, so the dev stack ends as it started.
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080): `just test-e2e-web`,
 *   or `just docker restart` then
 *   `cd web && bunx playwright test e2e/mod-install-release.spec.ts`
 * - Network access to the public mod database.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const HEADERS = { 'X-API-Key': API_KEY };

/** Mod IDs the real-API tests may install; cleaned up after each test. */
const TOUCHED = ['carryon', 'canjewelry', 'instruments', 'vsinstruments', 'vsinstrumentsbase'];

interface LookupRelease {
  version: string;
  modidstr: string;
  file_id: number | null;
}

interface LookupBody {
  data: { install_mod_id: string; latest_version: string | null; releases: LookupRelease[] };
}

const hasFile = (release: LookupRelease) =>
  typeof release.file_id === 'number' && release.file_id > 0;

/** What a plain install picks (ADR-2 rule 3): first stable release with a file, else first with a file. */
function expectedDefault(releases: LookupRelease[], modId: string): string | null {
  const candidates = releases.filter((r) => r.modidstr === modId && hasFile(r));
  const stable = candidates.find((r) => !r.version.includes('-'));
  return (stable ?? candidates[0])?.version ?? null;
}

/** Distinct versions of one mod ID, newest first, as the version list shows them. */
function versionsOf(releases: LookupRelease[], modId: string): string[] {
  return [...new Set(releases.filter((r) => r.modidstr === modId).map((r) => r.version))];
}

async function probeLookup(request: APIRequestContext, slug: string): Promise<LookupBody> {
  const response = await request.get(`/api/v1alpha1/mods/lookup/${slug}`, { headers: HEADERS });
  expect(response.ok()).toBe(true);
  return (await response.json()) as LookupBody;
}

async function installedSlugs(request: APIRequestContext): Promise<string[]> {
  const response = await request.get('/api/v1alpha1/mods', { headers: HEADERS });
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as { data: { mods: Array<{ slug: string }> } };
  return body.data.mods.map((mod) => mod.slug);
}

/** Serve the page one probed lookup response for `slug`. */
async function serveLookup(page: Page, slug: string, body: LookupBody) {
  await page.route(new RegExp(`/api/v1alpha1/mods/lookup/${slug}(\\?.*)?$`), (route) =>
    route.fulfill({ json: body })
  );
}

/** Replace the installed mods list (only `GET /api/v1alpha1/mods`) with no mods. */
async function fakeNoInstalledMods(page: Page) {
  await page.route(/\/api\/v1alpha1\/mods(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.fallback();
      return;
    }
    await route.fulfill({ json: { status: 'ok', data: { mods: [], pending_restart: false } } });
  });
}

/** Stub `POST /api/v1alpha1/mods`; returns the captured request bodies. */
async function stubInstall(page: Page): Promise<unknown[]> {
  const bodies: unknown[] = [];
  await page.route(/\/api\/v1alpha1\/mods(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'POST') {
      await route.fallback();
      return;
    }
    const body = route.request().postDataJSON() as { slug: string; version?: string };
    bodies.push(body);
    await route.fulfill({
      json: {
        status: 'ok',
        data: {
          slug: body.slug,
          version: body.version ?? 'stub',
          filename: 'stub.zip',
          compatibility: 'compatible',
          pending_restart: false,
        },
      },
    });
  });
  return bodies;
}

async function versionOptions(page: Page): Promise<Array<{ testId: string; text: string }>> {
  await page.getByTestId('mod-detail-version-select').click();
  const options = page.getByRole('option');
  await expect(options.first()).toBeVisible();
  return options.evaluateAll((elements) =>
    elements.map((element) => ({
      testId: element.getAttribute('data-testid') ?? '',
      text: element.textContent ?? '',
    }))
  );
}

// @moddb: reads the releases of live mod database entries
test.describe('Install picks the right release (Story 17.2)', { tag: '@moddb' }, () => {
  test.beforeEach(async ({ page }) => {
    await serveConfigKey(page, API_KEY);
    await pretendServerInstalled(page);
  });

  test('lookup reports the install mod ID and what a plain install picks', async ({
    request,
  }) => {
    for (const slug of ['carryon', 'instruments']) {
      const body = await probeLookup(request, slug);
      expect(body.data.install_mod_id).toBe(slug);
      expect(body.data.latest_version).toBe(expectedDefault(body.data.releases, slug));
    }
  });

  test('detail page preselects and installs the newest stable release', async ({
    page,
    request,
  }) => {
    test.setTimeout(120_000);
    const body = await probeLookup(request, 'carryon');
    const latest = expectedDefault(body.data.releases, 'carryon');
    expect(latest).not.toBeNull();
    await serveLookup(page, 'carryon', body);
    await fakeNoInstalledMods(page);
    const posted = await stubInstall(page);

    await page.goto('/game-server/mods/browse/carryon');
    // The trigger shows the selected item's text, "(Latest)" label included
    await expect(page.getByTestId('mod-detail-version-select')).toHaveText(
      `v${latest} (Latest)`,
      { timeout: 60_000 }
    );

    const options = await versionOptions(page);
    const carryonVersions = versionsOf(body.data.releases, 'carryon');
    for (const option of options) {
      const version = option.testId.replace('mod-detail-version-option-', '');
      expect(carryonVersions).toContain(version);
    }
    const labelled = options.filter((option) => option.text.includes('(Latest)'));
    expect(labelled.map((option) => option.testId)).toEqual([
      `mod-detail-version-option-${latest}`,
    ]);
    await page.keyboard.press('Escape');

    await page.getByTestId('mod-detail-install-button').click();
    await page.getByTestId('install-dialog-confirm').click();
    await expect.poll(() => posted).toEqual([{ slug: 'carryon', version: latest }]);
  });

  test('Instruments detail page lists only instruments releases', async ({ page, request }) => {
    const body = await probeLookup(request, 'instruments');
    await serveLookup(page, 'instruments', body);
    await fakeNoInstalledMods(page);

    await page.goto('/game-server/mods/browse/instruments');
    await expect(page.getByTestId('mod-detail-install-button')).toBeVisible({ timeout: 60_000 });

    const options = await versionOptions(page);
    expect(options.map((option) => option.testId)).toEqual(
      versionsOf(body.data.releases, 'instruments').map(
        (version) => `mod-detail-version-option-${version}`
      )
    );
  });

  test('browse card installs the newest stable release', async ({ page, request }) => {
    test.setTimeout(120_000);
    const body = await probeLookup(request, 'carryon');
    const latest = expectedDefault(body.data.releases, 'carryon');
    await serveLookup(page, 'carryon', body);
    await fakeNoInstalledMods(page);
    const posted = await stubInstall(page);

    await page.goto('/game-server/mods/browse?q=carry+on');
    const install = page.getByTestId('mod-card-install-carryon');
    await expect(install).toBeVisible({ timeout: 60_000 });
    await install.click();

    await expect(page.getByTestId('install-dialog-mod-version')).toHaveText(
      `Version: ${latest}`
    );
    await page.getByTestId('install-dialog-confirm').click();
    await expect.poll(() => posted).toEqual([{ slug: 'carryon', version: latest }]);
  });
});

// @moddb @install: installs real mods from the mod database and removes them again
test.describe(
  'Install picks the right release: real API (Story 17.2)',
  { tag: ['@moddb', '@install'] },
  () => {
  test.describe.configure({ mode: 'serial' });

  let before: string[] = [];
  // Cleanup deletes only what is missing from this snapshot, so it must never run
  // without one: it could otherwise remove a mod that was installed before the run.
  let hasSnapshot = false;

  test.beforeAll(async ({ playwright, baseURL }) => {
    const request = await playwright.request.newContext({ baseURL });
    try {
      before = await installedSlugs(request);
      hasSnapshot = true;
    } finally {
      await request.dispose();
    }
  });

  test.afterEach(async ({ request }) => {
    if (!hasSnapshot) {
      throw new Error('No snapshot of the installed mods; refusing to clean up');
    }
    for (const slug of await installedSlugs(request)) {
      if (TOUCHED.includes(slug) && !before.includes(slug)) {
        const removed = await request.delete(`/api/v1alpha1/mods/${slug}`, { headers: HEADERS });
        expect(removed.ok(), `cleanup DELETE /mods/${slug}`).toBe(true);
      }
    }
  });

  test('a version of another mod ID, and a release without a file, are refused', async ({
    request,
  }) => {
    const already = ['instruments', 'vsinstrumentsbase', 'canjewelry'].filter((slug) =>
      before.includes(slug)
    );
    test.skip(already.length > 0, `Already installed on this stack: ${already.join(', ')}`);

    const instruments = await probeLookup(request, 'instruments');
    const own = versionsOf(instruments.data.releases, 'instruments');
    const otherOnly = versionsOf(instruments.data.releases, 'vsinstrumentsbase').find(
      (version) => !own.includes(version)
    );
    expect(otherOnly).toBeDefined();
    const notFound = await request.post('/api/v1alpha1/mods', {
      headers: HEADERS,
      data: { slug: 'instruments', version: otherOnly },
    });
    expect(notFound.status()).toBe(404);
    expect(((await notFound.json()) as { detail: { code: string } }).detail.code).toBe(
      'MOD_VERSION_NOT_FOUND'
    );

    const canjewelry = await probeLookup(request, 'canjewelry');
    const own2 = canjewelry.data.releases.filter((r) => r.modidstr === 'canjewelry');
    const noFile = versionsOf(own2, 'canjewelry').find((version) =>
      own2.filter((r) => r.version === version).every((r) => !hasFile(r))
    );
    test.skip(noFile === undefined, 'canjewelry no longer lists a release without a file');
    const refused = await request.post('/api/v1alpha1/mods', {
      headers: HEADERS,
      data: { slug: 'canjewelry', version: noFile },
    });
    expect(refused.status()).toBe(422);
    expect(((await refused.json()) as { detail: { code: string } }).detail.code).toBe(
      'MOD_RELEASE_NOT_DOWNLOADABLE'
    );

    const after = await installedSlugs(request);
    // Only this spec's mods: another spec running in parallel may install its own
    expect(after.filter((slug) => TOUCHED.includes(slug) && !before.includes(slug))).toEqual([]);
  });

  test('a plain install of carryon installs its newest stable release', async ({ request }) => {
    test.setTimeout(120_000);
    test.skip(before.includes('carryon'), 'carryon is already installed on this stack');

    const body = await probeLookup(request, 'carryon');
    const latest = expectedDefault(body.data.releases, 'carryon');
    const response = await request.post('/api/v1alpha1/mods', {
      headers: HEADERS,
      data: { slug: 'carryon' },
      timeout: 60_000,
    });
    expect(response.status()).toBe(200);
    const installed = (await response.json()) as { data: { slug: string; version: string } };
    expect(installed.data.slug).toBe('carryon');
    expect(installed.data.version).toBe(latest);
    expect(await installedSlugs(request)).toContain('carryon');

    const removed = await request.delete('/api/v1alpha1/mods/carryon', { headers: HEADERS });
    expect(removed.ok()).toBe(true);
  });
});
