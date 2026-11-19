import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E tests.
 *
 * Tests run against a Docker stack that serves the full application (API and web UI).
 * The stack may have no game server installed.
 * - `just test-e2e-web`: every spec against the dev stack on port 9080 (DOCKER_PORT).
 * - `just test-e2e-ci`: the untagged specs against a throwaway container seeded with
 *   e2e/fixtures/serverconfig.json and no game server, then the `@moddb` specs on recorded
 *   mod database answers (e2e/fixtures/moddb/) against a second one (what CI runs; see
 *   e2e/README.md).
 *
 * Environment variables:
 * - E2E_BASE_URL: Override base URL (default: http://localhost:9080)
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  // In CI the list reporter also names each failing test in the job log
  reporter: process.env.CI ? [['list'], ['html']] : 'html',
  timeout: 30000,

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:9080',
    trace: 'on-first-retry',
  },

  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],

  /* Docker stack is managed by `just test-e2e-web`, not by Playwright */
});
