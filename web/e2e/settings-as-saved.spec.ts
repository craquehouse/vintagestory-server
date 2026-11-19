import { test, expect, type APIRequestContext, type Locator, type Page } from '@playwright/test';
import { fetchOnNewConnection, pretendServerInstalled, serveConfigKey } from './config-js';

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
 * Story 22.5 (FR300-FR303; VSS-9jv):
 * - The On switch turns Mod List Refresh off and on again from the API Settings tab:
 *   off saves 0 and the job leaves Scheduled Jobs; on restores the value the page showed
 *   before (also after another tab was opened), and after a reload the API default (4h).
 *   This writes the real `mod_list_refresh_interval`, inside the serial describe whose
 *   snapshot and restore guard it; the residue is the one above (the restored job's next
 *   run is one interval after the restore).
 * - Read-only: the Metrics Collection field and its help text, the refresh bounds (every
 *   settings POST is stubbed to fail the test), the switch's 44px tap target at 390px, and
 *   the API Settings tab for each role. The Monitor check needs VS_API_KEY_MONITOR and
 *   is skipped, with the reason, when it is not set (`just test-e2e-ci` sets it).
 *
 * Story 22.6 (FR304, FR305):
 * - Scheduled Restarts: add two restart times, have a third refused (10 minutes from
 *   another, nothing sent), and remove them again, with the API value and the
 *   scheduled_restart_* jobs checked at each step. Backup Cleanup: save a Backups kept
 *   value, have 1001 refused, and save the old value back. At 320px nothing scrolls
 *   sideways and Add time, a time input and its Remove button are at least 44px tall.
 *   This writes the real `scheduled_restart_times` and `backup_keep_count`, inside a serial
 *   describe whose snapshot and restore guard them. The times are picked 6 and 12 hours
 *   from now in the container's time (read from the disk_cleanup job's offset), so no
 *   restart job can fire during the run. Residue: none (both values are restored exactly,
 *   and the restored restart jobs have the same ids and times).
 *
 * Requirements:
 * - Docker stack on E2E_BASE_URL (default http://localhost:9080), rebuilt from this
 *   branch: `just docker restart`, then
 *   `cd web && bunx playwright test e2e/settings-as-saved.spec.ts`
 *   with VS_API_KEY_ADMIN exported (and VS_API_KEY_MONITOR for the Monitor check). Or
 *   `just test-e2e-ci e2e/settings-as-saved.spec.ts`, on a throwaway container. The game
 *   server is neither started nor stopped.
 */

// API keys from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const MONITOR_KEY = process.env.VS_API_KEY_MONITOR || '';
const HEADERS = { 'X-API-Key': API_KEY };

const INTERVAL_KEY = 'mod_list_refresh_interval';
const SETTINGS_POST = '**/api/v1alpha1/config/api/settings/**';
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

async function apiInterval(
  request: APIRequestContext,
  key: string = INTERVAL_KEY
): Promise<number> {
  const response = await request.get('/api/v1alpha1/config/api', { headers: HEADERS });
  expect(response.ok()).toBe(true);
  const body = (await response.json()) as { data: { settings: Record<string, unknown> } };
  const value = body.data.settings[key];
  if (typeof value !== 'number') throw new Error(`${key} is not a number`);
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
      const response = await fetchOnNewConnection(route);
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

  // Story 22.5 (AC 1, 2, 11): runs last, when the API value is the snapshot again
  test('the On switch turns Mod List Refresh off and on again', async ({ page, request }) => {
    const toggle = page.getByRole('switch', { name: 'Mod List Refresh On' });
    const input = page.getByLabel('Mod List Refresh', { exact: true });
    const off = page.getByTestId(`${INTERVAL_KEY}-off`);
    const schedule = page.getByTestId(`job-schedule-${JOB_ID}`);

    await page.goto('/config');
    // Open Scheduled Jobs first, so its data is cached before the change
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(page.getByTestId('scheduled-jobs-panel')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('api-settings-tab').click();
    await expect(toggle).toBeVisible({ timeout: 30000 });

    if (snapshotInterval === 0) {
      // Off on load: on saves the API default, off, then on restores it (remembered)
      await expect(toggle).not.toBeChecked();
      await toggle.click();
      await expect.poll(() => apiInterval(request)).toBe(14400);
      await expect(input).toHaveValue('4h');
      await toggle.click();
      await expect.poll(() => apiInterval(request)).toBe(0);
      await expect(off).toHaveText('Off');
      await toggle.click();
      await expect.poll(() => apiInterval(request)).toBe(14400);
      return;
    }

    await expect(toggle).toBeChecked();
    const shownBefore = await input.inputValue();

    // Off: 0 is saved, one toast, "Off" in place of the input, the job is gone
    await toggle.click();
    await expect(off).toHaveText('Off');
    await expect(input).toHaveCount(0);
    // Only this save's toast: an earlier test's may still be showing
    await expect(
      page.locator('[data-sonner-toast]', { hasText: `${INTERVAL_KEY} updated` })
    ).toHaveCount(1);
    await expect.poll(() => apiInterval(request)).toBe(0);
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(schedule).toHaveCount(0, { timeout: 5000 });

    // On, after another tab unmounted the panel: the value shown before comes back
    await page.getByTestId('api-settings-tab').click();
    await expect(toggle).not.toBeChecked();
    await toggle.click();
    await expect(input).toHaveValue(shownBefore);
    await expect.poll(() => apiInterval(request)).toBe(snapshotInterval);
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(schedule).toHaveText(scheduleText(snapshotInterval), { timeout: 5000 });

    // Off again, then a reload: still Off, and on saves the API default
    await page.getByTestId('api-settings-tab').click();
    await toggle.click();
    await expect(off).toHaveText('Off');
    await expect.poll(() => apiInterval(request)).toBe(0);
    await page.reload();
    await page.getByTestId('api-settings-tab').click();
    await expect(off).toHaveText('Off', { timeout: 30000 });
    await expect(toggle).not.toBeChecked();
    await toggle.click();
    await expect(input).toHaveValue('4h');
    await expect.poll(() => apiInterval(request)).toBe(14400);
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(schedule).toHaveText('every 4h', { timeout: 5000 });
    // afterAll restores the snapshot
  });
});

// Story 22.5: read-only checks; nothing is saved
test.describe('API Settings tab (Story 22.5)', () => {
  test.beforeEach(async ({ page }) => {
    await usePageKey(page);
  });

  test('Metrics Collection is shown and the refresh bounds refuse values', async ({
    page,
    request,
  }) => {
    test.skip(
      (await apiInterval(request, 'server_versions_refresh_interval')) === 0,
      'server_versions_refresh_interval is 0 on this stack (no input to type into)'
    );
    const posts: string[] = [];
    await page.route(SETTINGS_POST, async (route) => {
      posts.push(route.request().url());
      await route.fulfill({ status: 500, json: { detail: { code: 'E2E', message: 'stubbed' } } });
    });

    await openApiSettings(page);

    await expect(page.getByLabel('Metrics Collection', { exact: true })).toBeVisible();
    await expect(page.getByRole('switch', { name: 'Metrics Collection On' })).toBeVisible();
    await expect(
      page.getByText(/charts and its memory and players cards stop updating/)
    ).toBeVisible();
    await expect(page.getByText(/\/metrics is read live and keeps working/)).toBeVisible();

    // Not Mod List Refresh: the serial describe may have it Off at this moment
    const input = page.getByLabel('Server Versions Refresh', { exact: true });
    await input.fill('400d');
    await input.blur();
    await expect(page.getByText('Must be at most 365d')).toBeVisible();
    await input.fill('30s');
    await input.blur();
    await expect(page.getByText('Must be at least 1m')).toBeVisible();

    expect(posts).toEqual([]);
  });

  test('the switch has a 44px tap target at 390px and nothing scrolls sideways', async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await openApiSettings(page);

    const target = page.getByTestId(`${INTERVAL_KEY}-switch-target`);
    const box = await target.boundingBox();
    expect(box, 'tap target').not.toBeNull();
    expect(box?.height ?? 0).toBeGreaterThanOrEqual(44);
    // Below the fold on a phone: scrolled to, it is wholly inside the viewport (not cut off
    // at the side)
    const toggle = page.getByRole('switch', { name: 'Mod List Refresh On' });
    await toggle.scrollIntoViewIfNeeded();
    await expect(toggle).toBeInViewport({ ratio: 1 });
    const overflow = await page.evaluate(
      () => document.documentElement.scrollWidth - window.innerWidth
    );
    expect(overflow).toBeLessThanOrEqual(0);
  });
});

