import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { test, expect, type Page } from '@playwright/test';
import { serveConfigKey } from './config-js';

/**
 * E2E tests for editing a config file in the file browser (Story 23.5, FR319, FR320).
 *
 * The saving test writes a file of its own into the stack's data with `docker exec`, edits
 * and saves it through the page, checks it through the API, and removes it. It changes the
 * stack's data, so it runs only in the throwaway container of `just test-e2e-ci`
 * (scripts/e2e-ci.sh exports E2E_CONTAINER), whose game server is not installed (the
 * editor treats that as stopped), and skips, with the reason, on any other stack (Epic 23
 * ADR-9 decision 3). It never touches a file it did not create.
 *
 * Requirements:
 * - `just test-e2e-ci e2e/config-file-editor.spec.ts`
 */

const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const THROWAWAY_CONTAINER = 'vintagestory-manager-e2e'; // scripts/e2e-ci.sh CONTAINER
const SERVERDATA = '/data/serverdata'; // VS_DATA_DIR=/data in scripts/e2e-ci.sh
const NOT_THROWAWAY =
  'writes a config file with docker exec, so it runs only in the throwaway container of ' +
  `just test-e2e-ci (E2E_CONTAINER=${THROWAWAY_CONTAINER})`;

const ORIGINAL = '{\n  // How often flowers bloom\n  "BloomChance": 0.5,\n}\n';
const EDITED = '{\n  // How often flowers bloom\n  "BloomChance": 0.75,\n}\n';

declare global {
  interface Window {
    __editorCspViolations: string[];
  }
}

function dockerExec(args: string[], input?: string) {
  const interactive = input === undefined ? [] : ['-i'];
  // stdout ignored: `tee` would echo the file into the test output
  execFileSync('docker', ['exec', ...interactive, THROWAWAY_CONTAINER, ...args], {
    input,
    stdio: ['pipe', 'ignore', 'inherit'],
  });
}

async function openFile(page: Page, name: string) {
  await page.goto('/config');
  await page.getByTestId('file-manager-tab').click();
  await expect(page.getByTestId('file-manager-panel')).toBeVisible({ timeout: 30000 });
  await page.getByTestId('file-item-ModConfig').click();
  await expect(page.getByTestId('path-breadcrumb-current')).toHaveText('ModConfig');
  await page.getByTestId(`file-item-${name}`).click();
}

test.describe('Config file editor (Story 23.5)', () => {
  test('an Admin key edits and saves a config file, comments kept', async ({ page, request }) => {
    test.skip(process.env.E2E_CONTAINER !== THROWAWAY_CONTAINER, NOT_THROWAWAY);
    const name = `e2e-edit-${randomUUID().slice(0, 8)}.json`;
    const file = `${SERVERDATA}/ModConfig/${name}`;
    dockerExec(['mkdir', '-p', `${SERVERDATA}/ModConfig`]);
    dockerExec(['tee', file], ORIGINAL);

    try {
      await page.addInitScript(() => {
        window.__editorCspViolations = [];
        document.addEventListener('securitypolicyviolation', (event) => {
          window.__editorCspViolations.push(event.effectiveDirective);
        });
      });
      await serveConfigKey(page, ADMIN_KEY);
      await openFile(page, name);

      // The read-only view shows the comment (FR320)
      const view = page.getByTestId('file-viewer-code');
      await expect(view).toContainText('// How often flowers bloom');

      await page.getByTestId('file-viewer-edit').click();
      const editor = page.getByTestId('config-editor-text').locator('.cm-content');
      await expect(editor).toBeVisible();
      await expect(page.getByTestId('config-editor-status')).toHaveText('Valid');

      await editor.click();
      await page.keyboard.press('ControlOrMeta+A');
      await page.keyboard.insertText(EDITED);
      await expect(page.getByTestId('config-editor-status')).toHaveText('Valid');
      await expect(page.getByTestId('config-editor-save')).toBeEnabled();
      await page.getByTestId('config-editor-save').click();

      await expect(page.getByText(`Saved ModConfig/${name}`)).toBeVisible();
      await expect(page.getByTestId('file-viewer-code')).toContainText('0.75');

      const read = await request.get(`/api/v1alpha1/config/files/ModConfig/${name}`, {
        headers: { 'X-API-Key': ADMIN_KEY },
      });
      expect(read.ok()).toBe(true);
      const body: { data: { text: string; content: unknown } } = await read.json();
      expect(body.data.text).toBe(EDITED);
      expect(body.data.content).toEqual({ BloomChance: 0.75 });

      expect(await page.evaluate(() => window.__editorCspViolations)).toEqual([]);
    } finally {
      dockerExec(['rm', '-f', file]);
    }
  });

  test('a Monitor key (stubbed role) has no Edit button', async ({ page }) => {
    await serveConfigKey(page, ADMIN_KEY);
    await page.route('**/api/v1alpha1/auth/me', (route) =>
      route.fulfill({ json: { status: 'ok', data: { role: 'monitor' } } })
    );
    await page.goto('/config');
    await page.getByTestId('file-manager-tab').click();
    await expect(page.getByTestId('file-list')).toBeVisible({ timeout: 30000 });
    await page.getByTestId('file-item-serverconfig.json').click();

    await expect(page.getByTestId('file-viewer')).toBeVisible();
    await expect(page.getByTestId('file-viewer-edit')).toHaveCount(0);
  });
});
