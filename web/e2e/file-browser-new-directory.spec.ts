import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { test, expect, type Page } from '@playwright/test';
import { serveConfigKey } from './config-js';

/**
 * E2E test: a directory that appears while the File Manager is open (Settings → File
 * Manager) is listed after the page is loaded again (VSS-3mr).
 *
 * The directory is created from outside the page with `docker exec`, the way a game server
 * would write one. That changes the stack's data, so the test runs only in the throwaway
 * container of `just test-e2e-ci` (scripts/e2e-ci.sh exports E2E_CONTAINER) and skips, with
 * the reason, on any other stack. The container and the directory are removed with it.
 *
 * Requirements:
 * - `just test-e2e-ci`, which seeds `Logs` under serverdata (SEEDED_DIR in scripts/e2e-ci.sh)
 */

// API key from environment or default from docker-compose.dev.yaml
const API_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';

const THROWAWAY_CONTAINER = 'vintagestory-manager-e2e'; // scripts/e2e-ci.sh CONTAINER, pinned by test-e2e-ci.sh
const SERVERDATA = '/data/serverdata'; // VS_DATA_DIR=/data in scripts/e2e-ci.sh
const PARENT = 'Logs'; // seeded by scripts/e2e-ci.sh
const NOT_THROWAWAY =
  'creates a directory with docker exec, so it runs only in the throwaway container of ' +
  `just test-e2e-ci (E2E_CONTAINER=${THROWAWAY_CONTAINER})`;

const current = (page: Page) => page.getByTestId('path-breadcrumb-current');

/** Opens the File Manager tab and the PARENT directory in it. */
async function openParent(page: Page) {
  await page.getByTestId('file-manager-tab').click();
  await expect(page.getByTestId('file-manager-panel')).toBeVisible({ timeout: 30000 });
  await page.getByTestId(`file-item-${PARENT}`).click();
  await expect(current(page)).toHaveText(PARENT);
  await expect(page.getByTestId('file-list')).toBeVisible();
}

test('a directory created while the file manager is open is listed after a reload', async ({
  page,
}) => {
  test.skip(process.env.E2E_CONTAINER !== THROWAWAY_CONTAINER, NOT_THROWAWAY);
  // Lower case, so the API's sorted listing keeps the seeded Archive first (the navigation
  // spec's path), and unique per attempt, so a retry creates its own
  const name = `e2e-new-${randomUUID().slice(0, 8)}`;

  await serveConfigKey(page, API_KEY);
  await page.goto('/config');
  await openParent(page);
  await expect(page.getByTestId(`file-item-${name}`)).toHaveCount(0);

  // An argument array, no shell; without -p, so the parent must be the seeded one
  execFileSync('docker', ['exec', THROWAWAY_CONTAINER, 'mkdir', `${SERVERDATA}/${PARENT}/${name}`]);

  // The panel keeps its directory in component state, so open it again after the reload
  await page.reload();
  await openParent(page);
  await page.getByTestId(`file-item-${name}`).click();

  await expect(current(page)).toHaveText(name);
  await expect(page.getByTestId('file-list-empty')).toBeVisible();
});
