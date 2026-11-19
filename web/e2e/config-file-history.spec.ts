import { execFileSync } from 'node:child_process';
import { createHash, randomUUID } from 'node:crypto';
import { test, expect, type APIRequestContext } from '@playwright/test';
import { serveConfigKey } from './config-js';

/**
 * E2E test for config file history (Story 23.7, FR324): compare an earlier version with
 * the file and restore it.
 *
 * It writes a file of its own into the stack's data with `docker exec` and saves it twice
 * through the API, so it runs only in the throwaway container of `just test-e2e-ci`
 * (scripts/e2e-ci.sh exports E2E_CONTAINER; its game server is not installed, which counts
 * as stopped) and skips, with the reason, on any other stack (Epic 23 ADR-9 decision 3).
 * The file is removed afterwards; its history stays in the throwaway container's state.
 *
 * Requirements:
 * - `just test-e2e-ci e2e/config-file-history.spec.ts`
 */

const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const THROWAWAY_CONTAINER = 'vintagestory-manager-e2e'; // scripts/e2e-ci.sh CONTAINER
const SERVERDATA = '/data/serverdata'; // VS_DATA_DIR=/data in scripts/e2e-ci.sh
const NOT_THROWAWAY =
  'writes a config file with docker exec, so it runs only in the throwaway container of ' +
  `just test-e2e-ci (E2E_CONTAINER=${THROWAWAY_CONTAINER})`;

const FIRST = '{\n  // first\n  "Value": 1,\n}\n';
const SECOND = '{\n  // second\n  "Value": 2,\n}\n';
const THIRD = '{\n  // third\n  "Value": 3,\n}\n';

function dockerExec(args: string[], input?: string) {
  const interactive = input === undefined ? [] : ['-i'];
  // stdout ignored: `tee` would echo the file into the test output
  execFileSync('docker', ['exec', ...interactive, THROWAWAY_CONTAINER, ...args], {
    input,
    stdio: ['pipe', 'ignore', 'inherit'],
  });
}

const sha256 = (text: string) => createHash('sha256').update(text).digest('hex');

async function save(request: APIRequestContext, name: string, from: string, to: string) {
  const response = await request.put(`/api/v1alpha1/config/files/ModConfig/${name}`, {
    headers: { 'X-API-Key': ADMIN_KEY },
    data: { text: to, version: sha256(from) },
  });
  expect(response.status(), await response.text()).toBe(200);
}

test('an Admin key compares an earlier version and restores it', async ({ page, request }) => {
  test.skip(process.env.E2E_CONTAINER !== THROWAWAY_CONTAINER, NOT_THROWAWAY);
  const name = `e2e-history-${randomUUID().slice(0, 8)}.json`;
  const file = `${SERVERDATA}/ModConfig/${name}`;
  dockerExec(['mkdir', '-p', `${SERVERDATA}/ModConfig`]);
  dockerExec(['tee', file], FIRST);

  try {
    await save(request, name, FIRST, SECOND);
    await save(request, name, SECOND, THIRD);

    await serveConfigKey(page, ADMIN_KEY);
    await page.goto('/config');
    await page.getByTestId('file-manager-tab').click();
    await expect(page.getByTestId('file-manager-panel')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('file-item-ModConfig').click();
    await page.getByTestId(`file-item-${name}`).click();
    await expect(page.getByTestId('file-viewer-code')).toContainText('// third');

    await page.getByTestId('file-viewer-history').click();
    const items = page.getByTestId('config-history-list').getByRole('button');
    await expect(items).toHaveCount(2);
    await items.last().click();

    // The oldest kept version (FIRST) beside the file now (THIRD)
    const compare = page.getByTestId('config-history-compare');
    await expect(compare).toContainText('// first');
    await expect(compare).toContainText('// third');

    await page.getByTestId('config-history-restore').click();
    await page
      .getByTestId('config-history-restore-dialog')
      .getByRole('button', { name: 'Restore' })
      .click();
    await expect(page.getByText(`Restored ModConfig/${name}`)).toBeVisible();
    await expect(page.getByTestId('file-viewer-code')).toContainText('// first');

    const read = await request.get(`/api/v1alpha1/config/files/ModConfig/${name}`, {
      headers: { 'X-API-Key': ADMIN_KEY },
    });
    const body: { data: { text: string } } = await read.json();
    expect(body.data.text).toBe(FIRST);
  } finally {
    dockerExec(['rm', '-f', file]);
  }
});
