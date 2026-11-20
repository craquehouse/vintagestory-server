import { execFileSync } from 'node:child_process';
import { randomUUID } from 'node:crypto';
import { test, expect } from '@playwright/test';
import { pretendServerInstalled, serveConfigKey } from './config-js';

/**
 * E2E tests for Rescan and unused files on the Installed tab (Story 24.6, FR336, FR339).
 *
 * Each test writes files of its own into the stack's mods folder with `docker exec`, so it
 * runs only in the throwaway container of `just test-e2e-ci` (scripts/e2e-ci.sh exports
 * E2E_CONTAINER), and skips, with the reason, on any other stack (Epic 24 ADR-8). The
 * container has no game server, so the page is told one is installed. A test never
 * touches a file it did not create, and removes what it created.
 *
 * Requirements:
 * - `just test-e2e-ci e2e/mods-rescan-and-unused-files.spec.ts`
 */

const ADMIN_KEY = process.env.VS_API_KEY_ADMIN || 'changeme';
const THROWAWAY_CONTAINER = 'vintagestory-manager-e2e'; // scripts/e2e-ci.sh CONTAINER
const MODS_DIR = '/data/serverdata/Mods'; // VS_DATA_DIR=/data in scripts/e2e-ci.sh
const NOT_THROWAWAY =
  'writes into the mods folder with docker exec, so it runs only in the throwaway container ' +
  `of just test-e2e-ci (E2E_CONTAINER=${THROWAWAY_CONTAINER})`;

function dockerExec(args: string[]): string {
  return execFileSync('docker', ['exec', THROWAWAY_CONTAINER, ...args], {
    encoding: 'utf8',
    stdio: ['ignore', 'pipe', 'inherit'],
  });
}

/** Write a mod archive with the given modinfo.json, as a hand copy would put it. */
function writeModArchive(path: string, modid: string) {
  const modinfo = JSON.stringify({ modid, name: `E2E ${modid}`, version: '1.0.0' });
  dockerExec([
    'python3',
    '-c',
    'import sys, zipfile\n' +
      "with zipfile.ZipFile(sys.argv[1], 'w') as z: z.writestr('modinfo.json', sys.argv[2])",
    path,
    modinfo,
  ]);
}

test.describe('Rescan and unused files (Story 24.6)', () => {
  test.beforeEach(async ({ page }) => {
    test.skip(process.env.E2E_CONTAINER !== THROWAWAY_CONTAINER, NOT_THROWAWAY);
    dockerExec(['mkdir', '-p', MODS_DIR]);
    await serveConfigKey(page, ADMIN_KEY);
    await pretendServerInstalled(page);
  });

  test('Rescan lists a mod copied into the mods folder by hand', async ({ page, request }) => {
    const modid = `e2erescan${randomUUID().slice(0, 8)}`;
    writeModArchive(`${MODS_DIR}/${modid}_1.0.0.zip`, modid);

    try {
      await page.goto('/game-server/mods/installed');
      await expect(page.getByTestId('installed-tab-content')).toBeVisible({ timeout: 30000 });
      await expect(page.getByText(`E2E ${modid}`)).toHaveCount(0);

      await page.getByTestId('mods-rescan').click();

      await expect(page.getByText(`E2E ${modid}`).first()).toBeVisible();
      await expect(page.getByText('Rescanned the mods folder')).toBeVisible();
    } finally {
      // Through the API, so the entry and the file both go
      const removed = await request.delete(`/api/v1alpha1/mods/${modid}`, {
        headers: { 'X-API-Key': ADMIN_KEY },
      });
      expect(removed.ok(), `removing ${modid} through the API`).toBeTruthy();
      dockerExec(['rm', '-f', `${MODS_DIR}/${modid}_1.0.0.zip`]);
    }
  });

  test('an unused file is listed and deleted after confirming', async ({ page }) => {
    const name = `e2e-${randomUUID().slice(0, 8)}.tmp`;
    dockerExec(['touch', `${MODS_DIR}/${name}`]);

    try {
      await page.goto('/game-server/mods/installed');
      const notice = page.getByTestId('unused-files-notice');
      await expect(notice).toBeVisible({ timeout: 30000 });
      await page.getByTestId('unused-files-toggle').click();
      await expect(page.getByTestId(`unused-file-${name}`)).toContainText(
        'Leftover temporary or backup file'
      );

      await page.getByTestId(`unused-file-delete-${name}`).click();
      await expect(page.getByTestId('unused-file-delete-dialog')).toContainText(`Delete ${name}?`);
      await page.getByTestId('unused-file-delete-confirm').click();

      await expect(page.getByTestId(`unused-file-${name}`)).toHaveCount(0);
      expect(dockerExec(['ls', MODS_DIR]).split('\n')).not.toContain(name);
    } finally {
      dockerExec(['rm', '-f', `${MODS_DIR}/${name}`]);
    }
  });
});
