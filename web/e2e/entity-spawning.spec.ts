import { test, expect } from '@playwright/test';

/**
 * E2E test for Entity Spawning from the running game (Story 25.3, FR349, FR350, Epic 25
 * ADR-5).
 *
 * Reads only: it never starts, stops or changes anything. While the stack's game server
 * runs, Entity Spawning comes from the game (`source: game`, a bool). While it is stopped,
 * it is the last value the game reported or not known yet. The CI stack has no game server,
 * so the test is tagged and runs with `just test-e2e-web` against a stack with one.
 *
 * Requirements:
 * - `just test-e2e-web e2e/entity-spawning.spec.ts`
 */

const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

interface GameSetting {
  key: string;
  value: unknown;
  source?: string;
  observed_at?: string;
}

// @game-server: needs a game server process that has answered the manager's query
test('Entity Spawning comes from the game server', { tag: '@game-server' }, async ({ request }) => {
  const headers = { 'X-API-Key': ADMIN_KEY };
  const status = await request.get('/api/v1alpha1/server/status', { headers });
  expect(status.status()).toBe(200);
  const state = ((await status.json()) as { data: { state: string } }).data.state;

  const response = await request.get('/api/v1alpha1/config/game', { headers });
  expect(response.status(), await response.text()).toBe(200);
  const settings = ((await response.json()) as { data: { settings: GameSetting[] } }).data.settings;
  const spawning = settings.find((setting) => setting.key === 'EntitySpawning');
  expect(spawning).toBeDefined();
  expect(spawning).not.toHaveProperty('default');

  if (state === 'running') {
    // The query is sent when the game logs that it is ready; allow it a moment
    await expect
      .poll(
        async () => {
          const again = await request.get('/api/v1alpha1/config/game', { headers });
          const all = ((await again.json()) as { data: { settings: GameSetting[] } }).data.settings;
          return all.find((setting) => setting.key === 'EntitySpawning')?.source;
        },
        { timeout: 60_000 }
      )
      .toBe('game');
  } else {
    expect(['last_seen', 'unknown']).toContain(spawning?.source);
    if (spawning?.source === 'unknown') {
      expect(spawning.value).toBeNull();
    } else {
      expect(typeof spawning?.value).toBe('boolean');
    }
  }
});
