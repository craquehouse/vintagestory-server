import { test, expect, type APIRequestContext, type Page } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for settings that behave as saved.
 *
 * Story 17.6 (FR187, FR188; VSS-8bl, VSS-2le):
 * - A boolean game setting with no value shows the game's default ("Enabled (default)")
 *   or "Not set", never a plain "Disabled". The game settings are stubbed: nothing is
 *   written to the server's config.
 * - A changed refresh interval reschedules its job without an API restart, and the
 *   Scheduled Jobs tab shows the new schedule at once. This changes the real
 *   `mod_list_refresh_interval` and restores it (snapshot guard). Expected residue:
 *   the restored mod_cache_refresh job's next run is one interval after the restore,
 *   not the time it had before the run (an API restart would do the same).
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:8080), rebuilt from this
 *   branch: `just docker restart`, then
 *   `cd web && bunx playwright test e2e/settings-as-saved.spec.ts`
 *   with VS_API_KEY_ADMIN exported. The game server is neither started nor stopped.
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const HEADERS = { 'X-API-Key': API_KEY };

const INTERVAL_KEY = 'mod_list_refresh_interval';
const JOB_ID = 'mod_cache_refresh';

interface JobInfo {
  id: string;
  next_run_time: string | null;
  trigger_details: string;
}

async function usePageKey(page: Page): Promise<void> {
  // The Scheduled Jobs tab and the API settings exist only for an Admin key
  await serveConfigKey(page, API_KEY);
  await pretendServerInstalled(page);
  await page.setViewportSize({ width: 1440, height: 900 });
}

async function apiInterval(request: APIRequestContext): Promise<number> {
  const response = await request.get('/api/v1alpha1/config/api', { headers: HEADERS });
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as { data: { settings: Record<string, unknown> } };
  const value = body.data.settings[INTERVAL_KEY];
  if (typeof value !== 'number') throw new Error(`${INTERVAL_KEY} is not a number`);
  return value;
}

async function jobs(request: APIRequestContext): Promise<Map<string, JobInfo>> {
  const response = await request.get('/api/v1alpha1/jobs', { headers: HEADERS });
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as { data: { jobs: JobInfo[] } };
  return new Map(body.data.jobs.map((job) => [job.id, job]));
}

async function saveInterval(request: APIRequestContext, value: number): Promise<void> {
  const response = await request.post(`/api/v1alpha1/config/api/settings/${INTERVAL_KEY}`, {
    headers: HEADERS,
    data: { value },
  });
  expect(response.status(), `POST ${INTERVAL_KEY} ${value}`).toBe(200);
}

/** The Scheduled Jobs tab's text for an interval (JobsTable formatSchedule). */
function scheduleText(seconds: number): string {
  if (seconds >= 3600) return `every ${Math.round(seconds / 3600)}h`;
  if (seconds >= 60) return `every ${Math.round(seconds / 60)}m`;
  return `every ${seconds}s`;
}

test.describe('Boolean game settings with no value (Story 17.6)', () => {
  test.beforeEach(async ({ page }) => {
    await usePageKey(page);
  });

  test('show the default or "Not set", and the plain state once saved', async ({ page }) => {
    let entitySpawning: boolean | null = null;

    // Nothing under /config/game is written for real
    await page.route('**/api/v1alpha1/config/game/**', (route) =>
      route.fulfill({ status: 500, json: { detail: { code: 'E2E', message: 'stubbed' } } })
    );
    await page.route('**/api/v1alpha1/config/game/settings/EntitySpawning', async (route) => {
      if (route.request().method() !== 'POST') return route.fallback();
      entitySpawning = false;
      await route.fulfill({
        json: {
          status: 'ok',
          data: {
            key: 'EntitySpawning',
            value: false,
            method: 'file_update',
            pending_restart: false,
          },
        },
      });
    });
    await page.route('**/api/v1alpha1/config/game', async (route) => {
      if (route.request().method() !== 'GET') return route.fallback();
      const response = await route.fetch();
      const body = (await response.json()) as {
        data: { settings: Array<Record<string, unknown>> };
      };
      body.data.settings = body.data.settings.map((setting) => {
        if (setting.key === 'EntitySpawning') {
          return { ...setting, value: entitySpawning, default: true };
        }
        if (setting.key === 'AllowFireSpread') {
          // The API sends no default for it
          return { ...setting, value: null };
        }
        return setting;
      });
      await route.fulfill({ response, json: body });
    });

    await page.goto('/game-server/settings');
    await expect(page.getByTestId('game-config-panel')).toBeVisible({ timeout: 30000 });

    const entityState = page.getByTestId('setting-state-EntitySpawning');
    await expect(entityState).toHaveText('Enabled (default)');
    await expect(page.getByRole('switch', { name: 'Entity Spawning' })).toBeChecked();
    await expect(page.getByTestId('setting-state-AllowFireSpread')).toHaveText('Not set');
    await expect(page.getByRole('switch', { name: 'Allow Fire Spread' })).not.toBeChecked();

    await page.getByRole('switch', { name: 'Entity Spawning' }).click();

    await expect(entityState).toHaveText('Disabled');
    await expect(page.getByRole('switch', { name: 'Entity Spawning' })).not.toBeChecked();
  });
});