async function openApiSettings(page: Page): Promise<void> {
  await page.goto('/config');
  await page.getByTestId('api-settings-tab').click();
  await expect(page.getByTestId('api-settings-panel')).toBeVisible({ timeout: 30000 });
}

// Story 22.5 (AC 7, Epic 22 ADR-12): only an Admin key can read the API settings
test.describe('API Settings tab for each role (Story 22.5)', () => {
  test('an Admin sees the API Settings tab, which opens its panel', async ({ page }) => {
    await usePageKey(page);
    await openApiSettings(page);
  });

  test('a Monitor never sees the API Settings tab or requests its data', async ({ page }) => {
    test.skip(!MONITOR_KEY, 'VS_API_KEY_MONITOR is not set for this stack');
    await serveConfigKey(page, MONITOR_KEY);
    await pretendServerInstalled(page);
    await page.setViewportSize({ width: 1440, height: 900 });
    const apiSettingsRequests: string[] = [];
    page.on('request', (req) => {
      if (new URL(req.url()).pathname.endsWith('/api/v1alpha1/config/api')) {
        apiSettingsRequests.push(req.url());
      }
    });

    for (const path of ['/config', '/config?tab=api-settings']) {
      const authMe = page.waitForResponse((res) => res.url().includes('/api/v1alpha1/auth/me'));
      await page.goto(path);
      const role: { data: { role: string } } = await (await authMe).json();
      expect(role.data.role, 'the Monitor key').toBe('monitor');

      await expect(page.getByTestId('ui-preferences-tab')).toHaveAttribute('aria-selected', 'true');
      await expect(page.getByTestId('file-manager-tab')).toBeVisible();
      await expect(page.getByTestId('api-settings-tab')).toHaveCount(0);
      await expect(page.getByTestId('scheduled-jobs-tab')).toHaveCount(0);
      await expect(page.getByText('Failed to load settings')).not.toBeVisible();
    }

    expect(apiSettingsRequests).toEqual([]);
  });
});

