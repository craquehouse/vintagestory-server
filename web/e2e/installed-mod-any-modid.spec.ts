import { test, expect, type Page } from '@playwright/test';

/**
 * E2E tests for recognizing an installed mod by any mod ID of its mod database entry.
 *
 * Story 16.2 (FR169, VSS-ywb): the Instruments entry ships three mod IDs
 * (`instruments`, `vsinstruments`, `vsinstrumentsbase`) and its browse slug is
 * `instruments`. When another of its mod IDs is installed, the detail page must show
 * the installed state and that mod ID's releases, not the install flow.
 *
 * The installed mods list is replaced with `page.route`, so the spec installs nothing;
 * the mod lookup comes from the live mod database (fetched once per test and served
 * to the page from that one response where the test compares against it).
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080): `just test-e2e-web`,
 *   or `just docker restart` then
 *   `cd web && bunx playwright test e2e/installed-mod-any-modid.spec.ts`
 * - Network access to the public mod database.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const DETAIL = '/game-server/mods/browse/instruments';

interface LiveRelease {
  version: string;
  modidstr: string;
}

/** Replace the installed mods list (only `GET /api/v1alpha1/mods`) with the given mods. */
async function fakeInstalledMods(page: Page, mods: Array<{ slug: string; version: string }>) {
  await page.route(/\/api\/v1alpha1\/mods(\?.*)?$/, async (route) => {
    if (route.request().method() !== 'GET') {
      await route.continue();
      return;
    }
    await route.fulfill({
      json: {
        status: 'ok',
        data: {
          mods: mods.map(({ slug, version }) => ({
            filename: `${slug}_${version}.zip`,
            slug,
            version,
            enabled: true,
            installed_at: '2026-11-13T00:00:00Z',
            asset_id: 0,
            name: slug,
            authors: [],
            description: null,
            side: 'Both',
          })),
          pending_restart: false,
        },
      },
    });
  });
}

/** Open the detail page and return the live releases from its lookup response. */
async function openDetail(page: Page): Promise<LiveRelease[]> {
  const lookup = page.waitForResponse(
    (response) => response.url().includes('/mods/lookup/instruments') && response.ok()
  );
  await page.goto(DETAIL);
  const body = (await (await lookup).json()) as { data: { releases: LiveRelease[] } };
  await expect(page.getByTestId('mod-detail-page')).toBeVisible({ timeout: 60_000 });
  return body.data.releases;
}

/** Distinct versions of one mod ID, newest first, as the version list shows them. */
function versionsOf(releases: LiveRelease[], modId: string): string[] {
  return [...new Set(releases.filter((r) => r.modidstr === modId).map((r) => r.version))];
}

async function versionOptionTestIds(page: Page): Promise<string[]> {
  await page.getByTestId('mod-detail-version-select').click();
  const options = page.getByRole('option');
  await expect(options.first()).toBeVisible();
  return options.evaluateAll((elements) =>
    elements.map((element) => element.getAttribute('data-testid') ?? '')
  );
}

test.describe('Installed mod recognized by any mod ID (Story 16.2)', () => {
  test.beforeEach(async ({ page }) => {
    await page.addInitScript((apiKey) => {
      localStorage.setItem('apiKey', apiKey);
    }, API_KEY);
  });

  for (const modId of ['vsinstrumentsbase', 'vsinstruments']) {
    test(`shows the installed state for ${modId} on the instruments entry`, async ({ page }) => {
      // The version is not known before the lookup; any version of the mod ID works
      // for recognition, so install the one the live lookup lists first.
      const probe = await page.request.get(`/api/v1alpha1/mods/lookup/instruments`, {
        headers: { 'X-API-Key': API_KEY },
      });
      expect(probe.ok()).toBe(true);
      const probeBody = (await probe.json()) as { data: { releases: LiveRelease[] } };
      const own = versionsOf(probeBody.data.releases, modId);
      expect(own.length).toBeGreaterThan(0);

      // Serve the page the same lookup response, so a release published between the
      // probe and the page load cannot make the two disagree.
      await page.route(/\/api\/v1alpha1\/mods\/lookup\/instruments(\?.*)?$/, (route) =>
        route.fulfill({ json: probeBody })
      );
      await fakeInstalledMods(page, [{ slug: modId, version: own[0] }]);
      const releases = await openDetail(page);

      await expect(page.getByTestId('mod-detail-installed-indicator')).toHaveText(
        `Installed: v${own[0]}`
      );
      await expect(page.getByTestId('mod-detail-install-button')).toHaveCount(0);
      expect(await versionOptionTestIds(page)).toEqual(
        versionsOf(releases, modId).map((version) => `mod-detail-version-option-${version}`)
      );
    });
  }

  test('shows the install flow when no mod ID of the entry is installed', async ({ page }) => {
    await fakeInstalledMods(page, []);
    await openDetail(page);

    await expect(page.getByTestId('mod-detail-install-button')).toBeVisible();
    await expect(page.getByTestId('mod-detail-installed-indicator')).toHaveCount(0);
  });
});
