import { defineConfig, devices } from '@playwright/test';

/**
 * Playwright configuration for E2E tests.
 *
 * Tests run against the Docker stack which serves the full application on port 8080.
 * Use `just test-e2e-web` to run tests - it handles Docker orchestration automatically.
 *
 * The Docker stack includes:
 * - API server (FastAPI)
 * - Web UI (built and served by API)
 * - Game server (VintageStory)
 *
 * Environment variables:
 * - E2E_BASE_URL: Override base URL (default: http://localhost:8080)
 */
export default defineConfig({
  testDir: './e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: 'html',
  timeout: 30000,

  use: {
    baseURL: process.env.E2E_BASE_URL || 'http://localhost:8080',
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
