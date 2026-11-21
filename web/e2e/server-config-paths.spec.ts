import { test, expect } from '@playwright/test';

/**
 * E2E test for the serverconfig.json path check (Story 25.1, FR346, FR347, Epic 25 ADR-2).
 *
 * Reads only. On any stack, a game-written or seeded serverconfig.json has no path problem
 * and lists the manager's mods folder. In the throwaway container of `just test-e2e-ci`
 * (no game installed, never started) the statuses are the fresh-install ones: the game's
 * own `Mods` is `not_installed` and the default save is `not_created_yet`.
 *
 * Requirements:
 * - `just test-e2e-ci e2e/server-config-paths.spec.ts`
 */

const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const MONITOR_KEY = process.env.VS_API_KEY_MONITOR || '';
const THROWAWAY_CONTAINER = 'vintagestory-manager-e2e'; // scripts/e2e-ci.sh CONTAINER

interface PathEntry {
  given: string | null;
  resolved: string | null;
  status: string;
  problem: boolean;
}

interface PathCheck {
  mod_paths: PathEntry[];
  save_file: PathEntry;
  manager_mods_folder_listed: boolean;
}

test('the path check finds no problem and lists the manager mods folder', async ({ request }) => {
  const response = await request.get('/api/v1alpha1/config/game/paths', {
    headers: { 'X-API-Key': ADMIN_KEY },
  });
  expect(response.status(), await response.text()).toBe(200);
  expect(response.headers()['cache-control']).toBe('no-store');
  const check = ((await response.json()) as { data: PathCheck }).data;

  expect(check.manager_mods_folder_listed).toBe(true);
  for (const entry of [...check.mod_paths, check.save_file]) {
    expect(entry.problem, JSON.stringify(entry)).toBe(false);
  }

  if (process.env.E2E_CONTAINER === THROWAWAY_CONTAINER) {
    expect(check.mod_paths[0]).toMatchObject({
      given: 'Mods',
      resolved: '/data/server/Mods',
      status: 'not_installed',
    });
    expect(check.save_file).toMatchObject({
      given: null,
      resolved: '/data/serverdata/Saves/default.vcdbs',
      status: 'not_created_yet',
    });
  }
});

test('a Monitor key reads the path check too', async ({ request }) => {
  test.skip(MONITOR_KEY === '', 'no Monitor key configured on this stack');
  const response = await request.get('/api/v1alpha1/config/game/paths', {
    headers: { 'X-API-Key': MONITOR_KEY },
  });
  expect(response.status(), await response.text()).toBe(200);
});