// Story 22.6 (FR304, FR305): writes the real restart times and backup limit, restored after
test.describe('Restart times and the backup limit: real API (Story 22.6)', () => {
  test.describe.configure({ mode: 'serial' });

  const RESTART_KEY = 'scheduled_restart_times';
  const BACKUP_KEY = 'backup_keep_count';
  const RESTART_POST = `**/api/v1alpha1/config/api/settings/${RESTART_KEY}`;
  const BACKUP_POST = `**/api/v1alpha1/config/api/settings/${BACKUP_KEY}`;
  const RESTART_JOB_PREFIX = 'scheduled_restart_';

  let snapshotTimes: string[] = [];
  let snapshotKeepCount = 0;
  let snapshotJobIds: string[] = [];
  // Restoring must never run without a snapshot: it would overwrite the stack's values
  let hasSnapshot = false;

  function isRecord(value: unknown): value is Record<string, unknown> {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
  }

  async function apiSettings(request: APIRequestContext): Promise<Record<string, unknown>> {
    const response = await request.get('/api/v1alpha1/config/api', { headers: HEADERS });
    expect(response.ok()).toBe(true);
    const body: unknown = await response.json();
    if (!isRecord(body) || !isRecord(body.data) || !isRecord(body.data.settings)) {
      throw new Error('GET /config/api has no data.settings');
    }
    return body.data.settings;
  }

  async function apiRestartTimes(request: APIRequestContext): Promise<string[]> {
    const value = (await apiSettings(request))[RESTART_KEY];
    if (!Array.isArray(value) || !value.every((t): t is string => typeof t === 'string')) {
      throw new Error(`${RESTART_KEY} is not a list of strings`);
    }
    return value;
  }

  async function apiKeepCount(request: APIRequestContext): Promise<number> {
    const value = (await apiSettings(request))[BACKUP_KEY];
    if (typeof value !== 'number') throw new Error(`${BACKUP_KEY} is not a number`);
    return value;
  }

  async function restartJobIds(request: APIRequestContext): Promise<string[]> {
    return [...(await jobs(request)).keys()]
      .filter((id) => id.startsWith(RESTART_JOB_PREFIX))
      .sort();
  }

  async function save(request: APIRequestContext, key: string, value: unknown): Promise<void> {
    const response = await request.post(`/api/v1alpha1/config/api/settings/${key}`, {
      headers: HEADERS,
      data: { value },
    });
    expect(response.status(), `POST ${key}`).toBe(200);
  }

  function minutesOf(time: string): number {
    const [hours, minutes] = time.split(':');
    return Number(hours) * 60 + Number(minutes);
  }

  function hhmm(totalMinutes: number): string {
    const m = ((totalMinutes % 1440) + 1440) % 1440;
    return `${String(Math.floor(m / 60)).padStart(2, '0')}:${String(m % 60).padStart(2, '0')}`;
  }

  /** Minutes between two times of day, the shorter way round. */
  function apart(a: number, b: number): number {
    const d = (((a - b) % 1440) + 1440) % 1440;
    return Math.min(d, 1440 - d);
  }

  /**
   * Restart times far from now in the container's time: its UTC offset comes from the
   * disk_cleanup job's next run (`Z` when the container is on UTC, else +HH:MM / -HH:MM).
   */
  async function farTimes(request: APIRequestContext) {
    const cleanup = (await jobs(request)).get('disk_cleanup');
    if (!cleanup?.next_run_time) {
      throw new Error('disk_cleanup is not listed; cannot learn the container time zone');
    }
    const offset = /(Z|([+-])(\d{2}):(\d{2}))$/.exec(cleanup.next_run_time);
    if (!offset) throw new Error(`No UTC offset in ${cleanup.next_run_time}`);
    const offsetMinutes =
      offset[1] === 'Z'
        ? 0
        : (offset[2] === '-' ? -1 : 1) * (Number(offset[3]) * 60 + Number(offset[4]));
    const now = new Date(Date.now() + offsetMinutes * 60_000);
    const nowMinutes = now.getUTCHours() * 60 + now.getUTCMinutes();
    const quarter = (minutes: number) => Math.floor((minutes % 1440) / 15) * 15;
    const h1 = quarter(nowMinutes + 6 * 60);
    const h2 = quarter(nowMinutes + 12 * 60);
    for (const time of [h1, h2]) {
      // A restart job fires 15 minutes before its time: keep both well clear of the run
      const ahead = (((time - nowMinutes) % 1440) + 1440) % 1440;
      expect(ahead, `${hhmm(time)} is at least 2 hours ahead`).toBeGreaterThanOrEqual(120);
      for (const saved of snapshotTimes) {
        expect(apart(time, minutesOf(saved)), `${hhmm(time)} vs ${saved}`).toBeGreaterThanOrEqual(
          16
        );
      }
    }
    return { h1: hhmm(h1), h2: hhmm(h2), tooClose: hhmm(h1 + 10) };
  }

  async function countPosts(page: Page, pattern: string): Promise<{ count: () => number }> {
    let posts = 0;
    await page.route(pattern, async (route) => {
      if (route.request().method() === 'POST') posts += 1;
      await route.fallback();
    });
    return { count: () => posts };
  }

  test.beforeAll(async ({ playwright, baseURL }) => {
    const request = await playwright.request.newContext({ baseURL });
    try {
      snapshotTimes = await apiRestartTimes(request);
      snapshotKeepCount = await apiKeepCount(request);
      snapshotJobIds = await restartJobIds(request);
      hasSnapshot = true;
    } finally {
      await request.dispose();
    }
  });

  test.afterAll(async ({ playwright, baseURL }) => {
    if (!hasSnapshot) {
      throw new Error(`No snapshot of ${RESTART_KEY} and ${BACKUP_KEY}; refusing to restore`);
    }
    const request = await playwright.request.newContext({ baseURL });
    try {
      if ((await apiRestartTimes(request)).join(',') !== snapshotTimes.join(',')) {
        await save(request, RESTART_KEY, snapshotTimes);
      }
      if ((await apiKeepCount(request)) !== snapshotKeepCount) {
        await save(request, BACKUP_KEY, snapshotKeepCount);
      }
      expect(await apiRestartTimes(request)).toEqual(snapshotTimes);
      expect(await apiKeepCount(request)).toBe(snapshotKeepCount);
      expect(await restartJobIds(request)).toEqual(snapshotJobIds);
    } finally {
      await request.dispose();
    }
  });

  test.beforeEach(async ({ page }) => {
    await usePageKey(page);
  });

  test('restart times are added, refused and removed', async ({ page, request }) => {
    const { h1, h2, tooClose } = await farTimes(request);
    const jobName = (time: string) =>
      page.getByTestId(`job-name-${RESTART_JOB_PREFIX}${time.replace(':', '')}`);
    const timeInput = (n: number) => page.getByLabel(`Restart time ${n}`, { exact: true });
    const addTime = page.getByTestId('add-restart-time');
    // Only this save's toast: an earlier test's may still be showing
    const restartToasts = page.locator('[data-sonner-toast]', {
      hasText: `${RESTART_KEY} updated`,
    });

    await page.goto('/config');
    // Open Scheduled Jobs first, so its data is cached before the change
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(page.getByTestId('scheduled-jobs-panel')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('api-settings-tab').click();
    await expect(addTime).toBeVisible({ timeout: 30000 });

    // Add H1: one save, one toast, its job listed
    await addTime.click();
    let n = snapshotTimes.length + 1;
    await expect(timeInput(n)).toBeFocused();
    await timeInput(n).fill(h1);
    await timeInput(n).press('Enter');
    await expect(restartToasts).toHaveCount(1);
    const withH1 = [...snapshotTimes, h1].sort();
    await expect.poll(() => apiRestartTimes(request)).toEqual(withH1);
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(jobName(h1)).toBeVisible({ timeout: 5000 });

    // Add H2: the rows are shown sorted
    await page.getByTestId('api-settings-tab').click();
    await expect(addTime).toBeEnabled();
    await addTime.click();
    n += 1;
    await timeInput(n).fill(h2);
    await timeInput(n).press('Enter');
    const withBoth = [...snapshotTimes, h1, h2].sort();
    await expect.poll(() => apiRestartTimes(request)).toEqual(withBoth);
    for (const [i, time] of withBoth.entries()) {
      await expect(timeInput(i + 1)).toHaveValue(time);
    }

    // A third time 10 minutes from H1 is refused before sending
    const restartPosts = await countPosts(page, RESTART_POST);
    await expect(addTime).toBeEnabled();
    await addTime.click();
    n += 1;
    await timeInput(n).fill(tooClose);
    await timeInput(n).press('Enter');
    await expect(page.getByRole('alert')).toContainText('are 10 minutes apart');
    await expect(timeInput(n)).toHaveAttribute('aria-invalid', 'true');
    expect(restartPosts.count()).toBe(0);

    // Removing it sends nothing; removing H2, then H1, brings back the snapshot
    await page.getByRole('button', { name: `Remove restart time ${tooClose}` }).click();
    await expect(page.getByRole('alert')).toHaveCount(0);
    expect(restartPosts.count()).toBe(0);
    await page.getByRole('button', { name: `Remove restart time ${h2}` }).click();
    await expect.poll(() => apiRestartTimes(request)).toEqual(withH1);
    await expect(addTime).toBeEnabled();
    await page.getByRole('button', { name: `Remove restart time ${h1}` }).click();
    await expect.poll(() => apiRestartTimes(request)).toEqual(snapshotTimes);
    expect(restartPosts.count()).toBe(2);
    await expect.poll(() => restartJobIds(request)).toEqual(snapshotJobIds);
    await page.getByTestId('scheduled-jobs-tab').click();
    await expect(page.getByTestId('scheduled-jobs-panel')).toBeVisible();
    await expect(jobName(h1)).toHaveCount(0, { timeout: 5000 });
    await expect(jobName(h2)).toHaveCount(0);
  });

  test('Backups kept is saved, refused out of bounds, and saved back', async ({
    page,
    request,
  }) => {
    const target = snapshotKeepCount === 3 ? 4 : 3;
    await openApiSettings(page);
    const input = page.getByLabel('Backups kept', { exact: true });
    await expect(input).toHaveValue(String(snapshotKeepCount));

    await input.fill(String(target));
    await input.blur();
    // Only this save's toast: an earlier test's may still be showing
    await expect(
      page.locator('[data-sonner-toast]', { hasText: `${BACKUP_KEY} updated` })
    ).toHaveCount(1);
    await expect.poll(() => apiKeepCount(request)).toBe(target);

    const backupPosts = await countPosts(page, BACKUP_POST);
    await input.fill('1001');
    await input.blur();
    await expect(page.getByText('Must be between 0 and 1000')).toBeVisible();
    expect(backupPosts.count()).toBe(0);
    expect(await apiKeepCount(request)).toBe(target);

    await input.fill(String(snapshotKeepCount));
    await input.blur();
    await expect.poll(() => apiKeepCount(request)).toBe(snapshotKeepCount);
    expect(backupPosts.count()).toBe(1);
  });

  test('at 320px the new controls are 44px tall and nothing scrolls sideways', async ({ page }) => {
    const restartPosts = await countPosts(page, RESTART_POST);
    await page.setViewportSize({ width: 320, height: 640 });
    await openApiSettings(page);
    const overflow = () =>
      page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
    expect(await overflow()).toBeLessThanOrEqual(0);

    const addTime = page.getByTestId('add-restart-time');
    await addTime.scrollIntoViewIfNeeded();
    const tall = async (name: string, locator: Locator) => {
      await locator.scrollIntoViewIfNeeded();
      const box = await locator.boundingBox();
      expect(box, name).not.toBeNull();
      expect(box?.height ?? 0, name).toBeGreaterThanOrEqual(44);
    };
    await tall('Add time', addTime);

    await addTime.click();
    const n = snapshotTimes.length + 1;
    await tall('the new time input', page.getByTestId(`restart-time-${n}`));
    await tall('its Remove button', page.getByTestId(`remove-restart-time-${n}`));
    expect(await overflow()).toBeLessThanOrEqual(0);

    // Empty, so removing it saves nothing
    await page.getByTestId(`remove-restart-time-${n}`).click();
    await expect(page.getByTestId(`restart-time-${n}`)).toHaveCount(0);
    expect(restartPosts.count()).toBe(0);

    await page.setViewportSize({ width: 1440, height: 900 });
    expect(await overflow()).toBeLessThanOrEqual(0);
  });
});