test.describe('A changed refresh interval applies at once: real API (Story 17.6)', () => {
  test.describe.configure({ mode: 'serial' });

  let snapshotInterval = 0;
  let snapshotJob: JobInfo | undefined;
  // Restoring must never run without a snapshot: it would overwrite the stack's value
  let hasSnapshot = false;

  test.beforeAll(async ({ playwright, baseURL }) => {
    const request = await playwright.request.newContext({ baseURL });
    try {
      snapshotInterval = await apiInterval(request);
      snapshotJob = (await jobs(request)).get(JOB_ID);
      hasSnapshot = true;
    } finally {
      await request.dispose();
    }
  });

  test.afterAll(async ({ playwright, baseURL }) => {
    if (!hasSnapshot) {
      throw new Error(`No snapshot of ${INTERVAL_KEY}; refusing to restore`);
    }
    const request = await playwright.request.newContext({ baseURL });
    try {
      if ((await apiInterval(request)) !== snapshotInterval) {
        await saveInterval(request, snapshotInterval);
      }
      expect(await apiInterval(request)).toBe(snapshotInterval);
    } finally {
      await request.dispose();
    }
  });

  test.beforeEach(async ({ page }) => {
    await usePageKey(page);
  });

  test('the Scheduled Jobs tab shows a saved interval without a reload', async ({
    page,
    request,
  }) => {
    test.skip(snapshotInterval === 0, `${INTERVAL_KEY} is 0 on this stack; see the API test`);
    const target = snapshotInterval === 7200 ? 10800 : 7200;

    await page.goto('/config');
    // Open Scheduled Jobs first, so its data is cached before the change
    await page.getByTestId('scheduled-jobs-tab').click();
    const schedule = page.getByTestId(`job-schedule-${JOB_ID}`);
    const nextRun = page.getByTestId(`job-next-run-${JOB_ID}`);
    await expect(schedule).toHaveText(scheduleText(snapshotInterval), { timeout: 30000 });
    const nextRunBefore = await nextRun.textContent();

    await page.getByTestId('api-settings-tab').click();
    const input = page.getByLabel('Mod List Refresh', { exact: true });
    await input.fill(`${target / 3600}h`);
    await input.blur();
    await expect(page.getByText(`${INTERVAL_KEY} updated`)).toBeVisible({ timeout: 15000 });

    // Within the 30 s poll and stale time: only the invalidation can show it
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(schedule).toHaveText(scheduleText(target), { timeout: 5000 });
    await expect(nextRun).not.toHaveText(nextRunBefore ?? '', { timeout: 5000 });

    const job = (await jobs(request)).get(JOB_ID);
    expect(job?.trigger_details).toBe(`every ${target} seconds`);
  });

  test('0 removes the job and the old value brings it back', async ({ request }) => {
    if (snapshotInterval === 0) {
      // Transitions from 0: a value above 0 registers the job, 0 removes it again
      expect((await jobs(request)).has(JOB_ID)).toBe(false);
      await saveInterval(request, 7200);
      expect((await jobs(request)).get(JOB_ID)?.trigger_details).toBe('every 7200 seconds');
      await saveInterval(request, 0);
      expect((await jobs(request)).has(JOB_ID)).toBe(false);
      return;
    }

    await saveInterval(request, 0);
    expect((await jobs(request)).has(JOB_ID)).toBe(false);

    await saveInterval(request, snapshotInterval);
    const restored = (await jobs(request)).get(JOB_ID);
    expect(restored?.trigger_details).toBe(snapshotJob?.trigger_details);
    expect(restored?.trigger_details).toBe(`every ${snapshotInterval} seconds`);
  });
});
